"""Google Gemini (free tier works, supports images)."""
from __future__ import annotations

import re

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from config import settings
from services.llm.base import ImageInput, LLMProvider, call_with_retries
from services.llm.errors import ProviderError


def _retry_after(text: str) -> float | None:
    match = re.search(r"retry in ([\d.]+)\s*s", text, re.IGNORECASE) or re.search(r"retryDelay'?:\s*'(\d+)s", text)
    return float(match.group(1)) if match else None


def map_gemini_error(err: genai_errors.APIError) -> ProviderError:
    code = getattr(err, "code", 0) or 0
    text = str(err)
    if code in (401, 403) or "API key not valid" in text or "API_KEY_INVALID" in text:
        return ProviderError("Google rejected this Gemini API key. Check it in Settings → API keys.",
                             kind="invalid_key", provider="gemini")
    if code == 429:
        return ProviderError("Gemini free-tier limit reached. Wait a little or try again later.",
                             kind="rate_limited", provider="gemini", retry_after=_retry_after(text))
    if code in (500, 502, 503, 504):
        return ProviderError("Gemini is busy right now. Please try again shortly.",
                             kind="unavailable", provider="gemini")
    if code == 404:
        return ProviderError("This Gemini model doesn't exist (anymore). Pick another model in Settings.",
                             kind="bad_request", provider="gemini")
    return ProviderError(f"Gemini request failed ({code}).",
                         kind="bad_request" if 400 <= code < 500 else "unknown", provider="gemini")


class GeminiProvider(LLMProvider):
    name = "gemini"
    supports_images = True

    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        self._client = genai.Client(api_key=api_key)

    def _config(self, *, system, temperature, max_output_tokens, json_mode) -> types.GenerateContentConfig:
        """Request settings.

        Gemini 2.5 "thinking" tokens count against the output limit; settings.gemini_thinking_budget
        caps them (None = model default, 0 = off on Flash).
        """
        thinking = None
        if settings.gemini_thinking_budget is not None and self.model.startswith("gemini-2.5"):
            thinking = types.ThinkingConfig(thinking_budget=settings.gemini_thinking_budget)
        return types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json" if json_mode else None,
            thinking_config=thinking,
        )

    def generate(self, prompt, *, system=None, images=None, temperature=0.2,
                 max_output_tokens=4096, json_mode=False) -> str:
        """Ask Gemini. An answer that hit the output limit gets a visible "cut off" note."""
        contents: list = [types.Part.from_bytes(data=img.data, mime_type=img.mime_type) for img in images or []]
        contents.append(prompt)
        config = self._config(system=system, temperature=temperature,
                              max_output_tokens=max_output_tokens, json_mode=json_mode)

        def call():
            try:
                return self._client.models.generate_content(model=self.model, contents=contents, config=config)
            except genai_errors.APIError as err:
                raise map_gemini_error(err) from None

        response = call_with_retries(call)
        text = (response.text or "").strip()
        finish = response.candidates[0].finish_reason if response.candidates else None
        if text and finish == types.FinishReason.MAX_TOKENS and not json_mode:
            text += "\n\n_(The answer was cut off. Ask me to continue.)_"
        if not text:
            raise ProviderError("Gemini returned an empty answer. Try rephrasing or another model.",
                                kind="empty", provider="gemini")
        return text
