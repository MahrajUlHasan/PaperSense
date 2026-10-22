"""Tidy the [n] markers in an answer.

* Only sources the answer actually cites are returned, renumbered 1, 2, 3 in order of first use.
* [1, 2] and [1-3] become [1][2] / [1][2][3]; repeats like [2][2] collapse to [2].
* Anything inside math ($...$, $$...$$) or code is left alone, as are brackets that
  aren't valid source numbers, e.g. [2017] or [0, 1].
"""
from __future__ import annotations

import re

_PROTECTED = re.compile(r"(\$\$.+?\$\$|\$[^$\n]+?\$|```.+?```|`[^`\n]+`)", re.DOTALL)
_GROUP = re.compile(r"\[(\s*\d+(?:\s*[-–]\s*\d+)?(?:\s*,\s*\d+(?:\s*[-–]\s*\d+)?)*\s*)\]")
_REPEATS = re.compile(r"(\[\d+\])(?:\s*\1)+")


def _expand(group: str) -> list[int]:
    numbers: list[int] = []
    for part in group.split(","):
        part = part.strip()
        if re.search(r"[-–]", part):
            start, end = (int(x) for x in re.split(r"\s*[-–]\s*", part))
            if end < start or end - start > 20:
                return []
            numbers.extend(range(start, end + 1))
        else:
            numbers.append(int(part))
    return numbers


def renumber_citations(answer: str, source_count: int) -> tuple[str, list[int]]:
    """Return (new_answer, used) where used[k] is the original source number of new citation k+1.

    The answer is split into normal text (even pieces) and math/code (odd pieces);
    only normal text is changed.
    """
    used: list[int] = []

    def replace(match: re.Match) -> str:
        numbers = _expand(match.group(1))
        if not numbers or any(n < 1 or n > source_count for n in numbers):
            return match.group(0)
        out = []
        for n in dict.fromkeys(numbers):
            if n not in used:
                used.append(n)
            out.append(f"[{used.index(n) + 1}]")
        return "".join(out)

    pieces = _PROTECTED.split(answer)
    for i in range(0, len(pieces), 2):
        pieces[i] = _REPEATS.sub(r"\1", _GROUP.sub(replace, pieces[i]))
    return "".join(pieces), used
