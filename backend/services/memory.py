updated o"""Short-term chat memory per (workspace, session), kept in RAM (cleared on restart)."""
from __future__ import annotations

import threading
from collections import OrderedDict, deque


class ConversationMemory:
    def __init__(self, max_turns: int = 6, max_sessions: int = 500):
        self._sessions: OrderedDict[tuple[str, str], deque] = OrderedDict()
        self._max_turns = max_turns
        self._max_sessions = max_sessions
        self._lock = threading.Lock()

    def add_turn(self, workspace_id: str, session_id: str, question: str, answer: str) -> None:
        key = (workspace_id, session_id)
        with self._lock:
            turns = self._sessions.setdefault(key, deque(maxlen=self._max_turns))
            turns.append((question, answer))
            self._sessions.move_to_end(key)
            while len(self._sessions) > self._max_sessions:
                self._sessions.popitem(last=False)

    def history(self, workspace_id: str, session_id: str, max_chars: int = 4000) -> str:
        with self._lock:
            turns = list(self._sessions.get((workspace_id, session_id), ()))
        text = "\n\n".join(f"User: {q}\nAssistant: {a}" for q, a in turns)
        return text[-max_chars:] if len(text) > max_chars else text

    def clear(self, workspace_id: str, session_id: str) -> None:
        with self._lock:
            self._sessions.pop((workspace_id, session_id), None)
