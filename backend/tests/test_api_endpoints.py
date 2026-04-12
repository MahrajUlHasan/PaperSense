"""Tests for FastAPI endpoints using TestClient — all services mocked."""

import pytest
import io


class TestHealthEndpoints:
    def test_root(self, client):
        tc, pipeline, mocks = client
        resp = tc.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health(self, client):
        tc, *_ = client
        resp = tc.get("/health")
        assert resp.status_code == 200


class TestUploadEndpoint:
    def test_upload_non_pdf_rejected(self, client):
        tc, *_ = client
        resp = tc.post("/upload", files={"file": ("test.txt", b"hello", "text/plain")})
        assert resp.status_code == 400

    def test_upload_empty_file_rejected(self, client):
        tc, *_ = client
        resp = tc.post("/upload", files={"file": ("test.pdf", b"", "application/pdf")})
        assert resp.status_code == 400

    def test_upload_success(self, client, sample_pdf_bytes):
        tc, pipeline, mocks = client
        pipeline.process_document = lambda content, filename: {
            "success": True,
            "document_id": "doc-123",
            "filename": filename,
            "metadata": {},
            "statistics": {"chunks": 5},
        }
        resp = tc.post(
            "/upload",
            files={"file": ("paper.pdf", sample_pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["document_id"] == "doc-123"

    def test_upload_processing_failure(self, client, sample_pdf_bytes):
        tc, pipeline, mocks = client
        pipeline.process_document = lambda c, f: {"success": False, "error": "parse failed"}
        resp = tc.post(
            "/upload",
            files={"file": ("bad.pdf", sample_pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 500


class TestQueryEndpoint:
    def test_query_success(self, client):
        tc, pipeline, mocks = client
        pipeline.query = lambda **kw: {
            "success": True,
            "question": kw["question"],
            "answer": "42",
            "citations": [],
            "context_used": 1,
        }
        resp = tc.post("/query", json={"question": "meaning of life?"})
        assert resp.status_code == 200
        assert resp.json()["answer"] == "42"

    def test_query_empty_question(self, client):
        tc, pipeline, mocks = client
        pipeline.query = lambda **kw: {"success": False, "error": "empty question"}
        resp = tc.post("/query", json={"question": ""})
        assert resp.status_code == 200  # pipeline returns error inside response

    def test_query_with_document_filter(self, client):
        tc, pipeline, mocks = client
        captured = {}
        def mock_query(**kw):
            captured.update(kw)
            return {"success": True, "answer": "a", "citations": [], "context_used": 1}
        pipeline.query = mock_query
        tc.post("/query", json={"question": "q", "document_id": "doc-1", "top_k": 3})
        assert captured["document_id"] == "doc-1"
        assert captured["top_k"] == 3


class TestDeleteEndpoint:
    def test_delete_success(self, client):
        tc, pipeline, mocks = client
        pipeline.delete_document = lambda doc_id: {"success": True, "message": "deleted"}
        resp = tc.delete("/documents/doc-123")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestResearchEndpoints:
    def test_get_research_empty(self, client):
        tc, pipeline, mocks = client
        pipeline.get_research = lambda: {"success": True, "topic": "", "description": "", "breakdown": ""}
        resp = tc.get("/research")
        assert resp.status_code == 200
        assert resp.json()["topic"] == ""

    def test_set_research(self, client):
        tc, pipeline, mocks = client
        pipeline.set_research = lambda t, d: {
            "success": True, "topic": t, "description": d, "breakdown": "## Breakdown"
        }
        resp = tc.post("/research", json={"topic": "FL in IoT", "description": "desc"})
        assert resp.status_code == 200
        assert resp.json()["topic"] == "FL in IoT"
        assert resp.json()["breakdown"] == "## Breakdown"

    def test_set_research_missing_topic(self, client):
        tc, *_ = client
        resp = tc.post("/research", json={"description": "no topic"})
        assert resp.status_code == 422  # validation error


class TestScoreEndpoint:
    def test_score_success(self, client):
        tc, pipeline, mocks = client
        pipeline.score_document = lambda doc_id: {
            "success": True, "document_id": doc_id, "filename": "p.pdf",
            "score": 85, "explanation": "relevant",
        }
        resp = tc.post("/score/doc-123")
        assert resp.status_code == 200
        assert resp.json()["score"] == 85

    def test_score_no_research(self, client):
        tc, pipeline, mocks = client
        pipeline.score_document = lambda doc_id: {
            "success": False, "error": "No research topic set."
        }
        resp = tc.post("/score/doc-1")
        assert resp.status_code == 400


class TestStatsEndpoint:
    def test_stats(self, client):
        tc, pipeline, mocks = client
        pipeline.get_stats = lambda: {"total_documents": 2, "total_chunks": 50}
        resp = tc.get("/stats")
        assert resp.status_code == 200
