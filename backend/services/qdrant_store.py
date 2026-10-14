"""Qdrant Cloud storage for chunks: dense + BM25 + ColBERT vectors per chunk."""
from __future__ import annotations

import uuid
from typing import Iterable

from fastembed import LateInteractionTextEmbedding, SparseTextEmbedding
from loguru import logger
from qdrant_client import QdrantClient, models

from config import settings
from services.chunk_models import ChunkRecord

BM25_MODEL = "Qdrant/bm25"
COLBERT_MODEL = "colbert-ir/colbertv2.0"
COLBERT_DIM = 128
UPSERT_BATCH = 8
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

    def _bm25_model(self) -> SparseTextEmbedding:
        if self._bm25 is None:
            self._bm25 = SparseTextEmbedding(BM25_MODEL)
        return self._bm25

    def _colbert_model(self) -> LateInteractionTextEmbedding:
        if self._colbert is None:
            logger.info("Loading ColBERT reranker (first run downloads it)")
            self._colbert = LateInteractionTextEmbedding(COLBERT_MODEL)
        return self._colbert

    @staticmethod
    def point_id(document_id: str, order: int) -> str:
        """Same document + same order -> same id, so re-indexing overwrites instead of duplicating."""
        return str(uuid.uuid5(uuid.UUID(document_id), str(order)))

    def upsert_chunks(
        self,
        *,
        document_id: str,
        workspace_id: str,
        filename: str,
        title: str,
        records: list[ChunkRecord],
        dense_vectors: list[list[float]],
    ) -> int:
        """Store chunks with their dense, BM25 and ColBERT vectors.

        Points are sent UPSERT_BATCH at a time: ColBERT vectors are large, and small
        batches stay under Qdrant's request size limit.
        """
        if len(records) != len(dense_vectors):
            raise ValueError("records and dense_vectors must have the same length")
        texts = [r.embed_text or r.text for r in records]
        sparse = list(self._bm25_model().embed(texts))
        late = list(self._colbert_model().embed(texts))

        for start in range(0, len(records), UPSERT_BATCH):
            points = []
            for i in range(start, min(start + UPSERT_BATCH, len(records))):
                record = records[i]
                points.append(
                    models.PointStruct(
                        id=self.point_id(document_id, record.order),
                        vector={
                            "dense": dense_vectors[i],
                            "bm25": models.SparseVector(
                                indices=sparse[i].indices.tolist(), values=sparse[i].values.tolist()
                            ),
                            "colbert": late[i].tolist(),
                        },
                        payload=record.to_payload(
                            document_id=document_id, workspace_id=workspace_id,
                            filename=filename, title=title,
                        ),
                    )
                )
            self.client.upsert(collection_name=self.collection, points=points, wait=True)
        logger.info(f"Stored {len(records)} chunks for {filename} ({document_id})")
        return len(records)

    def delete_document(self, document_id: str) -> None:
        self.client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(filter=self._document_filter(document_id)),
            wait=True,
        )

    def count_document(self, document_id: str) -> int:
        return self.client.count(
            collection_name=self.collection, count_filter=self._document_filter(document_id), exact=True
        ).count

    @staticmethod
    def _document_filter(document_id: str) -> models.Filter:
        return models.Filter(
            must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
        )

    @staticmethod
    def _search_filter(workspace_id: str, document_ids: Iterable[str] | None = None) -> models.Filter:
        must = [models.FieldCondition(key="workspace_id", match=models.MatchValue(value=workspace_id))]
        ids = [d for d in (document_ids or []) if d]
        if ids:
            must.append(models.FieldCondition(key="document_id", match=models.MatchAny(any=ids)))
        return models.Filter(must=must)

    @staticmethod
    def _hit(point) -> dict:
        data = dict(point.payload or {})
        data["id"] = str(point.id)
        data["score"] = float(getattr(point, "score", None) or 0.0)
        return data

    def dense_search(self, query_vector: list[float], workspace_id: str,
                     document_ids: Iterable[str] | None = None, limit: int = 6) -> list[dict]:
        response = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            using="dense",
            query_filter=self._search_filter(workspace_id, document_ids),
            limit=limit,
            with_payload=True,
        )
        return [self._hit(p) for p in response.points]

    def hybrid_search(self, query_text: str, query_vector: list[float], workspace_id: str,
                      document_ids: Iterable[str] | None = None, limit: int = 6,
                      prefetch_limit: int = 40) -> list[dict]:
        """Dense + BM25 candidates, reranked with ColBERT."""
        search_filter = self._search_filter(workspace_id, document_ids)
        sparse = next(iter(self._bm25_model().query_embed(query_text)))
        late = next(iter(self._colbert_model().query_embed(query_text)))
        response = self.client.query_points(
            collection_name=self.collection,
            prefetch=[
                models.Prefetch(query=query_vector, using="dense", limit=prefetch_limit, filter=search_filter),
                models.Prefetch(
                    query=models.SparseVector(indices=sparse.indices.tolist(), values=sparse.values.tolist()),
                    using="bm25", limit=prefetch_limit, filter=search_filter,
                ),
            ],
            query=late.tolist(),
            using="colbert",
            limit=limit,
            with_payload=True,
        )
        return [self._hit(p) for p in response.points]

    def get_document_chunks(self, document_id: str) -> list[dict]:
        """Every chunk of one paper, in reading order."""
        chunks: list[dict] = []
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=self._document_filter(document_id),
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            chunks.extend(self._hit(p) for p in points)
            if offset is None:
                break
        chunks.sort(key=lambda c: c.get("order", 0))
        return chunks

    def fetch_chunks(self, keys: Iterable[tuple[str, int]]) -> list[dict]:
        """Fetch chunks by (document_id, order) without a search."""
        ids = [self.point_id(doc_id, order) for doc_id, order in keys if order >= 0]
        if not ids:
            return []
        points = self.client.retrieve(collection_name=self.collection, ids=ids,
                                      with_payload=True, with_vectors=False)
        return [self._hit(p) for p in points]
