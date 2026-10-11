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


# [LITWISE ARCHITECTURE]: Dynamic Processor Registry
# Why we do this: Instead of hardcoding processor references across API routes,
# we maintain a central registry. New processors automatically register their supported
# extensions (.pdf, .txt, .csv, etc.), making the system modular and pluggable.
class ProcessorRegistry:
    """Registry for all document processors."""
    
    _processors: Dict[str, Type[BaseDocumentProcessor]] = {}
    _initialized = False
    
    @classmethod
    def _initialize(cls):
        """Initialize the registry with all processors (Lazy Loading)."""
        if cls._initialized:
            return
        
        # Register core format processors
        cls.register(PDFProcessor)
        cls.register(TextProcessor)
        cls.register(CSVProcessor)
        
        cls._initialized = True
    
    @classmethod
    def register(cls, processor_class: Type[BaseDocumentProcessor]):
        """Register a processor class against its supported file extensions."""
        for ext in processor_class.SUPPORTED_EXTENSIONS:
            cls._processors[ext.lower()] = processor_class
        return processor_class
    
    @classmethod
    def get_processor(
        cls, 
        file_extension: str = None, 
        mime_type: str = None
    ) -> Optional[Type[BaseDocumentProcessor]]:
        """Get appropriate processor class by file extension or MIME type."""
        cls._initialize()
        
        # 1. Primary lookup: Match by file extension (e.g., '.pdf')
        if file_extension:
            ext = file_extension.lower()
            if not ext.startswith('.'):
                ext = '.' + ext
            return cls._processors.get(ext)
        
        # 2. Secondary fallback: Match by MIME type (e.g., 'application/pdf')
        if mime_type:
            for processor_class in set(cls._processors.values()):
                if processor_class.can_process(mime_type=mime_type):
                    return processor_class
        
        return None
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Get list of all supported file extensions."""
        cls._initialize()
        return sorted(list(cls._processors.keys()))
    
    @classmethod
    def get_supported_mime_types(cls) -> List[str]:
        """Get list of all supported MIME types."""
        cls._initialize()
        mime_types = set()
        for processor_class in set(cls._processors.values()):
            mime_types.update(processor_class.SUPPORTED_MIME_TYPES)
        return sorted(list(mime_types))
    
    @classmethod
    def get_processor_info(cls) -> List[Dict]:
        """Get diagnostic information about all registered processors."""
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


# [LITWISE ARCHITECTURE]: Factory Entry Point
# Why we do this: Callers (like routes/papers.py) simply pass a file path here.
# They never need to write `if file.endswith('.pdf'): ... elif file.endswith('.csv'): ...`.
# This adheres strictly to the Open/Closed Principle (SOLID).
def process_document(
    file_path: str, 
    file_extension: str = None, 
    mime_type: str = None
) -> ProcessedDocument:
    """Main entry point for document processing.
    
    Automatically selects the appropriate processor based on file type
    and processes the document.
    """
    # 1. Query registry for matching processor class
    processor_class = ProcessorRegistry.get_processor(file_extension, mime_type)
    
    # 2. Reject unsupported file formats with a clear, helpful error message
    if not processor_class:
        supported = ProcessorRegistry.get_supported_extensions()
        raise ValueError(
            f"Unsupported file type '{file_extension}'. "
            f"Supported formats: {', '.join(supported)}"
        )
    
    # 3. Instantiate the selected processor and execute its Template Method pipeline
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
