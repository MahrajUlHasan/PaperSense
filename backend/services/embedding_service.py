"""
Embedding service with multiple providers:

"""
from __future__ import annotations

import base64
import io
import time
from collections import deque
from typing import List, Dict, Optional
from google.genai import types

import openai
from loguru import logger

from config import settings

# Optional: LangChain Google GenAI embeddings
try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning(
        "langchain-google-genai not installed – LangChain embedding provider "
        "unavailable.  Install with: pip install langchain-google-genai"
    )

# Google GenAI (already a project dependency)
from google import genai
from google.genai import types as genai_types


# ---------------------------------------------------------------------------
# Rate limiter – keeps Google API calls under MAX_RPM requests per minute
# ---------------------------------------------------------------------------

MAX_RPM = 95  # stay slightly below the 100 RPM hard limit


class _RateLimiter:
    """Simple sliding-window rate limiter (per-instance)."""

    def __init__(self, max_rpm: int = MAX_RPM):
        self.max_rpm = max_rpm
        self._timestamps: deque[float] = deque()

    def wait_if_needed(self) -> None:
        """Block until a new request is allowed under the RPM budget."""
        now = time.time()
        window = 60.0  # one-minute sliding window

        # Evict timestamps older than the window
        while self._timestamps and self._timestamps[0] <= now - window:
            self._timestamps.popleft()

        if len(self._timestamps) >= self.max_rpm:
            # Must wait until the oldest request falls outside the window
            sleep_for = self._timestamps[0] + window - now + 0.05
            if sleep_for > 0:
                logger.debug(f"Rate-limiter: sleeping {sleep_for:.2f}s")
                time.sleep(sleep_for)

        self._timestamps.append(time.time())


# ---------------------------------------------------------------------------
# Content-type aware text preparation helpers
# ---------------------------------------------------------------------------

def _prepare_text_for_embedding(chunk: Dict) -> str:
    """
    Return an embedding-optimised text string based on the chunk's
    content_type (text | table | image).
    """
    content_type = chunk.get("content_type", "text")
    if content_type == "table":
        return _prepare_table_text(chunk)
    elif content_type == "image":
        return _prepare_image_text(chunk)
    return chunk.get("text", "")


def _prepare_table_text(chunk: Dict) -> str:
    """Build a richer textual representation of a table chunk."""
    raw = chunk.get("text", "")
    # If the chunker already prefixed with [TABLE …], keep it
    if raw.startswith("[TABLE"):
        return raw
    table_html = chunk.get("table_html", "")
    return f"[TABLE] {raw}" if not table_html else f"[TABLE]\n{raw}"


def _prepare_image_text(chunk: Dict) -> str:
    """Build a textual representation of an image chunk (caption based)."""
    raw = chunk.get("text", "")
    if raw.startswith("[FIGURE"):
        return raw
    return f"[FIGURE] {raw}"


class EmbeddingService:
    """Generate embeddings using OpenAI API"""

    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model
        self.embedding_dimension = 1536

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding of dimension {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch

        Returns:
            List of embedding vectors
        """
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}, size: {len(batch)}")

            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                # Fallback to individual processing
                for text in batch:
                    try:
                        emb = self.generate_embedding(text)
                        embeddings.append(emb)
                    except:
                        logger.error(f"Failed to embed text: {text[:50]}...")
                        embeddings.append([0.0] * self.embedding_dimension)

        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings

    def embed_chunks(self, chunks: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Add embeddings to chunk dictionaries.
        Uses content-type-aware text preparation for tables and images.
        """
        texts = [_prepare_text_for_embedding(chunk) for chunk in chunks]
        embeddings = self.generate_embeddings_batch(texts)

        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding

        return chunks


########################## LANGCHAIN EMBEDDING ######################################


class LangChainEmbeddingService:
    """
    Embedding service using LangChain with Google Generative AI
    ( 768-d by default).
    """

    def __init__(self):
        if not LANGCHAIN_AVAILABLE:
            raise RuntimeError(
                "langchain-google-genai is not installed. "
                "Install with: pip install langchain-google-genai"
            )
        self.model_name = getattr(settings, "gemma_embedding_model",
                                  "gemini-embedding-2-preview")
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=self.model_name,
            google_api_key=settings.google_api_key,
        )
        self.embedding_dimension = 768
        self._rate_limiter = _RateLimiter()
        logger.info(f"LangChain embedding service initialised ({self.model_name})")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        try:
            self._rate_limiter.wait_if_needed()
            return self.embeddings.embed_query(text)
        except Exception as e:
            logger.error(f"LangChain embedding failed: {e}")
            raise

    def generate_embeddings_batch(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """Generate embeddings for a batch of texts (rate-limited to <100 RPM)."""
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            logger.info(f"LangChain batch {i // batch_size + 1}, size: {len(batch)}")
            try:
                self._rate_limiter.wait_if_needed()
                all_embeddings.extend(self.embeddings.embed_documents(batch))
            except Exception as e:
                logger.error(f"LangChain batch embedding failed: {e}")
                for text in batch:
                    try:
                        self._rate_limiter.wait_if_needed()
                        all_embeddings.append(self.generate_embedding(text))
                    except Exception:
                        logger.error(f"Failed to embed text: {text[:50]}...")
                        all_embeddings.append([0.0] * self.embedding_dimension)
        logger.info(f"LangChain generated {len(all_embeddings)} embeddings")
        return all_embeddings

    def embed_chunks(self, chunks: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """Add embeddings to chunk dicts (content-type aware)."""
        texts = [_prepare_text_for_embedding(c) for c in chunks]
        embeddings = self.generate_embeddings_batch(texts)
        for chunk, emb in zip(chunks, embeddings):
            chunk["embedding"] = emb
        return chunks


########################## GEMMA / GOOGLE GENAI EMBEDDING ###########################


class GemmaEmbeddingService:
    """
    Embedding service using Google GenAI directly.
    Model: text-embedding-004 (768-d).
    Supports native multimodal image embedding via PIL images.
    """

    def __init__(self):
        self.client = genai.Client(api_key=settings.google_api_key)
        self.model_name = "gemini-embedding-2-preview"
        self.multimodal_embedding_model = getattr(settings, "gemma_multimodal_model", "gemini-embedding-2-preview")
        self.embedding_dimension = 3072 #768
        self._rate_limiter = _RateLimiter()
        logger.info(f"Gemma embedding service initialised ({self.model_name})")

    # ---- single text ----
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text string."""
        try:
            self._rate_limiter.wait_if_needed()
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=text,
                config=types.EmbedContentConfig(task_type="QUESTION_ANSWERING"),
            )
            return response.embeddings[0].values
        except Exception as e:
            logger.error(f"Gemma embedding failed: {e}")
            raise

    # ---- batch text ----
    def generate_embeddings_batch(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """Generate embeddings for a list of texts (rate-limited to <100 RPM)."""
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            logger.info(f"Gemma batch {i // batch_size + 1}, size: {len(batch)}")
            try:
                self._rate_limiter.wait_if_needed()
                response = self.client.models.embed_content(
                    model=self.model_name,
                    contents=batch,
                    config=types.EmbedContentConfig(task_type="QUESTION_ANSWERING"),
                )
                all_embeddings.extend([e.values for e in response.embeddings])
            except Exception as e:
                logger.error(f"Gemma batch embedding failed: {e}")
                for text in batch:
                    try:
                        self._rate_limiter.wait_if_needed()
                        all_embeddings.append(self.generate_embedding(text))
                    except Exception:
                        logger.error(f"Failed to embed text: {text[:50]}...")
                        all_embeddings.append([0.0] * self.embedding_dimension)
        logger.info(f"Gemma generated {len(all_embeddings)} embeddings")
        return all_embeddings

    # ---- image embedding (multimodal) ----
    def generate_image_embedding(self, image_base64: str) -> List[float]:
        """
        Generate embedding for an image using Google GenAI multimodal
        embedding.  Accepts a base64-encoded PNG string.
        """
        try:
            from PIL import Image
            self._rate_limiter.wait_if_needed()
            img_bytes = base64.b64decode(image_base64)
            pil_image = Image.open(io.BytesIO(img_bytes))
            response = self.client.models.embed_content(
                model=self.multimodal_embedding_model,
                contents=pil_image,
            )
            return response.embeddings[0].values
        except Exception as e:
            logger.warning(f"Image embedding failed, falling back to caption: {e}")
            return []

    # ---- content-type aware chunk embedding ----
    def embed_chunks(self, chunks: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """
        Add embeddings to chunk dicts.
        For image chunks with base64 data, attempts native multimodal
        embedding; falls back to caption text if unavailable.
        """
        text_indices: List[int] = []
        text_list: List[str] = []

        for idx, chunk in enumerate(chunks):
            ct = chunk.get("content_type", "text")
            if ct == "image" and chunk.get("image_base64"):
                emb = self.generate_image_embedding(chunk["image_base64"])
                logger.debug(f"Generated Image embedding: {emb}")
                if emb:
                    chunk["embedding"] = emb
                    continue
            # Fallback / text / table: collect for batch text embedding
            text_indices.append(idx)
            text_list.append(_prepare_text_for_embedding(chunk))

        if text_list:
            batch_embs = self.generate_embeddings_batch(text_list)
            for ti, emb in zip(text_indices, batch_embs):
                chunks[ti]["embedding"] = emb

        return chunks


# ---------------------------------------------------------------------------
# Factory – select embedding provider based on configuration
# ---------------------------------------------------------------------------

EMBEDDING_DIMENSIONS = {
    "openai": 1536,
    "langchain": 768,
    "gemma": 768,
}


def get_embedding_service(provider: Optional[str] = None):
    """
    Return an embedding service instance for the requested provider.

    Args:
        provider: One of 'openai', 'langchain', 'gemma'.
                  Defaults to ``settings.embedding_provider``.
    """
    provider = (provider or getattr(settings, "embedding_provider", "gemma")).lower()

    if provider == "langchain":
        logger.info("Using LangChain (Google GenAI) embedding provider")
        return LangChainEmbeddingService()
    elif provider in ("gemma", "google"):
        logger.info("Using Gemma / Google GenAI embedding provider")
        return GemmaEmbeddingService()
    else:
        logger.info("Using OpenAI embedding provider")
        return EmbeddingService()