"""Background ingestion: parse → figures → chunks → embeddings → Qdrant.

Runs one paper at a time in a worker thread (Docling is RAM-hungry on a laptop),
so the API stays responsive. Progress is written to the registry.
"""
from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

from loguru import logger

from services.chunking import Chunker
from services.embeddings import EmbeddingService
from services.parsing import PDFParser, extract_figures
from services.qdrant_store import QdrantStore
from services.registry import DocumentRegistry
from services.storage import DocumentStorage


class IngestionService:
    def __init__(self, *, parser: PDFParser, chunker: Chunker, embedder: EmbeddingService,
                 store: QdrantStore, storage: DocumentStorage, registry: DocumentRegistry):
        self.parser = parser
        self.chunker = chunker
        self.embedder = embedder
        self.store = store
        self.storage = storage
        self.registry = registry
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingest")

    def submit(self, *, pdf_bytes: bytes, filename: str, workspace_id: str) -> dict:
        """Save the PDF, register it as queued and process it in the background."""
        document_id = str(uuid.uuid4())
        self.storage.save_pdf(document_id, pdf_bytes)
        record = self.registry.create(document_id, workspace_id, filename)
        self._executor.submit(self.run, document_id, workspace_id, filename)
        return record

    def run(self, document_id: str, workspace_id: str, filename: str) -> None:
        """Process one stored PDF.

        Every failure is caught and recorded in the registry as status "error", and
        any vectors already written for the document are removed again.
        """
        try:
            self._progress(document_id, "parsing", "Reading the PDF")
            pdf_bytes = self.storage.pdf_path(document_id).read_bytes()
            parsed = self.parser.parse(pdf_bytes, filename)

            figures = extract_figures(parsed.doc)
            for fig in figures:
                self.storage.save_figure(document_id, fig.index, fig.image)

            self._progress(document_id, "embedding", "Building the search index")
            title, records = self.chunker.build(parsed, filename, figures=figures)
            vectors = self.embedder.embed_documents([r.embed_text for r in records])
            self.store.upsert_chunks(
                document_id=document_id, workspace_id=workspace_id, filename=filename,
                title=title, records=records, dense_vectors=vectors,
            )

            stats = {
                "title": title,
                "chunks": len(records),
                "tables": sum(r.content_type == "table" for r in records),
                "figures": len(figures),
                "formulas": sum(len(r.formulas) for r in records),
                "coverage": round(parsed.coverage, 3),
                "low_coverage_pages": parsed.low_coverage_pages,
                "ocr_used": parsed.ocr_used,
                "parse_seconds": round(parsed.seconds, 1),
                "notes": [],
            }
            self.registry.update(document_id, status="ready", progress="Ready", error=None,
                                 page_count=parsed.page_count, stats=stats)
            logger.info(f"Ingested {filename}: {stats}")
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"Ingestion failed for {filename}")
            self.registry.update(document_id, status="error", progress="Failed", error=str(exc)[:500])
            try:
                self.store.delete_document(document_id)
            except Exception:  # noqa: BLE001
                logger.warning(f"Could not remove partial vectors of {document_id}")

    def _progress(self, document_id: str, status: str, progress: str) -> None:
        self.registry.update(document_id, status=status, progress=progress)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
