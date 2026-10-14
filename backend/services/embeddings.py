"""Dense embeddings computed locally with FastEmbed: free, CPU-only, no API key.

One fixed model for the whole collection: every document must be embedded with
the same model, or search breaks.
"""
from __future__ import annotations

from fastembed import TextEmbedding
from loguru import logger

from config import settings


class EmbeddingService:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.dense_model
        logger.info(f"Loading embedding model {self.model_name} (downloaded on first use)")
        self._model = TextEmbedding(model_name=self.model_name)
        self.dimension = len(self.embed_query("dimension probe"))

    def embed_documents(self, texts: list[str], batch_size: int = 16) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.embed(texts, batch_size=batch_size)]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self._model.query_embed(text))).tolist()
