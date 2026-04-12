"""Tests for Pydantic schemas / data models."""

import pytest
from models.schemas import (
    Citation, SourceInfo, QueryRequest, QueryResponse,
    ResearchRequest, ResearchResponse, ScoreResponse,
    DocumentUploadResponse, HealthResponse,
)


class TestCitation:
    def test_minimal(self):
        c = Citation(index=1, section="intro", score=0.9, document_id="d1")
        assert c.index == 1
        assert c.filename is None
        assert c.text is None
        assert c.page is None

    def test_full(self):
        c = Citation(
            index=2, section="results", score=0.75, document_id="d2",
            filename="paper.pdf", text="some text", content_type="table", page=3,
        )
        assert c.filename == "paper.pdf"
        assert c.page == 3
        assert c.content_type == "table"

    def test_serialization_roundtrip(self):
        c = Citation(index=1, section="s", score=0.5, document_id="d")
        data = c.model_dump()
        c2 = Citation(**data)
        assert c == c2


class TestSourceInfo:
    def test_basic(self):
        s = SourceInfo(document_id="d1", filename="a.pdf")
        assert s.metadata is None

    def test_with_metadata(self):
        s = SourceInfo(document_id="d1", filename="a.pdf", metadata={"pages": 10})
        assert s.metadata["pages"] == 10


class TestQueryRequest:
    def test_defaults(self):
        q = QueryRequest(question="What is AI?")
        assert q.top_k == 5
        assert q.document_id is None

    def test_custom(self):
        q = QueryRequest(question="x", document_id="d1", top_k=10)
        assert q.top_k == 10


class TestQueryResponse:
    def test_success(self):
        r = QueryResponse(
            success=True, question="q", answer="a",
            citations=[Citation(index=1, section="s", score=0.9, document_id="d")],
            sources=[SourceInfo(document_id="d", filename="f.pdf")],
            context_used=1,
        )
        assert r.success
        assert len(r.citations) == 1
        assert len(r.sources) == 1

    def test_error(self):
        r = QueryResponse(success=False, error="fail")
        assert not r.success
        assert r.citations is None


class TestResearchSchemas:
    def test_request_requires_topic(self):
        with pytest.raises(Exception):
            ResearchRequest(description="desc only")

    def test_request_valid(self):
        r = ResearchRequest(topic="FL in IoT", description="studying federation")
        assert r.topic == "FL in IoT"

    def test_response(self):
        r = ResearchResponse(success=True, topic="t", breakdown="b")
        assert r.success

    def test_score_response(self):
        s = ScoreResponse(success=True, document_id="d", score=87, explanation="good")
        assert s.score == 87


class TestHealthResponse:
    def test_basic(self):
        h = HealthResponse(status="ok", version="1.0.0", services={"qdrant": "ok"})
        assert h.services["qdrant"] == "ok"
