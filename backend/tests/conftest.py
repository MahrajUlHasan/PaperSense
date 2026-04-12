"""
Shared pytest fixtures for backend tests.
All heavy services (Qdrant, Gemini, OpenAI) are mocked so tests run offline.
"""
import os, sys
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

# Ensure backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Patch settings BEFORE anything imports them ────────────────────
_env = {
    "GOOGLE_API_KEY": "test-key",
    "OPENAI_API_KEY": "test-key",
    "QDRANT_HOST": "localhost",
    "QDRANT_PORT": "6333",
    "EMBEDDING_PROVIDER": "openai",
    "EMBEDDING_DIMENSION": "1536",
    "GEMINI_MODEL": "gemini-pro",
    "CHUNK_SIZE": "500",
    "CHUNK_OVERLAP": "100",
}

for k, v in _env.items():
    os.environ.setdefault(k, v)


# ── Mock VectorStore (Qdrant) ──────────────────────────────────────

@pytest.fixture
def mock_vector_store():
    with patch("services.vector_store.QdrantClient") as MockClient:
        client = MockClient.return_value
        # get_collections returns empty list by default
        coll = MagicMock()
        coll.collections = []
        client.get_collections.return_value = coll
        from services.vector_store import VectorStore
        store = VectorStore()
        yield store, client


# ── Mock LLMService (Gemini) ───────────────────────────────────────

@pytest.fixture
def mock_llm():
    with patch("services.llm_service.genai") as mock_genai:
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        # generate_content returns a mock with .text
        mock_response = MagicMock()
        mock_response.text = "Mocked LLM answer."
        mock_client.models.generate_content.return_value = mock_response

        from services.llm_service import LLMService
        svc = LLMService()
        yield svc, mock_client


# ── Mock RAGPipeline (all sub-services mocked) ────────────────────

@pytest.fixture
def mock_rag():
    with (
        patch("services.rag_pipeline.PDFParser") as MockParser,
        patch("services.rag_pipeline.Chunker") as MockChunker,
        patch("services.rag_pipeline.get_embedding_service") as MockEmb,
        patch("services.rag_pipeline.VectorStore") as MockVS,
        patch("services.rag_pipeline.LLMService") as MockLLM,
    ):
        from services.rag_pipeline import RAGPipeline
        pipeline = RAGPipeline()
        yield pipeline, {
            "parser": MockParser.return_value,
            "chunker": MockChunker.return_value,
            "embedding": MockEmb.return_value,
            "vector_store": MockVS.return_value,
            "llm": MockLLM.return_value,
        }


# ── FastAPI TestClient ─────────────────────────────────────────────

@pytest.fixture
def client(mock_rag):
    pipeline, mocks = mock_rag
    with patch("main.rag_pipeline", pipeline):
        from fastapi.testclient import TestClient
        from main import app
        yield TestClient(app), pipeline, mocks


# ── Helpers ────────────────────────────────────────────────────────

@pytest.fixture
def sample_pdf_bytes():
    """Minimal valid-ish PDF bytes for testing upload."""
    return b"%PDF-1.4 fake pdf content for testing"


@pytest.fixture
def sample_chunks():
    """Sample chunks as returned by vector store search."""
    return [
        {
            "text": "Neural networks are universal approximators.",
            "section": "Introduction",
            "score": 0.92,
            "document_id": "doc-123",
            "content_type": "text",
            "page": 1,
            "metadata": {"filename": "paper.pdf", "title": "Deep Learning"},
        },
        {
            "text": "Table 1 shows results across datasets.",
            "section": "Results",
            "score": 0.85,
            "document_id": "doc-123",
            "content_type": "table",
            "page": 5,
            "metadata": {"filename": "paper.pdf", "title": "Deep Learning"},
        },
    ]
