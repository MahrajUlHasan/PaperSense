"""Tests for RAGPipeline — all sub-services are mocked via conftest."""

import pytest


class TestProcessDocument:
    def test_success_flow(self, mock_rag, sample_pdf_bytes):
        pipeline, m = mock_rag

        # Parser returns valid data
        m["parser"].parse_pdf.return_value = {
            "text": "Hello world",
            "metadata": {"title": "T", "author": "A"},
            "page_count": 2,
            "tables": [],
            "images": [],
        }
        # Chunker returns chunks
        m["chunker"].chunk_text.return_value = [
            {"text": "chunk1", "chunk_id": 0, "section": "intro", "metadata": {}}
        ]
        m["chunker"].create_table_chunks.return_value = []
        m["chunker"].create_image_chunks.return_value = []
        # Embedding returns chunks with vectors
        m["embedding"].embed_chunks.return_value = [
            {"text": "chunk1", "chunk_id": 0, "embedding": [0.1] * 10, "metadata": {}}
        ]
        m["vector_store"].add_documents.return_value = True

        result = pipeline.process_document(sample_pdf_bytes, "test.pdf")
        assert result["success"] is True
        assert "document_id" in result

    def test_empty_text_fails(self, mock_rag, sample_pdf_bytes):
        pipeline, m = mock_rag
        m["parser"].parse_pdf.return_value = {
            "text": "",
            "metadata": {},
            "page_count": 0,
            "tables": [],
            "images": [],
        }
        result = pipeline.process_document(sample_pdf_bytes, "empty.pdf")
        assert result["success"] is False
        assert "text" in result["error"].lower()

    def test_vector_store_failure(self, mock_rag, sample_pdf_bytes):
        pipeline, m = mock_rag
        m["parser"].parse_pdf.return_value = {
            "text": "content", "metadata": {}, "page_count": 1,
            "tables": [], "images": [],
        }
        m["chunker"].chunk_text.return_value = [{"text": "c", "chunk_id": 0, "metadata": {}}]
        m["chunker"].create_table_chunks.return_value = []
        m["chunker"].create_image_chunks.return_value = []
        m["embedding"].embed_chunks.return_value = [{"text": "c", "embedding": [0.1], "metadata": {}}]
        m["vector_store"].add_documents.return_value = False

        result = pipeline.process_document(sample_pdf_bytes, "test.pdf")
        assert result["success"] is False


class TestQuery:
    def test_success_flow(self, mock_rag):
        pipeline, m = mock_rag
        m["embedding"].embed_query.return_value = [0.1] * 10
        m["vector_store"].search.return_value = [
            {"text": "chunk", "section": "s", "score": 0.9,
             "document_id": "d1", "content_type": "text", "metadata": {"filename": "a.pdf"}}
        ]
        m["llm"].answer_question.return_value = {
            "answer": "The answer", "citations": [], "context_used": 1
        }

        result = pipeline.query("What is X?")
        assert result["success"] is True
        assert result["answer"] == "The answer"

    def test_empty_question(self, mock_rag):
        pipeline, m = mock_rag
        result = pipeline.query("")
        assert result["success"] is False

    def test_no_results(self, mock_rag):
        pipeline, m = mock_rag
        m["embedding"].embed_query.return_value = [0.1] * 10
        m["vector_store"].search.return_value = []

        result = pipeline.query("obscure question")
        assert result["success"] is False
        # assert "no relevant" in result.get("error", "").lower()


class TestResearch:
    def test_set_research(self, mock_rag):
        pipeline, m = mock_rag
        m["llm"].generate_research_breakdown.return_value = "## Breakdown\n- Key theme"

        result = pipeline.set_research("FL in IoT", "Studying federated learning")
        assert result["success"] is True
        assert "breakdown" in result
        assert result["topic"] == "FL in IoT"

    def test_get_research_empty(self, mock_rag):
        pipeline, m = mock_rag
        result = pipeline.get_research()
        assert result["success"] is True
        assert result["topic"] == ""

    def test_score_document_no_research(self, mock_rag):
        pipeline, m = mock_rag
        result = pipeline.score_document("doc-1")
        assert result["success"] is False
        assert "no research" in result["error"].lower()

    def test_score_document_success(self, mock_rag):
        pipeline, m = mock_rag
        # Set research first
        m["llm"].generate_research_breakdown.return_value = "breakdown"
        pipeline.set_research("topic", "desc")

        m["vector_store"].get_by_document_id.return_value = [
            {"text": "chunk", "content_type": "text",
             "metadata": {"filename": "paper.pdf"}}
        ]
        m["llm"].score_document_relevance.return_value = {
            "score": 75, "explanation": "Relevant"
        }

        result = pipeline.score_document("doc-1")
        assert result["success"] is True
        assert result["score"] == 75
