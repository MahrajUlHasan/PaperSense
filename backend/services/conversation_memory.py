"""
Conversation memory service.

Maintains a running context.md file that logs every Q&A exchange so the LLM
can answer follow-up questions.  The file is cleared on application
startup/shutdown.
"""

import os
import threading
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "context.md")


class ConversationMemory:
    """Thread-safe, file-backed conversation memory."""

    def __init__(self, path: str = _DEFAULT_PATH, max_turns: int = 50):
        self._path = os.path.abspath(path)
        self._max_turns = max_turns
        self._lock = threading.Lock()
        self._turns: List[Dict[str, str]] = []
        # Start fresh
        self.clear()

    # ── public API ────────────────────────────────────────────────

    def add_turn(self, question: str, answer: str) -> None:
        """Append a Q&A turn and flush to disk."""
        turn = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "question": question,
            "answer": answer,
        }
        with self._lock:
            self._turns.append(turn)
            # Trim oldest turns if we exceed the cap
            if len(self._turns) > self._max_turns:
                self._turns = self._turns[-self._max_turns:]
            self._flush()

    def get_context_for_prompt(self, max_chars: int = 6000) -> str:
        """
        Return a condensed conversation history string suitable for
        injecting into the LLM prompt. Truncates from the oldest turns
        first to stay within *max_chars*.
        """
        with self._lock:
            if not self._turns:
                return ""
            lines: List[str] = []
            for t in self._turns:
                lines.append(f"User: {t['question']}")
                lines.append(f"Assistant: {t['answer']}")
                lines.append("")  # blank separator
            history = "\n".join(lines)
            # Trim from the front if too long
            if len(history) > max_chars:
                history = "… (earlier conversation omitted)\n" + history[-max_chars:]
            return history

    def clear(self) -> None:
        """Wipe the in-memory history and the context file."""
        with self._lock:
            self._turns = []
            try:
                if os.path.exists(self._path):
                    os.remove(self._path)
                logger.info(f"Conversation memory cleared ({self._path})")
            except OSError as e:
                logger.warning(f"Could not remove context file: {e}")

    # ── internal ──────────────────────────────────────────────────

    def _flush(self) -> None:
        """Write the current turns to context.md (caller holds lock)."""
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                f.write("# Conversation Context\n\n")
                for t in self._turns:
                    f.write(f"## [{t['timestamp']}]\n\n")
                    f.write(f"**User:** {t['question']}\n\n")
                    f.write(f"**Assistant:** {t['answer']}\n\n")
                    f.write("---\n\n")
        except OSError as e:
            logger.error(f"Failed to write context file: {e}")
