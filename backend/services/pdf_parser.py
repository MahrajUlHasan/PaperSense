"""
PDF parsing service for extracting text from research papers.

Uses Docling as the primary parser for advanced extraction of structured text,
tables, and images.  Falls back to pdfplumber / PyPDF2 when Docling is
unavailable or fails.
"""
import base64
import io
import tempfile
import os
from typing import Dict, List, Optional

import PyPDF2
import pdfplumber
from loguru import logger

# Docling imports – wrapped so the rest of the module still works if docling
# is not installed (graceful degradation).
try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat, DocumentStream
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling_core.types.doc import PictureItem, TableItem

    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    logger.warning(
        "Docling is not installed – advanced PDF parsing (tables, images) "
        "will be unavailable.  Install with: pip install docling"
    )


class PDFParser:
    """Extract and structure text from PDF research papers"""

    def __init__(self):
        self.supported_formats = ['.pdf']

        # Lazily initialised Docling converter (heavy model download on first use)
        self._docling_converter: Optional["DocumentConverter"] = None

    # ------------------------------------------------------------------
    # Docling helpers
    # ------------------------------------------------------------------

    def _get_docling_converter(self) -> "DocumentConverter":
        """Return a cached DocumentConverter, creating it on first call."""
        if self._docling_converter is None:
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_table_structure = True
            pipeline_options.generate_picture_images = False  # skip heavy image generation todo:turn on if there is enough ram
            pipeline_options.generate_page_images = False     # not needed for RAG
            pipeline_options.images_scale = 1.0               # lower resolution to save memory
            pipeline_options.do_ocr = False                   # skip OCR for born-digital PDFs

            self._docling_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    )
                }
            )
        return self._docling_converter

    def extract_with_docling(self, pdf_file: bytes, filename: str = "document.pdf") -> Dict[str, any]:
        """
        Parse a PDF with Docling and return structured results including
        markdown text, extracted tables (as markdown), and base64-encoded
        images of figures found in the document.

        Returns a dict with keys:
            - text:   full document exported as Markdown
            - tables: list of dicts with table markdown and optional dataframe CSV
            - images: list of dicts with base64 PNG data and captions
        """
        converter = self._get_docling_converter()

        # Docling can accept a DocumentStream for in-memory bytes
        buf = io.BytesIO(pdf_file)
        source = DocumentStream(name=filename, stream=buf)

        conv_result = converter.convert(source)
        doc = conv_result.document

        # --- Full text as Markdown ---
        markdown_text = doc.export_to_markdown()

        # --- Tables ---
        tables: List[Dict[str, str]] = []
        for idx, table in enumerate(doc.tables):
            table_data: Dict[str, str] = {
                "index": idx,
                "html": table.export_to_html(doc=doc),
            }
            try:
                import pandas as pd
                df = table.export_to_dataframe(doc=doc)
                table_data["csv"] = df.to_csv(index=False)
                table_data["markdown"] = df.to_markdown(index=False)
            except Exception:
                table_data["csv"] = ""
                table_data["markdown"] = ""
            tables.append(table_data)

        # --- Images / Figures (captions only; actual images skipped to save memory) ---
        images: List[Dict[str, str]] = []
        for element, _level in doc.iterate_items():
            if isinstance(element, PictureItem):
                try:
                    caption = getattr(element, "caption", "") or ""
                    entry: Dict[str, str] = {"caption": caption}
                    # Only encode image bytes when picture generation is enabled
                    pil_image = element.get_image(doc)
                    if pil_image is not None:
                        img_buffer = io.BytesIO()
                        pil_image.save(img_buffer, format="PNG")
                        entry["base64_png"] = base64.b64encode(
                            img_buffer.getvalue()
                        ).decode("utf-8")
                    images.append(entry)
                except Exception as img_err:
                    logger.warning(f"Could not extract image: {img_err}")

        return {
            "text": markdown_text,
            "tables": tables,
            "images": images,
        }

    # ------------------------------------------------------------------
    # Legacy parsers (kept as fallbacks)
    # ------------------------------------------------------------------

    def extract_text_pypdf2(self, pdf_file: bytes) -> str:
        """Extract text using PyPDF2"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            return ""

    def extract_text_pdfplumber(self, pdf_file: bytes) -> str:
        """Extract text using pdfplumber (better for complex layouts)"""
        try:
            text = ""
            with pdfplumber.open(io.BytesIO(pdf_file)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            return ""

    def extract_metadata(self, pdf_file: bytes) -> Dict[str, str]:
        """Extract metadata from PDF"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file))
            metadata = pdf_reader.metadata
            return {
                "title": metadata.get("/Title", "Unknown"),
                "author": metadata.get("/Author", "Unknown"),
                "subject": metadata.get("/Subject", ""),
                "creator": metadata.get("/Creator", ""),
                "producer": metadata.get("/Producer", ""),
                "creation_date": str(metadata.get("/CreationDate", "")),
            }
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return {}

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def parse_pdf(self, pdf_file: bytes, filename: str = "") -> Dict[str, any]:
        """
        Main parsing method that extracts text, tables, images, and metadata.

        Strategy:
            1. Try Docling first (best quality – structured text, tables, images).
            2. Fall back to pdfplumber → PyPDF2 for plain text if Docling fails.

        Args:
            pdf_file: PDF file as bytes
            filename: Original filename

        Returns:
            Dictionary with text, metadata, page_count, tables, images, etc.
        """
        logger.info(f"Parsing PDF: {filename}")

        tables: List[Dict] = []
        images: List[Dict] = []
        text = ""

        # --- Attempt Docling extraction ---
        if DOCLING_AVAILABLE:
            try:
                logger.info("Using Docling for advanced PDF parsing")
                docling_result = self.extract_with_docling(pdf_file, filename or "document.pdf")
                text = docling_result.get("text", "")
                tables = docling_result.get("tables", [])
                images = docling_result.get("images", [])
                logger.info(
                    f"Docling extracted {len(text)} chars, "
                    f"{len(tables)} tables, {len(images)} images"
                )
            except Exception as e:
                logger.error(f"Docling extraction failed, falling back: {e}")
                text = ""

        # --- Fallback to legacy parsers if Docling produced no text ---
        if not text or len(text.strip()) < 100:
            logger.warning("Docling text insufficient, trying pdfplumber")
            text = self.extract_text_pdfplumber(pdf_file)

        if not text or len(text.strip()) < 100:
            logger.warning("pdfplumber extraction poor, trying PyPDF2")
            text = self.extract_text_pypdf2(pdf_file)

        metadata = self.extract_metadata(pdf_file)

        # Count pages
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file))
            page_count = len(pdf_reader.pages)
        except Exception:
            page_count = 0

        return {
            "text": text,
            "metadata": metadata,
            "page_count": page_count,
            "filename": filename,
            "char_count": len(text),
            "tables": tables,
            "images": images,
        }

