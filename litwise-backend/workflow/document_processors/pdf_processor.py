"""
PDF Document Processor

Processes PDF documents with full multimodal support (text + images + tables).
Uses existing PyPDF2, PyMuPDF, and pdfplumber infrastructure.
"""

import PyPDF2
import warnings
from typing import Dict, List, Tuple
from .base_processor import BaseDocumentProcessor
from ..utils import sanitize_text

# ✅ Suppress PyPDF2 advanced encoding warnings (informational only, doesn't affect extraction)
warnings.filterwarnings('ignore', category=PyPDF2.errors.PdfReadWarning)


# [LITWISE ARCHITECTURE]: PDF Processor Implementation
# Why we do this: PDFs are the most complex document type in academic and enterprise RAG.
# They require 3 distinct capabilities:
# 1. Clean character-level text extraction with exact page boundaries.
# 2. Multimodal table and image extraction for layout awareness.
# 3. Robust handling of encryption and corrupt binary characters.
class PDFProcessor(BaseDocumentProcessor):
    """Process PDF documents - maintains existing multimodal capabilities."""
    
    SUPPORTED_EXTENSIONS = ['.pdf']
    SUPPORTED_MIME_TYPES = ['application/pdf']
    MAX_FILE_SIZE_MB = 35
    
    def extract_text(self, file_path: str) -> Tuple[str, List[Dict]]:
        """Extract text using PyPDF2 with character offset tracking."""
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                
                # [LITWISE RAG LOGIC]: Decryption Fallback
                # Why we do this: Many published research papers are 'encrypted' with an empty password
                # (printing/editing restrictions). Trying empty password decrypts them without crashing.
                if reader.is_encrypted:
                    self.logger.warning("PDF is encrypted, attempting decryption")
                    try:
                        reader.decrypt('')
                    except Exception as decrypt_error:
                        raise Exception(
                            f"PDF is encrypted and cannot be decrypted. "
                            f"Please use an unencrypted PDF. Error: {decrypt_error}"
                        )
                
                full_text = ""
                page_info = []
                
                self.logger.info(f"PDF contains {len(reader.pages)} pages")
                
                # [LITWISE RAG LOGIC]: Character Offset Page Tracking
                # Why we do this: When an LLM cites "Page 4", how does it know where Page 4 was?
                # We record start_pos and end_pos string indices for every page.
                # When a text chunk is retrieved from Qdrant, we match its string position to these
                # page boundaries to provide 100% verified citations.
                for page_num, page in enumerate(reader.pages, 1):
                    page_text = page.extract_text()
                    
                    # Sanitize text: vacuum out null bytes (\x00) that crash Postgres/Qdrant
                    page_text = sanitize_text(page_text)
                    
                    start_pos = len(full_text)
                    full_text += page_text + "\n"  # Add page break
                    end_pos = len(full_text) - 1  # Exclude trailing newline
                    
                    page_info.append({
                        "page_num": page_num,
                        "start_pos": start_pos,
                        "end_pos": end_pos,
                        "text": page_text,
                        "type": "page"
                    })
                
                self.logger.info(
                    f"PDF extraction complete: {len(page_info)} pages, {len(full_text)} total chars"
                )
                return full_text, page_info
        
        except Exception as e:
            self.logger.error(f"PDF extraction failed: {e}")
            raise
    
    # [LITWISE RAG LOGIC]: Multimodal Extraction (Tables & Images)
    # Why we do this: Traditional RAG ignores tables and diagrams.
    # We pass the page_info to multimodal_extractor so tables are captured with their page coordinates.
    def extract_multimodal(self, file_path: str, page_info: List[Dict] = None) -> Dict:
        """Extract images and tables with layout awareness."""
        from ..multimodal_extractor import multimodal_extractor
        
        self.logger.info("Extracting multimodal content (images, tables) with layout awareness")
        multimodal_content = multimodal_extractor.extract_all(file_path, page_info)
        
        self.logger.info(
            f"Multimodal extraction complete - "
            f"Images: {len(multimodal_content.get('images', []))}, "
            f"Tables: {len(multimodal_content.get('tables', []))}"
        )
        
        return multimodal_content
    
    # [LITWISE RAG LOGIC]: Native Metadata Extraction with IndirectObject Safe String Conversion
    # Why we do this: PyPDF2 often returns 'IndirectObject' pointers instead of strings.
    # If saved directly to JSON, the API will crash with TypeError: Object of type IndirectObject is not JSON serializable.
    # Our _safe_str resolver ensures all fields are clean Python strings.
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract PDF metadata using PyPDF2."""
        try:
            self.logger.info("Extracting metadata from PDF")
            
            metadata = {
                'title': None,
                'authors': [],
                'publication_year': None,
                'doi': None,
                'journal': None,
                'abstract': None,
                'keywords': [],
                'extraction_source': 'pypdf2'
            }
            
            try:
                with open(file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    if pdf_reader.metadata:
                        pdf_meta = pdf_reader.metadata

                        def _safe_str(val) -> str | None:
                            """Convert IndirectObject pointers into JSON-serializable strings."""
                            if val is None:
                                return None
                            resolved = str(val).strip()
                            return resolved if resolved else None

                        raw_title = _safe_str(pdf_meta.get('/Title') or pdf_meta.get('Title'))
                        raw_author = _safe_str(pdf_meta.get('/Author') or pdf_meta.get('Author'))
                        raw_keywords = _safe_str(pdf_meta.get('/Keywords') or pdf_meta.get('Keywords'))

                        metadata['title'] = raw_title
                        metadata['authors'] = [{'name': raw_author}] if raw_author else []
                        metadata['keywords'] = [k.strip() for k in raw_keywords.split(',') if k.strip()] if raw_keywords else []

                    self.logger.debug(f"Extracted {len(pdf_reader.pages)} pages from PDF")
            
            except Exception as e:
                self.logger.debug(f"PyPDF2 extraction failed: {e}")
            
            return metadata

        except Exception as e:
            self.logger.debug(f"Metadata extraction failed: {e} - continuing without metadata")
            return {}
