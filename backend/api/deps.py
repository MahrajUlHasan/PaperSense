"""Values every request carries in its headers.

X-Workspace-Id   random id stored in the browser -> one separate library per browser
X-Session-Id     one id per chat (chat memory)
X-LLM-Provider   gemini | groq | openrouter
X-LLM-Model      optional model override
X-LLM-Key        the visitor's key for that provider
X-Gemini-Key     optional extra Gemini key for figures/formulas when the chat provider isn't Gemini

Keys live only for the duration of the request: they are never stored or logged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import Header, HTTPException, Query

from config import settings
from services.llm import PROVIDERS, LLMCredentials, MissingKeyError

_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


@dataclass
class RequestContext:
    workspace_id: str
    session_id: str
    provider: str = "gemini"
    llm: LLMCredentials | None = None
    gemini_key: str | None = None

    def require_llm(self) -> LLMCredentials:
        if self.llm is None:
            raise MissingKeyError(self.provider)
        return self.llm

    def __repr__(self) -> str:
        return f"RequestContext(workspace={self.workspace_id!r}, provider={self.provider!r})"


def default_model(provider: str) -> str:
    return {
        "gemini": settings.gemini_model,
        "groq": settings.groq_model,
        "openrouter": settings.openrouter_model,
    }[provider]


def _require_id(value: str | None, name: str) -> str:
    if not value or not _ID.match(value):
        raise HTTPException(status_code=400, detail=f"Missing or invalid {name} header.")
    return value


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def get_context(
    x_workspace_id: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
    x_llm_provider: str | None = Header(default=None),
    x_llm_model: str | None = Header(default=None),
    x_llm_key: str | None = Header(default=None),
    x_gemini_key: str | None = Header(default=None),
) -> RequestContext:
    workspace_id = _require_id(x_workspace_id, "X-Workspace-Id")
    session_id = x_session_id if x_session_id and _ID.match(x_session_id) else "default-session"

    provider = (_clean(x_llm_provider) or settings.default_provider).lower()
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown LLM provider '{provider}'.")

    llm_key = _clean(x_llm_key)
    server_key = _clean(settings.server_gemini_api_key) if settings.allow_server_key else None
    gemini_key = _clean(x_gemini_key) or (llm_key if provider == "gemini" else None) or server_key
    key = llm_key or (gemini_key if provider == "gemini" else None)
    llm = LLMCredentials(provider, key, _clean(x_llm_model) or default_model(provider)) if key else None

    return RequestContext(workspace_id=workspace_id, session_id=session_id, provider=provider,
                          llm=llm, gemini_key=gemini_key)


def get_file_workspace(
    x_workspace_id: str | None = Header(default=None),
    ws: str | None = Query(default=None),
) -> str:
    """PDF/figure URLs may be opened by <img> or pdf.js, which can't always send headers,
    so they also accept ?ws=<workspace id>."""
    return _require_id(x_workspace_id or ws, "X-Workspace-Id")


__all__ = ["RequestContext", "default_model", "get_context", "get_file_workspace", "MissingKeyError"]
