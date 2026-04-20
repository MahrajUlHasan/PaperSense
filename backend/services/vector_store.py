"""
Qdrant vector store service for storing and retrieving embeddings
"""
from fastembed import SparseTextEmbedding, LateInteractionTextEmbedding
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
    """Qdrant vector database manager with hybrid search support"""

    # FastEmbed model identifiers
    BM25_MODEL = "Qdrant/bm25"
    COLBERT_MODEL = "colbert-ir/colbertv2.0"

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
        self.embedding_dimension = settings.embedding_dimension

        # Lazy-loaded FastEmbed models for hybrid search
        self._bm25_model: Optional[SparseTextEmbedding] = None
        self._colbert_model: Optional[LateInteractionTextEmbedding] = None

        # Create collection if it doesn't exist
        self._ensure_collection()

    # ── FastEmbed model loaders (lazy) ─────────────────────────────

    def _get_bm25_model(self) -> SparseTextEmbedding:
        if self._bm25_model is None:
            logger.info(f"Loading BM25 model: {self.BM25_MODEL}")
            self._bm25_model = SparseTextEmbedding(self.BM25_MODEL)
        return self._bm25_model

    def _get_colbert_model(self) -> LateInteractionTextEmbedding:
        if self._colbert_model is None:
            logger.info(f"Loading ColBERT model: {self.COLBERT_MODEL}")
            self._colbert_model = LateInteractionTextEmbedding(self.COLBERT_MODEL)
        return self._colbert_model

    # ── Collection management ──────────────────────────────────────

    def _ensure_collection(self):
        """Create collection with multi-vector config if it doesn't exist."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        # Dense embeddings from the active embedding provider
                        "dense": models.VectorParams(
                            size=self.embedding_dimension,
                            distance=models.Distance.COSINE,
                        ),
                        # ColBERT late-interaction embeddings for reranking
                        "colbert": models.VectorParams(
                            size=128,  # colbertv2.0 token dim
                            distance=models.Distance.COSINE,
                            multivector_config=models.MultiVectorConfig(
                                comparator=models.MultiVectorComparator.MAX_SIM,
                            ),
                            hnsw_config=models.HnswConfigDiff(m=0),  # no index – rerank only
                        ),
                    },
                    sparse_vectors_config={
                        # BM25 sparse embeddings
                        "bm25": models.SparseVectorParams(
                            modifier=models.Modifier.IDF,
                        ),
                    },
                )
                logger.info("Collection created with dense + bm25 + colbert vectors")
            else:
                logger.info(f"Collection {self.collection_name} already exists")

            # Payload indexes for filtered queries
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
    
    def recreate_collection(self, new_dimension: int) -> None:
        """
        Drop the existing collection and create a fresh one with the given
        vector dimension.  All previously stored vectors are lost.

        Args:
            new_dimension: Size of the new embedding vectors.
        """
        try:
            logger.warning(
                f"Recreating collection '{self.collection_name}' "
                f"(old dim={self.embedding_dimension}, new dim={new_dimension})"
            )
            # Delete the old collection if it exists
            collections = self.client.get_collections().collections
            if any(c.name == self.collection_name for c in collections):
                self.client.delete_collection(self.collection_name)
                logger.info(f"Deleted old collection '{self.collection_name}'")

            # Update dimension and recreate
            self.embedding_dimension = new_dimension
            self._ensure_collection()
            logger.info(
                f"Collection '{self.collection_name}' recreated with dimension {new_dimension}"
            )
        except Exception as e:
            logger.error(f"Error recreating collection: {e}")
            raise

    def add_documents(self, chunks: List[Dict[str, any]], document_id: str) -> bool:
        """
        Add document chunks to vector store.

        Each chunk MUST already have a ``embedding`` key (dense vector from the
        active embedding provider).  This method additionally computes BM25
        sparse and ColBERT late-interaction embeddings via FastEmbed and stores
        all three vector types in Qdrant.

        Args:
            chunks: List of chunks with dense embeddings
            document_id: Unique identifier for the document

        Returns:
            Success status
        """
        try:
            texts = [c["text"] for c in chunks]

            # ── Compute BM25 sparse embeddings ─────────────────────
            logger.info("Computing BM25 sparse embeddings for chunks")
            bm25_model = self._get_bm25_model()
            bm25_embeddings = list(bm25_model.embed(texts))

            # ── Compute ColBERT late-interaction embeddings ────────
            logger.info("Computing ColBERT late-interaction embeddings for chunks")
            colbert_model = self._get_colbert_model()
            colbert_embeddings = list(colbert_model.embed(texts))

            # ── Build points ───────────────────────────────────────
            points = []
            for idx, chunk in enumerate(chunks):
                point_id = str(uuid.uuid4())

                content_type = chunk.get("content_type", "text")
                payload = {
                    "document_id": document_id,
                    "chunk_id": chunk.get("chunk_id", 0),
                    "text": chunk["text"],
                    "section": chunk.get("section", "unknown"),
                    "char_count": chunk.get("char_count", 0),
                    "content_type": content_type,
                    "metadata": chunk.get("metadata", {}),
                }
                if content_type == "table" and chunk.get("table_html"):
                    payload["table_html"] = chunk["table_html"]
                if content_type == "image" and chunk.get("image_base64"):
                    payload["image_base64"] = chunk["image_base64"]

                point = PointStruct(
                    id=point_id,
                    vector={
                        "dense": chunk["embedding"],
                        "bm25": bm25_embeddings[idx].as_object(),
                        "colbert": colbert_embeddings[idx].tolist(),
                    },
                    payload=payload,
                )
                points.append(point)

            # Upload points to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

            logger.info(f"Added {len(points)} chunks for document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False
    
    # ── helpers ──────────────────────────────────────────────────────

    def _build_filter(self, document_id: Optional[str]) -> Optional[Filter]:
        if not document_id:
            return None
        return Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
        )

    @staticmethod
    def _format_point(point) -> Dict[str, any]:
        """Convert a Qdrant scored point into a flat dict."""
        result = {
            "id": point.id,
            "score": point.score,
            "text": point.payload.get("text", ""),
            "section": point.payload.get("section", ""),
            "document_id": point.payload.get("document_id", ""),
            "chunk_id": point.payload.get("chunk_id", 0),
            "content_type": point.payload.get("content_type", "text"),
            "metadata": point.payload.get("metadata", {}),
        }
        if point.payload.get("table_html"):
            result["table_html"] = point.payload["table_html"]
        if point.payload.get("image_base64"):
            result["image_base64"] = point.payload["image_base64"]
        return result

    # ── Dense-only search (existing behaviour) ─────────────────────

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Dict[str, any]]:
        """
        Dense-only search using the named ``dense`` vector.
        """
        try:
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                using="dense",
                query_filter=self._build_filter(document_id),
                limit=top_k,
                score_threshold=score_threshold,
                with_payload=True,
            )
            results = [self._format_point(p) for p in response.points]
            logger.info(f"Dense search: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Dense search error: {e}")
            return []

    # ── Hybrid search (dense + BM25 → ColBERT rerank) ──────────────

    def hybrid_search(
        self,
        query_vector: List[float],
        query_text: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        prefetch_limit: int = 20,
    ) -> List[Dict[str, any]]:
        """
          1. Prefetch with dense embeddings
          2. Prefetch with BM25 sparse embeddings
          3. Rerank the union using ColBERT late-interaction embeddings

        Args:
            query_vector: Dense embedding of the query (from the active provider)
            query_text:   Raw query string (needed for BM25 + ColBERT encoding)
            top_k:        Final number of results after reranking
            document_id:  Optional filter
            prefetch_limit: How many candidates each sub-query fetches
        """
        try:
            search_filter = self._build_filter(document_id)

            # Encode query for sparse + late-interaction
            bm25_model = self._get_bm25_model()
            colbert_model = self._get_colbert_model()

            sparse_vec = next(bm25_model.query_embed(query_text))
            late_vec = next(colbert_model.query_embed(query_text))

            # Build prefetch sub-queries
            prefetch = [
                models.Prefetch(
                    query=query_vector,
                    using="dense",
                    limit=prefetch_limit,
                    filter=search_filter,
                ),
                models.Prefetch(
                    query=models.SparseVector(**sparse_vec.as_object()),
                    using="bm25",
                    limit=prefetch_limit,
                    filter=search_filter,
                ),
            ]

            # Rerank with ColBERT
            response = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=prefetch,
                query=late_vec.tolist(),
                using="colbert",
                with_payload=True,
                limit=top_k,
            )

            results = [self._format_point(p) for p in response.points]
            logger.info(f"Hybrid search: {len(results)} results (prefetch={prefetch_limit})")
            return results

        except Exception as e:
            logger.error(f"Hybrid search error: {e}")
            return []

    def get_by_document_id(self, document_id: str, limit: int = 1000) -> List[Dict[str, any]]:
        """
        Retrieve all chunks for a specific document using scroll (no query vector needed).

        Args:
            document_id: The document to retrieve chunks for
            limit: Maximum number of chunks to return

        Returns:
            List of chunk dicts with text, metadata, etc.
        """
        try:
            doc_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )

            results = []
            offset = None
            while True:
                points, next_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=doc_filter,
                    limit=min(limit - len(results), 100),
                    with_payload=True,
                    offset=offset,
                )
                for point in points:
                    result = {
                        "id": point.id,
                        "text": point.payload.get("text", ""),
                        "section": point.payload.get("section", ""),
                        "document_id": point.payload.get("document_id", ""),
                        "chunk_id": point.payload.get("chunk_id", 0),
                        "content_type": point.payload.get("content_type", "text"),
                        "metadata": point.payload.get("metadata", {}),
                    }
                    if point.payload.get("table_data"):
                        result["table_data"] = point.payload["table_data"]
                    if point.payload.get("image_data"):
                        result["image_data"] = point.payload["image_data"]
                    results.append(result)

                if next_offset is None or len(results) >= limit:
                    break
                offset = next_offset

            logger.info(f"Retrieved {len(results)} chunks for document {document_id}")
            return results

        except Exception as e:
            logger.error(f"Error retrieving document chunks: {e}")
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
                "vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}

