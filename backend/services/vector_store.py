"""
Qdrant vector store service for storing and retrieving embeddings
Updated to use the latest qdrant-client API (query_points)
"""
from typing import List, Dict, Optional
from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue
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
        """Create collection if it doesn't exist, and ensure payload indexes"""
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

            # Create payload indexes so filtered queries work
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="document_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="content_type",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            logger.info("Payload indexes on 'document_id' and 'content_type' ensured")

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
                
                content_type = chunk.get('content_type', 'text')
                payload = {
                    "document_id": document_id,
                    "chunk_id": chunk.get('chunk_id', 0),
                    "text": chunk['text'],
                    "section": chunk.get('section', 'unknown'),
                    "char_count": chunk.get('char_count', 0),
                    "content_type": content_type,
                    "metadata": chunk.get('metadata', {})
                }
                # Store table HTML for rich rendering
                if content_type == 'table' and chunk.get('table_html'):
                    payload["table_html"] = chunk['table_html']
                # Store image base64 for multimodal LLM usage
                if content_type == 'image' and chunk.get('image_base64'):
                    payload["image_base64"] = chunk['image_base64']
                
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
        Search for similar chunks using query_points (latest Qdrant API)

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

            # Perform search using query_points (replaces deprecated client.search)
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=search_filter,
                limit=top_k,
                score_threshold=score_threshold,
                with_payload=True,
            )

            # Format results — query_points returns a QueryResponse with .points
            formatted_results = []
            for point in response.points:
                result = {
                    "id": point.id,
                    "score": point.score,
                    "text": point.payload.get("text", ""),
                    "section": point.payload.get("section", ""),
                    "document_id": point.payload.get("document_id", ""),
                    "chunk_id": point.payload.get("chunk_id", 0),
                    "content_type": point.payload.get("content_type", "text"),
                    "metadata": point.payload.get("metadata", {})
                }
                # Include rich table/image data when present
                if point.payload.get("table_html"):
                    result["table_html"] = point.payload["table_html"]
                if point.payload.get("image_base64"):
                    result["image_base64"] = point.payload["image_base64"]
                formatted_results.append(result)

                # Log the payload in a nicely formatted JSON form
                try:
                    logger.debug("Point payload:\n" + json.dumps(point.payload, indent=2, ensure_ascii=False))
                except Exception:
                    logger.debug(f"Point payload (non-serializable): {point.payload}")

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
                points_selector=models.FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="document_id",
                                match=MatchValue(value=document_id)
                            )
                        ]
                    )
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

