"""Page geometry helpers for Docling items."""
from __future__ import annotations

from dataclasses import dataclass

from docling_core.types.doc import DoclingDocument


@dataclass(frozen=True)
class Box:
    """A rectangle on a PDF page, in PDF points, with the origin at the TOP-LEFT corner."""

    page: int
    l: float
    t: float
    r: float
    b: float

    def as_dict(self) -> dict:
        return {
            "page": self.page,
            "l": round(self.l, 2),
            "t": round(self.t, 2),
            "r": round(self.r, 2),
            "b": round(self.b, 2),
        }


def item_boxes(item, doc: DoclingDocument) -> list[Box]:
    """Every box of a Docling item (one per provenance entry), converted to top-left origin."""
    boxes: list[Box] = []
    for prov in getattr(item, "prov", None) or []:
        page = doc.pages.get(prov.page_no)
        if page is None:
            continue
        bb = prov.bbox.to_top_left_origin(page_height=page.size.height)
        boxes.append(Box(prov.page_no, bb.l, bb.t, bb.r, bb.b))
    return boxes
