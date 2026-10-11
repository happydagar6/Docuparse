"""
Text File Processor

Processes plain text files (.txt, .md, .markdown, .rst).
Supports section detection and YAML frontmatter parsing.
"""

import os
import re
from typing import Dict, List, Tuple
from .base_processor import BaseDocumentProcessor
from ..utils import sanitize_text


# [LITWISE ARCHITECTURE]: Plain Text & Markdown Processor
# Why we do this: Plain text (.txt, .md) lacks physical page numbers and tables.
# This processor handles two critical challenges:
# 1. Encoding Detection: Using chardet to prevent crashes on non-UTF8 files (Windows-1252, ISO-8859).
# 2. Section Chunking: Using Markdown headers (#, ##) to create 'Virtual Sections' that act as pages for citations.
class TextProcessor(BaseDocumentProcessor):
    """Process plain text files (.txt, .md)."""
    
    SUPPORTED_EXTENSIONS = ['.txt', '.md', '.markdown', '.rst']
    SUPPORTED_MIME_TYPES = ['text/plain', 'text/markdown']
    MAX_FILE_SIZE_MB = 50  # Allow larger text files
    
    def extract_text(self, file_path: str) -> Tuple[str, List[Dict]]:
        """Extract text with dynamic encoding detection and section segmentation."""
        try:
            # [LITWISE RAG LOGIC]: Dynamic Encoding Detection
            # Why we do this: If you open a text file with `open(..., encoding='utf-8')` on Windows,
            # it will crash if the user uploaded an ANSI or Latin-1 file.
            # chardet reads the raw bytes and automatically detects the correct charset.
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                detected = chardet.detect(raw_data)
                encoding = detected['encoding'] or 'utf-8'
            
            self.logger.info(f"Detected encoding: {encoding}")
            
            # Read file using the detected encoding
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                full_text = sanitize_text(f.read())
            
            # Split text into logical sections based on headers
            page_info = self._create_sections(full_text)
            
            self.logger.info(
                f"Text extraction complete: {len(full_text)} chars, {len(page_info)} sections"
            )
            
            return full_text, page_info
        
        except Exception as e:
            self.logger.error(f"Text extraction failed: {e}")
            raise
    
    # [LITWISE RAG LOGIC]: Header-Based Virtual Sections
    # Why we do this: Text files don't have pages. To provide meaningful citations,
    # we detect Markdown headers (# H1, ## H2) and double newlines.
    # Each section is assigned a section number so the citation UI can cite: "Section 2: Methodology".
    def _create_sections(self, text: str) -> List[Dict]:
        """Split text into logical sections for citation purposes."""
        sections = []
        lines = text.split('\n')
        current_section = []
        section_num = 1
        current_pos = 0
        
        for line in lines:
            current_section.append(line)
            
            # Detect section breaks (markdown headers # or double blank lines)
            if re.match(r'^#{1,6}\s', line) or (line.strip() == '' and len(current_section) > 1):
                if current_section:
                    section_text = '\n'.join(current_section).strip()
                    
                    if section_text:  # Only add non-empty sections
                        start_pos = current_pos
                        end_pos = current_pos + len(section_text)
                        
                        sections.append({
                            "page_num": section_num,  # Use section number as virtual page
                            "start_pos": start_pos,
                            "end_pos": end_pos,
                            "text": section_text,
                            "type": "section"
                        })
                        
                        current_pos = end_pos + 1
                        section_num += 1
                    
                    current_section = []
        
        # Add final trailing section
        if current_section:
            section_text = '\n'.join(current_section).strip()
            if section_text:
                sections.append({
                    "page_num": section_num,
                    "start_pos": current_pos,
                    "end_pos": current_pos + len(section_text),
                    "text": section_text,
                    "type": "section"
                })
        
        # Fallback safety: If no headers were found, treat the entire document as 1 single section
        if not sections:
            sections = [{
                "page_num": 1,
                "start_pos": 0,
                "end_pos": len(text),
                "text": text,
                "type": "document"
            }]
        
        return sections
    
    # [LITWISE RAG LOGIC]: Polymorphic Multimodal Stub
    # Why we do this: Text files don't contain embedded images/tables, but to satisfy the
    # BaseDocumentProcessor interface, we return empty collections so downstream logic doesn't throw KeyErrors.
    def extract_multimodal(self, file_path: str, page_info: List[Dict] = None) -> Dict:
        """Text files don't have multimodal content."""
        return {
            'images': [],
            'tables': [],
            'has_equations': False
        }
    
    # [LITWISE RAG LOGIC]: Frontmatter and Header Metadata Extraction
    # Why we do this: Documentation and notes often contain YAML headers (e.g., Jekyll, Obsidian, Hugo)
    # like `--- title: Research Notes, tags: [AI, ML] ---`.
    # We parse this frontmatter to populate author, title, and tags automatically.
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract metadata from YAML frontmatter or Markdown H1 headers."""
        import yaml
        
        metadata = {
            'title': os.path.basename(file_path),
            'authors': [],
            'extraction_source': 'filename'
        }
        
        try:
            # Detect encoding
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                detected = chardet.detect(raw_data)
                encoding = detected['encoding'] or 'utf-8'
            
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            
            # 1. Parse YAML frontmatter if present (between --- markers)
            if content.startswith('---'):
                try:
                    end_idx = content.find('---', 3)
                    if end_idx > 0:
                        frontmatter_text = content[3:end_idx]
                        frontmatter = yaml.safe_load(frontmatter_text)
                        
                        if isinstance(frontmatter, dict):
                            metadata.update({
                                'title': frontmatter.get('title', metadata['title']),
                                'authors': frontmatter.get('authors', []),
                                'keywords': frontmatter.get('tags', []),
                                'publication_year': frontmatter.get('date', None),
                                'extraction_source': 'frontmatter'
                            })
                            
                            self.logger.info("Successfully extracted YAML frontmatter")
                except Exception as e:
                    self.logger.warning(f"Failed to parse frontmatter: {e}")
            
            # 2. If no frontmatter title, extract the first Markdown # H1 header as title
            if metadata['extraction_source'] == 'filename':
                match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                if match:
                    metadata['title'] = match.group(1).strip()
                    metadata['extraction_source'] = 'header'
        
        except Exception as e:
            self.logger.warning(f"Metadata extraction failed: {e}")
        
        return metadata
