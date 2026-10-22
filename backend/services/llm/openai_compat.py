"""Groq and OpenRouter: both speak the OpenAI chat API (text only here)."""
from __future__ import annotations

import openai

from services.llm.base import LLMProvider, call_with_retries
from services.llm.errors import ProviderError

BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}
DISPLAY = {"groq": "Groq", "openrouter": "OpenRouter"}


def map_openai_error(err: Exception, provider: str) -> ProviderError:
    name = DISPLAY.get(provider, provider)
    if isinstance(err, (openai.AuthenticationError, openai.PermissionDeniedError)):
        return ProviderError(f"{name} rejected this API key. Check it in Settings → API keys.",
                             kind="invalid_key", provider=provider)
    if isinstance(err, openai.RateLimitError):
        retry = None
        try:
            retry = float(err.response.headers.get("retry-after"))
        except (TypeError, ValueError, AttributeError):
            pass
        return ProviderError(f"{name} free-tier limit reached. Wait a little or try again later.",
                             kind="rate_limited", provider=provider, retry_after=retry)
    if isinstance(err, openai.NotFoundError):
        return ProviderError(f"This {name} model doesn't exist (anymore). Pick another model in Settings.",
                             kind="bad_request", provider=provider)
    if isinstance(err, openai.APIConnectionError):
        return ProviderError(f"Could not reach {name}.", kind="unavailable", provider=provider)
    if isinstance(err, openai.APIStatusError) and err.status_code >= 500:
        return ProviderError(f"{name} is busy right now. Please try again shortly.",
                             kind="unavailable", provider=provider)
    if isinstance(err, openai.BadRequestError):
        return ProviderError(f"{name} refused the request.", kind="bad_request", provider=provider)
    return ProviderError(f"{name} request failed.", kind="unknown", provider=provider)


class OpenAICompatibleProvider(LLMProvider):
    supports_images = False

    def __init__(self, provider: str, api_key: str, model: str):
        if provider not in BASE_URLS:
            raise ValueError(f"Unknown OpenAI-compatible provider: {provider}")
        super().__init__(api_key, model)
        self.name = provider
        self._client = openai.OpenAI(api_key=api_key, base_url=BASE_URLS[provider], max_retries=0, timeout=120)

    def generate(self, prompt, *, system=None, images=None, temperature=0.2,
                 max_output_tokens=4096, json_mode=False) -> str:
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": prompt})
        kwargs = {"model": self.model, "messages": messages, "temperature": temperature,
                  "max_tokens": max_output_tokens}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        def call():
            try:
                return self._client.chat.completions.create(**kwargs)
            except openai.OpenAIError as err:
                raise map_openai_error(err, self.name) from None

        response = call_with_retries(call)
        text = (response.choices[0].message.content or "").strip() if response.choices else ""
        if not text:
            raise ProviderError(f"{DISPLAY[self.name]} returned an empty answer.", kind="empty", provider=self.name)
        return text
