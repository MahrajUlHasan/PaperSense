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


class QueryResponse(BaseModel):
    """Response for a query"""
    success: bool
    question: Optional[str] = None
    answer: Optional[str] = None
    citations: Optional[List[Citation]] = None
    context_used: Optional[int] = None
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

