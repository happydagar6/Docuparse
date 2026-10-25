"""
services/rag/ingestion.py
=============================================================================
Document Ingestion & Smart Chunking Service
=============================================================================
This module is responsible for:
1. Cleaning raw text extracted from documents (PDF, CSV, TXT).
2. Recursively splitting text into coherent semantic chunks.
3. Mapping each chunk to its exact page number for accurate citation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re
import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """
    Represets a single atomic piece of a document ready for vector embedding.
    """
    chunk_id: str                   #unique identifier: e.g., "paper123_chunk_0"
    paper_id: str                   # The ID of the parent research paper
    content: str                    # The actual text snippet (approx. 1,000 characters)
    page_number: int                # The PDF page where this text appears (e.g., Page 4)
    chunk_index: int                # Sequential order in the document (0, 1, 2...)
    metadata: Dict[str, Any] = field(default_factory=dict) # Extra metadata (title, authors, etc.)


    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk object to a dictionary for database and Qdrant storage. """
        return {
            "chunk_id": self.chunk_id,
            "paper_id": self.paper_id,
            "content": self.content,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
        }


class DocumentIngestionService:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the ingestion service with chunk configuration.
        
        Args:
            chunk_size (int): Max characters per chunk (default: 1000 ≈ 200-250 words).
            chunk_overlap (int): Overlapping characters between consecutive chunks (default: 200).
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Configure the industry-standard recursive text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]  # Paragraphs -> Lines -> Words -> Chars
        )

    def clean_text(self, text: str) -> str:
        """
        Sanitize raw text extracted from PDF/CSV files.
        """
        if not text:
            return ""

        # 1. Strip null bytes (\x00). PostgreSQL crashes if a string contains null bytes!
        cleaned = text.replace("\x00", "")

        # 2. Normalize carriage returns (\r\n -> \n)
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

        # 3. Replace 3 or more consecutive newlines with 2 (cleans up empty page gaps)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # 4. Replace multiple horizontal spaces or tabs with a single space
        cleaned = re.sub(r"[ \t]+", " ", cleaned)

        return cleaned.strip()

    
    def _find_page_number(self, char_offset: int, page_info: Optional[List[Dict[str, Any]]]) -> int:
        """
        Determine which PDF page a character offset belongs to.
        
        Args:
            char_offset (int): The starting character index of the chunk in the full document.
            page_info (list): Page boundaries from PDF parser, e.g.
                              [{"page_number": 1, "start_char": 0, "end_char": 2000}, ...]
        """
        if not page_info:
            return 1 # Fallback to page 1 if no page metadata exists (e.g., text/csv files)

        for page in page_info:
            start = page.get("start_char", 0)
            end = page.get("end_char", 0)
            # Check if this chunk starts within this page's character range
            if start <= char_offset <= end:
                return page.get("page_number", 1)

        # If beyond the last recorded offset, return the last page number
        return page_info[-1].get("page_number", 1)

    def chunk_document(
        self, 
        text: str, 
        paper_id: str, 
        page_info: Optional[List[Dict[str, Any]]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Splits full document text into structured DocumentChunk objects with page mapping.
        """
        # 1. Clean the incoming text
        sanitized_text = self.clean_text(text)
        if not sanitized_text:
            logger.warning(f"No text to chunk for paper: {paper_id}")
            return []

        # 2. Split text into raw string chunks using LangChain
        raw_chunks = self.text_splitter.split_text(sanitized_text)
        logger.info(f"Generated {len(raw_chunks)} chunks for paper {paper_id}")

        document_chunks: List[DocumentChunk] = []
        current_search_offset = 0

        # 3. Iterate through chunks and map each to its exact page number
        for index, chunk_text in enumerate(raw_chunks):
            # Find the character position of this chunk inside the full document text
            chunk_start_char = sanitized_text.find(chunk_text[:50], current_search_offset)
            if chunk_start_char == -1:
                chunk_start_char = current_search_offset

            # Determine the exact PDF page for this chunk
            page_num = self._find_page_number(chunk_start_char, page_info)

            # Create our structured chunk object
            chunk_obj = DocumentChunk(
                chunk_id=f"{paper_id}_chunk_{index}",
                paper_id=paper_id,
                content=chunk_text,
                page_number=page_num,
                chunk_index=index,
                metadata=extra_metadata or {}
            )
            document_chunks.append(chunk_obj)

            # Advance our search offset for the next chunk
            current_search_offset = chunk_start_char + (len(chunk_text) - self.chunk_overlap)

        return document_chunks

    # Default singleton instance for easy import across the backend
document_ingestion_service = DocumentIngestionService()