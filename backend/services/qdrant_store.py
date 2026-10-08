"""Qdrant Cloud storage for chunks: dense + BM25 + ColBERT vectors per chunk."""
from __future__ import annotations

from fastembed import LateInteractionTextEmbedding, SparseTextEmbedding
from loguru import logger
from qdrant_client import QdrantClient, models

from config import settings

BM25_MODEL = "Qdrant/bm25"
COLBERT_MODEL = "colbert-ir/colbertv2.0"
COLBERT_DIM = 128
PAYLOAD_INDEXES = {
    "workspace_id": models.PayloadSchemaType.KEYWORD,
    "document_id": models.PayloadSchemaType.KEYWORD,
    "content_type": models.PayloadSchemaType.KEYWORD,
    "order": models.PayloadSchemaType.INTEGER,
}


class CollectionMismatchError(RuntimeError):
    """The existing collection was made for a different embedding model."""


class QdrantStore:
    def __init__(self, dense_dim: int, collection: str | None = None, client: QdrantClient | None = None):
        if client is None and not settings.qdrant_url:
            raise RuntimeError("QDRANT_URL is not set in backend/.env")
        self.client = client or QdrantClient(
            url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=60
        )
        self.collection = collection or settings.qdrant_collection
        self.dense_dim = dense_dim
        self._bm25: SparseTextEmbedding | None = None
        self._colbert: LateInteractionTextEmbedding | None = None
        self.ensure_collection()

    def ensure_collection(self) -> None:
        """Create the collection if missing. Never deletes or recreates anything.

        The ColBERT vectors are only used for reranking, so they get no HNSW graph
        (m=0) and live on disk to save RAM on the free cluster. Creating a payload
        index that already exists raises on some server versions; that is ignored.
        """
        if not self.client.collection_exists(self.collection):
            logger.info(f"Creating Qdrant collection '{self.collection}' (dense size {self.dense_dim})")
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config={
                    "dense": models.VectorParams(size=self.dense_dim, distance=models.Distance.COSINE),
                    "colbert": models.VectorParams(
                        size=COLBERT_DIM,
                        distance=models.Distance.COSINE,
                        multivector_config=models.MultiVectorConfig(
                            comparator=models.MultiVectorComparator.MAX_SIM
                        ),
                        hnsw_config=models.HnswConfigDiff(m=0),
                        on_disk=True,
                    ),
                },
                sparse_vectors_config={
                    "bm25": models.SparseVectorParams(modifier=models.Modifier.IDF),
                },
            )
        else:
            vectors = self.client.get_collection(self.collection).config.params.vectors
            size = vectors["dense"].size if isinstance(vectors, dict) and "dense" in vectors else None
            if size != self.dense_dim:
                raise CollectionMismatchError(
                    f"Qdrant collection '{self.collection}' stores dense vectors of size {size}, "
                    f"but the embedding model produces size {self.dense_dim}. Set a new "
                    "QDRANT_COLLECTION name in backend/.env (nothing is deleted automatically)."
                )
        for field_name, schema in PAYLOAD_INDEXES.items():
            try:
                self.client.create_payload_index(self.collection, field_name=field_name, field_schema=schema)
            except Exception as exc:
                logger.debug(f"payload index {field_name}: {exc}")
