"""
PDF parsing service for extracting text from research papers
"""
import io
from typing import Dict, List, Optional
import PyPDF2
import pdfplumber
from loguru import logger


class PDFParser:
    """Extract and structure text from PDF research papers"""
    
    def __init__(self):
        self.supported_formats = ['.pdf']
    
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
    
    def parse_pdf(self, pdf_file: bytes, filename: str = "") -> Dict[str, any]:
        """
        Main parsing method that extracts text and metadata
        
        Args:
            pdf_file: PDF file as bytes
            filename: Original filename
            
        Returns:
            Dictionary with text, metadata, and page count
        """
        logger.info(f"Parsing PDF: {filename}")
        
        # Try pdfplumber first (better quality), fallback to PyPDF2
        text = self.extract_text_pdfplumber(pdf_file)
        if not text or len(text.strip()) < 100:
            logger.warning("pdfplumber extraction poor, trying PyPDF2")
            text = self.extract_text_pypdf2(pdf_file)
        
        metadata = self.extract_metadata(pdf_file)
        
        # Count pages
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file))
            page_count = len(pdf_reader.pages)
        except:
            page_count = 0
        
        return {
            "text": text,
            "metadata": metadata,
            "page_count": page_count,
            "filename": filename,
            "char_count": len(text)
        }

