"""
Text chunking service for splitting documents into semantic chunks
"""
from typing import List, Dict
import re
from loguru import logger


class Chunker:
    """Intelligent text chunking for research papers"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove page numbers and headers/footers patterns
        text = re.sub(r'\n\d+\n', '\n', text)
        return text.strip()
    
    def detect_sections(self, text: str) -> List[Dict[str, str]]:
        """
        Detect common research paper sections
        Returns list of sections with their content
        """
        sections = []
        
        # Common section headers in research papers
        section_patterns = [
            r'\n(Abstract|ABSTRACT)\s*\n',
            r'\n(Introduction|INTRODUCTION)\s*\n',
            r'\n(Related Work|RELATED WORK|Literature Review)\s*\n',
            r'\n(Methodology|METHODOLOGY|Methods|METHODS)\s*\n',
            r'\n(Results|RESULTS)\s*\n',
            r'\n(Discussion|DISCUSSION)\s*\n',
            r'\n(Conclusion|CONCLUSION|Conclusions)\s*\n',
            r'\n(References|REFERENCES)\s*\n',
        ]
        
        # Find all section boundaries
        boundaries = []
        for pattern in section_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                boundaries.append({
                    'position': match.start(),
                    'title': match.group(1)
                })
        
        # Sort by position
        boundaries.sort(key=lambda x: x['position'])
        
        # Extract sections
        for i, boundary in enumerate(boundaries):
            start = boundary['position']
            end = boundaries[i + 1]['position'] if i + 1 < len(boundaries) else len(text)
            sections.append({
                'title': boundary['title'],
                'content': text[start:end].strip()
            })
        
        return sections
    
    def chunk_by_sentences(self, text: str) -> List[str]:
        """Split text into chunks while preserving sentence boundaries"""
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence exceeds chunk_size, save current chunk
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Start new chunk with overlap
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_text + " " + sentence
            else:
                current_chunk += " " + sentence
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict[str, any]]:
        """
        Main chunking method that creates semantic chunks

        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to each chunk

        Returns:
            List of chunk dictionaries with text and metadata
        """
        logger.info(f"Chunking text of length {len(text)}")

        # Clean text
        text = self.clean_text(text)

        # Detect sections
        sections = self.detect_sections(text)

        chunks = []
        chunk_id = 0

        if sections:
            # Chunk each section separately
            for section in sections:
                section_chunks = self.chunk_by_sentences(section['content'])
                for chunk_text in section_chunks:
                    chunks.append({
                        'chunk_id': chunk_id,
                        'text': chunk_text,
                        'section': section['title'],
                        'char_count': len(chunk_text),
                        'content_type': 'text',
                        'metadata': metadata or {}
                    })
                    chunk_id += 1
        else:
            # No sections detected, chunk the entire text
            text_chunks = self.chunk_by_sentences(text)
            for chunk_text in text_chunks:
                chunks.append({
                    'chunk_id': chunk_id,
                    'text': chunk_text,
                    'section': 'unknown',
                    'char_count': len(chunk_text),
                    'content_type': 'text',
                    'metadata': metadata or {}
                })
                chunk_id += 1

        logger.info(f"Created {len(chunks)} text chunks")
        return chunks

    def create_table_chunks(
        self, tables: List[Dict], metadata: Dict = None, start_chunk_id: int = 0
    ) -> List[Dict[str, any]]:
        """
        Create chunks from extracted tables.

        Each table becomes a single chunk whose text is the Markdown (or CSV)
        representation so it can be embedded and retrieved.

        Args:
            tables: List of table dicts from Docling (keys: index, html, csv, markdown)
            metadata: Optional metadata to attach
            start_chunk_id: Starting chunk_id to continue numbering

        Returns:
            List of chunk dictionaries with content_type='table'
        """
        chunks = []
        chunk_id = start_chunk_id

        for table in tables:
            # Prefer markdown, fall back to csv, then html
            table_text = (
                table.get("markdown")
                or table.get("csv")
                or table.get("html", "")
            )
            if not table_text or not table_text.strip():
                continue

            chunks.append({
                'chunk_id': chunk_id,
                'text': f"[TABLE {table.get('index', chunk_id)}]\n{table_text}",
                'section': 'table',
                'char_count': len(table_text),
                'content_type': 'table',
                'table_html': table.get('html', ''),
                'metadata': metadata or {},
            })
            chunk_id += 1

        logger.info(f"Created {len(chunks)} table chunks")
        return chunks

    def create_image_chunks(
        self, images: List[Dict], metadata: Dict = None, start_chunk_id: int = 0
    ) -> List[Dict[str, any]]:
        """
        Create chunks from extracted images.

        Each image becomes a chunk whose text is the caption (used for
        embedding).  The base64 PNG data is stored in the chunk metadata so it
        can be forwarded to a multimodal LLM later.

        Args:
            images: List of image dicts from Docling (keys: base64_png, caption)
            metadata: Optional metadata to attach
            start_chunk_id: Starting chunk_id to continue numbering

        Returns:
            List of chunk dictionaries with content_type='image'
        """
        chunks = []
        chunk_id = start_chunk_id

        for idx, img in enumerate(images):
            caption = img.get("caption", "").strip() or f"Figure {idx + 1}"
            # The text used for embedding is the caption / description
            chunks.append({
                'chunk_id': chunk_id,
                'text': f"[FIGURE] {caption}",
                'section': 'figure',
                'char_count': len(caption),
                'content_type': 'image',
                'image_base64': img.get('base64_png', ''),
                'metadata': metadata or {},
            })
            chunk_id += 1

        logger.info(f"Created {len(chunks)} image chunks")
        return chunks

