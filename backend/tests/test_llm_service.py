"""Tests for LLMService — all Gemini calls are mocked."""

from unittest.mock import MagicMock, patch
import pytest


class TestGenerateResponse:
    def test_returns_text(self, mock_llm):
        svc, client = mock_llm
        resp = MagicMock()
        resp.text = "Hello world"
        client.models.generate_content.return_value = resp

        result = svc.generate_response("Say hello")
        assert result == "Hello world"
        client.models.generate_content.assert_called_once()

    def test_empty_response_fallback(self, mock_llm):
        svc, client = mock_llm
        resp = MagicMock()
        resp.text = None
        client.models.generate_content.return_value = resp

        result = svc.generate_response("Say hello")
        assert "no response" in result.lower() or "unable" in result.lower() or result == "No response generated"

    def test_exception_returns_error_string(self, mock_llm):
        svc, client = mock_llm
        client.models.generate_content.side_effect = Exception("API down")
        result = svc.generate_response("question")
        assert "error" in result.lower() or "unable" in result.lower()


class TestAnswerQuestion:
    def test_returns_answer_and_citations(self, mock_llm, sample_chunks):
        svc, client = mock_llm
        resp = MagicMock()
        resp.text = "Neural nets are powerful [1] and results are in table [2]."
        client.models.generate_content.return_value = resp

        result = svc.answer_question("What are neural nets?", sample_chunks)

        assert "answer" in result
        assert "citations" in result
        assert len(result["citations"]) == 2
        assert result["citations"][0]["filename"] == "paper.pdf"
        assert result["citations"][0]["content_type"] == "text"
        assert result["citations"][1]["content_type"] == "table"
        assert result["context_used"] == 2

    def test_empty_chunks(self, mock_llm):
        svc, client = mock_llm
        resp = MagicMock()
        resp.text = "No context available."
        client.models.generate_content.return_value = resp

        result = svc.answer_question("question", [])
        assert result["citations"] == []
        assert result["context_used"] == 0


class TestResearchBreakdown:
    def test_generates_breakdown(self, mock_llm):
        svc, client = mock_llm
        resp = MagicMock()
        resp.text = "## Breakdown\n- Theme 1\n- Theme 2"
        client.models.generate_content.return_value = resp

        result = svc.generate_research_breakdown("FL in IoT", "Studying federated learning")
        assert "Breakdown" in result or "Theme" in result


class TestScoreDocumentRelevance:
    def test_parses_score_and_explanation(self, mock_llm):
        svc, client = mock_llm
        resp = MagicMock()
        resp.text = "SCORE: 82\nEXPLANATION: Highly relevant to federated learning."
        client.models.generate_content.return_value = resp

        result = svc.score_document_relevance(
            "Some doc text", "paper.pdf", "FL in IoT", "breakdown text"
        )
        assert result["score"] == 82
        assert "relevant" in result["explanation"].lower()

    def test_score_clamped_to_0_100(self, mock_llm):
        svc, client = mock_llm
        resp = MagicMock()
        resp.text = "SCORE: 150\nEXPLANATION: Very relevant."
        client.models.generate_content.return_value = resp

        result = svc.score_document_relevance("t", "f", "topic", "brk")
        assert 0 <= result["score"] <= 100

    def test_unparseable_defaults_to_50(self, mock_llm):
        svc, client = mock_llm
        resp = MagicMock()
        resp.text = "I think this paper is quite relevant."
        client.models.generate_content.return_value = resp

        result = svc.score_document_relevance("t", "f", "topic", "brk")
        assert result["score"] == 50


class TestExtractLimitations:
    def test_parses_bullet_points(self, mock_llm):
        svc, client = mock_llm
        resp = MagicMock()
        resp.text = "- Small sample size\n- Limited to English\n- No real-world test"
        client.models.generate_content.return_value = resp

        result = svc.extract_limitations("paper text")
        assert len(result) == 3
        assert "Small sample size" in result[0]
