"""Gemini vision jobs at upload time. Several images per request to save free quota."""
from __future__ import annotations

import io
import time

from loguru import logger

from config import settings
from services.json_utils import parse_json, repair_latex
from services.llm import GeminiProvider, ImageInput, ProviderError
from services.parsing import FigureImage
from services.rate_limit import vision_limiter

BUSY_WAITS = (15, 45)
FIGURE_BATCH = 4
FIGURE_PROMPT = """You get {n} figure image(s) from a research paper, in order. For each one write 2-4 sentences describing what it shows: the kind of chart or diagram, axes and units, the main components or trend, and any key numbers you can read. Use the captions for context.

Captions, in the same order:
{captions}

Return ONLY a JSON array of {n} strings, one description per image, in order."""

FORMULA_BATCH = 8
FORMULA_PROMPT = r"""You get {n} image(s), each showing one mathematical formula cropped from a research paper, in order. Transcribe each formula into LaTeX exactly as printed: no surrounding $ signs, no explanations. If an image is not a formula or is unreadable, use an empty string.

Return ONLY a JSON array of {n} strings, in order. Remember that JSON strings need doubled backslashes (\\frac, \\alpha)."""


def png_bytes(image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def as_string_list(data, expected: int) -> list[str] | None:
    """The model's list of strings, or None if it has the wrong shape.

    Some models wrap the list in an object, e.g. {"items": [...]}; that is unwrapped.
    """
    if isinstance(data, dict):
        data = next((v for v in data.values() if isinstance(v, list)), None)
    if not isinstance(data, list) or len(data) != expected:
        return None
    return [str(x).strip() for x in data]


class VisionService:
    def __init__(self, gemini_key: str, model: str | None = None):
        self._key = gemini_key
        self._provider = GeminiProvider(gemini_key, model or settings.vision_model)

    def _ask(self, prompt: str, images: list[ImageInput], expected: int) -> list[str] | None:
        """One vision request, returning the expected number of strings (or None).

        Uploads run in the background, so a busy model (503 "high demand") is retried
        patiently: after the provider's own quick retries, wait BUSY_WAITS seconds in turn
        before giving up. Other errors are raised at once.
        """
        for wait in (*BUSY_WAITS, None):
            vision_limiter.wait(self._key)
            try:
                text = self._provider.generate(prompt, images=images, temperature=0.1,
                                               max_output_tokens=4096, json_mode=True)
                return as_string_list(parse_json(text), expected)
            except ProviderError as err:
                if err.kind != "unavailable" or wait is None:
                    raise
                logger.warning(f"Gemini vision is busy, trying again in {wait}s")
                time.sleep(wait)
        return None

    def describe_figures(self, figures: list[FigureImage]) -> dict[int, str]:
        """figure index -> description. Raises ProviderError for key/quota problems."""
        descriptions: dict[int, str] = {}
        for start in range(0, len(figures), FIGURE_BATCH):
            batch = figures[start:start + FIGURE_BATCH]
            captions = "\n".join(f"{i}. {f.caption or '(no caption)'}" for i, f in enumerate(batch, start=1))
            result = self._ask(FIGURE_PROMPT.format(n=len(batch), captions=captions),
                               [ImageInput(png_bytes(f.image)) for f in batch], len(batch))
            if result is None:
                logger.warning(f"Unreadable figure descriptions for figures {[f.index for f in batch]}")
                continue
            descriptions.update({f.index: text for f, text in zip(batch, result) if text})
        return descriptions

    def formulas_to_latex(self, crops) -> int:
        """Write LaTeX into each formula item. Returns how many formulas were filled in.

        The chunker then writes $$latex$$ for every formula that got text here.
        """
        filled = 0
        for start in range(0, len(crops), FORMULA_BATCH):
            batch = crops[start:start + FORMULA_BATCH]
            result = self._ask(FORMULA_PROMPT.format(n=len(batch)),
                               [ImageInput(png_bytes(image)) for _, image in batch], len(batch))
            if result is None:
                logger.warning(f"Unreadable LaTeX batch at formula {start}")
                continue
            for (item, _image), latex in zip(batch, result):
                latex = repair_latex(latex).strip().strip("$").strip()
                if latex:
                    item.text = latex
                    filled += 1
        return filled
