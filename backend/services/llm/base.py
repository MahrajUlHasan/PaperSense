"""What every LLM provider looks like to the rest of the app."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, TypeVar

from loguru import logger

from services.llm.errors import ProviderError

T = TypeVar("T")


@dataclass(frozen=True)
class LLMCredentials:
    """Provider, key and model for one request. Its repr never shows the key."""

    provider: str
    api_key: str
    model: str

    def __repr__(self) -> str:
        return f"LLMCredentials(provider={self.provider!r}, model={self.model!r}, api_key='***')"


@dataclass
class ImageInput:
    data: bytes
    mime_type: str = "image/png"


class LLMProvider(ABC):
    name = "base"
    supports_images = False

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        images: list[ImageInput] | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 4096,
        json_mode: bool = False,
    ) -> str:
        """Return the model's text, or raise ProviderError."""


def call_with_retries(fn: Callable[[], T], *, max_attempts: int = 3) -> T:
    """Retry short-lived failures (overloaded server, per-minute limit) with backoff."""
    delay = 2.0
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except ProviderError as err:
            retryable = err.kind == "unavailable" or (
                err.kind == "rate_limited" and err.retry_after is not None and err.retry_after <= 30
            )
            if not retryable or attempt == max_attempts:
                raise
            wait = err.retry_after or delay
            logger.warning(f"{err.provider}: {err.kind}, retrying in {wait:.0f}s ({attempt}/{max_attempts})")
            time.sleep(wait)
            delay *= 2
    raise AssertionError("unreachable")
