"""Turn raw search hits into context blocks for the answer step.

A block = one hit, plus its neighbouring chunks from the same section, merged
when they are consecutive. Highlight boxes come only from the actual hits.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Iterable

TEXTUAL = {"text", "page_text"}
_WORD = re.compile(r"\w+")


def _words(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def dedupe_hits(hits: list[dict], threshold: float = 0.85) -> list[dict]:
    """Drop repeated chunks and near-duplicates (same paper, mostly the same words)."""
    kept: list[tuple[dict, set[str]]] = []
    seen: set[tuple[str, int]] = set()
    for hit in sorted(hits, key=lambda h: h["score"], reverse=True):
        key = (hit["document_id"], hit["order"])
        if key in seen:
            continue
        words = _words(hit["text"])
        duplicate = any(
            other["document_id"] == hit["document_id"]
            and len(words & other_words) / max(1, min(len(words), len(other_words))) >= threshold
            for other, other_words in kept
        )
        if not duplicate:
            seen.add(key)
            kept.append((hit, words))
    return [hit for hit, _ in kept]


@dataclass
class ContextBlock:
    document_id: str
    filename: str
    content_type: str
    section: str
    text: str
    orders: list[int]
    pages: list[int]
    boxes: list[dict]
    relevance: float
    figure_index: int | None = None
    table_html: str = ""
    formulas: list[str] = field(default_factory=list)


def normalize_scores(hits: list[dict]) -> list[dict]:
    """Add `relevance` in [0, 1]: each hit's score relative to the best hit."""
    if not hits:
        return hits
    best = max(h["score"] for h in hits) or 1.0
    for h in hits:
        h["relevance"] = round(max(0.0, min(1.0, h["score"] / best)), 3)
    return hits


def _continues(previous: dict, chunk: dict) -> bool:
    return (
        chunk["order"] == previous["order"] + 1
        and previous.get("content_type") in TEXTUAL
        and chunk.get("content_type") in TEXTUAL
        and previous.get("section") == chunk.get("section")
    )


def _make_block(run: list[tuple[dict, bool]]) -> ContextBlock:
    chunks = [chunk for chunk, _ in run]
    hits = [chunk for chunk, is_hit in run if is_hit]
    first = chunks[0]
    return ContextBlock(
        document_id=first["document_id"],
        filename=first.get("filename", ""),
        content_type=first.get("content_type", "text"),
        section=first.get("section", ""),
        text="\n\n".join(c["text"] for c in chunks),
        orders=[c["order"] for c in chunks],
        pages=sorted({p for c in hits for p in c.get("pages", [])}),
        boxes=[b for c in hits for b in c.get("boxes", [])],
        relevance=max((c.get("relevance", 0.0) for c in hits), default=0.0),
        figure_index=first.get("figure_index"),
        table_html=first.get("table_html", ""),
        formulas=[f for c in chunks for f in c.get("formulas", [])],
    )


def build_context_blocks(
    hits: list[dict],
    fetch_neighbors: Callable[[Iterable[tuple[str, int]]], list[dict]] | None = None,
    max_blocks: int = 6,
) -> list[ContextBlock]:
    """Dedupe the hits, add same-section text neighbours and merge consecutive chunks.

    Blocks are sorted by their best hit's relevance, highest first.
    """
    hits = dedupe_hits(hits)[:max_blocks]
    pool: dict[tuple[str, int], tuple[dict, bool]] = {(h["document_id"], h["order"]): (h, True) for h in hits}

    if fetch_neighbors:
        wanted = {
            (h["document_id"], order)
            for h in hits if h.get("content_type") in TEXTUAL
            for order in (h["order"] - 1, h["order"] + 1)
        } - set(pool)
        for chunk in fetch_neighbors(sorted(wanted)):
            doc_id, order = chunk["document_id"], chunk["order"]
            anchor = pool.get((doc_id, order - 1)) or pool.get((doc_id, order + 1))
            if (
                anchor
                and anchor[1]
                and chunk.get("content_type") in TEXTUAL
                and chunk.get("section") == anchor[0].get("section")
            ):
                pool.setdefault((doc_id, order), (chunk, False))

    blocks: list[ContextBlock] = []
    for doc_id in dict.fromkeys(key[0] for key in pool):
        run: list[tuple[dict, bool]] = []
        for chunk, is_hit in sorted((v for k, v in pool.items() if k[0] == doc_id), key=lambda v: v[0]["order"]):
            if run and _continues(run[-1][0], chunk):
                run.append((chunk, is_hit))
                continue
            if run:
                blocks.append(_make_block(run))
            run = [(chunk, is_hit)]
        if run:
            blocks.append(_make_block(run))

    blocks = [b for b in blocks if b.boxes or b.relevance > 0]
    blocks.sort(key=lambda b: b.relevance, reverse=True)
    return blocks[:max_blocks]
