# Multi-Format Document Support Architecture

## Executive Summary
Extension of the Litwise RAG system to support multiple document formats beyond PDF, including `.txt`, `.csv`, `.docx`, `.md`, and other common types. This architecture maintains production-grade reliability while ensuring scalability and ease of maintenance.

---

## 1. Current System Analysis

### 1.1 Existing PDF Processing Pipeline
```
Upload → Validation → Extraction → Metadata Extraction → Embedding → Storage
   ↓          ↓            ↓              ↓                  ↓           ↓
FastAPI   PDF Check   PyPDF2/Fitz   AI Citation    OpenAI/Qdrant  Supabase
```

**Key Components:**
- **File Validation**: `app.py:257-259` - Hardcoded PDF-only validation
- **Text Extraction**: `utils.py:extract_text_from_pdf()` - PDF-specific with PyPDF2
- **Multimodal Extraction**: `multimodal_extractor.py` - Images/tables from PDF
- **Metadata Extraction**: AI-powered DOI + GPT extraction
- **Embedding Storage**: Qdrant vector DB with OpenAI embeddings
- **Error Handling**: Comprehensive try-catch blocks with fallbacks

### 1.2 Strengths to Preserve
✅ **Robust error handling** with fallback mechanisms  
✅ **Multi-modal support** (text + images + tables)  
✅ **Page tracking** for accurate source citations  
✅ **Deduplication** of chunks and images  
✅ **Production-ready** logging and monitoring  
✅ **User authentication** and ownership verification

### 1.3 Current Limitations
❌ **Single format support** - Only PDF files accepted  
❌ **Hardcoded file type checks** scattered across codebase  
❌ **Monolithic extraction** functions  
❌ **No format-specific configuration**

---

## 2. Proposed Architecture

### 2.1 Strategy Pattern for Document Processors

```python
# New file: workflow/document_processors/base_processor.py

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class ProcessedDocument:
    """Standardized output from any document processor."""
    full_text: str
    page_info: List[Dict]  # Page/section info with positions
    multimodal_content: Dict  # Images, tables, charts
    metadata: Dict  # Format-specific metadata
    file_type: str
    processing_notes: List[str]  # Warnings, info messages


class BaseDocumentProcessor(ABC):
    """Abstract base class for all document processors."""
    
    # Class attributes
    SUPPORTED_EXTENSIONS: List[str] = []
    SUPPORTED_MIME_TYPES: List[str] = []
    MAX_FILE_SIZE_MB: int = 35
    
    def __init__(self):
        self.logger = self._setup_logger()
    
    @abstractmethod
    def extract_text(self, file_path: str) -> Tuple[str, List[Dict]]:
        """Extract text with position tracking.
        
        Returns:
            Tuple[full_text, page_info]
        """
        pass
    
    @abstractmethod
    def extract_multimodal(self, file_path: str) -> Dict:
        """Extract images, tables, charts, etc.
        
        Returns:
            Dict with 'images', 'tables', 'charts', etc.
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract format-specific metadata.
        
        Returns:
            Dict with title, author, keywords, etc.
        """
        pass
    
    def process(self, file_path: str) -> ProcessedDocument:
        """Main processing pipeline - Template Method pattern.
        
        This method orchestrates the extraction process and handles
        errors uniformly across all processors.
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
        """Check if this processor can handle the file."""
        if file_extension:
            return file_extension.lower() in [ext.lower() for ext in cls.SUPPORTED_EXTENSIONS]
        if mime_type:
            return mime_type in cls.SUPPORTED_MIME_TYPES
        return False
    
    def _setup_logger(self):
        """Setup processor-specific logger."""
        import logging
        logger = logging.getLogger(self.__class__.__name__)
        return logger
```

### 2.2 Concrete Processor Implementations

#### 2.2.1 PDF Processor (Existing Logic)
```python
# workflow/document_processors/pdf_processor.py

import PyPDF2
import fitz
from .base_processor import BaseDocumentProcessor
from ..multimodal_extractor import multimodal_extractor
from ..utils import sanitize_text

class PDFProcessor(BaseDocumentProcessor):
    """Process PDF documents - maintains existing multimodal capabilities."""
    
    SUPPORTED_EXTENSIONS = ['.pdf']
    SUPPORTED_MIME_TYPES = ['application/pdf']
    
    def extract_text(self, file_path: str) -> Tuple[str, List[Dict]]:
        """Extract text using PyPDF2 (existing implementation)."""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            
            # Handle encryption
            if reader.is_encrypted:
                self.logger.warning("PDF is encrypted, attempting decryption")
                reader.decrypt('')
            
            full_text = ""
            page_info = []
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = sanitize_text(page.extract_text())
                
                start_pos = len(full_text)
                full_text += page_text + "\n"
                end_pos = len(full_text) - 1
                
                page_info.append({
                    "page_num": page_num,
                    "start_pos": start_pos,
                    "end_pos": end_pos,
                    "text": page_text,
                    "type": "page"
                })
            
            return full_text, page_info
    
    def extract_multimodal(self, file_path: str) -> Dict:
        """Extract images and tables using existing multimodal_extractor."""
        return multimodal_extractor.extract_all(file_path)
    
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract PDF metadata (existing AI citation logic moved here)."""
        from services.ai_citation_service import ai_citation_service
        
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
                'extraction_source': citation_result.get('source')
            }
        
        return {}
```

#### 2.2.2 Text File Processor
```python
# workflow/document_processors/text_processor.py

from .base_processor import BaseDocumentProcessor
from ..utils import sanitize_text
import chardet  # For encoding detection

class TextProcessor(BaseDocumentProcessor):
    """Process plain text files (.txt, .md)."""
    
    SUPPORTED_EXTENSIONS = ['.txt', '.md', '.markdown', '.rst']
    SUPPORTED_MIME_TYPES = ['text/plain', 'text/markdown']
    MAX_FILE_SIZE_MB = 50  # Allow larger text files
    
    def extract_text(self, file_path: str) -> Tuple[str, List[Dict]]:
        """Extract text with section detection."""
        # Detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            detected = chardet.detect(raw_data)
            encoding = detected['encoding'] or 'utf-8'
        
        # Read file
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            full_text = sanitize_text(f.read())
        
        # Create sections (split by double newlines or headers)
        page_info = self._create_sections(full_text)
        
        return full_text, page_info
    
    def _create_sections(self, text: str) -> List[Dict]:
        """Split text into logical sections for citation purposes."""
        import re
        
        sections = []
        current_pos = 0
        
        # Try to detect markdown headers or section breaks
        lines = text.split('\n')
        current_section = []
        section_num = 1
        
        for line in lines:
            current_section.append(line)
            
            # Detect section breaks (markdown headers, double newlines)
            if re.match(r'^#{1,6}\s', line) or line.strip() == '':
                if current_section:
                    section_text = '\n'.join(current_section)
                    start_pos = current_pos
                    end_pos = current_pos + len(section_text)
                    
                    sections.append({
                        "page_num": section_num,  # Use section number as "page"
                        "start_pos": start_pos,
                        "end_pos": end_pos,
                        "text": section_text,
                        "type": "section"
                    })
                    
                    current_pos = end_pos
                    section_num += 1
                    current_section = []
        
        # Add final section
        if current_section:
            section_text = '\n'.join(current_section)
            sections.append({
                "page_num": section_num,
                "start_pos": current_pos,
                "end_pos": current_pos + len(section_text),
                "text": section_text,
                "type": "section"
            })
        
        return sections if sections else [{
            "page_num": 1,
            "start_pos": 0,
            "end_pos": len(text),
            "text": text,
            "type": "document"
        }]
    
    def extract_multimodal(self, file_path: str) -> Dict:
        """Text files don't have multimodal content."""
        return {
            'images': [],
            'tables': [],
            'has_equations': False
        }
    
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract metadata from text file (headers, frontmatter)."""
        import os
        import yaml
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        metadata = {
            'title': os.path.basename(file_path),
            'authors': [],
            'extraction_source': 'filename'
        }
        
        # Try to extract YAML frontmatter (common in Markdown)
        if content.startswith('---'):
            try:
                end_idx = content.find('---', 3)
                if end_idx > 0:
                    frontmatter = yaml.safe_load(content[3:end_idx])
                    if isinstance(frontmatter, dict):
                        metadata.update({
                            'title': frontmatter.get('title', metadata['title']),
                            'authors': frontmatter.get('authors', []),
                            'keywords': frontmatter.get('tags', []),
                            'publication_year': frontmatter.get('date', None),
                            'extraction_source': 'frontmatter'
                        })
            except Exception as e:
                self.logger.warning(f"Failed to parse frontmatter: {e}")
        
        return metadata
```

#### 2.2.3 CSV Processor
```python
# workflow/document_processors/csv_processor.py

import pandas as pd
from .base_processor import BaseDocumentProcessor
from ..utils import sanitize_text

class CSVProcessor(BaseDocumentProcessor):
    """Process CSV files with tabular data."""
    
    SUPPORTED_EXTENSIONS = ['.csv', '.tsv']
    SUPPORTED_MIME_TYPES = ['text/csv', 'text/tab-separated-values']
    MAX_FILE_SIZE_MB = 100  # Allow larger data files
    
    def extract_text(self, file_path: str) -> Tuple[str, List[Dict]]:
        """Convert CSV to searchable text representation."""
        # Auto-detect delimiter
        with open(file_path, 'r') as f:
            first_line = f.readline()
            delimiter = ',' if ',' in first_line else '\t'
        
        # Read CSV
        df = pd.read_csv(file_path, delimiter=delimiter, encoding='utf-8', on_bad_lines='skip')
        
        # Create text representation
        text_parts = []
        
        # Add column headers
        headers = ' | '.join(df.columns)
        text_parts.append(f"Data Columns: {headers}")
        
        # Add sample rows (first 100 for context)
        for idx, row in df.head(100).iterrows():
            row_text = ' | '.join(str(val) for val in row.values)
            text_parts.append(f"Row {idx + 1}: {row_text}")
        
        # Add summary statistics
        text_parts.append(f"\nDataset Summary: {len(df)} rows, {len(df.columns)} columns")
        
        # Add column statistics for numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            text_parts.append("\nNumeric Column Statistics:")
            for col in numeric_cols:
                stats = df[col].describe()
                text_parts.append(f"{col}: mean={stats['mean']:.2f}, std={stats['std']:.2f}, min={stats['min']}, max={stats['max']}")
        
        full_text = sanitize_text('\n'.join(text_parts))
        
        # Create "pages" as row ranges (100 rows per page)
        page_info = []
        rows_per_page = 100
        for page_num, start_idx in enumerate(range(0, len(df), rows_per_page), 1):
            end_idx = min(start_idx + rows_per_page, len(df))
            page_data = df.iloc[start_idx:end_idx]
            
            page_text = '\n'.join(
                ' | '.join(str(val) for val in row.values)
                for _, row in page_data.iterrows()
            )
            
            page_info.append({
                "page_num": page_num,
                "start_pos": 0,  # Will be calculated during chunking
                "end_pos": 0,
                "text": sanitize_text(page_text),
                "type": "data_range",
                "row_range": f"{start_idx}-{end_idx}"
            })
        
        return full_text, page_info
    
    def extract_multimodal(self, file_path: str) -> Dict:
        """Extract table structure as multimodal content."""
        df = pd.read_csv(file_path, on_bad_lines='skip')
        
        return {
            'images': [],
            'tables': [{
                'page': 1,
                'table_index': 0,
                'headers': list(df.columns),
                'rows': df.head(50).values.tolist(),  # First 50 rows
                'row_count': len(df),
                'col_count': len(df.columns),
                'text_representation': f"CSV data with {len(df)} rows and {len(df.columns)} columns"
            }],
            'has_equations': False
        }
    
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract metadata from CSV (limited)."""
        import os
        df = pd.read_csv(file_path, on_bad_lines='skip')
        
        return {
            'title': os.path.basename(file_path),
            'authors': [],
            'columns': list(df.columns),
            'row_count': len(df),
            'column_count': len(df.columns),
            'data_types': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'extraction_source': 'csv_analysis'
        }
```

### 2.3 Processor Factory & Registry

```python
# workflow/document_processors/factory.py

from typing import Dict, Type, Optional
from .base_processor import BaseDocumentProcessor
from .pdf_processor import PDFProcessor
from .text_processor import TextProcessor
from .csv_processor import CSVProcessor

class ProcessorRegistry:
    """Registry for all document processors."""
    
    _processors: Dict[str, Type[BaseDocumentProcessor]] = {}
    
    @classmethod
    def register(cls, processor_class: Type[BaseDocumentProcessor]):
        """Register a processor class."""
        for ext in processor_class.SUPPORTED_EXTENSIONS:
            cls._processors[ext.lower()] = processor_class
        return processor_class
    
    @classmethod
    def get_processor(cls, file_extension: str = None, mime_type: str = None) -> Optional[Type[BaseDocumentProcessor]]:
        """Get appropriate processor for file type."""
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
        """Get list of all supported file extensions."""
        return list(cls._processors.keys())
    
    @classmethod
    def get_supported_mime_types(cls) -> List[str]:
        """Get list of all supported MIME types."""
        mime_types = set()
        for processor_class in set(cls._processors.values()):
            mime_types.update(processor_class.SUPPORTED_MIME_TYPES)
        return list(mime_types)


# Auto-register all processors
ProcessorRegistry.register(PDFProcessor)
ProcessorRegistry.register(TextProcessor)
ProcessorRegistry.register(CSVProcessor)


def process_document(file_path: str, file_extension: str = None, mime_type: str = None) -> ProcessedDocument:
    """
    Main entry point for document processing.
    
    Args:
        file_path: Path to the document file
        file_extension: File extension (e.g., '.pdf')
        mime_type: MIME type (e.g., 'application/pdf')
    
    Returns:
        ProcessedDocument with extracted content
    
    Raises:
        ValueError: If file type is not supported
        Exception: If processing fails
    """
    processor_class = ProcessorRegistry.get_processor(file_extension, mime_type)
    
    if not processor_class:
        supported = ProcessorRegistry.get_supported_extensions()
        raise ValueError(f"Unsupported file type. Supported: {', '.join(supported)}")
    
    processor = processor_class()
    return processor.process(file_path)
```

### 2.4 Updated Upload Endpoint

```python
# Update in app.py

@app.post("/upload", response_model=dict)
async def upload_paper(
    file: UploadFile = File(...), 
    title: str = None,
    current_user: AuthUser = Depends(get_current_user)
):
    """Upload and extract text/metadata from various document formats."""
    from workflow.document_processors.factory import process_document, ProcessorRegistry
    
    try:
        paper_id = str(uuid.uuid4())
        
        # Extract file extension and MIME type
        file_extension = os.path.splitext(file.filename)[1] if file.filename else None
        mime_type = file.content_type
        
        # Validate file type using registry
        if not ProcessorRegistry.get_processor(file_extension, mime_type):
            supported = ProcessorRegistry.get_supported_extensions()
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type '{file_extension}'. Supported: {', '.join(supported)}"
            )
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Process document using appropriate processor
            print(f"🚀 Processing {file_extension} file with {file.filename}")
            processed_doc = process_document(tmp_path, file_extension, mime_type)
            
            # Validate extraction
            if not processed_doc.full_text or len(processed_doc.full_text.strip()) < 10:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Could not extract meaningful text from {file_extension} file"
                )
            
            print(f"✅ Extraction complete: {len(processed_doc.full_text)} chars")
            print(f"   File type: {processed_doc.file_type}")
            print(f"   Sections/Pages: {len(processed_doc.page_info)}")
            if processed_doc.processing_notes:
                print(f"   Notes: {', '.join(processed_doc.processing_notes)}")
            
            # Extract metadata
            paper_metadata = processed_doc.metadata or {}
            
        finally:
            os.unlink(tmp_path)  # Cleanup
        
        # Determine final title
        clean_filename = os.path.splitext(file.filename)[0] if file.filename else None
        final_title = (
            title
            or clean_filename
            or paper_metadata.get("title")
            or "Untitled Document"
        )
        
        # Store in Supabase
        paper_data = {
            "id": paper_id,
            "title": final_title,
            "content_text": processed_doc.full_text,
            "page_info": json.dumps(processed_doc.page_info),
            "embedding_id": paper_id,
            "user_id": current_user.id,
            "file_size": file_size,
            "filename": file.filename,
            "file_type": file_extension.lstrip('.'),  # NEW: Store file type
            "processing_status": "uploaded",
            "created_at": datetime.now(timezone.utc).isoformat(),
            # Metadata
            "authors": paper_metadata.get("authors", []),
            "publication_year": paper_metadata.get("publication_year"),
            "doi": paper_metadata.get("doi"),
            "keywords": paper_metadata.get("keywords", []),
            "abstract": paper_metadata.get("abstract"),
            # Multimodal flags
            "has_images": len(processed_doc.multimodal_content.get("images", [])) > 0,
            "has_tables": len(processed_doc.multimodal_content.get("tables", [])) > 0,
            "has_equations": processed_doc.multimodal_content.get("has_equations", False),
        }
        
        supabase.table("papers").insert(paper_data).execute()
        
        # Store embeddings (multimodal for supported formats, text-only for others)
        paper_metadata_for_embedding = {
            "id": paper_id,
            "title": final_title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "authors": paper_metadata.get("authors", []),
            "publication_year": paper_metadata.get("publication_year"),
        }
        
        store_multimodal_embeddings(
            text=processed_doc.full_text,
            multimodal_content=processed_doc.multimodal_content,
            metadata=paper_metadata_for_embedding,
            paper_id=paper_id,
            page_info=processed_doc.page_info
        )
        
        return {
            "id": paper_id,
            "title": final_title,
            "status": "uploaded",
            "file_type": file_extension.lstrip('.'),
            "message": f"{file_extension.upper()} file uploaded successfully! You can start chatting now.",
            "metadata": paper_metadata,
            "processing_notes": processed_doc.processing_notes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
```

---

## 3. Database Schema Updates

```sql
-- Add file_type column to papers table
ALTER TABLE papers
ADD COLUMN IF NOT EXISTS file_type VARCHAR(10) DEFAULT 'pdf';

-- Create index for file type queries
CREATE INDEX IF NOT EXISTS idx_papers_file_type ON papers(file_type);

-- Add comment for documentation
COMMENT ON COLUMN papers.file_type IS 'File extension without dot (pdf, txt, csv, md, docx)';
```

---

## 4. Frontend Updates

### 4.1 Update File Validation
```javascript
// src/lib/api.js

export function validateUploadFile(file) {
    const maxSize = 50 * 1024 * 1024; // 50MB limit
    const allowedExtensions = [
        'pdf', 'txt', 'md', 'markdown', 'csv', 'tsv'
    ];
    const allowedTypes = [
        'application/pdf',
        'text/plain',
        'text/markdown',
        'text/csv',
        'text/tab-separated-values'
    ];

    if (!file) {
        throw new Error('No file selected');
    }

    // Get extension
    const extension = file.name.split('.').pop().toLowerCase();
    
    // Check extension
    if (!allowedExtensions.includes(extension)) {
        throw new Error(`File type not supported. Allowed: ${allowedExtensions.join(', ')}`);
    }

    // Check MIME type
    if (!allowedTypes.includes(file.type)) {
        console.warn(`MIME type ${file.type} not in allowlist, but extension ${extension} is valid`);
    }

    // Check size
    if (file.size > maxSize) {
        throw new Error("File size exceeds 50MB limit");
    }

    return true;
}
```

### 4.2 Update Upload UI
```jsx
// src/components/forms/UploadForm.js

const handleFileSelect = (e) => {
  const file = e.target.files?.[0];
  if (file) {
    try {
      validateUploadFile(file);
      setSelectedFile(file);
      resetUpload();
    } catch (error) {
      toast.error(error.message);
    }
  }
};

// Update accepted file types in input
<input
  type="file"
  accept=".pdf,.txt,.md,.csv"
  onChange={handleFileSelect}
/>

// Update UI text
<p className="text-sm text-gray-600">
  Supports PDF, TXT, Markdown, and CSV files (max 50MB)
</p>
```

---

## 5. Testing Strategy

### 5.1 Unit Tests
```python
# tests/test_document_processors.py

import pytest
from workflow.document_processors.factory import process_document, ProcessorRegistry

def test_pdf_processor():
    """Test PDF processing."""
    result = process_document('sample.pdf', file_extension='.pdf')
    assert result.full_text
    assert len(result.page_info) > 0
    assert result.file_type == 'PDFProcessor'

def test_text_processor():
    """Test text file processing."""
    result = process_document('sample.txt', file_extension='.txt')
    assert result.full_text
    assert len(result.page_info) > 0

def test_csv_processor():
    """Test CSV processing."""
    result = process_document('sample.csv', file_extension='.csv')
    assert result.full_text
    assert len(result.multimodal_content['tables']) > 0

def test_unsupported_format():
    """Test unsupported format rejection."""
    with pytest.raises(ValueError):
        process_document('sample.exe', file_extension='.exe')

def test_processor_registry():
    """Test processor registry."""
    assert '.pdf' in ProcessorRegistry.get_supported_extensions()
    assert '.txt' in ProcessorRegistry.get_supported_extensions()
    assert '.csv' in ProcessorRegistry.get_supported_extensions()
```

### 5.2 Integration Tests
- Test complete upload flow for each format
- Verify embedding storage for all formats
- Test chat functionality with different formats
- Verify citation tracking across formats

---

## 6. Implementation Roadmap

### Phase 1: Foundation (Week 1)
- ✅ Create base processor architecture
- ✅ Implement processor registry
- ✅ Add database schema updates
- ✅ Update validation logic

### Phase 2: Core Processors (Week 2)
- ✅ Implement PDFProcessor (refactor existing)
- ✅ Implement TextProcessor
- ✅ Implement CSVProcessor
- ✅ Add comprehensive error handling

### Phase 3: Integration (Week 3)
- Update upload endpoint
- Frontend validation updates
- Update UI components
- End-to-end testing

### Phase 4: Additional Formats (Week 4+)
- Add DOCX processor (python-docx)
- Add XLSX processor (openpyxl)
- Add JSON processor
- Add HTML processor

---

## 7. Error Handling & Monitoring

### 7.1 Error Categories
1. **Unsupported Format**: Clear user message with supported types
2. **Extraction Failure**: Fallback to basic text extraction
3. **Encoding Issues**: Auto-detection with fallback to UTF-8
4. **Corrupted Files**: Graceful error with retry suggestion
5. **Size Limits**: Pre-validation with clear limits

### 7.2 Logging Strategy
```python
# Each processor logs:
- File type and size
- Extraction duration
- Number of pages/sections extracted
- Multimodal content counts
- Any warnings or fallbacks used
- Success/failure status
```

---

## 8. Production Considerations

### 8.1 Performance
- **Caching**: Cache processed documents temporarily
- **Async Processing**: Use background tasks for large files
- **Memory Management**: Stream large files instead of loading fully
- **Batch Processing**: Support bulk uploads

### 8.2 Security
- **File Type Validation**: Both extension and content-based
- **Size Limits**: Per-format limits
- **Sanitization**: All extracted text sanitized
- **Malware Scanning**: Consider integration with antivirus APIs

### 8.3 Scalability
- **Horizontal Scaling**: Stateless processors
- **Queue-based**: Use Celery/Redis for async processing
- **CDN Storage**: S3 for original files
- **Database Sharding**: By user_id or date

---

## 9. Migration Plan

### 9.1 Backward Compatibility
- Existing PDF uploads continue working
- Old data remains accessible
- Gradual rollout to users

### 9.2 Data Migration
```sql
-- Update existing records
UPDATE papers
SET file_type = 'pdf'
WHERE file_type IS NULL;
```

### 9.3 Rollout Strategy
1. Deploy backend changes (processors)
2. Update database schema
3. Deploy frontend changes
4. Monitor error rates
5. Gradual feature flag rollout

---

## 10. Future Extensions

### Potential Formats
- **DOCX**: Microsoft Word documents (python-docx)
- **XLSX**: Excel spreadsheets (openpyxl)
- **PPTX**: PowerPoint presentations (python-pptx)
- **EPUB**: E-books (ebooklib)
- **HTML**: Web pages (BeautifulSoup)
- **JSON**: Structured data
- **XML**: Structured documents

### Advanced Features
- **Format Conversion**: Auto-convert incompatible formats
- **OCR Integration**: Extract text from images in documents
- **Audio Transcription**: Process audio/video files
- **Code Files**: Syntax-aware processing for .py, .js, etc.

---

## Conclusion

This architecture provides a **scalable**, **maintainable**, and **production-ready** solution for multi-format document support. The strategy pattern ensures:

✅ **Easy Extension**: Add new formats by creating new processor classes  
✅ **Consistent Interface**: All formats processed uniformly  
✅ **Error Resilience**: Comprehensive fallback mechanisms  
✅ **Type Safety**: Clear contracts via abstract base class  
✅ **Testing**: Isolated unit tests for each processor  
✅ **Monitoring**: Centralized logging and metrics  

The implementation maintains the high quality and reliability of the existing PDF-only system while opening the platform to a much wider range of document types.
