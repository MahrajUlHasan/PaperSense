from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys
import json

from config import settings
from services.rag_pipeline import RAGPipeline
from models.schemas import (
    DocumentUploadResponse, QueryRequest, QueryResponse,
    AnalysisResponse, DeleteResponse, StatsResponse, HealthResponse,
    EmbeddingConfigRequest, EmbeddingConfigResponse,
    ResearchRequest, ResearchResponse, ScoreResponse,
)

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO" if not settings.debug else "DEBUG")
logger.add("logs/app.log", rotation="500 MB", level="DEBUG")

# Initialize RAG pipeline
rag_pipeline = RAGPipeline()

logger.info(f"Starting {settings.app_name} v{settings.app_version}")


# Lifespan: clear conversation memory on startup and shutdown
@asynccontextmanager
async def lifespan(application: FastAPI):
    # Startup – fresh conversation each run
    rag_pipeline.conversation_memory.clear()
    logger.info("Conversation memory cleared on startup")
    yield
    # Shutdown – clean up
    rag_pipeline.conversation_memory.clear()
    logger.info("Conversation memory cleared on shutdown")
    rag_pipeline.vector_store.close()
    logger.info("Vector store closed")


# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="RAG-based research paper analyzer with Qdrant, OpenAI, and Gemini",
    lifespan=lifespan,
)

# Configure CORS
#todo: configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _health_payload() -> dict:
    emb_info = rag_pipeline.get_embedding_info()
    return {
        "status": "healthy",
        "version": settings.app_version,
        "services": {
            "vector_store": "qdrant",
            "embeddings": emb_info["provider"],
            "llm": "gemini"
        }
    }


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check"""
    return _health_payload()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return _health_payload()


@app.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a research paper PDF
    
    Args:
        file: PDF file to upload
        
    Returns:
        Processing result with document_id
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        logger.info(f"Received file: {file.filename}, size: {len(content)} bytes")
        
        # Process document through RAG pipeline
        result = rag_pipeline.process_document(content, file.filename)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Query the knowledge base with a question
    
    Args:
        request: Query request with question and optional filters
        
    Returns:
        Answer with citations
    """
    try:
        result = rag_pipeline.query(
            question=request.question,
            document_id=request.document_id,
            top_k=request.top_k,
            use_hybrid=request.use_hybrid or False,
        )
        logger.debug(f"Query result: {json.dumps(result, indent=4)}")
        return result
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze/{document_id}", response_model=AnalysisResponse)
async def analyze_document(document_id: str):
    """
    Perform comprehensive analysis of a document
    
    Args:
        document_id: ID of the document to analyze
        
    Returns:
        Analysis with summary, findings, methodology, limitations
    """
    try:
        result = rag_pipeline.analyze_document(document_id)
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Document not found"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str):
    """
    Delete a document from the vector store
    
    Args:
        document_id: ID of the document to delete
        
    Returns:
        Deletion result
    """
    try:
        result = rag_pipeline.delete_document(document_id)
        return result
        
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=StatsResponse)
async def get_statistics():
    """
    Get statistics about the vector store

    Returns:
        Collection statistics
    """
    try:
        result = rag_pipeline.get_stats()
        return result

    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/embedding", response_model=EmbeddingConfigResponse)
async def get_embedding_config():
    """
    Get the current embedding provider configuration.

    Returns:
        Current provider, model name, dimension, and list of available providers.
    """
    try:
        info = rag_pipeline.get_embedding_info()
        return {"success": True, **info}
    except Exception as e:
        logger.error(f"Embedding config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/embedding", response_model=EmbeddingConfigResponse)
async def set_embedding_config(request: EmbeddingConfigRequest):
    """
    Switch the active embedding provider at runtime.

    **Providers:**
    - `openai`    – OpenAI text-embedding-3-small (1536-d)
    - `langchain` – LangChain + Google Generative AI text-embedding-004 (768-d)
    - `gemma`     – Google GenAI text-embedding-004 (768-d, multimodal image support)

    > **Note:** Switching providers changes the embedding dimension.
    > Documents embedded with one provider cannot be searched with another.
    """
    valid = {"openai", "langchain", "gemma"}
    if request.provider.lower() not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider '{request.provider}'. Must be one of: {', '.join(sorted(valid))}"
        )
    try:
        result = rag_pipeline.set_embedding_service(request.provider)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to switch provider"))
        info = rag_pipeline.get_embedding_info()
        return {"success": True, **info}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding switch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Research endpoints ────────────────────────────────────────────

@app.post("/research", response_model=ResearchResponse)
async def set_research(request: ResearchRequest):
    """
    Set or update the research topic and description.
    Generates a detailed breakdown via the LLM for document scoring.
    """
    try:
        result = rag_pipeline.set_research(request.topic, request.description)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Research error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/research", response_model=ResearchResponse)
async def get_research():
    """Get the current research topic, description, and breakdown."""
    return rag_pipeline.get_research()


@app.post("/score/{document_id}", response_model=ScoreResponse)
async def score_document(document_id: str):
    """
    Score a document's relevance to the current research topic (0-100).
    Requires a research topic to be set first via POST /research.
    """
    try:
        result = rag_pipeline.score_document(document_id)
        if not result.get("success"):
            raise HTTPException(
                status_code=400 if "No research" in result.get("error", "") else 500,
                detail=result.get("error", "Scoring failed"),
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Score error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )

