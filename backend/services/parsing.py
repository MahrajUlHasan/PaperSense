"""
v2 PDF parsing with Docling.
"""
from __future__ import annotations

import io
import time
from dataclasses import dataclass, field

from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import ConversionStatus, DocumentStream, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import DoclingDocument, TableItem, TextItem
from loguru import logger
from pypdf import PdfReader

from config import settings


class ParseError(RuntimeError):
    """The PDF could not be parsed at all."""

@dataclass
class ParseResult:
    doc: DoclingDocument
    status: str
    errors: list[str]
    page_count: int
    seconds: float
    pypdf_page_text: dict[int, str]                 # page -> text from the PDF text layer
    docling_page_chars: dict[int, int]              # page -> characters Docling extracted
    pdf_page_sizes: dict[int, tuple[float, float]]  # page -> (width, height) in points
    low_coverage_pages: list[int] = field(default_factory=list)
    ocr_used: bool = False

    @property
    def pypdf_chars(self) -> int:
        return sum(len(t) for t in self.pypdf_page_text.values())

    @property
    def docling_chars(self) -> int:
        return sum(self.docling_page_chars.values())

    @property
    def coverage(self) -> float:
        return self.docling_chars / self.pypdf_chars if self.pypdf_chars else 1.0


def read_text_layer(pdf_bytes: bytes) -> tuple[dict[int, str], dict[int, tuple[float, float]]]:
    """Text and size of every page, straight from the PDF (no layout analysis)."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    texts, sizes = {}, {}
    for number, page in enumerate(reader.pages, start=1):
        texts[number] = (page.extract_text() or "").strip()
        sizes[number] = (float(page.mediabox.width), float(page.mediabox.height))
    return texts, sizes


def docling_chars_per_page(doc: DoclingDocument) -> dict[int, int]:
    counts: dict[int, int] = {}
    for item, _level in doc.iterate_items():
        if not getattr(item, "prov", None):
            continue
        page = item.prov[0].page_no
        if isinstance(item, TableItem):
            counts[page] = counts.get(page, 0) + sum(len(c.text) for c in item.data.table_cells)
        elif isinstance(item, TextItem):
            counts[page] = counts.get(page, 0) + len(item.text or item.orig or "")
    return counts


class PDFParser:
    def __init__(self, ocr_mode: str | None = None, formula_mode: str | None = None):
        self.ocr_mode = ocr_mode or settings.ocr_mode
        self.formula_mode = formula_mode or settings.formula_mode
        self._converters: dict[bool, DocumentConverter] = {}

    def _build_converter(self, do_ocr: bool) -> DocumentConverter:
        opts = PdfPipelineOptions()
        opts.do_table_structure = True
        opts.accelerator_options = AcceleratorOptions(
            num_threads=settings.docling_threads, device=AcceleratorDevice.CPU
        )

        opts.do_ocr = False
        # Formulas (Phase B5)
        opts.do_formula_enrichment = False
        # Figures (Phase B6)
        opts.generate_picture_images = False
        # pypdfium backend: the default docling-parse backend crashed with std::bad_alloc
        # on some pages and stopped the whole pipeline early (A8/B1 finding).
        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=opts, backend=PyPdfiumDocumentBackend)
            }
        )

    def _converter(self, do_ocr: bool) -> DocumentConverter:
        if do_ocr not in self._converters:
            self._converters[do_ocr] = self._build_converter(do_ocr)
        return self._converters[do_ocr]

    def _should_ocr(self, page_text: dict[int, str]) -> bool:
        return False  # replaced in Phase B4

    def parse(self, pdf_bytes: bytes, filename: str) -> ParseResult:
        start = time.perf_counter()
        page_text, page_sizes = read_text_layer(pdf_bytes)
        do_ocr = self._should_ocr(page_text)

        result = self._converter(do_ocr).convert(
            DocumentStream(name=filename, stream=io.BytesIO(pdf_bytes)),
            raises_on_error=False,
        )
        errors = [getattr(e, "error_message", str(e)) for e in (result.errors or [])]
        if result.status == ConversionStatus.FAILURE or result.document is None:
            raise ParseError(f"Docling could not parse {filename}: {errors or result.status.value}")

        doc = result.document
        per_page = docling_chars_per_page(doc)
        low = [
            page for page, text in page_text.items()
            if len(text) >= 200 and per_page.get(page, 0) < settings.min_page_coverage * len(text)
        ]
        parsed = ParseResult(
            doc=doc,
            status=result.status.value,
            errors=errors,
            page_count=len(page_text),
            seconds=time.perf_counter() - start,
            pypdf_page_text=page_text,
            docling_page_chars=per_page,
            pdf_page_sizes=page_sizes,
            low_coverage_pages=low,
            ocr_used=do_ocr,
        )
        if parsed.status != ConversionStatus.SUCCESS.value or low:
            logger.warning(
                f"{filename}: status={parsed.status} coverage={parsed.coverage:.0%} "
                f"low-coverage pages={low} errors={errors}"
            )
        else:
            logger.info(
                f"{filename}: {parsed.page_count} pages in {parsed.seconds:.1f}s, "
                f"coverage {parsed.coverage:.0%}"
            )
        return parsed