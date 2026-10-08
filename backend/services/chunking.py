"""
Chunking of a parsed paper.

* Text: Docling's HybridChunker follows the real heading tree, never cuts a
  paragraph/formula in half, and respects the embedding model's token limit.
  Tables and pictures are left out of text chunks (they get their own), and so
  are page headers/footers and the reference list, which only add noise.
* Tables and figures: one chunk each, so they're never duplicated.
* Pages where Docling found much less text than the PDF text layer get extra
  chunks made from that raw page text.
* Every chunk keeps the boxes of the items it came from, i.e. its exact place in the PDF.
"""
from __future__ import annotations

from pathlib import Path

from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.types.doc import (
    DocItemLabel,
    DoclingDocument,
    FormulaItem,
    RefItem,
    SectionHeaderItem,
    TitleItem,
)
from docling_core.types.doc.document import DEFAULT_EXPORT_LABELS

from config import settings
from services.chunk_models import ChunkRecord
from services.geometry import Box, item_boxes
from services.parsing import FigureImage, ParseResult

TEXT_LABELS = set(DEFAULT_EXPORT_LABELS) - {
    DocItemLabel.TABLE,
    DocItemLabel.PICTURE,
    DocItemLabel.PAGE_HEADER,
    DocItemLabel.PAGE_FOOTER,
    DocItemLabel.REFERENCE,
}
NOT_FOUND = 10**9
MAX_BOXES_PER_CHUNK = 30


def one_line(text: str) -> str:
    """Collapse line breaks and repeated spaces (Docling keeps them inside some headings)."""
    return " ".join(text.split())


def document_title(doc: DoclingDocument, fallback: str) -> str:
    """The paper's title.

    Docling often labels a paper's title as the first heading on page 1 instead of
    a title item, so that heading is used when there is no title item.
    """
    first_heading = None
    for item, _level in doc.iterate_items():
        if isinstance(item, TitleItem) and item.text.strip():
            return one_line(item.text)
        if (first_heading is None and isinstance(item, SectionHeaderItem) and item.prov
                and item.prov[0].page_no == 1 and item.text.strip()):
            first_heading = one_line(item.text)
    return first_heading or fallback


def resolve_items(items, doc: DoclingDocument) -> list:
    """Chunk metadata only keeps plain DocItem copies (no text, no subclass).
    Look up the real items in the document so formulas etc. can be read."""
    return [RefItem(cref=item.self_ref).resolve(doc) for item in items]


def reading_positions(doc: DoclingDocument) -> dict[str, int]:
    """Docling reference -> position in reading order."""
    return {item.self_ref: index for index, (item, _level) in enumerate(doc.iterate_items())}


def section_paths(doc: DoclingDocument) -> dict[str, list[str]]:
    """Docling reference -> list of headings above it (used for tables and figures)."""
    stack: dict[int, str] = {}
    paths: dict[str, list[str]] = {}
    for item, _level in doc.iterate_items():
        if isinstance(item, SectionHeaderItem):
            for level in [k for k in stack if k >= item.level]:
                del stack[level]
            stack[item.level] = one_line(item.text)
            continue
        paths[item.self_ref] = [stack[k] for k in sorted(stack)]
    return paths


def first_position_per_page(doc: DoclingDocument) -> dict[int, float]:
    """Page number -> reading position of the first Docling item on that page."""
    first: dict[int, float] = {}
    for index, (item, _level) in enumerate(doc.iterate_items()):
        for prov in getattr(item, "prov", None) or []:
            first.setdefault(prov.page_no, index)
    return first


def split_lines(text: str, max_chars: int = 1500) -> list[str]:
    """Group the lines of raw page text into pieces of about max_chars."""
    parts, current, size = [], [], 0
    for line in (raw.strip() for raw in text.splitlines()):
        if not line:
            continue
        if current and size + len(line) > max_chars:
            parts.append(" ".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line) + 1
    if current:
        parts.append(" ".join(current))
    return parts


def build_embed_text(record: ChunkRecord, title: str) -> str:
    """Title and section in front of the text help retrieval; users still see plain `text`."""
    context = " › ".join([title, *record.section_path])
    kind = {"table": "Table", "figure": "Figure"}.get(record.content_type)
    return f"{context}\n{kind}: {record.text}" if kind else f"{context}\n{record.text}"


class Chunker:
    """Turns a ParseResult into ordered ChunkRecords.

    The tokenizer is the embedding model's own, so every text chunk fits into it.
    """

    def __init__(self, tokenizer_model: str | None = None, max_tokens: int | None = None):
        tokenizer = HuggingFaceTokenizer.from_pretrained(
            model_name=tokenizer_model or settings.dense_model,
            max_tokens=max_tokens or settings.chunk_max_tokens,
        )
        self._hybrid = HybridChunker(tokenizer=tokenizer, merge_peers=True)

    def build(
        self,
        parsed: ParseResult,
        filename: str,
        figures: list[FigureImage] | None = None,
        figure_descriptions: dict[int, str] | None = None,
    ) -> tuple[str, list[ChunkRecord]]:
        """Return the paper's title and all its chunks in reading order."""
        doc = parsed.doc
        title = document_title(doc, fallback=Path(filename).stem)
        positions = reading_positions(doc)
        sections = section_paths(doc)

        records = self._text_chunks(doc, positions, title)
        records += self._table_chunks(doc, positions, sections)
        records += self._figure_chunks(figures or [], figure_descriptions or {}, positions, sections)
        records += self._page_fallback_chunks(parsed, first_position_per_page(doc))

        records.sort(key=lambda r: r.sort_key)
        for order, record in enumerate(records):
            record.order = order
            record.embed_text = build_embed_text(record, title)
        return title, records

    def _text_chunks(self, doc: DoclingDocument, positions: dict[str, int], title: str) -> list[ChunkRecord]:
        """Text chunks with their boxes and formulas. The paper title is not used as a section."""
        records: list[ChunkRecord] = []
        for chunk in self._hybrid.chunk(dl_doc=doc, labels=TEXT_LABELS):
            text = chunk.text.strip()
            if not text:
                continue
            items = resolve_items(chunk.meta.doc_items, doc)
            headings = [one_line(h) for h in chunk.meta.headings or []]
            if headings and headings[0] == title:
                headings = headings[1:]
            boxes = [box for item in items for box in item_boxes(item, doc)][:MAX_BOXES_PER_CHUNK]
            formulas = [item.text for item in items if isinstance(item, FormulaItem) and item.text]
            records.append(
                ChunkRecord(
                    order=0,
                    content_type="text",
                    text=text,
                    section_path=headings,
                    boxes=boxes,
                    formulas=formulas,
                    sort_key=min((positions.get(i.self_ref, NOT_FOUND) for i in items), default=NOT_FOUND),
                )
            )
        return records

    def _table_chunks(self, doc: DoclingDocument, positions: dict[str, int], sections: dict[str, list[str]]) -> list[ChunkRecord]:
        """One chunk per table: caption + Markdown as text, HTML kept for display.

        Docling's Markdown export already starts with the caption; it is cut from
        there so the caption appears only once.
        """
        records: list[ChunkRecord] = []
        for table in doc.tables:
            caption = table.caption_text(doc).strip()
            markdown = table.export_to_markdown(doc=doc).strip()
            if caption and markdown.startswith(caption):
                markdown = markdown[len(caption):].strip()
            if not markdown:
                continue
            records.append(
                ChunkRecord(
                    order=0,
                    content_type="table",
                    text=f"{caption}\n\n{markdown}" if caption else markdown,
                    caption=caption,
                    table_html=table.export_to_html(doc=doc),
                    section_path=sections.get(table.self_ref, []),
                    boxes=item_boxes(table, doc),
                    sort_key=positions.get(table.self_ref, NOT_FOUND),
                )
            )
        return records

    def _figure_chunks(
        self,
        figures: list[FigureImage],
        descriptions: dict[int, str],
        positions: dict[str, int],
        sections: dict[str, list[str]],
    ) -> list[ChunkRecord]:
        """One chunk per figure: its caption, plus a text description when one is given
        (descriptions are keyed by figure index)."""
        records: list[ChunkRecord] = []
        for fig in figures:
            label = fig.caption or f"Figure {fig.index}"
            description = descriptions.get(fig.index, "").strip()
            records.append(
                ChunkRecord(
                    order=0,
                    content_type="figure",
                    text=f"{label}\n\n{description}" if description else label,
                    caption=fig.caption,
                    figure_index=fig.index,
                    section_path=sections.get(fig.self_ref, []),
                    boxes=fig.boxes,
                    sort_key=positions.get(fig.self_ref, NOT_FOUND),
                )
            )
        return records

    def _page_fallback_chunks(self, parsed: ParseResult, first_positions: dict[int, float]) -> list[ChunkRecord]:
        """Pages where Docling found much less text than the PDF has: index the raw page text."""
        records: list[ChunkRecord] = []
        for page_no in parsed.low_coverage_pages:
            width, height = parsed.pdf_page_sizes.get(page_no, (612.0, 792.0))
            whole_page = [Box(page_no, 0.0, 0.0, width, height)]
            base = first_positions.get(page_no, page_no * 100_000) - 0.5
            for part_no, part in enumerate(split_lines(parsed.pypdf_page_text.get(page_no, ""))):
                records.append(
                    ChunkRecord(
                        order=0,
                        content_type="page_text",
                        text=part,
                        section_path=[f"Page {page_no}"],
                        boxes=whole_page,
                        sort_key=base + part_no * 0.001,
                    )
                )
        return records
