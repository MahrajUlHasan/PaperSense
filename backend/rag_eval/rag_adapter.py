import sys
import os
from pathlib import Path

# Add backend/ to python path to access the services module
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.rag_pipeline import RAGPipeline


class PaperSenseRAGAdapter:
    """Wrapper to integrate PaperSense RAGPipeline with Ragas evaluations."""

    def __init__(self):
        self.pipeline = RAGPipeline()
        self.document_id = None

    def ingest_test_paper(self, pdf_path: str) -> str:
        """Reads a PDF file, processes it through the pipeline, and saves the document_id."""
        path = Path(pdf_path)
        filename = path.name

        with open(path, "rb") as f:
            pdf_bytes = f.read()

        result = self.pipeline.process_document(pdf_bytes, filename)

        if not result.get("success"):
            raise RuntimeError(f"Failed to ingest document: {result.get('error')}")

        self.document_id = result["document_id"]
        return self.document_id

    def query(self, question: str , use_hybrid :bool = False) -> dict:
        """Queries the pipeline and formats the output specifically for Ragas."""
        if not self.document_id:
            raise ValueError("No document ingested. Call ingest_test_paper first.")

        result = self.pipeline.query(question=question, document_id=self.document_id , use_hybrid=use_hybrid)

        # Ragas natively expects 'answer' and 'contexts' (list of strings)
        return {
            "answer": result.get("answer", ""),
            "contexts": result.get("contexts", [])
        }