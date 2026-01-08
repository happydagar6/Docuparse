"""
Document Processor Factory

Registry and factory for all document processors.
Provides automatic processor selection based on file type.
"""

from typing import Dict, Type, Optional, List
from .base_processor import BaseDocumentProcessor, ProcessedDocument
from .pdf_processor import PDFProcessor
from .text_processor import TextProcessor
from .csv_processor import CSVProcessor


class ProcessorRegistry:
    """Registry for all document processors."""
    
    _processors: Dict[str, Type[BaseDocumentProcessor]] = {}
    _initialized = False
    
    @classmethod
    def _initialize(cls):
        """Initialize the registry with all processors."""
        if cls._initialized:
            return
        
        # Register all processors
        cls.register(PDFProcessor)
        cls.register(TextProcessor)
        cls.register(CSVProcessor)
        
        cls._initialized = True
    
    @classmethod
    def register(cls, processor_class: Type[BaseDocumentProcessor]):
        """Register a processor class.
        
        Args:
            processor_class: Processor class to register
        
        Returns:
            The processor class (for decorator use)
        """
        for ext in processor_class.SUPPORTED_EXTENSIONS:
            cls._processors[ext.lower()] = processor_class
        return processor_class
    
    @classmethod
    def get_processor(
        cls, 
        file_extension: str = None, 
        mime_type: str = None
    ) -> Optional[Type[BaseDocumentProcessor]]:
        """Get appropriate processor for file type.
        
        Args:
            file_extension: File extension (e.g., '.pdf')
            mime_type: MIME type (e.g., 'application/pdf')
        
        Returns:
            Processor class or None if not supported
        """
        cls._initialize()
        
        if file_extension:
            ext = file_extension.lower()
            if not ext.startswith('.'):
                ext = '.' + ext
            return cls._processors.get(ext)
        
        # If only mime type provided, search through all processors
        if mime_type:
            for processor_class in set(cls._processors.values()):
                if processor_class.can_process(mime_type=mime_type):
                    return processor_class
        
        return None
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Get list of all supported file extensions.
        
        Returns:
            List of extensions (e.g., ['.pdf', '.txt', '.csv'])
        """
        cls._initialize()
        return sorted(list(cls._processors.keys()))
    
    @classmethod
    def get_supported_mime_types(cls) -> List[str]:
        """Get list of all supported MIME types.
        
        Returns:
            List of MIME types
        """
        cls._initialize()
        mime_types = set()
        for processor_class in set(cls._processors.values()):
            mime_types.update(processor_class.SUPPORTED_MIME_TYPES)
        return sorted(list(mime_types))
    
    @classmethod
    def get_processor_info(cls) -> List[Dict]:
        """Get information about all registered processors.
        
        Returns:
            List of dicts with processor details
        """
        cls._initialize()
        
        info = []
        seen_processors = set()
        
        for processor_class in cls._processors.values():
            if processor_class.__name__ in seen_processors:
                continue
            
            seen_processors.add(processor_class.__name__)
            info.append({
                'name': processor_class.__name__,
                'extensions': processor_class.SUPPORTED_EXTENSIONS,
                'mime_types': processor_class.SUPPORTED_MIME_TYPES,
                'max_size_mb': processor_class.MAX_FILE_SIZE_MB
            })
        
        return info


def process_document(
    file_path: str, 
    file_extension: str = None, 
    mime_type: str = None
) -> ProcessedDocument:
    """Main entry point for document processing.
    
    Automatically selects the appropriate processor based on file type
    and processes the document.
    
    Args:
        file_path: Path to the document file
        file_extension: File extension (e.g., '.pdf')
        mime_type: MIME type (e.g., 'application/pdf')
    
    Returns:
        ProcessedDocument with extracted content
    
    Raises:
        ValueError: If file type is not supported
        Exception: If processing fails
    
    Example:
        >>> result = process_document('paper.pdf', file_extension='.pdf')
        >>> print(f"Extracted {len(result.full_text)} chars")
    """
    processor_class = ProcessorRegistry.get_processor(file_extension, mime_type)
    
    if not processor_class:
        supported = ProcessorRegistry.get_supported_extensions()
        raise ValueError(
            f"Unsupported file type '{file_extension}'. "
            f"Supported formats: {', '.join(supported)}"
        )
    
    # Create processor instance and process document
    processor = processor_class()
    return processor.process(file_path)


def get_supported_formats() -> Dict[str, List[str]]:
    """Get all supported file formats grouped by type.
    
    Returns:
        Dict mapping processor names to their supported extensions
    
    Example:
        >>> formats = get_supported_formats()
        >>> print(formats)
        {'PDFProcessor': ['.pdf'], 'TextProcessor': ['.txt', '.md'], ...}
    """
    info = ProcessorRegistry.get_processor_info()
    return {item['name']: item['extensions'] for item in info}
