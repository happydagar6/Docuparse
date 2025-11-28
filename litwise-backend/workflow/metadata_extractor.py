"""
PDF Metadata Extraction Module

Extracts paper metadata from PDFs including:
- Authors and affiliations
- Publication year
- DOI
- Abstract
- Keywords
- Journal/Conference name

Uses multiple extraction strategies:
1. PDF metadata fields
2. First page text parsing with regex patterns
3. Fallback extraction with LLM if needed
"""

import re
import fitz  # PyMuPDF
from typing import Dict, List, Optional, Tuple
import os
from datetime import datetime


class MetadataExtractor:
    """Extract academic paper metadata from PDF files"""
    
    # Regex patterns for common metadata fields
    PATTERNS = {
        'doi': [
            r'doi[:\s]+([0-9]{2}\.[0-9]{4,}/[^\s]+)',
            r'(10\.\d{4,}/[^\s]+)',
            r'https?://doi\.org/([0-9.]+/[^\s]+)'
        ],
        'year': [
            r'\b(19|20)\d{2}\b',
            r'published[:\s]+.*?(\d{4})',
            r'copyright[:\s]+.*?(\d{4})'
        ],
        'email': [
            r'[\w\.-]+@[\w\.-]+\.\w+',
        ],
        'abstract': [
            r'abstract[:\s]*\n(.*?)(?=\n\s*(?:keywords|introduction|1\.|index terms))',
            r'abstract[:\s]+(.*?)(?=\n\s*\n)',
        ],
        'keywords': [
            r'keywords?[:\s]*[—\-]?\s*(.*?)(?=\n\s*\n|\n\s*(?:introduction|1\.))',
            r'index terms[:\s]*[—\-]?\s*(.*?)(?=\n\s*\n)',
        ]
    }
    
    def __init__(self):
        """Initialize metadata extractor"""
        print("✅ Metadata extractor initialized")
    
    def extract_from_pdf(self, pdf_path: str) -> Dict:
        """
        Extract metadata from PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            'authors': [],
            'publication_year': None,
            'doi': None,
            'keywords': [],
            'abstract': None,
            'journal_or_conference': None,
            'extraction_method': 'combined'
        }
        
        try:
            doc = fitz.open(pdf_path)
            
            # 1. Extract from PDF metadata
            pdf_metadata = doc.metadata
            metadata.update(self._extract_from_metadata(pdf_metadata))
            
            # 2. Extract from first few pages
            first_pages_text = self._get_first_pages_text(doc, num_pages=3)
            text_metadata = self._extract_from_text(first_pages_text)
            
            # Merge text metadata (don't overwrite if already found)
            for key, value in text_metadata.items():
                if value and not metadata.get(key):
                    metadata[key] = value
            
            # 3. Extract authors from first page
            if not metadata['authors']:
                authors = self._extract_authors_from_text(first_pages_text)
                if authors:
                    metadata['authors'] = authors
            
            doc.close()
            
            # Validate and clean metadata
            metadata = self._validate_metadata(metadata)
            
            print(f"✅ Extracted metadata: {len(metadata['authors'])} authors, year: {metadata['publication_year']}, DOI: {metadata['doi']}")
            return metadata
            
        except Exception as e:
            print(f"⚠️ Metadata extraction failed: {e}")
            return metadata
    
    def _extract_from_metadata(self, pdf_metadata: Dict) -> Dict:
        """Extract metadata from PDF metadata fields"""
        metadata = {
            'authors': [],
            'publication_year': None,
            'doi': None,
            'keywords': [],
            'abstract': None,
            'journal_or_conference': None
        }
        
        if not pdf_metadata:
            return metadata
        
        # Extract author
        author_str = pdf_metadata.get('author', '')
        if author_str:
            # Split by common delimiters
            authors = re.split(r'[;,]|\sand\s', author_str)
            metadata['authors'] = [
                {'name': author.strip(), 'affiliation': None, 'email': None}
                for author in authors if author.strip()
            ]
        
        # Extract year from creation/modification date
        for date_field in ['creationDate', 'modDate']:
            date_str = pdf_metadata.get(date_field, '')
            if date_str:
                year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
                if year_match:
                    metadata['publication_year'] = int(year_match.group())
                    break
        
        # Extract title (useful for validation)
        title = pdf_metadata.get('title', '').strip()
        if title:
            metadata['extracted_title'] = title
        
        # Extract subject/keywords
        subject = pdf_metadata.get('subject', '')
        keywords_str = pdf_metadata.get('keywords', '')
        if keywords_str:
            keywords = re.split(r'[;,]', keywords_str)
            metadata['keywords'] = [kw.strip() for kw in keywords if kw.strip()]
        elif subject:
            metadata['keywords'] = [subject.strip()]
        
        return metadata
    
    def _get_first_pages_text(self, doc, num_pages: int = 3) -> str:
        """Extract text from first N pages"""
        text_parts = []
        for page_num in range(min(num_pages, len(doc))):
            page = doc[page_num]
            text_parts.append(page.get_text())
        return '\n'.join(text_parts)
    
    def _extract_from_text(self, text: str) -> Dict:
        """Extract metadata from text using regex patterns"""
        metadata = {
            'publication_year': None,
            'doi': None,
            'keywords': [],
            'abstract': None,
            'journal_or_conference': None
        }
        
        text_lower = text.lower()
        
        # Extract DOI
        for pattern in self.PATTERNS['doi']:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                doi = match.group(1) if match.lastindex else match.group()
                metadata['doi'] = doi.strip()
                break
        
        # Extract year (prefer year near beginning)
        year_matches = re.findall(self.PATTERNS['year'][0], text[:1000])
        if year_matches:
            # Get most recent plausible year
            years = [int(y) for y in year_matches if 1950 <= int(y) <= datetime.now().year]
            if years:
                metadata['publication_year'] = max(years)
        
        # Extract abstract
        for pattern in self.PATTERNS['abstract']:
            match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Clean and limit abstract length
                abstract = re.sub(r'\s+', ' ', abstract)
                metadata['abstract'] = abstract[:1500]  # Limit to 1500 chars
                break
        
        # Extract keywords
        for pattern in self.PATTERNS['keywords']:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                keywords_str = match.group(1).strip()
                # Split by common delimiters
                keywords = re.split(r'[;,·•]', keywords_str)
                metadata['keywords'] = [
                    kw.strip() for kw in keywords 
                    if kw.strip() and len(kw.strip()) > 2
                ][:10]  # Limit to 10 keywords
                break
        
        # Extract journal/conference (look for common patterns)
        journal_patterns = [
            r'published in[:\s]+(.*?)(?=\n|,)',
            r'proceedings of[:\s]+(.*?)(?=\n|,)',
            r'journal of[:\s]+(.*?)(?=\n|,)',
            r'conference on[:\s]+(.*?)(?=\n|,)',
        ]
        for pattern in journal_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                venue = match.group(1).strip()
                metadata['journal_or_conference'] = venue[:200]  # Limit length
                break
        
        return metadata
    
    def _extract_authors_from_text(self, text: str) -> List[Dict]:
        """
        Extract author names and affiliations from first page
        Uses heuristics to find author block
        """
        authors = []
        
        # Look for author block (usually after title, before abstract)
        lines = text.split('\n')[:50]  # First 50 lines
        
        # Find potential author lines (names often have specific patterns)
        author_lines = []
        email_pattern = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
        
        # Look for lines with names (capitalized words, possibly with initials)
        name_pattern = re.compile(r'^[A-Z][a-z]+\s+([A-Z]\.?\s+)?[A-Z][a-z]+')
        
        in_author_block = False
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip if line is too long (likely not author name)
            if len(line) > 100:
                continue
            
            # Check if this looks like an author name
            if name_pattern.match(line):
                in_author_block = True
                
                # Extract email if on same or next line
                email = None
                for search_line in [line, lines[i+1] if i+1 < len(lines) else '']:
                    email_match = email_pattern.search(search_line)
                    if email_match:
                        email = email_match.group()
                        break
                
                # Look for affiliation (usually follows name)
                affiliation = None
                if i+1 < len(lines) and not name_pattern.match(lines[i+1]):
                    potential_affiliation = lines[i+1].strip()
                    if len(potential_affiliation) > 10 and len(potential_affiliation) < 150:
                        affiliation = potential_affiliation
                
                authors.append({
                    'name': line,
                    'affiliation': affiliation,
                    'email': email
                })
            
            # Stop at abstract or introduction
            if re.match(r'^\s*(abstract|introduction|1\.)', line.lower()):
                break
            
            # Stop after finding several authors
            if len(authors) >= 10:
                break
        
        return authors if authors else []
    
    def _validate_metadata(self, metadata: Dict) -> Dict:
        """Validate and clean extracted metadata"""
        
        # Validate year
        if metadata.get('publication_year'):
            year = metadata['publication_year']
            current_year = datetime.now().year
            if year < 1950 or year > current_year + 1:
                print(f"⚠️ Invalid year {year}, setting to None")
                metadata['publication_year'] = None
        
        # Clean DOI
        if metadata.get('doi'):
            doi = metadata['doi']
            # Remove common prefixes
            doi = re.sub(r'^(doi:|https?://doi\.org/)', '', doi, flags=re.IGNORECASE)
            metadata['doi'] = doi.strip()
        
        # Validate authors
        if metadata.get('authors'):
            valid_authors = []
            for author in metadata['authors']:
                if isinstance(author, dict) and author.get('name'):
                    # Clean name
                    name = author['name'].strip()
                    if len(name) > 3 and len(name) < 100:
                        valid_authors.append(author)
            metadata['authors'] = valid_authors
        
        # Clean keywords
        if metadata.get('keywords'):
            keywords = [
                kw.strip().lower() 
                for kw in metadata['keywords'] 
                if isinstance(kw, str) and 2 < len(kw.strip()) < 50
            ]
            metadata['keywords'] = list(set(keywords))[:15]  # Deduplicate and limit
        
        return metadata


# Global instance
metadata_extractor = MetadataExtractor()
