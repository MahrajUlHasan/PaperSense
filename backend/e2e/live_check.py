"""Live end-to-end check against a running backend (not part of the unit tests).

    uv run python e2e/live_check.py [--api http://localhost:8000] [--pdf path] [--keep]

Uploads a paper into a throwaway workspace, waits until it is processed, then checks search,
an answer with citations and page boxes, the PDF and figure endpoints and workspace isolation,
and finally deletes the paper again. The Gemini key is read from PAPERSENSE_GEMINI_KEY; without
it the server's own key is used (ALLOW_SERVER_KEY=true). The key is never printed.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import httpx

BACKEND = Path(__file__).resolve().parents[1]
DEFAULT_PDF = BACKEND / "rag_eval" / "evals" / "datasets" / "test_paper.pdf"
WORKSPACE = "e2e-workspace-0001"


class Checks:
    def __init__(self):
        self.failed = 0

    def __call__(self, ok: bool, label: str, detail: str = "") -> bool:
        print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail and not ok else ""))
        self.failed += not ok
        return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Live end-to-end check of the PaperSense API.")
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--keep", action="store_true", help="don't delete the uploaded paper")
    parser.add_argument("--timeout", type=int, default=900, help="seconds to wait for processing")
    args = parser.parse_args()

    headers = {"X-Workspace-Id": WORKSPACE, "X-Session-Id": "e2e-session-0001"}
    key = os.environ.get("PAPERSENSE_GEMINI_KEY", "").strip()
    if key:
        headers["X-LLM-Key"] = key
    check = Checks()
    client = httpx.Client(base_url=args.api, headers=headers, timeout=120)

    try:
        health = client.get("/health").json()
    except httpx.HTTPError as err:
        print(f"Can't reach {args.api}: {err}")
        return 1
    check(health.get("status") == "ok", "server is up")

    with args.pdf.open("rb") as f:
        r = client.post("/documents", files={"file": (args.pdf.name, f, "application/pdf")})
    if not check(r.status_code == 202, "upload accepted", r.text[:200]):
        return 1
    doc = r.json()
    doc_id = doc["id"]

    deadline = time.monotonic() + args.timeout
    while doc["status"] not in ("ready", "error") and time.monotonic() < deadline:
        time.sleep(5)
        doc = client.get(f"/documents/{doc_id}").json()
        print(f"      {doc['status']}: {doc.get('progress')}")
    stats = doc.get("stats") or {}
    check(doc["status"] == "ready", "paper processed", doc.get("error") or "timed out")
    check(stats.get("chunks", 0) > 0, "chunks were indexed", str(stats))
    check(stats.get("coverage", 0) >= 0.9, "text coverage is at least 90%", str(stats.get("coverage")))

    if doc["status"] == "ready":
        hits = client.post("/search", json={"query": "Which optimizer was used?", "document_ids": [doc_id], "top_k": 3})
        hits = hits.json().get("hits", [])
        check(bool(hits) and all(h["boxes"] for h in hits), "search returns hits with page boxes")

        r = client.post("/query", json={"question": "Which optimizer was used for training?", "document_ids": [doc_id]})
        if check(r.status_code == 200, "question answered", r.text[:200]):
            body = r.json()
            citations = body["citations"]
            check(bool(citations), "the answer has citations")
            check(all(c["page"] for c in citations) and any(c["boxes"] for c in citations), "citations have pages and boxes")
            check(all(f"[{c['index']}]" in body["answer"] for c in citations), "every citation is used in the answer")

        r = client.get(f"/documents/{doc_id}/file", params={"ws": WORKSPACE})
        check(r.status_code == 200 and r.content.startswith(b"%PDF"), "the PDF endpoint returns the file")
        if stats.get("figures"):
            r = client.get(f"/documents/{doc_id}/figures/1", params={"ws": WORKSPACE})
            check(r.status_code == 200 and r.headers["content-type"] == "image/png", "the figure endpoint returns a PNG")

    other = client.get(f"/documents/{doc_id}", headers={"X-Workspace-Id": "e2e-other-0001"})
    check(other.status_code == 404, "another workspace can't see the paper")

    if not args.keep:
        check(client.delete(f"/documents/{doc_id}").status_code == 200, "paper deleted")

    print("\nAll checks passed." if not check.failed else f"\n{check.failed} check(s) failed.")
    return 1 if check.failed else 0


if __name__ == "__main__":
    sys.exit(main())
