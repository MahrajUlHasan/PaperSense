"""RAGAS evaluation of PaperSense v2: dense vs hybrid retrieval on "Attention Is All You Need".

Run from the backend folder:

    uv run --group eval python rag_eval/evals.py

Steps:
1. Ingest evals/datasets/test_paper.pdf with the v2 pipeline into the evaluation workspace
   (reused on later runs; --reingest does it again) and report the ingestion metrics.
2. Answer every question in evals/datasets/eval_dataset.csv with dense and with hybrid retrieval.
3. Score each answer with RAGAS (faithfulness, answer relevancy, context precision, context
   recall) using a free judge (see judge.py).
4. Write the results to evals/experiments/ (see write_outputs) and compare them with v1.

Answers use gemini-3.5-flash-lite by default: the app's default gemini-3.5-flash has a free
quota of about 20 requests a day, too few for a run. The judge is gemini-3.1-flash-lite, which
has a daily quota of its own (about 500 requests; a full run needs about 440). With
--judge-provider mistral it is mistral-medium-latest (needs MISTRAL_API_KEY and a Mistral plan
that allows that model).

Progress is saved after every question, so running the command again continues where it
stopped (for example after a daily quota ran out); --fresh starts over. Switching the judge
re-scores the saved answers without generating them again. Keys are read from backend/.env
(SERVER_GEMINI_API_KEY, MISTRAL_API_KEY) and are never printed.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import os
import sys
import time
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from rag_adapter import PaperSenseRAGAdapter  # noqa: E402
from ragas.metrics.collections import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness  # noqa: E402

from config import settings  # noqa: E402
from judge import JUDGES, Judge, LocalEmbeddings  # noqa: E402
from pacing import QuotaExhausted  # noqa: E402
from services.llm import ProviderError  # noqa: E402
from services.logging_setup import setup_logging  # noqa: E402

DATASET = HERE / "evals" / "datasets" / "eval_dataset.csv"
PAPER = HERE / "evals" / "datasets" / "test_paper.pdf"
OUT = HERE / "evals" / "experiments"
STATE = OUT / "v2_run_state.json"
V1_RESULTS = OUT / "v1_results.csv"
V1_MODES = {"Dense Search": "dense", "Hybrid Search": "hybrid"}

MODES = ("dense", "hybrid")
METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
LABELS = ("faith", "relev", "prec", "recall")
TIMES = ("retrieval_seconds", "generation_seconds", "answer_seconds", "judge_seconds")
INGESTION_FIELDS = ("paper", "pages", "chunks", "tables", "figures", "figures_described", "formulas",
                    "formulas_decoded", "formulas_read", "coverage", "low_coverage_pages", "ocr_used",
                    "parse_seconds", "ingest_seconds")
FATAL_KINDS = ("invalid_key", "missing_key", "bad_request")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    parser.add_argument("--categories", nargs="+", help="only these question categories (text, formula, table, figure)")
    parser.add_argument("--limit", type=int, help="only the first N questions (quick check)")
    parser.add_argument("--answer-model", default=os.environ.get("EVAL_ANSWER_MODEL", "gemini-3.5-flash-lite"))
    parser.add_argument("--judge-provider", choices=list(JUDGES), default="gemini")
    parser.add_argument("--judge-model", help="default: mistral-medium-latest / gemini-3.1-flash-lite")
    parser.add_argument("--answer-rpm", type=int, default=8, help="answer requests per minute")
    parser.add_argument("--judge-rpm", type=int, help="judge requests per minute (default: 30 Mistral, 12 Gemini)")
    parser.add_argument("--fresh", action="store_true", help="ignore saved progress and start over")
    parser.add_argument("--reingest", action="store_true", help="ingest the paper again")
    args = parser.parse_args()
    args.judge_model = args.judge_model or JUDGES[args.judge_provider]["model"]
    args.judge_rpm = args.judge_rpm or JUDGES[args.judge_provider]["rpm"]
    return args


def load_dataset(categories: list[str] | None, limit: int | None) -> list[dict]:
    with DATASET.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if not categories or r["category"] in categories]
    return rows[:limit] if limit else rows


def load_state(fresh: bool) -> dict:
    if STATE.exists() and not fresh:
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"ingestion": {}, "results": {}}


def save_state(state: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE)


def prepare_paper(adapter: PaperSenseRAGAdapter, state: dict, reingest: bool) -> dict:
    """The ingested test paper and its ingestion metrics (E3), ingesting it if needed."""
    record = None if reingest else adapter.find_ready(PAPER.name)
    if record is None:
        adapter.remove(PAPER.name)
        print(f"Ingesting {PAPER.name} (takes a few minutes)...")
        record, seconds = adapter.ingest(PAPER)
        state["ingestion"] = {"document_id": record["id"], "ingest_seconds": round(seconds, 1)}
        save_state(state)
    adapter.document = record
    stats = record.get("stats") or {}
    known = state["ingestion"].get("document_id") == record["id"]
    return {
        "paper": PAPER.name,
        "pages": record.get("page_count"),
        **{k: stats.get(k) for k in INGESTION_FIELDS if k in stats},
        "low_coverage_pages": " ".join(map(str, stats.get("low_coverage_pages") or [])),
        "ingest_seconds": state["ingestion"].get("ingest_seconds") if known else None,
    }


def build_metrics(judge: Judge, embeddings: LocalEmbeddings) -> dict:
    return {
        "faithfulness": Faithfulness(llm=judge),
        "answer_relevancy": AnswerRelevancy(llm=judge, embeddings=embeddings),
        "context_precision": ContextPrecision(llm=judge),
        "context_recall": ContextRecall(llm=judge),
    }


async def score(metrics: dict, question: str, reference: str, answer: str, contexts: list[str]) -> tuple[dict, list[str]]:
    """All four metrics for one answer, run side by side. A failed metric is left empty."""
    jobs = {
        "faithfulness": metrics["faithfulness"].ascore(user_input=question, response=answer, retrieved_contexts=contexts),
        "answer_relevancy": metrics["answer_relevancy"].ascore(user_input=question, response=answer),
        "context_precision": metrics["context_precision"].ascore(user_input=question, reference=reference,
                                                                 retrieved_contexts=contexts),
        "context_recall": metrics["context_recall"].ascore(user_input=question, retrieved_contexts=contexts,
                                                           reference=reference),
    }
    outcomes = await asyncio.gather(*jobs.values(), return_exceptions=True)
    scores, errors = {}, []
    for name, outcome in zip(jobs, outcomes):
        if isinstance(outcome, QuotaExhausted):
            raise outcome
        if isinstance(outcome, ProviderError) and outcome.kind in FATAL_KINDS:
            raise outcome
        if isinstance(outcome, Exception):
            scores[name] = None
            errors.append(f"{name}: {type(outcome).__name__}: {str(outcome)[:200]}")
            continue
        value = float(getattr(outcome, "value", outcome))
        scores[name] = None if math.isnan(value) else round(value, 4)
    return scores, errors


def answer_is_current(entry: dict | None, row: dict, args: argparse.Namespace, document_id: str) -> bool:
    """A saved answer counts only if the question, the answer model and the ingested paper are unchanged."""
    return bool(entry) and all((
        entry["question"] == row["question"],
        entry["answer_model"] == args.answer_model,
        entry["document_id"] == document_id,
    ))


def scores_are_current(entry: dict, row: dict, args: argparse.Namespace) -> bool:
    """Saved scores count only if the reference answer and the judge are unchanged."""
    return entry["ground_truth"] == row["ground_truth"] and entry["judge_model"] == args.judge_model


def is_current(entry: dict | None, row: dict, args: argparse.Namespace, document_id: str) -> bool:
    return answer_is_current(entry, row, args, document_id) and scores_are_current(entry, row, args)


def run_question(adapter, metrics, state: dict, row: dict, mode: str, args) -> dict:
    """Answer and score one question, saving after each step so a stop loses little work.

    A saved answer whose scores are out of date (new judge or reference answer) is only re-scored.
    """
    key = f"{mode}|{row['id']}"
    entry = state["results"].get(key)
    if answer_is_current(entry, row, args, adapter.document["id"]) and not scores_are_current(entry, row, args):
        entry.update({m: None for m in METRICS}, ground_truth=row["ground_truth"],
                     judge_model=args.judge_model, judge_seconds=None, errors=[])
    if not answer_is_current(entry, row, args, adapter.document["id"]):
        answer = adapter.query(row["question"], use_hybrid=mode == "hybrid")
        entry = {
            "id": row["id"], "category": row["category"], "mode": mode,
            "question": row["question"], "ground_truth": row["ground_truth"],
            "answer_model": args.answer_model, "judge_model": args.judge_model,
            "document_id": adapter.document["id"],
            "answer": answer.text, "contexts": answer.contexts,
            "retrieval_seconds": round(answer.retrieval_seconds, 3),
            "generation_seconds": round(answer.generation_seconds, 3),
            "answer_seconds": round(answer.seconds, 3),
            **{m: None for m in METRICS}, "judge_seconds": None, "errors": [],
        }
        state["results"][key] = entry
        save_state(state)
    if any(entry[m] is None for m in METRICS):
        start = time.perf_counter()
        scores, errors = asyncio.run(score(metrics, row["question"], row["ground_truth"],
                                           entry["answer"], entry["contexts"]))
        entry.update(scores, errors=errors, judge_seconds=round(time.perf_counter() - start, 1))
        save_state(state)
    return entry


def avg(values) -> float | None:
    values = [v for v in values if v is not None]
    return round(mean(values), 4) if values else None


def summarize(entries: list[dict], modes: list[str]) -> list[dict]:
    """Averages per mode, overall and per question category, with the run time of each group."""
    rows = []
    for mode in modes:
        in_mode = [e for e in entries if e["mode"] == mode]
        groups = [("all", in_mode)] + [(c, [e for e in in_mode if e["category"] == c])
                                       for c in dict.fromkeys(e["category"] for e in in_mode)]
        for category, group in groups:
            if not group:
                continue
            answer_total = sum(e["answer_seconds"] or 0 for e in group)
            judge_total = sum(e["judge_seconds"] or 0 for e in group)
            rows.append({
                "mode": mode, "category": category, "questions": len(group),
                **{m: avg(e[m] for e in group) for m in METRICS},
                "avg_retrieval_seconds": avg(e["retrieval_seconds"] for e in group),
                "avg_generation_seconds": avg(e["generation_seconds"] for e in group),
                "avg_answer_seconds": avg(e["answer_seconds"] for e in group),
                "avg_judge_seconds": avg(e["judge_seconds"] for e in group),
                "total_answer_seconds": round(answer_total, 1),
                "total_judge_seconds": round(judge_total, 1),
                "total_run_seconds": round(answer_total + judge_total, 1),
                "answer_model": group[0]["answer_model"], "judge_model": group[0]["judge_model"],
            })
    return rows


def compare_with_v1(entries: list[dict]) -> list[dict]:
    """v1 vs v2 averages on the questions both runs share (the original ten)."""
    if not V1_RESULTS.exists():
        return []
    with V1_RESULTS.open(encoding="utf-8") as f:
        v1 = [r for r in csv.DictReader(f) if r["search_mode"] in V1_MODES]
    shared = {r["question"] for r in v1} & {e["question"] for e in entries}
    rows = []
    for v1_mode, mode in V1_MODES.items():
        old = [r for r in v1 if r["search_mode"] == v1_mode and r["question"] in shared]
        new = [e for e in entries if e["mode"] == mode and e["question"] in shared]
        if not old or not new:
            continue
        for metric in METRICS:
            before = avg(float(r[metric]) if r[metric] not in ("", "nan") else None for r in old)
            after = avg(e[metric] for e in new)
            change = round(after - before, 4) if before is not None and after is not None else None
            rows.append({"mode": mode, "metric": metric, "questions": len(new),
                         "v1": before, "v2": after, "change": change})
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(entries: list[dict], ingestion: dict, modes: list[str]) -> tuple[list[dict], list[dict]]:
    """v2_results.csv (one row per question and mode), v2_summary.csv, v2_ingestion.csv, v1_vs_v2.csv."""
    columns = ("id", "category", "mode", "question", "ground_truth", "answer", *METRICS, *TIMES)
    results = [{**{c: e.get(c) for c in columns}, "contexts": len(e["contexts"]),
                "errors": " | ".join(e["errors"])} for e in entries]
    summary = summarize(entries, modes)
    comparison = compare_with_v1(entries)
    write_csv(OUT / "v2_results.csv", results)
    write_csv(OUT / "v2_summary.csv", summary)
    write_csv(OUT / "v2_ingestion.csv", [ingestion])
    write_csv(OUT / "v1_vs_v2.csv", comparison)
    return summary, comparison


def fmt(value) -> str:
    return "  -  " if value is None else f"{value:.3f}"


def print_report(ingestion: dict, summary: list[dict], comparison: list[dict]) -> None:
    print("\n--- Ingestion ---")
    for key, value in ingestion.items():
        print(f"  {key:<20} {value}")
    print("\n--- Results ---")
    print(f"  {'mode':<7} {'category':<8} {'n':>3}  {'faith':>6} {'relev':>6} {'prec':>6} {'recall':>6}"
          f"  {'retr s':>6} {'gen s':>6} {'run s':>7}")
    for r in summary:
        print(f"  {r['mode']:<7} {r['category']:<8} {r['questions']:>3}  "
              + " ".join(f"{fmt(r[m]):>6}" for m in METRICS)
              + f"  {fmt(r['avg_retrieval_seconds']):>6} {fmt(r['avg_generation_seconds']):>6}"
              f" {r['total_run_seconds']:>7.0f}")
    if comparison:
        print("\n--- v1 vs v2 (the original ten questions) ---")
        for r in comparison:
            print(f"  {r['mode']:<7} {r['metric']:<18} v1 {fmt(r['v1'])}  v2 {fmt(r['v2'])}  change {fmt(r['change'])}")


def main() -> None:
    args = parse_args()
    setup_logging()
    key = (settings.server_gemini_api_key or os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        sys.exit("Set SERVER_GEMINI_API_KEY in backend/.env (or GEMINI_API_KEY) to run the evaluation.")

    rows = load_dataset(args.categories, args.limit)
    state = load_state(args.fresh)
    adapter = PaperSenseRAGAdapter(key, args.answer_model, args.answer_rpm)
    ingestion = prepare_paper(adapter, state, args.reingest)
    adapter.warm_up()
    judge_key = (settings.mistral_api_key or "").strip() if args.judge_provider == "mistral" else key
    if not judge_key:
        sys.exit("Set MISTRAL_API_KEY in backend/.env to use the Mistral judge.")
    judge = Judge(args.judge_provider, judge_key, args.judge_model, args.judge_rpm)
    metrics = build_metrics(judge, LocalEmbeddings(adapter.embedder))

    print(f"{len(rows)} questions x {len(args.modes)} modes | answers: {args.answer_model} | judge: {args.judge_model}")
    started, stopped = time.perf_counter(), None
    try:
        for mode in args.modes:
            for n, row in enumerate(rows, start=1):
                entry = run_question(adapter, metrics, state, row, mode, args)
                print(f"[{mode} {n}/{len(rows)}] {row['id']} "
                      + " ".join(f"{label}={fmt(entry[m])}" for label, m in zip(LABELS, METRICS))
                      + f" | answer {entry['answer_seconds']:.1f}s, judge {entry['judge_seconds'] or 0:.0f}s"
                      + (f" | {len(entry['errors'])} metric error(s)" if entry["errors"] else ""))
    except QuotaExhausted as err:
        stopped = str(err)

    by_id = {row["id"]: row for row in rows}
    order = [f"{mode}|{row['id']}" for mode in args.modes for row in rows]
    entries = [state["results"][k] for k in order if k in state["results"]
               and is_current(state["results"][k], by_id[k.split("|", 1)[1]], args, adapter.document["id"])]
    summary, comparison = write_outputs(entries, ingestion, args.modes)
    print_report(ingestion, summary, comparison)
    print(f"\nThis run took {time.perf_counter() - started:.0f}s, {judge.requests} judge request(s). "
          f"Results: {OUT}")
    if stopped:
        print(f"\nStopped early: {stopped}. Run the same command again after the quota resets "
              "(midnight Pacific time) to continue.")


if __name__ == "__main__":
    main()
