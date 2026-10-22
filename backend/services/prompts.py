"""All prompt text in one place, easy to tune (and to quote in the thesis)."""
from __future__ import annotations

from services.retrieval import ContextBlock

SYSTEM_PROMPT = """You are PaperSense, a research assistant. You answer questions about research papers using ONLY the numbered sources in the message.

Rules:
1. Use only facts from the sources. If they don't contain the answer, reply: "The uploaded papers don't cover this." You may add one sentence about what the sources do discuss.
2. After each sentence that uses a source, cite it with its number in square brackets, e.g. [2]. For several sources write [1][3]. Only use numbers that exist in the sources. Never cite the conversation.
3. Write all mathematics in LaTeX: inline as $...$, displayed equations as $$...$$ on their own lines. Copy formulas from the sources faithfully.
4. When a source is a TABLE, you may reproduce the relevant rows as a Markdown table. When a source is a FIGURE, describe what it shows using its description and the attached image, if any.
5. Be concise and direct. Use Markdown lists or headings only when they help. Don't explain your reasoning or restate the question."""

REWRITE_PROMPT = """Rewrite the user's last question so it can be understood without the conversation. Keep names, numbers and technical terms. Return only the rewritten question.

Conversation:
{history}

Last question: {question}"""


def format_sources(blocks: list[ContextBlock]) -> str:
    parts = []
    for number, block in enumerate(blocks, start=1):
        pages = ", ".join(str(p) for p in block.pages) or "?"
        kind = {"table": " · TABLE", "figure": " · FIGURE"}.get(block.content_type, "")
        section = f" · {block.section}" if block.section else ""
        parts.append(f"[{number}] {block.filename} · p.{pages}{section}{kind}\n{block.text}")
    return "\n\n---\n\n".join(parts)


def build_answer_prompt(question: str, blocks: list[ContextBlock], history: str = "",
                        image_refs: list[int] | None = None) -> str:
    parts = []
    if history:
        parts.append(f"Conversation so far (context only, never cite it):\n{history}")
    parts.append(f"Sources:\n\n{format_sources(blocks)}")
    if image_refs:
        refs = ", ".join(f"[{n}]" for n in image_refs)
        parts.append(f"The attached images are the figures of sources {refs}, in that order.")
    parts.append(f"Question: {question}")
    return "\n\n".join(parts)
