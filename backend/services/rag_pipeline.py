"""
RAG (Retrieval-Augmented Generation) Pipeline
Combines all services for end-to-end document processing and querying
"""
from typing import Dict, List, Optional
import uuid
from loguru import logger

from services.pdf_parser import PDFParser
from services.chunker import Chunker
from services.embedding_service import EmbeddingService
from services.vector_store import VectorStore
from services.llm_service import LLMService
from config import settings


class RAGPipeline:
    """Main RAG pipeline orchestrating all services"""
    
    def __init__(self):
        self.pdf_parser = PDFParser()
        self.text_chunker = Chunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.llm_service = LLMService()
        
        logger.info("RAG Pipeline initialized")
    
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
        top_k: int = None
    ) -> Dict[str, any]:
        """
        Query the knowledge base with a question
        
        Args:
            question: User's question
            document_id: Optional specific document to search
            top_k: Number of chunks to retrieve
            
        Returns:
            Answer with citations and context
        """
        try:
            if top_k is None:
                top_k = settings.top_k_results
            
            logger.info(f"Processing query: {question}")
            
            # Step 1: Generate query embedding
            logger.info("Step 1: Generating query embedding")
            query_embedding = self.embedding_service.generate_embedding(question)
            
            # Step 2: Retrieve relevant chunks
            logger.info("Step 2: Retrieving relevant chunks")
            retrieved_chunks = self.vector_store.search(
                query_vector=query_embedding,
                top_k=top_k,
                document_id=document_id,
                score_threshold=settings.similarity_threshold
            )
            
            if not retrieved_chunks:
                return {
                    "success": False,
                    "answer": "No relevant information found in the knowledge base.",
                    "citations": [],
                    "context_used": 0
                }
            
            # Step 3: Generate answer using LLM
            logger.info("Step 3: Generating answer")
            result = self.llm_service.answer_question(question, retrieved_chunks)
            
            result["success"] = True
            result["question"] = question
            
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

            # Retrieve all chunks for the document
            # Use a dummy query vector to get all chunks (search with high top_k)
            dummy_embedding = [0.0] * 1536
            all_chunks = self.vector_store.search(
                query_vector=dummy_embedding,
                top_k=1000,  # Get many chunks
                document_id=document_id,
                score_threshold=0.0  # No threshold
            )

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
