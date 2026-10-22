"""Provider errors, already translated into messages a user can act on."""
from __future__ import annotations

KEY_HELP_URLS = {
    "gemini": "https://aistudio.google.com/apikey",
    "groq": "https://console.groq.com/keys",
    "openrouter": "https://openrouter.ai/keys",
}

_STATUS = {
    "missing_key": 401,
    "invalid_key": 401,
    "rate_limited": 429,
    "unavailable": 503,
    "bad_request": 400,
    "empty": 502,
    "unknown": 502,
}


class ProviderError(Exception):
    """kind: missing_key | invalid_key | rate_limited | unavailable | bad_request | empty | unknown"""

    def __init__(self, message: str, *, kind: str = "unknown", provider: str | None = None,
                 retry_after: float | None = None):
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.provider = provider
        self.retry_after = retry_after

    @property
    def status_code(self) -> int:
        return _STATUS.get(self.kind, 502)

    def to_dict(self) -> dict:
        needs_key = self.kind in ("missing_key", "invalid_key")
        return {
            "code": self.kind,
            "message": self.message,
            "provider": self.provider,
            "help_url": KEY_HELP_URLS.get(self.provider or "gemini") if needs_key else None,
            "retry_after": self.retry_after,
        }


class MissingKeyError(ProviderError):
    def __init__(self, provider: str = "gemini"):
        super().__init__(
            "Add your free API key in Settings → API keys to ask questions.",
            kind="missing_key", provider=provider,
        )
