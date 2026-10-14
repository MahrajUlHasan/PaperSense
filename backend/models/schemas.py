"""Pydantic models for the v2 API."""
from __future__ import annotations

from pydantic import BaseModel


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
