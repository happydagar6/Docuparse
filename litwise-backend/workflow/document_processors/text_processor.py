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


class TextProcessor(BaseDocumentProcessor):
    """Process plain text files (.txt, .md)."""
    
    SUPPORTED_EXTENSIONS = ['.txt', '.md', '.markdown', '.rst']
    SUPPORTED_MIME_TYPES = ['text/plain', 'text/markdown']
    MAX_FILE_SIZE_MB = 50  # Allow larger text files
    
    def extract_text(self, file_path: str) -> Tuple[str, List[Dict]]:
        """Extract text with section detection.
        
        Args:
            file_path: Path to text file
        
        Returns:
            Tuple of (full_text, section_info)
        
        Raises:
            Exception: If file cannot be read
        """
        try:
            # Detect encoding
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                detected = chardet.detect(raw_data)
                encoding = detected['encoding'] or 'utf-8'
            
            self.logger.info(f"Detected encoding: {encoding}")
            
            # Read file
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                full_text = sanitize_text(f.read())
            
            # Create sections (split by double newlines or headers)
            page_info = self._create_sections(full_text)
            
            self.logger.info(
                f"Text extraction complete: {len(full_text)} chars, {len(page_info)} sections"
            )
            
            return full_text, page_info
        
        except Exception as e:
            self.logger.error(f"Text extraction failed: {e}")
            raise
    
    def _create_sections(self, text: str) -> List[Dict]:
        """Split text into logical sections for citation purposes.
        
        Args:
            text: Full document text
        
        Returns:
            List of section dicts with page_num, start_pos, end_pos, text, type
        """
        sections = []
        lines = text.split('\n')
        current_section = []
        section_num = 1
        current_pos = 0
        
        for line in lines:
            current_section.append(line)
            
            # Detect section breaks (markdown headers, double newlines)
            if re.match(r'^#{1,6}\s', line) or (line.strip() == '' and len(current_section) > 1):
                if current_section:
                    section_text = '\n'.join(current_section).strip()
                    
                    if section_text:  # Only add non-empty sections
                        start_pos = current_pos
                        end_pos = current_pos + len(section_text)
                        
                        sections.append({
                            "page_num": section_num,  # Use section number as "page"
                            "start_pos": start_pos,
                            "end_pos": end_pos,
                            "text": section_text,
                            "type": "section"
                        })
                        
                        current_pos = end_pos + 1  # +1 for newline
                        section_num += 1
                    
                    current_section = []
        
        # Add final section
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
        
        # If no sections detected, treat entire document as one section
        if not sections:
            sections = [{
                "page_num": 1,
                "start_pos": 0,
                "end_pos": len(text),
                "text": text,
                "type": "document"
            }]
        
        return sections
    
    def extract_multimodal(self, file_path: str) -> Dict:
        """Text files don't have multimodal content.
        
        Args:
            file_path: Path to text file
        
        Returns:
            Dict with empty images/tables lists
        """
        return {
            'images': [],
            'tables': [],
            'has_equations': False
        }
    
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract metadata from text file (headers, frontmatter).
        
        Args:
            file_path: Path to text file
        
        Returns:
            Dict with title, authors, keywords, etc.
        
        Raises:
            Exception: If metadata extraction fails
        """
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
            
            # Try to extract YAML frontmatter (common in Markdown)
            if content.startswith('---'):
                try:
                    end_idx = content.find('---', 3)
                    if end_idx > 0:
                        frontmatter_text = content[3:end_idx]
                        frontmatter = yaml.safe_load(frontmatter_text)
                        
                        if isinstance(frontmatter, dict):
                            # Update metadata with frontmatter
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
            
            # Try to extract first header as title (if no frontmatter)
            if metadata['extraction_source'] == 'filename':
                # Look for markdown H1 header
                match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                if match:
                    metadata['title'] = match.group(1).strip()
                    metadata['extraction_source'] = 'header'
        
        except Exception as e:
            self.logger.warning(f"Metadata extraction failed: {e}")
        
        return metadata
