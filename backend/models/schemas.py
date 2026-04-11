"""
Pydantic models for API request/response schemas
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document"""
    success: bool
    document_id: Optional[str] = None
    filename: Optional[str] = None
    metadata: Optional[Dict] = None
    statistics: Optional[Dict] = None
    error: Optional[str] = None


class QueryRequest(BaseModel):
    """Request for querying the knowledge base"""
    question: str = Field(..., description="what is the topic of this paper and is it relevent to genAI")
    document_id: Optional[str] = Field(None, description="Specific document to search")
    top_k: Optional[int] = Field(5, description="Number of chunks to retrieve")


class Citation(BaseModel):
    """Citation information"""
    index: int
    section: str
    score: float
    document_id: str
    filename: Optional[str] = None
    text: Optional[str] = None
    content_type: Optional[str] = None
    page: Optional[int] = None


class SourceInfo(BaseModel):
    """Metadata for a source document referenced in a query response"""
    document_id: str
    filename: str
    metadata: Optional[Dict] = None


class QueryResponse(BaseModel):
    """Response for a query"""
    success: bool
    question: Optional[str] = None
    answer: Optional[str] = None
    citations: Optional[List[Citation]] = None
    sources: Optional[List[SourceInfo]] = None
    context_used: Optional[int] = None
    error: Optional[str] = None


# ── Research ──────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    """Request to set / update the research topic"""
    topic: str = Field(..., description="Research topic / title")
    description: str = Field("", description="Detailed research description")


class ResearchResponse(BaseModel):
    """Response after setting research context"""
    success: bool
    topic: Optional[str] = None
    description: Optional[str] = None
    breakdown: Optional[str] = None
    error: Optional[str] = None


class ScoreResponse(BaseModel):
    """Response after scoring a document against the research"""
    success: bool
    document_id: Optional[str] = None
    filename: Optional[str] = None
    score: Optional[int] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class AnalysisResponse(BaseModel):
    """Response for document analysis"""
    success: bool
    document_id: Optional[str] = None
    summary: Optional[str] = None
    key_findings: Optional[List[str]] = None
    methodology: Optional[str] = None
    limitations: Optional[List[str]] = None
    metadata: Optional[Dict] = None
    error: Optional[str] = None


class DeleteResponse(BaseModel):
    """Response for document deletion"""
    success: bool
    document_id: Optional[str] = None
    error: Optional[str] = None


class StatsResponse(BaseModel):
    """Response for statistics"""
    success: bool
    stats: Optional[Dict] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    services: Dict[str, str]


class EmbeddingConfigRequest(BaseModel):
    """Request to change the embedding provider"""
    provider: str = Field(
        ...,
        description="Embedding provider to use: 'openai', 'langchain', or 'gemma'"
    )


class EmbeddingConfigResponse(BaseModel):
    """Response after changing or querying the embedding config"""
    success: bool
    provider: Optional[str] = None
    model: Optional[str] = None
    dimension: Optional[int] = None
    available_providers: Optional[List[str]] = None
    error: Optional[str] = None

