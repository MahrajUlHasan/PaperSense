"""Logging that redacts anything that looks like an API key."""
from __future__ import annotations

import re
import sys

from loguru import logger

from config import BACKEND_DIR, settings

_SECRETS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"gsk_[0-9A-Za-z]{20,}"),
    re.compile(r"sk-or-[0-9A-Za-z_\-]{20,}"),
    re.compile(r"sk-[0-9A-Za-z_\-]{20,}"),
]


def redact(text: str) -> str:
    """Replace Google/Gemini (AIza…), Groq (gsk_…), OpenRouter (sk-or-…) and OpenAI-style (sk-…) keys."""
    for pattern in _SECRETS:
        text = pattern.sub("[REDACTED]", text)
    return text


def _patch(record) -> None:
    record["message"] = redact(record["message"])


def setup_logging() -> None:
    """Console + logs/app.log, both redacted.

    diagnose=False: tracebacks must not print variable values, because they could hold keys.
    """
    logger.remove()
    logger.configure(patcher=_patch)
    logger.add(sys.stderr, level="DEBUG" if settings.debug else "INFO", backtrace=False, diagnose=False)
    logger.add(BACKEND_DIR / "logs" / "app.log", rotation="20 MB", retention=5, level="INFO",
               backtrace=False, diagnose=False)
