"""
RAG (Retrieval-Augmented Generation) Pipeline
Combines all services for end-to-end document processing and querying
"""
from typing import Dict, List, Optional
import uuid
from loguru import logger

from services.pdf_parser import PDFParser
from services.chunker import Chunker
from services.embedding_service import get_embedding_service, EMBEDDING_DIMENSIONS
from services.vector_store import VectorStore
from services.llm_service import LLMService
from services.conversation_memory import ConversationMemory
from config import settings


class RAGPipeline:
    """Main RAG pipeline orchestrating all services"""

    def __init__(self):
        self.pdf_parser = PDFParser()
        self.text_chunker = Chunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        self.embedding_service = get_embedding_service()
        self.vector_store = VectorStore()
        self.vector_store.recreate_collection(self.embedding_service.embedding_dimension)
        self.llm_service = LLMService()
        self.conversation_memory = ConversationMemory()

        logger.info("RAG Pipeline initialized")

    def set_embedding_service(self, provider: str) -> Dict[str, any]:
        """
        Switch the active embedding provider at runtime.

        If the new provider uses a different vector dimension the Qdrant
        collection is automatically dropped and recreated so that the
        stored vectors stay consistent with the active embeddings.

        Args:
            provider: One of 'openai', 'langchain', 'gemma'

        Returns:
            Dict with success status, provider name, model, and dimension
        """
        try:
            new_service = get_embedding_service(provider)
            old_dimension = self.embedding_service.embedding_dimension
            new_dimension = new_service.embedding_dimension

            self.embedding_service = new_service

            # Recreate the Qdrant collection when the dimension changes
            if new_dimension != old_dimension:
                logger.warning(
                    f"Embedding dimension changed ({old_dimension} → {new_dimension}). "
                    "Recreating Qdrant collection – all existing vectors will be removed."
                )
                self.vector_store.recreate_collection(new_dimension)

            provider_lower = provider.lower()
            return {
                "success": True,
                "provider": provider_lower,
                "model": getattr(new_service, "model", None)
                         or getattr(new_service, "model_name", "unknown"),
                "dimension": new_dimension,
            }
        except Exception as e:
            logger.error(f"Failed to switch embedding provider: {e}")
            return {"success": False, "error": str(e)}

    def get_embedding_info(self) -> Dict[str, any]:
        """Return information about the currently active embedding service."""
        svc = self.embedding_service
        cls_name = type(svc).__name__
        provider_map = {
            "EmbeddingService": "openai",
            "LangChainEmbeddingService": "langchain",
            "GemmaEmbeddingService": "gemma",
        }
        return {
            "provider": provider_map.get(cls_name, cls_name),
            "model": getattr(svc, "model", None)
                     or getattr(svc, "model_name", "unknown"),
            "dimension": svc.embedding_dimension,
            "available_providers": list(EMBEDDING_DIMENSIONS.keys()),
        }

    def process_document(self, pdf_file: bytes, filename: str) -> Dict[str, any]:
        """
        Process a PDF document through the entire pipeline

        Args:
            pdf_file: PDF file as bytes
            filename: Original filename

        Returns:
            Processing result with document_id and statistics
        """
        try:
            # Generate unique document ID
            document_id = str(uuid.uuid4())
            logger.info(f"Processing document {filename} with ID {document_id}")

            # Step 1: Parse PDF
            logger.info("Step 1: Parsing PDF")
            parsed_data = self.pdf_parser.parse_pdf(pdf_file, filename)

            if not parsed_data['text']:
                return {
                    "success": False,
                    "error": "Failed to extract text from PDF"
                }

            # Step 2: Chunk text
            logger.info("Step 2: Chunking text")
            doc_metadata = {
                "filename": filename,
                "title": parsed_data['metadata'].get('title', 'Unknown'),
                "author": parsed_data['metadata'].get('author', 'Unknown'),
                "page_count": parsed_data['page_count']
            }

            chunks = self.text_chunker.chunk_text(
                parsed_data['text'],
                metadata=doc_metadata,
            )

            # Step 2b: Create table chunks
            tables = parsed_data.get('tables', [])
            table_chunks = self.text_chunker.create_table_chunks(
                tables,
                metadata=doc_metadata,
                start_chunk_id=len(chunks),
            )
            chunks.extend(table_chunks)

            # Step 2c: Create image chunks
            images = parsed_data.get('images', [])
            image_chunks = self.text_chunker.create_image_chunks(
                images,
                metadata=doc_metadata,
                start_chunk_id=len(chunks),
            )
            chunks.extend(image_chunks)

            if not chunks:
                return {
                    "success": False,
                    "error": "Failed to create chunks"
                }

            # Step 3: Generate embeddings
            logger.info("Step 3: Generating embeddings")
            chunks_with_embeddings = self.embedding_service.embed_chunks(chunks)

            # Step 4: Store in vector database
            logger.info("Step 4: Storing in vector database")
            success = self.vector_store.add_documents(chunks_with_embeddings, document_id)

            if not success:
                return {
                    "success": False,
                    "error": "Failed to store in vector database"
                }

            # Return success with statistics
            return {
                "success": True,
                "document_id": document_id,
                "filename": filename,
                "metadata": parsed_data['metadata'],
                "statistics": {
                    "page_count": parsed_data['page_count'],
                    "char_count": parsed_data['char_count'],
                    "chunk_count": len(chunks),
                    "table_count": len(table_chunks),
                    "image_count": len(image_chunks),
                }
            }

        except Exception as e:
            logger.error(f"Document processing error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def query(
        self,
        question: str,
        document_id: Optional[str] = None,
        top_k: int = None,
        use_hybrid: bool = False,
    ) -> Dict[str, any]:
        """
        Query the knowledge base with a question.

        Args:
            question: User's question
            document_id: Optional specific document to search
            top_k: Number of chunks to retrieve
            use_hybrid: If True, use hybrid search (dense + BM25 → ColBERT rerank)

        Returns:
            Answer with citations and context
        """
        try:
            if top_k is None:
                top_k = settings.top_k_results

            mode = "hybrid" if use_hybrid else "dense"
            logger.info(f"Processing query ({mode}): {question}")

            # Step 1: Generate dense query embedding
            logger.info("Step 1: Generating query embedding")
            query_embedding = self.embedding_service.generate_embedding(question)

            # Step 2: Retrieve relevant chunks
            if use_hybrid:
                logger.info("Step 2: Hybrid search (dense + BM25 → ColBERT rerank)")
                retrieved_chunks = self.vector_store.hybrid_search(
                    query_vector=query_embedding,
                    query_text=question,
                    top_k=top_k,
                    document_id=document_id,
                )
            else:
                logger.info("Step 2: Dense-only search")
                retrieved_chunks = self.vector_store.search(
                    query_vector=query_embedding,
                    top_k=top_k,
                    document_id=document_id,
                    score_threshold=settings.similarity_threshold,
                )

            # Step 3: Get conversation history for follow-up awareness
            history = self.conversation_memory.get_context_for_prompt()

            # Step 4: Generate answer using LLM
            logger.info("Step 4: Generating answer")
            result = self.llm_service.answer_question(
                question, retrieved_chunks, conversation_history=history
            )

            result["success"] = True
            result["question"] = question
            result["search_mode"] = mode
            if not retrieved_chunks:
                result["error"] = "No relevant information found."

            # Step 5: Record this Q&A turn in conversation memory
            self.conversation_memory.add_turn(question, result["answer"])

            logger.debug(f"Query processed successfully. Answer: {result['answer']}")
            return result

        except Exception as e:
            logger.error(f"Query error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def analyze_document(self, document_id: str) -> Dict[str, any]:
        """
        Perform comprehensive analysis of a document

        Args:
            document_id: Document to analyze

        Returns:
            Analysis results including summary, findings, methodology, limitations
        """
        try:
            logger.info(f"Analyzing document {document_id}")

            # Retrieve all chunks for the document using scroll (no dummy vector needed)
            all_chunks = self.vector_store.get_by_document_id(document_id)

            if not all_chunks:
                return {
                    "success": False,
                    "error": "Document not found"
                }

            # Separate chunks by content type
            text_chunks = [c for c in all_chunks if c.get('content_type', 'text') == 'text']
            table_chunks = [c for c in all_chunks if c.get('content_type') == 'table']
            image_chunks = [c for c in all_chunks if c.get('content_type') == 'image']

            # Combine text from chunks (use first 20 text chunks)
            full_text = " ".join([chunk['text'] for chunk in text_chunks[:20]])

            # Append table data to context so the LLM can reference it
            if table_chunks:
                table_text = "\n\n".join([c['text'] for c in table_chunks[:10]])
                full_text += f"\n\n--- TABLES FOUND IN THE PAPER ---\n{table_text}"

            # Append image/figure captions
            if image_chunks:
                fig_text = "\n".join([c['text'] for c in image_chunks[:10]])
                full_text += f"\n\n--- FIGURES/IMAGES IN THE PAPER ---\n{fig_text}"

            # Generate various analyses
            logger.info("Generating summary")
            summary = self.llm_service.generate_summary(full_text)

            logger.info("Extracting key findings")
            key_findings = self.llm_service.extract_key_findings(full_text)

            logger.info("Identifying methodology")
            methodology = self.llm_service.identify_methodology(full_text)

            logger.info("Extracting limitations")
            limitations = self.llm_service.extract_limitations(full_text)

            return {
                "success": True,
                "document_id": document_id,
                "summary": summary,
                "key_findings": key_findings,
                "methodology": methodology,
                "limitations": limitations,
                "metadata": all_chunks[0].get('metadata', {}) if all_chunks else {}
            }

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def delete_document(self, document_id: str) -> Dict[str, any]:
        """Delete a document from the vector store"""
        try:
            success = self.vector_store.delete_document(document_id)
            return {
                "success": success,
                "document_id": document_id
            }
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_stats(self) -> Dict[str, any]:
        """Get statistics about the vector store"""
        try:
            info = self.vector_store.get_collection_info()
            return {
                "success": True,
                "stats": info
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


    # ── Research context ──────────────────────────────────────────

    def set_research(self, topic: str, description: str) -> Dict[str, any]:
        """
        Store the research context and generate a detailed breakdown
        using the LLM. The breakdown is cached for document scoring.
        """
        try:
            logger.info(f"Setting research topic: {topic}")
            breakdown = self.llm_service.generate_research_breakdown(topic, description)
            self._research = {
                "topic": topic,
                "description": description,
                "breakdown": breakdown,
            }
            logger.info("Research breakdown generated and stored")
            return {
                "success": True,
                "topic": topic,
                "description": description,
                "breakdown": breakdown,
            }
        except Exception as e:
            logger.error(f"Research error: {e}")
            return {"success": False, "error": str(e)}

    def get_research(self) -> Dict[str, any]:
        """Return the currently stored research context."""
        r = getattr(self, "_research", None)
        if not r:
            return {"success": True, "topic": "", "description": "", "breakdown": ""}
        return {"success": True, **r}

    def score_document(self, document_id: str) -> Dict[str, any]:
        """Score a document against the current research context."""
        try:
            r = getattr(self, "_research", None)
            if not r or not r.get("topic"):
                return {
                    "success": False,
                    "error": "No research topic set. Set a research topic first.",
                }

            # Get document text from vector store
            all_chunks = self.vector_store.get_by_document_id(document_id)
            if not all_chunks:
                return {"success": False, "error": "Document not found"}

            text_chunks = [c for c in all_chunks if c.get("content_type", "text") == "text"]
            full_text = " ".join([c["text"] for c in text_chunks[:15]])
            filename = all_chunks[0].get("metadata", {}).get("filename", "unknown")

            result = self.llm_service.score_document_relevance(
                full_text, filename, r["topic"], r["breakdown"]
            )

            return {
                "success": True,
                "document_id": document_id,
                "filename": filename,
                "score": result["score"],
                "explanation": result["explanation"],
            }
        except Exception as e:
            logger.error(f"Scoring error: {e}")
            return {"success": False, "error": str(e)}