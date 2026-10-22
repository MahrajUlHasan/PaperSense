"""Build the right provider from the credentials a request carried."""
from __future__ import annotations

from services.llm.base import LLMCredentials, LLMProvider
from services.llm.errors import ProviderError
from services.llm.gemini import GeminiProvider
from services.llm.openai_compat import OpenAICompatibleProvider

PROVIDERS = ("gemini", "groq", "openrouter")


def build_provider(creds: LLMCredentials) -> LLMProvider:
    if creds.provider == "gemini":
        return GeminiProvider(creds.api_key, creds.model)
    if creds.provider in ("groq", "openrouter"):
        return OpenAICompatibleProvider(creds.provider, creds.api_key, creds.model)
    raise ProviderError(f"Unknown provider '{creds.provider}'.", kind="bad_request", provider=creds.provider)
