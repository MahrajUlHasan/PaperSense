"""Chunker tests on a small hand-built Docling document (no PDF parsing needed)."""
from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    ProvenanceItem,
    Size,
)

from services.chunking import Chunker
from services.parsing import ParseResult

ATTENTION = r"\mathrm{Attention}(Q,K,V)=\mathrm{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V"


def prov(l, t, r, b, n):
    """A provenance on page 1 in Docling's PDF coordinates (origin bottom-left, so t > b)."""
    return ProvenanceItem(
        page_no=1,
        bbox=BoundingBox(l=l, t=t, r=r, b=b, coord_origin=CoordOrigin.BOTTOMLEFT),
        charspan=(0, n),
    )


def make_parsed() -> ParseResult:
    doc = DoclingDocument(name="sample")
    doc.add_page(page_no=1, size=Size(width=612, height=792))
    doc.add_title(text="A Tiny Paper", prov=prov(72, 760, 540, 740, 12))
    doc.add_heading(text="1 Introduction", level=1, prov=prov(72, 720, 300, 705, 14))
    intro = "Transformers rely on attention. " * 5
    doc.add_text(label=DocItemLabel.TEXT, text=intro, prov=prov(72, 700, 540, 640, len(intro)))
    doc.add_formula(text=ATTENTION, prov=prov(100, 630, 500, 600, 40))
    doc.add_heading(text="2 Results", level=1, prov=prov(72, 580, 300, 565, 9))
    doc.add_text(label=DocItemLabel.TEXT, text="The model reaches 28.4 BLEU.", prov=prov(72, 560, 540, 540, 28))
    return ParseResult(
        doc=doc, status="success", errors=[], page_count=1, seconds=0.0,
        pypdf_page_text={1: "x"}, docling_page_chars={1: 1}, pdf_page_sizes={1: (612.0, 792.0)},
    )


def test_order_sections_and_boxes():
    """Chunks are numbered in order, keep their section, and have boxes in top-left origin."""
    title, records = Chunker(max_tokens=64).build(make_parsed(), "sample.pdf")
    assert title == "A Tiny Paper"
    assert [r.order for r in records] == list(range(len(records)))
    assert any(r.section_path == ["2 Results"] for r in records)
    assert all(r.boxes for r in records)
    assert all(b.t < b.b for r in records for b in r.boxes)


def test_formula_is_never_split():
    _, records = Chunker(max_tokens=64).build(make_parsed(), "sample.pdf")
    assert all(r.text.count("$$") % 2 == 0 for r in records)
    assert [f for r in records for f in r.formulas] == [ATTENTION]


def test_embed_text_has_context():
    _, records = Chunker(max_tokens=64).build(make_parsed(), "sample.pdf")
    results = next(r for r in records if r.section_path == ["2 Results"])
    assert results.embed_text.startswith("A Tiny Paper › 2 Results")
