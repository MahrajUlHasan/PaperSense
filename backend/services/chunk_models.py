"""
The unit we store in Qdrant: one ChunkRecord per text passage, table or figure.

Qdrant payload:
    document_id, workspace_id, filename, title   which paper, and whose
    order                  reading order inside the paper (0, 1, 2, …)
    content_type           text | table | figure | page_text (fallback text from the PDF layer)
    text                   what users and the LLM see
    section, section_path  "3 Model Architecture › 3.2 Attention"
    pages, boxes           where it is: [{page, l, t, r, b}] in PDF points, top-left origin
    formulas, has_formula  LaTeX of formulas inside this chunk
    caption, table_html, figure_index   extras for tables and figures
"""
from __future__ import annotations

from dataclasses import dataclass, field

from services.geometry import Box


@dataclass
class ChunkRecord:
    """One chunk of a paper.

    `sort_key` is the chunk's reading position in the Docling document; it is only
    used to compute `order` and is not stored.
    """

    order: int
    content_type: str
    text: str
    embed_text: str = ""
    section_path: list[str] = field(default_factory=list)
    boxes: list[Box] = field(default_factory=list)
    formulas: list[str] = field(default_factory=list)
    caption: str = ""
    table_html: str = ""
    figure_index: int | None = None
    sort_key: float = 0.0

    @property
    def pages(self) -> list[int]:
        return sorted({box.page for box in self.boxes})

    def to_payload(self, *, document_id: str, workspace_id: str, filename: str, title: str) -> dict:
        return {
            "document_id": document_id,
            "workspace_id": workspace_id,
            "filename": filename,
            "title": title,
            "order": self.order,
            "content_type": self.content_type,
            "text": self.text,
            "section": " › ".join(self.section_path),
            "section_path": self.section_path,
            "pages": self.pages,
            "boxes": [box.as_dict() for box in self.boxes],
            "formulas": self.formulas,
            "has_formula": bool(self.formulas),
            "caption": self.caption,
            "table_html": self.table_html,
            "figure_index": self.figure_index,
        }
