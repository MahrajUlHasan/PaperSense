# PaperSense v2 evaluation (RAGAS)

Measures how well PaperSense answers questions about *Attention Is All You Need*, with **dense** and with **hybrid** retrieval, using four RAGAS metrics:

| Metric | Question it answers |
|---|---|
| faithfulness | Is every claim in the answer supported by the retrieved passages? |
| answer_relevancy | Does the answer address the question? |
| context_precision | Are the relevant passages ranked near the top? |
| context_recall | Do the retrieved passages contain everything in the reference answer? |

## Run it

From the `backend` folder:

```powershell
uv run --group eval python rag_eval/evals.py
```

The eval uses the backend's own environment and `.env`. It needs `QDRANT_URL`, `QDRANT_API_KEY` and `SERVER_GEMINI_API_KEY`. No server has to be running.

What happens:
1. `evals/datasets/test_paper.pdf` is ingested with the v2 pipeline into its own workspace (`eval-workspace-0001`), so it never mixes with papers uploaded in the app. Later runs reuse it; `--reingest` processes it again.
2. Every question in `evals/datasets/eval_dataset.csv` is answered twice, once per retrieval mode. Each question starts a fresh chat.
3. A judge model scores every answer.
4. The results are written to `evals/experiments/`.

A full run (22 questions × 2 modes) takes about 40 minutes, mostly pauses that keep the judge inside its free per-minute limit.

### Options

| Option | Default | Meaning |
|---|---|---|
| `--modes dense hybrid` | both | Which retrieval modes to run |
| `--categories text formula table figure` | all | Only these question types |
| `--limit N` | all | Only the first N questions (quick check) |
| `--answer-model` | `gemini-3.5-flash-lite` | Model that writes the answers |
| `--judge-provider` | `gemini` | `gemini`, or `mistral` (needs `MISTRAL_API_KEY` and a plan that allows `mistral-medium-latest`) |
| `--judge-model` | `gemini-3.1-flash-lite` / `mistral-medium-latest` | Model that scores them |
| `--answer-rpm`, `--judge-rpm` | 8, 12 | Requests per minute for each |
| `--fresh` | off | Ignore saved progress and start over |
| `--reingest` | off | Ingest the paper again |

### Free quotas and resuming

Free Gemini-API quotas are per model and reset at midnight Pacific time:
- The app's answer model, `gemini-3.5-flash`, allows only about 20 requests a day, so the eval answers with `gemini-3.5-flash-lite` (about 500 a day). A run uses 44.
- The judge, `gemini-3.1-flash-lite`, has its own quota of about 500 a day. A run uses about 440: 10 per answer.

Progress is saved after every question in `evals/experiments/v2_run_state.json`. If a quota runs out, the run stops, writes what it has, and says so. Run the same command after the reset to continue. A saved result is redone only if its question, reference answer, models or ingested paper changed.

The free Gemma 4 models (`gemma-4-31b-it`, `gemma-4-26b-a4b-it`) have a much larger quota, but their endpoint was overloaded when this eval was set up. Try them with `--judge-model gemma-4-31b-it`.

## Dataset

`evals/datasets/eval_dataset.csv` has the columns `id, category, question, ground_truth`:

| Category | Questions | What it tests |
|---|---|---|
| text (`T01`–`T10`) | 10 | The original v1 questions with their v1 reference answers, so v1 and v2 can be compared |
| formula (`F01`–`F04`) | 4 | Attention, feed-forward, positional-encoding and learning-rate formulas |
| table (`B01`–`B04`) | 4 | Values from Tables 1–4 |
| figure (`G01`–`G04`) | 4 | What Figures 1–4 show |

## Output files (`evals/experiments/`)

| File | Contents |
|---|---|
| `v2_results.csv` | One row per question and mode: the answer, the four scores, the number of passages, any metric errors, and the run time of that question: `retrieval_seconds`, `generation_seconds`, `answer_seconds` (the two together) and `judge_seconds` |
| `v2_summary.csv` | Averages per mode, overall and per category, with average and total run times per group (`total_run_seconds` = answering + judging) |
| `v2_ingestion.csv` | Ingestion metrics: pages, chunks, tables, figures stored/described, formulas found/decoded, text coverage, low-coverage pages, parse and total ingestion seconds |
| `v1_vs_v2.csv` | v1 vs v2 averages per mode and metric on the ten shared questions |
| `v1_results.csv` | The v1 ("before") results, copied from the baseline backup |
| `v2_run_state.json` | Saved progress, including the retrieved passages of every answer |

Run times measure only the pipeline and the judge, not the pauses spent waiting for the free per-minute limit. The first retrieval of each mode is run once beforehand, so model loading isn't counted.

## Comparing with v1

Retrieval, chunking and parsing all changed between v1 and v2, and so did the models:

| | v1 | v2 |
|---|---|---|
| Answers | Gemini (paid preview model) | `gemini-3.5-flash-lite` (free) |
| Judge | OpenAI `gpt-4o` | `gemini-3.1-flash-lite` (free) |
| AnswerRelevancy embeddings | OpenAI `text-embedding-3-small` | local `BAAI/bge-base-en-v1.5` |

Differences in scores therefore reflect the whole system and the judge, not only retrieval. Mention this when presenting the comparison.
