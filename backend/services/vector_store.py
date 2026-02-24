"""
Qdrant vector store service for storing and retrieving embeddings
"""
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, MatchValue, SearchParams
)
from loguru import logger
from config import settings
import uuid


class VectorStore:
    """Qdrant vector database manager"""
    
    def __init__(self):
        # Initialize Qdrant client
        if settings.qdrant_api_key:
            self.client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key
            )
        else:
            self.client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port
            )
        
        self.collection_name = settings.qdrant_collection_name
        self.embedding_dimension = 1536  # OpenAI text-embedding-3-small
        
        # Create collection if it doesn't exist
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info("Collection created successfully")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            raise
    
    def add_documents(self, chunks: List[Dict[str, any]], document_id: str) -> bool:
        """
        Add document chunks to vector store
        
        Args:
            chunks: List of chunks with embeddings
            document_id: Unique identifier for the document
            
        Returns:
            Success status
        """
        try:
            points = []
            
            for chunk in chunks:
                point_id = str(uuid.uuid4())
                
                payload = {
                    "document_id": document_id,
                    "chunk_id": chunk.get('chunk_id', 0),
                    "text": chunk['text'],
                    "section": chunk.get('section', 'unknown'),
                    "char_count": chunk.get('char_count', 0),
                    "metadata": chunk.get('metadata', {})
                }
                
                point = PointStruct(
                    id=point_id,
                    vector=chunk['embedding'],
                    payload=payload
                )
                points.append(point)
            
            # Upload points to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Added {len(points)} chunks for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False
    
    def search(
        self, 
        query_vector: List[float], 
        top_k: int = 5,
        document_id: Optional[str] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, any]]:
        """
        Search for similar chunks
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            document_id: Optional filter by document ID
            score_threshold: Minimum similarity score
            
        Returns:
            List of search results with text and metadata
        """
        try:
            # Build filter if document_id provided
            search_filter = None
            if document_id:
                search_filter = Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            
            # Perform search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=search_filter,
                score_threshold=score_threshold
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "section": result.payload.get("section", ""),
                    "document_id": result.payload.get("document_id", ""),
                    "chunk_id": result.payload.get("chunk_id", 0),
                    "metadata": result.payload.get("metadata", {})
                })

            logger.info(f"Found {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a document"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                )
            )
            logger.info(f"Deleted document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False

    def get_collection_info(self) -> Dict:
        """Get information about the collection"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}

