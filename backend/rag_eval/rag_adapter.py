"""PaperSense v2 as the evaluation sees it: ingest a paper, then answer questions about it.

The backend services are used directly (no running server needed), in a workspace of
their own, so evaluation papers never mix with the papers uploaded in the app.
"""
from __future__ import annotations

import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from pacing import patient_call  # noqa: E402
from services.chunking import Chunker  # noqa: E402
from services.embeddings import EmbeddingService  # noqa: E402
from services.ingestion import IngestionService  # noqa: E402
from services.llm import LLMCredentials  # noqa: E402
from services.parsing import PDFParser  # noqa: E402
from services.pipeline import QueryPipeline  # noqa: E402
from services.qdrant_store import QdrantStore  # noqa: E402
from services.rate_limit import RateLimiter  # noqa: E402
from services.registry import DocumentRegistry  # noqa: E402
from services.storage import DocumentStorage  # noqa: E402

EVAL_WORKSPACE = "eval-workspace-0001"


@dataclass
class Answer:
    """An answer with the retrieved passages the model was given and how long each step took.

    The times cover only the pipeline itself, not the pauses that keep requests inside the
    free per-minute limit.
    """

    text: str
    contexts: list[str]
    retrieval_seconds: float
    generation_seconds: float

    @property
    def seconds(self) -> float:
        return self.retrieval_seconds + self.generation_seconds


class PaperSenseRAGAdapter:
    def __init__(self, gemini_key: str, answer_model: str, answer_rpm: int = 8,
                 workspace_id: str = EVAL_WORKSPACE):
        self.workspace_id = workspace_id
        self.answer_model = answer_model
        self._key = gemini_key
        self._creds = LLMCredentials("gemini", gemini_key, answer_model)
        self._limiter = RateLimiter(per_minute=answer_rpm)
        self.registry = DocumentRegistry()
        self.storage = DocumentStorage()
        self.embedder = EmbeddingService()
        self.store = QdrantStore(dense_dim=self.embedder.dimension)
        self.pipeline = QueryPipeline(embedder=self.embedder, store=self.store, storage=self.storage)
        self.document: dict | None = None
        self._last_retrieval = 0.0
        self._time_retrieval()

    def _time_retrieval(self) -> None:
        """Measure the retrieval step inside QueryPipeline.answer, so generation time can be told apart."""
        retrieve = self.pipeline.retrieve

        def timed(*args, **kwargs):
            start = time.perf_counter()
            try:
                return retrieve(*args, **kwargs)
            finally:
                self._last_retrieval = time.perf_counter() - start

        self.pipeline.retrieve = timed

    def find_ready(self, filename: str) -> dict | None:
        for doc in self.registry.list(self.workspace_id):
            if doc["filename"] == filename and doc["status"] == "ready" and self.store.count_document(doc["id"]):
                return doc
        return None

    def remove(self, filename: str) -> None:
        for doc in self.registry.list(self.workspace_id):
            if doc["filename"] == filename:
                self.store.delete_document(doc["id"])
                self.storage.delete(doc["id"])
                self.registry.delete(doc["id"])

    def ingest(self, pdf_path: Path) -> tuple[dict, float]:
        """Full v2 ingestion: parse, figures, Gemini figure descriptions, chunks, vectors.

        Returns the registry record and the wall-clock seconds it took.
        """
        ingestion = IngestionService(parser=PDFParser(), chunker=Chunker(), embedder=self.embedder,
                                     store=self.store, storage=self.storage, registry=self.registry)
        document_id = str(uuid.uuid4())
        self.storage.save_pdf(document_id, pdf_path.read_bytes())
        self.registry.create(document_id, self.workspace_id, pdf_path.name)
        start = time.perf_counter()
        try:
            ingestion.run(document_id, self.workspace_id, pdf_path.name, self._key)
        finally:
            ingestion.shutdown()
        seconds = time.perf_counter() - start
        record = self.registry.get(document_id)
        if record["status"] != "ready":
            raise RuntimeError(f"Ingestion failed: {record.get('error')}")
        return record, seconds

    def warm_up(self) -> None:
        """Load the BM25 and ColBERT models up front, so the first question isn't charged for it."""
        for use_hybrid in (False, True):
            self.pipeline.retrieve("warm up", self.workspace_id, [self.document["id"]], settings.top_k, use_hybrid)

    def query(self, question: str, use_hybrid: bool) -> Answer:
        """Answer one question with the v2 pipeline. Every question starts a fresh chat."""
        timing: dict[str, float] = {}

        def call() -> dict:
            start = time.perf_counter()
            result = self.pipeline.answer(question=question, creds=self._creds, workspace_id=self.workspace_id,
                                          session_id="eval", document_ids=[self.document["id"]],
                                          use_hybrid=use_hybrid)
            timing["total"] = time.perf_counter() - start
            return result

        result = patient_call(call, label=f"answers {self.answer_model}", limiter=self._limiter, key=self._key)
        retrieval = self._last_retrieval
        return Answer(text=result["answer"], contexts=result["contexts"],
                      retrieval_seconds=retrieval, generation_seconds=max(0.0, timing["total"] - retrieval))
