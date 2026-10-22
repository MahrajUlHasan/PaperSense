"""PaperSense API v2."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from loguru import logger

from api.deps import RequestContext, default_model, get_context, get_file_workspace
from config import settings
from models.schemas import (
    AnalysisResponse, DeleteResponse, DocumentInfo, DocumentList, HealthResponse, KeyTestRequest,
    KeyTestResponse, ProvidersResponse, QueryRequest, QueryResponse, ResearchRequest, ResearchResponse,
    ScoreResponse, SearchRequest, SearchResponse,
)
from services.chunking import Chunker
from services.embeddings import EmbeddingService
from services.ingestion import IngestionService
from services.llm import KEY_HELP_URLS, PROVIDERS, LLMCredentials, ProviderError, build_provider
from services.logging_setup import setup_logging
from services.memory import ConversationMemory
from services.parsing import PDFParser
from services.pipeline import QueryPipeline
from services.qdrant_store import QdrantStore
from services.registry import DocumentRegistry
from services.research import ResearchService
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
    setup_logging()
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
    memory = ConversationMemory()
    pipeline = QueryPipeline(embedder=embedder, store=store, storage=storage, memory=memory)
    services = Services(registry=registry, storage=storage, embedder=embedder, store=store,
                        ingestion=ingestion, pipeline=pipeline, memory=memory, research=ResearchService())
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


@app.exception_handler(ProviderError)
async def provider_error_handler(request, exc: ProviderError):
    """Provider problems become clear HTTP errors (401 + key link, 429 + Retry-After, ...)."""
    headers = {"Retry-After": str(int(exc.retry_after))} if exc.retry_after else None
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.to_dict()}, headers=headers)


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


def _ready_chunks(svc: Services, document_id: str, workspace_id: str) -> tuple[dict, list[dict]]:
    doc = _owned_document(svc, document_id, workspace_id)
    if doc["status"] != "ready":
        raise HTTPException(status_code=409, detail="This paper is still processing.")
    return doc, svc.store.get_document_chunks(document_id)


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
    return svc.ingestion.submit(pdf_bytes=data, filename=file.filename,
                                workspace_id=ctx.workspace_id, gemini_key=ctx.gemini_key)


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


@app.get("/config/providers", response_model=ProvidersResponse)
def list_providers():
    names = {"gemini": "Google Gemini", "groq": "Groq", "openrouter": "OpenRouter"}
    return {
        "default_provider": settings.default_provider,
        "providers": [
            {"id": p, "name": names[p], "default_model": default_model(p),
             "supports_images": p == "gemini", "key_url": KEY_HELP_URLS[p]}
            for p in PROVIDERS
        ],
        "server_key_available": settings.allow_server_key and bool(settings.server_gemini_api_key),
    }


@app.post("/keys/test", response_model=KeyTestResponse)
def test_key(body: KeyTestRequest):
    """Makes one tiny request with the given key. The key is not stored or logged.

    A rate-limited or empty reply still means the provider accepted the key.
    """
    if body.provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail="Unknown provider.")
    creds = LLMCredentials(body.provider, body.api_key.strip(), body.model or default_model(body.provider))
    try:
        build_provider(creds).generate("Reply with the single word OK.", temperature=0.0, max_output_tokens=512)
        return {"ok": True, "message": f"Your key works with {creds.model}."}
    except ProviderError as err:
        if err.kind == "rate_limited":
            return {"ok": True, "message": "The key is valid, but its free-tier limit is reached right now."}
        if err.kind == "empty":
            return {"ok": True, "message": f"Your key works with {creds.model}."}
        return {"ok": False, "message": err.message, "code": err.kind}


@app.post("/query", response_model=QueryResponse)
def query(body: QueryRequest, ctx: RequestContext = Depends(get_context),
          svc: Services = Depends(get_services)):
    """Answer a question from the browser's papers. Without a key: 401 with a "get a key" link."""
    creds = ctx.require_llm()
    document_ids = _owned_ids(svc, ctx.workspace_id, body.document_ids)
    result = svc.pipeline.answer(
        question=body.question, creds=creds, workspace_id=ctx.workspace_id,
        session_id=ctx.session_id, document_ids=document_ids,
        top_k=body.top_k, use_hybrid=body.use_hybrid,
    )
    return {"question": body.question, **result}


@app.delete("/sessions/current")
def clear_session(ctx: RequestContext = Depends(get_context), svc: Services = Depends(get_services)):
    """'New chat': forget this session's history."""
    svc.memory.clear(ctx.workspace_id, ctx.session_id)
    return {"success": True}


@app.post("/research", response_model=ResearchResponse)
def set_research(body: ResearchRequest, ctx: RequestContext = Depends(get_context),
                 svc: Services = Depends(get_services)):
    provider = build_provider(ctx.require_llm())
    breakdown = svc.research.breakdown(provider, body.topic.strip(), body.description.strip())
    return svc.registry.set_research(ctx.workspace_id, body.topic.strip(), body.description.strip(), breakdown)


@app.get("/research", response_model=ResearchResponse)
def get_research(ctx: RequestContext = Depends(get_context), svc: Services = Depends(get_services)):
    return svc.registry.get_research(ctx.workspace_id) or {}


@app.post("/documents/{document_id}/score", response_model=ScoreResponse)
def score_document(document_id: str, ctx: RequestContext = Depends(get_context),
                   svc: Services = Depends(get_services)):
    research = svc.registry.get_research(ctx.workspace_id)
    if not research:
        raise HTTPException(status_code=400, detail="Set a research topic first.")
    provider = build_provider(ctx.require_llm())
    doc, chunks = _ready_chunks(svc, document_id, ctx.workspace_id)
    score, explanation = svc.research.score(provider, chunks, doc["filename"], research)
    svc.registry.update(document_id, score=score, score_explanation=explanation)
    return {"document_id": document_id, "score": score, "explanation": explanation}


@app.get("/documents/{document_id}/analysis", response_model=AnalysisResponse)
def analyze_document(document_id: str, ctx: RequestContext = Depends(get_context),
                     svc: Services = Depends(get_services)):
    provider = build_provider(ctx.require_llm())
    _doc, chunks = _ready_chunks(svc, document_id, ctx.workspace_id)
    return {"document_id": document_id, **svc.research.analyze(provider, chunks)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=settings.debug)
