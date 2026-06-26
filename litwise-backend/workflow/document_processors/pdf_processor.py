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


class PDFProcessor(BaseDocumentProcessor):
    """Process PDF documents - maintains existing multimodal capabilities."""
    
    SUPPORTED_EXTENSIONS = ['.pdf']
    SUPPORTED_MIME_TYPES = ['application/pdf']
    MAX_FILE_SIZE_MB = 35
    
    def extract_text(self, file_path: str) -> Tuple[str, List[Dict]]:
        """Extract text using PyPDF2 (existing implementation).
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            Tuple of (full_text, page_info)
        
        Raises:
            Exception: If PDF extraction fails or is encrypted without password
        """
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                
                # Handle encryption
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
                
                for page_num, page in enumerate(reader.pages, 1):
                    page_text = page.extract_text()
                    # Sanitize text to remove null bytes and control characters
                    page_text = sanitize_text(page_text)
                    
                    start_pos = len(full_text)
                    full_text += page_text + "\n"  # Add page break
                    end_pos = len(full_text) - 1  # Don't include the newline in range
                    
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
    
    def extract_multimodal(self, file_path: str, page_info: List[Dict] = None) -> Dict:
        """Extract images and tables using existing multimodal_extractor with layout awareness.
        
        Args:
            file_path: Path to PDF file
            page_info: Page information for layout-aware processing (page-span detection)
        
        Returns:
            Dict with 'images', 'tables', 'has_equations' keys
        
        Raises:
            Exception: If multimodal extraction fails
        """
        from ..multimodal_extractor import multimodal_extractor
        
        self.logger.info("Extracting multimodal content (images, tables) with layout awareness")
        multimodal_content = multimodal_extractor.extract_all(file_path, page_info)
        
        self.logger.info(
            f"Multimodal extraction complete - "
            f"Images: {len(multimodal_content.get('images', []))}, "
            f"Tables: {len(multimodal_content.get('tables', []))}"
        )
        
        return multimodal_content
    
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract PDF metadata using PyPDF2 (synchronous fallback).
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            Dict with title, authors, publication_year, doi, journal, etc.
        
        Raises:
            Exception: If metadata extraction fails
        """
        try:
            import PyPDF2
            
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
            
            # Extract metadata from PDF
            try:
                with open(file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    # Extract PDF metadata if available
                    if pdf_reader.metadata:
                        pdf_meta = pdf_reader.metadata

                        def _safe_str(val) -> str | None:
                            """
                            Convert any PyPDF2 value (including IndirectObject) to a plain
                            Python string.  IndirectObject is a lazy reference that is NOT
                            JSON-serializable; str() resolves it to its actual value.
                            Returns None for blank/missing values.
                            """
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

                    # Note: ⚠️ For full AI-powered extraction, use async api in RAG pipeline
                    self.logger.debug(f"Extracted {len(pdf_reader.pages)} pages from PDF")
            
            except Exception as e:
                self.logger.debug(f"PyPDF2 extraction failed: {e}")
            
            return metadata

        
        except Exception as e:
            self.logger.debug(f"Metadata extraction failed: {e} - continuing without metadata")
            # Return empty dict - metadata is optional
            return {}
