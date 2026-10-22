"""Research topic breakdown, paper relevance scores and quick paper analysis.

Each paper is judged from a digest of the whole paper in reading order (beginning,
end, section list and captions), so scoring costs one request per paper.
"""
from __future__ import annotations

from services.json_utils import parse_json, repair_latex
from services.llm import LLMProvider, ProviderError

BREAKDOWN_PROMPT = """You are a research methodology expert. Break down this research topic so it can be used to judge whether a paper is relevant.

Topic: {topic}
Description: {description}

Write Markdown with these sections: Core research questions; Key themes and sub-topics; Relevant methods; Expected data and sources; Important keywords; Related fields. Be specific and concise."""

SCORE_PROMPT = """Rate how relevant this paper is to the research below, from 0 (unrelated) to 100 (directly answers the core questions).

Research topic: {topic}
Research breakdown:
{breakdown}

Paper: {filename}
Paper digest:
{digest}

Return ONLY JSON: {{"score": <integer 0-100>, "explanation": "<2-3 sentences>"}}"""

ANALYSIS_PROMPT = """Analyse this research paper digest.

{digest}

Return ONLY JSON with these keys:
{{"summary": "<120-200 words>", "key_findings": ["..."], "methodology": "<60-120 words>", "limitations": ["..."]}}
Use only information in the digest. Write math in LaTeX ($...$)."""


def paper_digest(chunks: list[dict], max_chars: int = 12000) -> str:
    """The paper in reading order, trimmed to a budget: mostly the start, some of the end."""
    texts = [c for c in chunks if c.get("content_type") in ("text", "page_text")]
    head, tail = [], []
    used, head_budget, tail_budget = 0, int(max_chars * 0.65), int(max_chars * 0.35)
    for chunk in texts:
        if used + len(chunk["text"]) > head_budget:
            break
        head.append(chunk["text"])
        used += len(chunk["text"])
    used = 0
    for chunk in reversed(texts[len(head):]):
        if used + len(chunk["text"]) > tail_budget:
            break
        tail.insert(0, chunk["text"])
        used += len(chunk["text"])

    sections = list(dict.fromkeys(c["section"] for c in texts if c.get("section")))
    captions = [c["caption"] for c in chunks if c.get("content_type") in ("table", "figure") and c.get("caption")]
    parts = []
    if sections:
        parts.append("Sections: " + "; ".join(sections[:40]))
    parts.append("\n\n".join(head))
    if tail:
        parts.append("[…]\n\n" + "\n\n".join(tail))
    if captions:
        parts.append("Tables and figures: " + "; ".join(captions[:20]))
    return "\n\n".join(parts)


class ResearchService:
    def breakdown(self, provider: LLMProvider, topic: str, description: str) -> str:
        return provider.generate(BREAKDOWN_PROMPT.format(topic=topic, description=description or "-"),
                                 temperature=0.3, max_output_tokens=2048)

    def score(self, provider: LLMProvider, chunks: list[dict], filename: str, research: dict) -> tuple[int, str]:
        prompt = SCORE_PROMPT.format(topic=research["topic"], breakdown=research["breakdown"][:4000],
                                     filename=filename, digest=paper_digest(chunks, max_chars=8000))
        data = parse_json(provider.generate(prompt, temperature=0.1, max_output_tokens=1024, json_mode=True))
        if not isinstance(data, dict) or "score" not in data:
            raise ProviderError("The model didn't return a usable score. Try again.", kind="empty")
        score = max(0, min(100, int(float(data["score"]))))
        return score, str(data.get("explanation", "")).strip()

    def analyze(self, provider: LLMProvider, chunks: list[dict]) -> dict:
        data = parse_json(provider.generate(ANALYSIS_PROMPT.format(digest=paper_digest(chunks)),
                                            temperature=0.3, max_output_tokens=4096, json_mode=True))
        if not isinstance(data, dict):
            raise ProviderError("The model didn't return a usable analysis. Try again.", kind="empty")

        def clean(value) -> str:
            return repair_latex(str(value), newlines=False).strip()

        return {
            "summary": clean(data.get("summary", "")),
            "key_findings": [clean(x) for x in data.get("key_findings", []) or []],
            "methodology": clean(data.get("methodology", "")),
            "limitations": [clean(x) for x in data.get("limitations", []) or []],
        }
