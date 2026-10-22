"""Read JSON that a model returned (sometimes wrapped in ``` fences)."""
from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_CONTROL = {"\t": r"\t", "\x0c": r"\f", "\x08": r"\b", "\r": r"\r"}


def parse_json(text: str) -> Any | None:
    cleaned = _FENCE.sub("", text.strip())
    for candidate in (cleaned, *re.findall(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def repair_latex(value: str, newlines: bool = True) -> str:
    r"""Undo JSON escapes that eat LaTeX: "\theta" read as TAB+"heta", "\frac" as FORMFEED+"rac", ...

    With newlines=True, a newline followed by a letter is restored as "\n" (\nabla, \neq, \nu)
    and any other newline becomes a space.
    """
    for char, escaped in _CONTROL.items():
        value = value.replace(char, escaped)
    if newlines:
        value = re.sub(r"\n(?=[A-Za-z])", r"\\n", value)
        value = value.replace("\n", " ")
    return value
