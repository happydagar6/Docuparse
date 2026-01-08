"""
Base Document Processor

Abstract base class for all document processors.
Implements the Strategy pattern for different file format processing.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import logging


@dataclass
class ProcessedDocument:
    """Standardized output from any document processor."""
    full_text: str
    page_info: List[Dict]  # Page/section info with positions
    multimodal_content: Dict  # Images, tables, charts
    metadata: Dict  # Format-specific metadata
    file_type: str
    processing_notes: List[str] = field(default_factory=list)  # Warnings, info messages


class BaseDocumentProcessor(ABC):
    """Abstract base class for all document processors."""
    
    # Class attributes - must be overridden by subclasses
    SUPPORTED_EXTENSIONS: List[str] = []
    SUPPORTED_MIME_TYPES: List[str] = []
    MAX_FILE_SIZE_MB: int = 35
    
    def __init__(self):
        self.logger = self._setup_logger()
    
    @abstractmethod
    def extract_text(self, file_path: str) -> Tuple[str, List[Dict]]:
        """Extract text with position tracking.
        
        Args:
            file_path: Path to the document file
        
        Returns:
            Tuple of (full_text, page_info)
            - full_text: Complete extracted text
            - page_info: List of dicts with page/section metadata
        
        Raises:
            Exception: If text extraction fails
        """
        pass
    
    @abstractmethod
    def extract_multimodal(self, file_path: str) -> Dict:
        """Extract images, tables, charts, etc.
        
        Args:
            file_path: Path to the document file
        
        Returns:
            Dict with 'images', 'tables', 'charts', etc.
            Example: {'images': [], 'tables': [], 'has_equations': False}
        
        Raises:
            Exception: If multimodal extraction fails
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract format-specific metadata.
        
        Args:
            file_path: Path to the document file
        
        Returns:
            Dict with title, author, keywords, etc.
            Example: {'title': 'Document', 'authors': [], 'publication_year': None}
        
        Raises:
            Exception: If metadata extraction fails
        """
        pass
    
    def process(self, file_path: str) -> ProcessedDocument:
        """Main processing pipeline - Template Method pattern.
        
        This method orchestrates the extraction process and handles
        errors uniformly across all processors.
        
        Args:
            file_path: Path to the document file
        
        Returns:
            ProcessedDocument with all extracted content
        
        Raises:
            ValueError: If extracted text is empty or invalid
            Exception: If processing fails critically
        """
        processing_notes = []
        
        try:
            # Step 1: Extract text
            self.logger.info(f"Extracting text from {file_path}")
            full_text, page_info = self.extract_text(file_path)
            
            if not full_text or len(full_text.strip()) < 10:
                raise ValueError("Extracted text is empty or too short")
            
            # Step 2: Extract multimodal content
            self.logger.info(f"Extracting multimodal content")
            try:
                multimodal_content = self.extract_multimodal(file_path)
            except Exception as e:
                self.logger.warning(f"Multimodal extraction failed: {e}")
                multimodal_content = {'images': [], 'tables': []}
                processing_notes.append(f"Multimodal extraction failed: {str(e)}")
            
            # Step 3: Extract metadata
            self.logger.info(f"Extracting metadata")
            try:
                metadata = self.extract_metadata(file_path)
            except Exception as e:
                self.logger.warning(f"Metadata extraction failed: {e}")
                metadata = {}
                processing_notes.append(f"Metadata extraction failed: {str(e)}")
            
            return ProcessedDocument(
                full_text=full_text,
                page_info=page_info,
                multimodal_content=multimodal_content,
                metadata=metadata,
                file_type=self.__class__.__name__,
                processing_notes=processing_notes
            )
            
        except Exception as e:
            self.logger.error(f"Processing failed for {file_path}: {e}")
            raise
    
    @classmethod
    def can_process(cls, file_extension: str = None, mime_type: str = None) -> bool:
        """Check if this processor can handle the file.
        
        Args:
            file_extension: File extension (e.g., '.pdf')
            mime_type: MIME type (e.g., 'application/pdf')
        
        Returns:
            True if this processor supports the file type
        """
        if file_extension:
            return file_extension.lower() in [ext.lower() for ext in cls.SUPPORTED_EXTENSIONS]
        if mime_type:
            return mime_type in cls.SUPPORTED_MIME_TYPES
        return False
    
    def _setup_logger(self) -> logging.Logger:
        """Setup processor-specific logger.
        
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(self.__class__.__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
