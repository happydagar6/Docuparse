"""
PDF Document Processor

Processes PDF documents with full multimodal support (text + images + tables).
Uses existing PyPDF2, PyMuPDF, and pdfplumber infrastructure.
"""

import PyPDF2
from typing import Dict, List, Tuple
from .base_processor import BaseDocumentProcessor
from ..utils import sanitize_text


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
    
    def extract_multimodal(self, file_path: str) -> Dict:
        """Extract images and tables using existing multimodal_extractor.
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            Dict with 'images', 'tables', 'has_equations' keys
        
        Raises:
            Exception: If multimodal extraction fails
        """
        from ..multimodal_extractor import multimodal_extractor
        
        self.logger.info("Extracting multimodal content (images, tables)")
        multimodal_content = multimodal_extractor.extract_all(file_path)
        
        self.logger.info(
            f"Multimodal extraction complete - "
            f"Images: {len(multimodal_content.get('images', []))}, "
            f"Tables: {len(multimodal_content.get('tables', []))}"
        )
        
        return multimodal_content
    
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract PDF metadata using AI-powered citation service.
        
        Args:
            file_path: Path to PDF file
        
        Returns:
            Dict with title, authors, publication_year, doi, journal, etc.
        
        Raises:
            Exception: If metadata extraction fails
        """
        try:
            from services.ai_citation_service import ai_citation_service
            
            self.logger.info("Extracting metadata using AI citation service")
            
            # Use existing AI-powered extraction
            citation_result = ai_citation_service.generate_citation_from_pdf(file_path)
            
            if citation_result.get('success') and citation_result.get('metadata'):
                metadata = citation_result['metadata']
                return {
                    'title': metadata.get('title'),
                    'authors': [{'name': author} for author in metadata.get('authors', [])],
                    'publication_year': metadata.get('year'),
                    'doi': metadata.get('doi'),
                    'journal': metadata.get('journal'),
                    'abstract': metadata.get('abstract'),
                    'keywords': metadata.get('keywords', []),
                    'extraction_source': citation_result.get('source', 'ai_citation')
                }
            
            self.logger.warning("AI citation extraction returned no metadata")
            return {}
        
        except Exception as e:
            self.logger.warning(f"Metadata extraction failed: {e}")
            # Return empty dict - not critical for processing
            return {}
