"""Free judge for the RAGAS metrics, plus the backend's local embeddings.

v1 was judged by OpenAI gpt-4o (paid). v2 uses a free model through the backend's own
provider classes, so key handling and error mapping are the same as in the app:

- mistral: mistral-medium-latest on Mistral's free "Experiment" plan (needs MISTRAL_API_KEY)
- gemini:  gemini-3.1-flash-lite (or any Gemini-API model such as gemma-4-31b-it)
"""
from __future__ import annotations

import asyncio
import json
import threading
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError
from ragas.embeddings.base import BaseRagasEmbedding
from ragas.llms.base import InstructorBaseRagasLLM

from pacing import patient_call
from services.embeddings import EmbeddingService
from services.json_utils import parse_json
from services.llm import GeminiProvider, LLMProvider
from services.llm.openai_compat import OpenAICompatibleProvider
from services.rate_limit import RateLimiter

T = TypeVar("T", bound=BaseModel)

JUDGES = {
    "mistral": {"model": "mistral-medium-latest", "rpm": 30},
    "gemini": {"model": "gemini-3.1-flash-lite", "rpm": 12},
}
SCHEMA_NOTE = "\n\nReturn ONLY a JSON object that matches this JSON schema, with no other text:\n{schema}"
RETRY_NOTE = "\n\nYour previous reply was not valid JSON for this schema. Reply with the JSON object only."


def judge_provider(provider: str, api_key: str, model: str) -> LLMProvider:
    if provider == "gemini":
        return GeminiProvider(api_key, model)
    return OpenAICompatibleProvider(provider, api_key, model)


class Judge(InstructorBaseRagasLLM):
    """RAGAS judge backed by one of the backend's providers.

    RAGAS passes a prompt and a pydantic model. The model's JSON schema is added to the
    prompt, the reply is validated against it, and a malformed reply is asked for once more.
    Replies are kept per prompt: at temperature 0 the same prompt gives the same reply, so
    AnswerRelevancy's three identical question-generation prompts cost one request.
    """

    def __init__(self, provider: str, api_key: str, model: str, rpm: int):
        self.model = model
        self._key = api_key
        self._provider = judge_provider(provider, api_key, model)
        self._limiter = RateLimiter(per_minute=rpm)
        self._replies: dict[str, BaseModel] = {}
        self._lock = threading.Lock()
        self.requests = 0

    def _ask(self, prompt: str) -> str:
        with self._lock:
            self.requests += 1
        return patient_call(
            lambda: self._provider.generate(prompt, temperature=0.0, max_output_tokens=4096, json_mode=True),
            label=f"judge {self.model}", limiter=self._limiter, key=self._key,
        )

    def generate(self, prompt: str, response_model: Type[T]) -> T:
        full_prompt = prompt + SCHEMA_NOTE.format(schema=json.dumps(response_model.model_json_schema()))
        with self._lock:
            known = self._replies.get(full_prompt)
        if known is not None:
            return known
        error: Exception | None = None
        for attempt_prompt in (full_prompt, full_prompt + RETRY_NOTE):
            try:
                reply = response_model.model_validate(parse_json(self._ask(attempt_prompt)))
            except (ValidationError, ValueError) as err:
                error = err
                continue
            with self._lock:
                self._replies[full_prompt] = reply
            return reply
        raise ValueError(f"The judge's reply didn't match {response_model.__name__}: {error}")

    async def agenerate(self, prompt: str, response_model: Type[T]) -> T:
        return await asyncio.to_thread(self.generate, prompt, response_model)


class LocalEmbeddings(BaseRagasEmbedding):
    """The backend's FastEmbed model (BAAI/bge-base-en-v1.5) for AnswerRelevancy: free and offline.

    Every text is embedded the same way, because the metric compares questions with questions.
    """

    def __init__(self, embedder: EmbeddingService):
        super().__init__()
        self._embedder = embedder

    def embed_text(self, text: str, **kwargs) -> list[float]:
        return self._embedder.embed_documents([text])[0]

    async def aembed_text(self, text: str, **kwargs) -> list[float]:
        return await asyncio.to_thread(self.embed_text, text)

    def embed_texts(self, texts: list[str], **kwargs) -> list[list[float]]:
        return self._embedder.embed_documents(list(texts))

    async def aembed_texts(self, texts: list[str], **kwargs) -> list[list[float]]:
        return await asyncio.to_thread(self.embed_texts, texts)
