"""PaperSense API v2."""
from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from loguru import logger

from api.deps import RequestContext, get_context, get_file_workspace
from config import settings
from models.schemas import (
    DeleteResponse, DocumentInfo, DocumentList, HealthResponse, SearchRequest, SearchResponse,
)
from services.chunking import Chunker
from services.embeddings import EmbeddingService
from services.ingestion import IngestionService
from services.parsing import PDFParser
from services.qdrant_store import QdrantStore
from services.registry import DocumentRegistry
from services.retrieval import build_context_blocks, normalize_scores
from services.storage import DocumentStorage

MAX_UPLOAD_BYTES = 50 * 1024 * 1024


@dataclass
class Services:
    registry: DocumentRegistry | None = None
    storage: DocumentStorage | None = None
    embedder: EmbeddingService | None = None
    store: QdrantStore | None = None
    ingestion: IngestionService | None = None
    pipeline: Any = None
    memory: Any = None
    research: Any = None


services: Services | None = None


def get_services() -> Services:
    if services is None:
        raise HTTPException(status_code=503, detail="The server is still starting. Try again in a moment.")
    return services


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build every service on startup. Shutdown only stops the worker: documents are kept."""
    global services
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if settings.debug else "INFO")
    logger.add("logs/app.log", rotation="20 MB", retention=5, level="INFO")
    if getattr(settings, "hf_token", None):
        os.environ.setdefault("HF_TOKEN", settings.hf_token)

    registry = DocumentRegistry()
    interrupted = registry.fail_interrupted()
    if interrupted:
        logger.warning(f"{interrupted} upload(s) were interrupted by the last shutdown")
    storage = DocumentStorage()
    embedder = EmbeddingService()
    store = QdrantStore(dense_dim=embedder.dimension)
    ingestion = IngestionService(parser=PDFParser(), chunker=Chunker(), embedder=embedder,
                                 store=store, storage=storage, registry=registry)
    services = Services(registry=registry, storage=storage, embedder=embedder,
                        store=store, ingestion=ingestion)
    logger.info(f"{settings.app_name} ready - Qdrant collection '{store.collection}'")
    yield
    ingestion.shutdown()


app = FastAPI(title="PaperSense API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _owned_document(svc: Services, document_id: str, workspace_id: str) -> dict:
    doc = svc.registry.get(document_id)
    if not doc or doc["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


def _owned_ids(svc: Services, workspace_id: str, document_ids: list[str] | None) -> list[str] | None:
    """None/empty -> all papers of this browser. Otherwise only ids this browser owns."""
    if not document_ids:
        return None
    owned = {d["id"] for d in svc.registry.list(workspace_id)}
    ids = [d for d in document_ids if d in owned]
    if not ids:
        raise HTTPException(status_code=404, detail="None of the selected documents were found.")
    return ids


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok" if services else "starting", version="2.0.0")


@app.post("/documents", response_model=DocumentInfo, status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(get_context),
    svc: Services = Depends(get_services),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="The file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The file is larger than 50 MB.")
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="This file is not a valid PDF.")
    return svc.ingestion.submit(pdf_bytes=data, filename=file.filename, workspace_id=ctx.workspace_id)


@app.get("/documents", response_model=DocumentList)
def list_documents(ctx: RequestContext = Depends(get_context), svc: Services = Depends(get_services)):
    return {"documents": svc.registry.list(ctx.workspace_id)}


@app.get("/documents/{document_id}", response_model=DocumentInfo)
def get_document(document_id: str, ctx: RequestContext = Depends(get_context),
                 svc: Services = Depends(get_services)):
    return _owned_document(svc, document_id, ctx.workspace_id)


@app.get("/documents/{document_id}/file")
def get_document_file(document_id: str, workspace_id: str = Depends(get_file_workspace),
                      svc: Services = Depends(get_services)):
    doc = _owned_document(svc, document_id, workspace_id)
    path = svc.storage.pdf_path(document_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found.")
    return FileResponse(path, media_type="application/pdf", filename=doc["filename"],
                        content_disposition_type="inline")


@app.get("/documents/{document_id}/figures/{index}")
def get_figure(document_id: str, index: int, workspace_id: str = Depends(get_file_workspace),
               svc: Services = Depends(get_services)):
    _owned_document(svc, document_id, workspace_id)
    path = svc.storage.figure_path(document_id, index)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Figure not found.")
    return FileResponse(path, media_type="image/png")


@app.delete("/documents/{document_id}", response_model=DeleteResponse)
def delete_document(document_id: str, ctx: RequestContext = Depends(get_context),
                    svc: Services = Depends(get_services)):
    _owned_document(svc, document_id, ctx.workspace_id)
    svc.store.delete_document(document_id)
    svc.storage.delete(document_id)
    svc.registry.delete(document_id)
    return {"success": True, "document_id": document_id}


@app.post("/search", response_model=SearchResponse)
def search(body: SearchRequest, ctx: RequestContext = Depends(get_context),
           svc: Services = Depends(get_services)):
    """Retrieval only (no LLM): useful to check what the model would be given."""
    body.document_ids = _owned_ids(svc, ctx.workspace_id, body.document_ids)
    top_k = body.top_k or settings.top_k
    vector = svc.embedder.embed_query(body.query)
    if body.use_hybrid:
        hits = svc.store.hybrid_search(body.query, vector, ctx.workspace_id, body.document_ids,
                                       limit=top_k, prefetch_limit=settings.prefetch_limit)
    else:
        hits = svc.store.dense_search(vector, ctx.workspace_id, body.document_ids, limit=top_k)
    hits = normalize_scores(hits)
    blocks = build_context_blocks([dict(h) for h in hits], fetch_neighbors=svc.store.fetch_chunks, max_blocks=top_k)
    return {"hits": hits, "blocks": [asdict(b) for b in blocks]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.debug)
