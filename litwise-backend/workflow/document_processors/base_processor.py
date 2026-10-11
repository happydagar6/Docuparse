"""
Base Document Processor

Abstract base class for all document processors.
Implements the Strategy pattern for different file format processing.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
import logging


# [LITWISE ARCHITECTURE]: Standardized Document Data Model
# Why we do this: In an enterprise RAG pipeline, downstream components (chunkers, embedders, Qdrant)
# should NOT care whether a document was originally a PDF, CSV, or Text file.
# This dataclass acts as a universal container, standardizing the output across all formats.
@dataclass
class ProcessedDocument:
    """Standardized output from any document processor."""
    full_text: str                          # Complete sanitized text of the document
    page_info: List[Dict]                   # Page or section offsets used for pinpoint citations
    multimodal_content: Dict                # Extracted visual elements (tables, images, charts)
    metadata: Dict                          # Format-specific metadata (title, author, row count)
    file_type: str                          # Name of processor used (e.g., 'PDFProcessor')
    processing_notes: List[str] = field(default_factory=list)  # Non-fatal warnings and diagnostic logs


# [LITWISE ARCHITECTURE]: Base Processor Interface (Strategy Pattern)
# Why we do this: We use Python's ABC (Abstract Base Class) to define a strict contract.
# Any new file format (e.g., DOCX, HTML) only needs to inherit from this class and implement
# the 3 abstract methods. This follows the Open/Closed Principle (open for extension, closed for modification).
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
        """Extract text with position tracking."""
        pass
    
    @abstractmethod
    def extract_multimodal(self, file_path: str) -> Dict:
        """Extract images, tables, charts, etc."""
        pass
    
    @abstractmethod
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract format-specific metadata."""
        pass
    
    # [LITWISE ARCHITECTURE]: Template Method Pattern
    # Why we do this: The master workflow (validation -> text extraction -> multimodal extraction ->
    # metadata extraction -> graceful fallback) is defined once here in the base class.
    # Subclasses only supply format-specific parsing logic, avoiding duplicated error-handling code.
    def process(self, file_path: str) -> ProcessedDocument:
        """Main processing pipeline - Template Method pattern.
        
        This method orchestrates the extraction process and handles
        errors uniformly across all processors.
        """
        processing_notes = []
        
        try:
            # Step 1: Extract text and page/section boundaries
            self.logger.info(f"Extracting text from {file_path}")
            full_text, page_info = self.extract_text(file_path)
            
            # Validation guard: reject empty or corrupt documents early
            if not full_text or len(full_text.strip()) < 10:
                raise ValueError("Extracted text is empty or too short")
            
            # Step 2: Extract multimodal content (tables, images)
            # Notice the try-catch: if image/table extraction fails, we DO NOT crash the entire upload.
            # We log a warning note and gracefully continue with text only.
            self.logger.info(f"Extracting multimodal content")
            try:
                multimodal_content = self.extract_multimodal(file_path, page_info)
            except Exception as e:
                self.logger.warning(f"Multimodal extraction failed: {e}")
                multimodal_content = {'images': [], 'tables': []}
                processing_notes.append(f"Multimodal extraction failed: {str(e)}")
            
            # Step 3: Extract metadata (author, title, creation date)
            # Same graceful fallback: metadata failures do not block document ingestion.
            self.logger.info(f"Extracting metadata")
            try:
                metadata = self.extract_metadata(file_path)
            except Exception as e:
                self.logger.warning(f"Metadata extraction failed: {e}")
                metadata = {}
                processing_notes.append(f"Metadata extraction failed: {str(e)}")
            
            # Step 4: Package into standardized ProcessedDocument container
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
