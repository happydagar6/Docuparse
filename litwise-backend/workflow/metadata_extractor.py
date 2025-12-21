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
            
            # CRITICAL: Extract from Page 1 ONLY for primary metadata (title, authors, journal, DOI, year)
            # This prevents contamination from the References/Bibliography section
            first_page_text = self._get_first_page_text(doc)
            
            # 1. Extract from PDF metadata fields
            pdf_metadata = doc.metadata
            metadata.update(self._extract_from_metadata(pdf_metadata))
            
            # 2. Extract PRIMARY metadata from Page 1 ONLY (title, authors, journal, DOI, year)
            page1_metadata = self._extract_primary_metadata_from_page1(first_page_text)
            
            # Merge Page 1 metadata (prioritize over PDF metadata for accuracy)
            for key in ['publication_year', 'doi', 'journal_or_conference']:
                if page1_metadata.get(key) and not metadata.get(key):
                    metadata[key] = page1_metadata[key]
            
            # 3. Extract authors from Page 1 ONLY
            if not metadata['authors']:
                authors = self._extract_authors_from_page1(first_page_text)
                if authors:
                    metadata['authors'] = authors
            
            # 4. Extract title from Page 1 (largest bold text)
            if not metadata.get('extracted_title'):
                title = self._extract_title_from_page1(first_page_text)
                if title:
                    metadata['extracted_title'] = title
            
            # 5. Extract abstract and keywords from first 2 pages (safe, won't reach bibliography)
            first_two_pages = self._get_first_pages_text(doc, num_pages=2)
            abstract_keywords = self._extract_abstract_keywords(first_two_pages)
            if not metadata.get('abstract'):
                metadata['abstract'] = abstract_keywords.get('abstract')
            if not metadata.get('keywords'):
                metadata['keywords'] = abstract_keywords.get('keywords', [])
            
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
    
    def _get_first_page_text(self, doc) -> str:
        """Extract text from ONLY the first page (for title, authors, journal, DOI)"""
        from workflow.utils import sanitize_text
        
        if len(doc) == 0:
            return ""
        
        page = doc[0]
        page_text = page.get_text()
        # Sanitize to remove null bytes and control characters
        return sanitize_text(page_text)
    
    def _get_first_pages_text(self, doc, num_pages: int = 3) -> str:
        """Extract text from first N pages (for abstract/keywords only)"""
        from workflow.utils import sanitize_text
        
        text_parts = []
        for page_num in range(min(num_pages, len(doc))):
            page = doc[page_num]
            page_text = page.get_text()
            # Sanitize to remove null bytes and control characters
            text_parts.append(sanitize_text(page_text))
        return '\n'.join(text_parts)
    
    def _extract_primary_metadata_from_page1(self, page1_text: str) -> Dict:
        """Extract PRIMARY metadata from Page 1 ONLY (DOI, year, journal) - NO bibliography contamination"""
        metadata = {
            'publication_year': None,
            'doi': None,
            'journal_or_conference': None
        }
        
        # CRITICAL: Only analyze first 2000 characters of Page 1 (before references could start)
        text_safe = page1_text[:2000]
        text_lower = text_safe.lower()
        
        # Extract DOI (very reliable on Page 1)
        for pattern in self.PATTERNS['doi']:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                doi = match.group(1) if match.lastindex else match.group()
                metadata['doi'] = doi.strip()
                break
        
        # Extract year from Page 1 header/footer (NOT from middle of page where refs might be)
        # Look for year near DOI or in parentheses (common in academic papers)
        year_found = None
        
        # Strategy 1: Look for year near DOI
        if metadata.get('doi'):
            doi_index = text_safe.find(metadata['doi'])
            if doi_index > 0:
                # Search 200 chars before and after DOI for year
                doi_context = text_safe[max(0, doi_index-200):min(len(text_safe), doi_index+200)]
                year_matches = re.findall(r'\b(19|20)\d{2}\b', doi_context)
                if year_matches:
                    years = [int(y) for y in year_matches if 1950 <= int(y) <= datetime.now().year]
                    if years:
                        year_found = min(years)  # Use oldest year near DOI (publication year)
        
        # Strategy 2: Look for year in first 600 chars (header area)
        if not year_found:
            header_text = text_safe[:600]
            # Look for year in parentheses or after common keywords
            year_patterns = [
                r'\((\d{4})\)',  # (2021)
                r'published.*?(\d{4})',
                r'copyright.*?(\d{4})',
                r'\b(\d{4})\b'  # Any 4-digit year
            ]
            for pattern in year_patterns:
                matches = re.findall(pattern, header_text, re.IGNORECASE)
                if matches:
                    years = [int(y) for y in matches if 1950 <= int(y) <= datetime.now().year]
                    if years:
                        # Prefer years that are NOT the current year (avoid headers with current date)
                        non_current = [y for y in years if y != datetime.now().year]
                        year_found = min(non_current) if non_current else min(years)
                        break
        
        if year_found:
            metadata['publication_year'] = year_found
        
        # Extract journal/conference name from Page 1 header
        journal_patterns = [
            r'published in[:\s]+([^\n,]+)',
            r'proceedings of[:\s]+([^\n,]+)',
            r'journal of[:\s]+([^\n,]+)',
            r'conference on[:\s]+([^\n,]+)',
            # Header patterns (first 300 chars)
        ]
        
        header_text = text_safe[:400]  # Journal name typically in header
        for pattern in journal_patterns:
            match = re.search(pattern, header_text, re.IGNORECASE)
            if match:
                venue = match.group(1).strip()
                # Validate: should be capitalized, reasonable length
                if len(venue) > 5 and len(venue) < 150 and venue[0].isupper():
                    metadata['journal_or_conference'] = venue[:200]
                    break
        
        return metadata
    
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
    
    def _extract_title_from_page1(self, page1_text: str) -> Optional[str]:
        """
        Extract article title from Page 1 using academic paper formatting patterns
        
        Titles in academic papers are typically:
        1. Positioned after header/journal info (lines 3-8)
        2. Often spanning multiple lines with larger/distinctive formatting
        3. Between journal/author section and abstract
        4. NOT the topic/section heading
        
        KEY INSIGHT: The TITLE is almost always:
        - The first substantive text block after header/author info
        - Much longer than section headings (usually 80-300 chars)
        - Appears BEFORE any affiliations or emails
        """
        # Analyze first 1000 chars to find title
        text_chunk = page1_text[:1000]
        lines = text_chunk.split('\n')
        
        # Keywords that indicate WRONG content (not the title)
        section_keywords = [
            'abstract', 'keywords', 'introduction', 'methods', 'results', 'discussion',
            'conclusion', 'conclusions', 'references', 'acknowledgment', 'acknowledgments',
            'funding', 'conflict', 'author contributions', 'data availability',
        ]
        
        # Keywords that suggest metadata (affiliations, contact)
        metadata_keywords = [
            'department', 'university', 'institute', 'college', 'school',
            'email', 'corresponding author', 'author notes', 'received',
            'accepted', 'published', 'online', 'doi:', 'volume', 'issue',
            'pages', 'copyright', 'all rights reserved'
        ]
        
        print(f"📄 Starting title extraction from {len(lines)} lines")
        
        candidate_blocks = []
        skip_until_empty = False
        
        # Parse through the page looking for title candidate blocks
        i = 2  # Skip first 2 lines (usually header)
        while i < min(20, len(lines)):
            line = lines[i].strip()
            i += 1
            
            # Skip empty lines
            if not line or len(line) < 10:
                skip_until_empty = False
                continue
            
            # Skip if it's a metadata line
            if any(kw in line.lower() for kw in metadata_keywords):
                continue
            
            # Skip if it's a section keyword
            if any(kw in line.lower() for kw in section_keywords):
                skip_until_empty = True
                continue
            
            # Skip if it's all caps (usually headers/journal names)
            if line.isupper() and len(line) > 5:
                continue
            
            # Skip if it looks like a numbered list or citation
            if re.match(r'^\d+\.|^\[\d+\]', line):
                continue
            
            # Skip URLs, emails, DOIs
            if any(p in line.lower() for p in ['http', '@', 'doi.org', 'doi:']):
                continue
            
            # Skip lines with excessive punctuation
            if line.count('|') > 1:
                continue
            
            # Title characteristics:
            # - Multiple words (4+ for academic titles)
            # - Medium to long length (60-350 chars)
            # - Doesn't look like metadata
            
            words = line.split()
            if len(words) < 4:
                continue
            
            if not (60 <= len(line) <= 350):
                continue
            
            # Check word lengths (should be reasonable words, not random characters)
            avg_word_len = sum(len(w) for w in words) / len(words)
            if avg_word_len < 3 or avg_word_len > 15:
                continue
            
            # This looks promising! Add to candidates
            candidate_blocks.append({
                'text': line,
                'line_num': i - 1,
                'length': len(line),
                'word_count': len(words)
            })
            
            # Typical pattern: title appears once, so stop after first good candidate
            if len(candidate_blocks) >= 1:
                break
        
        # If we found candidates, pick the best one
        if candidate_blocks:
            # Prefer longer titles (more characteristic of academic papers)
            best = max(candidate_blocks, key=lambda x: x['length'])
            title = best['text']
            print(f"✅ Title (line {best['line_num']}): {title[:80]}...")
            return title
        
        # Fallback: Look for multi-line title (combined from consecutive lines)
        if len(lines) > 5:
            potential_title_lines = []
            for i in range(2, min(15, len(lines))):
                line = lines[i].strip()
                if (line and 
                    not any(kw in line.lower() for kw in section_keywords + metadata_keywords) and
                    not line.isupper() and
                    len(line) > 20 and len(line) < 200 and
                    not any(p in line.lower() for p in ['http', '@', 'doi:'])):
                    potential_title_lines.append(line)
                    if len(' '.join(potential_title_lines)) > 80:
                        break
            
            if potential_title_lines and len(' '.join(potential_title_lines)) >= 60:
                title = ' '.join(potential_title_lines)
                print(f"✅ Reconstructed title: {title[:80]}...")
                return title
        
        print("⚠️  No title found on Page 1")
        return None
    
    def _extract_abstract_keywords(self, text: str) -> Dict:
        """Extract ONLY abstract and keywords (safe from first 2 pages)"""
        result = {'abstract': None, 'keywords': []}
        
        text_lower = text.lower()
        
        # Extract abstract
        for pattern in self.PATTERNS['abstract']:
            match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Clean and limit abstract length
                abstract = re.sub(r'\s+', ' ', abstract)
                result['abstract'] = abstract[:1500]
                break
        
        # Extract keywords
        for pattern in self.PATTERNS['keywords']:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                keywords_str = match.group(1).strip()
                # Split by common delimiters
                keywords = re.split(r'[;,·•]', keywords_str)
                result['keywords'] = [
                    kw.strip() for kw in keywords 
                    if kw.strip() and len(kw.strip()) > 2
                ][:10]
                break
        
        return result
    
    def _extract_authors_from_page1(self, page1_text: str) -> List[Dict]:
        """Extract authors from Page 1 ONLY - avoiding bibliography contamination"""
        # ONLY analyze first 1500 characters (before any references could start)
        return self._extract_authors_from_text(page1_text[:1500])
    
    def _extract_authors_from_text(self, text: str) -> List[Dict]:
        """
        Extract author names from first page using multiple strategies
        Handles common academic formats:
        - van Agteren, J., Iasiello, M., Lo, L., & Kyrios, M.
        - John van Agteren1, Mary Iasiello2
        - J. van Agteren, M. Iasiello
        
        CRITICAL: Remove superscript numbers like "1,2" or "1" after names
        """
        authors = []
        lines = text.split('\n')
        
        print(f"🔍 Searching for authors in {len(lines)} lines of text")
        
        # Strategy 1: Look for comma-separated author list (most common in academic papers)
        # This is the PRIMARY pattern used in most academic journals
        # Pattern matches: "LastName, Initial., LastName, Initial." with optional &
        
        # Search in first 25 lines for author block (before abstract/keywords)
        for i, line in enumerate(lines[:25]):
            line_clean = line.strip()
            
            # Skip very short or very long lines
            if len(line_clean) < 15 or len(line_clean) > 500:
                continue
            
            # Skip lines that are clearly not authors
            skip_keywords = ['abstract', 'introduction', 'keywords', 'published', 
                           'received', 'doi', 'volume', 'copyright', 'article', 'http',
                           'department', 'university', 'institute', 'affiliation']
            if any(kw in line_clean.lower() for kw in skip_keywords):
                continue
            
            # Check if this line contains multiple commas (author lists have many commas)
            if line_clean.count(',') < 2:
                continue
            
            # Look for academic author pattern: "LastName, Initial., LastName, Initial."
            # This detects lines with multiple author entries separated by commas and ampersands
            if re.search(r'[A-Z][a-z\-]+\s*,\s*[A-Z]\.', line_clean):
                # This looks like an author line! Try to parse it
                print(f"📝 Found potential author line (line {i+1}): {line_clean[:80]}...")
                authors = self._parse_comma_separated_authors(line_clean)
                if len(authors) >= 2:  # Found valid author list with multiple authors
                    print(f"✅ Found {len(authors)} authors in comma-separated format")
                    return authors
        
        # Strategy 2: Look for author blocks spanning multiple lines
        # Some papers have authors on consecutive lines
        for i, line in enumerate(lines[:20]):
            line_clean = line.strip()
            
            # Check if line starts with author name pattern (Last, First or Last, Initial)
            if re.match(r'^[A-Z][a-z\-]+\s*,\s*[A-Z]\.?', line_clean):
                # Collect consecutive author lines
                author_block = []
                j = i
                while j < min(i + 15, len(lines)):
                    current_line = lines[j].strip()
                    
                    # Stop if we hit keywords
                    if any(kw in current_line.lower() for kw in ['abstract', 'keywords', 'introduction']):
                        break
                    
                    # If line matches author pattern or is connector, keep it
                    if current_line and (re.match(r'^[A-Z][a-z\-]+\s*,\s*[A-Z]\.?', current_line) or 
                                        current_line in ['&', 'and']):
                        author_block.append(current_line)
                    elif author_block and current_line:
                        # Non-author line after starting author block
                        # But check if it could be email or affiliation
                        if not any(p in current_line.lower() for p in ['@', 'email', 'institute', 'university']):
                            break
                    
                    j += 1
                
                if len(author_block) >= 2:
                    combined = ' '.join(author_block)
                    authors = self._parse_comma_separated_authors(combined)
                    if len(authors) >= 2:
                        print(f"✅ Found {len(authors)} authors in multi-line format")
                        return authors
        
        # Strategy 3: Look for author line with "and" or "&" separator
        # Some papers use "Author1 and Author2 and Author3" format
        for i, line in enumerate(lines[:20]):
            line_clean = line.strip()
            
            # Check for "and" or "&" separators with capital letters
            if ((' and ' in line_clean or ' & ' in line_clean) and
                line_clean.count(',') >= 1 and
                re.search(r'[A-Z][a-z\-]+\s*,\s*[A-Z]', line_clean)):
                
                print(f"📝 Found author line with separators (line {i+1}): {line_clean[:80]}...")
                authors = self._parse_comma_separated_authors(line_clean)
                if len(authors) >= 2:
                    print(f"✅ Found {len(authors)} authors with 'and'/'&' separators")
                    return authors
        
        # Strategy 4: Fallback - look for individual author lines
        # Pattern: "John Smith" or "J. Smith"
        collected_authors = []
        for i, line in enumerate(lines[:25]):
            line = line.strip()
            
            # Skip short lines or lines with keywords
            if len(line) < 5 or len(line) > 60:
                continue
            
            if any(kw in line.lower() for kw in ['abstract', 'university', 'department', 'email', '@']):
                continue
            
            # Simple author name pattern (2-3 words, starts with capital)
            if (re.match(r'^[A-Z][a-z\-]+(\s+[a-z]+)?\s+[A-Z][a-z\-]+', line) and
                not line[0].islower()):
                collected_authors.append({
                    'name': line,
                    'affiliation': None,
                    'email': None
                })
            
            if len(collected_authors) >= 2 or 'abstract' in line.lower():
                break
        
        if collected_authors:
            print(f"✅ Found {len(collected_authors)} authors (fallback format)")
            return collected_authors
        
        # No authors found
        print("⚠️  No authors found with current patterns")
        return []
    
    def _parse_comma_separated_authors(self, author_text: str) -> List[Dict]:
        """
        Parse comma-separated author list with superscript number removal
        Input: "van Agteren, J.1,2, Iasiello, M.1, Lo, L.3, & Kyrios, M.1"
        Output: [{"name": "van Agteren, J.", ...}, {"name": "Iasiello, M.", ...}, ...]
        
        Key features:
        - Removes superscript numbers (1,2 or 1)
        - Handles "LastName, Initial" format
        - Handles "&" and "and" connectors
        """
        authors = []
        
        # CRITICAL: Remove superscript/affiliation numbers first
        # Pattern 1: Numbers in superscript like "J.1,2" or "J.1" or "M.²"
        author_text = re.sub(r'(\.)[\s,]*\d+[,\s]*', r'\1', author_text)  # J.1 -> J.
        author_text = re.sub(r'(\.)[\s,]*[,\s]+(\d+[,\s]*)+', r'\1', author_text)  # J.1,2 -> J.
        
        # Pattern 2: Superscript unicode characters (², ³, etc.)
        author_text = re.sub(r'[⁰¹²³⁴⁵⁶⁷⁸⁹]+', '', author_text)
        
        # Remove extra whitespace
        author_text = re.sub(r'\s+', ' ', author_text).strip()
        
        print(f"📝 Cleaned author text: {author_text[:100]}...")
        
        # Split by ", &" or ", and" or just ","
        # We need to handle: "LastName, Initial., LastName, Initial., & LastName, Initial."
        
        # First, split by "&" if present
        if ' & ' in author_text:
            parts = author_text.split(' & ')
            author_parts = []
            # Last part after &
            last_parts = parts[-1].split(',')
            author_parts.extend(last_parts[:-1])  # All but last
            # Parts before &
            for part in parts[:-1]:
                author_parts.extend(part.split(','))
            author_parts.append(last_parts[-1])  # Last part
        else:
            author_parts = author_text.split(',')
        
        # Clean up and pair "LastName" with "Initial"
        current_last = None
        for i, part in enumerate(author_parts):
            part = part.strip()
            if not part or part in ['and']:
                continue
            
            # Check if this part looks like "LastName Initial" or just "Initial"
            if re.match(r'^[A-Z][a-z\-]+$', part):
                # This is a last name
                current_last = part
            elif re.match(r'^[A-Z]\.?$', part) and current_last:
                # This is an initial, combine with last name
                full_name = f"{current_last}, {part}"
                authors.append({
                    'name': full_name,
                    'affiliation': None,
                    'email': None
                })
                current_last = None
            elif ', ' in part:
                # Already formatted "LastName, Initial"
                authors.append({
                    'name': part,
                    'affiliation': None,
                    'email': None
                })
                current_last = None
            elif part and len(part) > 2:
                # Single author name (not split)
                authors.append({
                    'name': part,
                    'affiliation': None,
                    'email': None
                })
                current_last = None
        
        print(f"✅ Parsed {len(authors)} authors from text")
        return authors[:15]  # Limit to 15 authors
    
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
