"""Pydantic models for the v2 API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str


class DocumentInfo(BaseModel):
    """An uploaded paper.

    `status` is one of: queued | parsing | enriching | embedding | ready | error.
    """

    id: str
    filename: str
    status: str
    progress: str | None = None
    error: str | None = None
    mode: str | None = None
    page_count: int | None = None
    stats: dict | None = None
    score: int | None = None
    score_explanation: str | None = None
    created_at: str
    updated_at: str


class DocumentList(BaseModel):
    documents: list[DocumentInfo]


class DeleteResponse(BaseModel):
    success: bool
    document_id: str


class SearchRequest(BaseModel):
    query: str
    document_ids: list[str] | None = None
    top_k: int | None = None
    use_hybrid: bool = True


class SearchHit(BaseModel):
    document_id: str
    filename: str
    order: int
    content_type: str
    section: str
    pages: list[int]
    boxes: list[dict]
    relevance: float
    score: float
    text: str


class ContextBlockOut(BaseModel):
    document_id: str
    filename: str
    content_type: str
    section: str
    text: str
    orders: list[int]
    pages: list[int]
    boxes: list[dict]
    relevance: float
    figure_index: int | None = None


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    blocks: list[ContextBlockOut] = []


class ProviderInfo(BaseModel):
    id: str
    name: str
    default_model: str
    supports_images: bool
    key_url: str


class ProvidersResponse(BaseModel):
    default_provider: str
    providers: list[ProviderInfo]
    server_key_available: bool


class KeyTestRequest(BaseModel):
    provider: str
    api_key: str
    model: str | None = None


class KeyTestResponse(BaseModel):
    ok: bool
    message: str
    code: str | None = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    document_ids: list[str] | None = None
    top_k: int | None = Field(default=None, ge=1, le=12)
    use_hybrid: bool = True


class Citation(BaseModel):
    index: int
    document_id: str
    filename: str
    section: str
    content_type: str
    pages: list[int]
    page: int | None = None
    boxes: list[dict]
    relevance: float
    text: str
    figure_index: int | None = None


class QueryResponse(BaseModel):
    success: bool = True
    question: str
    answer: str
    citations: list[Citation]
    search_query: str
    contexts: list[str] = []


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=5000)


class ResearchResponse(BaseModel):
    topic: str = ""
    description: str = ""
    breakdown: str = ""
    updated_at: str | None = None


class ScoreResponse(BaseModel):
    document_id: str
    score: int
    explanation: str


class AnalysisResponse(BaseModel):
    document_id: str
    summary: str
    key_findings: list[str]
    methodology: str
    limitations: list[str]
