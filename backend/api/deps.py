"""Values every request carries in its headers.

X-Workspace-Id  random id the browser stores in localStorage -> one separate library per browser
X-Session-Id    one id per chat (used for chat memory)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import Header, HTTPException, Query

_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


@dataclass
class RequestContext:
    workspace_id: str
    session_id: str


def _require_id(value: str | None, name: str) -> str:
    if not value or not _ID.match(value):
        raise HTTPException(status_code=400, detail=f"Missing or invalid {name} header.")
    return value


def get_context(
    x_workspace_id: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
) -> RequestContext:
    workspace_id = _require_id(x_workspace_id, "X-Workspace-Id")
    session_id = x_session_id if x_session_id and _ID.match(x_session_id) else "default-session"
    return RequestContext(workspace_id=workspace_id, session_id=session_id)


def get_file_workspace(
    x_workspace_id: str | None = Header(default=None),
    ws: str | None = Query(default=None),
) -> str:
    """PDF/figure URLs may be opened by <img> or pdf.js, which can't always send headers,
    so they also accept ?ws=<workspace id>."""
    return _require_id(x_workspace_id or ws, "X-Workspace-Id")
