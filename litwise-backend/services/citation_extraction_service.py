import re
from typing import List, Dict, Optional, Tuple, Any
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)

class CitationExtractionService:
    """Extract and parse citations from research papers using advanced regex patterns"""
    
    def __init__(self):
        # Patterns for in-text citations
        self.in_text_patterns = [
            r'\[(\d+(?:,\s*\d+)*)\]',  # [1], [1,2,3]
            r'\(([A-Z][a-z]+(?:\s+et\s+al\.?)?\s+\d{4}[a-z]?)\)',  # (Smith 2020), (Smith et al. 2020)
            r'([A-Z][a-z]+(?:\s+et\s+al\.?)?\s+\(\d{4}[a-z]?\))',  # Smith (2020), Smith et al. (2020)
        ]
    
    def extract_bibliography_section(self, full_text: str) -> Optional[str]:
        """Extract bibliography/references section from paper text"""
        text_lower = full_text.lower()
        
        # Common bibliography section headers
        bib_headers = [
            r'\n\s*references\s*\n',
            r'\n\s*bibliography\s*\n',
            r'\n\s*works cited\s*\n',
            r'\n\s*literature cited\s*\n',
        ]
        
        for pattern in bib_headers:
            match = re.search(pattern, text_lower)
            if match:
                # Extract from header to end of document
                bib_start = match.end()
                bib_text = full_text[bib_start:]
                
                # Try to find end of bibliography (appendix, acknowledgments, etc.)
                end_patterns = [
                    r'\n\s*appendix\s*\n',
                    r'\n\s*acknowledgments?\s*\n',
                    r'\n\s*supplementary materials?\s*\n',
                ]
                
                for end_pattern in end_patterns:
                    end_match = re.search(end_pattern, bib_text.lower())
                    if end_match:
                        bib_text = bib_text[:end_match.start()]
                        break
                
                return bib_text.strip()
        
        return None
    
    def parse_bibliography_entries(self, bib_text: str) -> List[Dict]:
        """Parse bibliography into individual citation entries"""
        if not bib_text:
            return []
        
        citations = []
        
        # Split by common patterns (numbered, line breaks)
        # Pattern 1: [1] Author (Year) ...
        numbered_pattern = r'\[(\d+)\]\s*(.+?)(?=\n\[\d+\]|\Z)'
        numbered_matches = re.findall(numbered_pattern, bib_text, re.DOTALL)
        
        if numbered_matches:
            for num, text in numbered_matches:
                citations.append({
                    'ref_number': num,
                    'raw_text': text.strip(),
                    'in_text_refs': [f'[{num}]']
                })
        else:
            # Pattern 2: Split by double newlines or numbered lines
            entries = re.split(r'\n\s*\n+|\n\d+\.\s+', bib_text)
            entries = [e.strip() for e in entries if e.strip() and len(e.strip()) > 50]
            
            for idx, entry in enumerate(entries, 1):
                citations.append({
                    'ref_number': str(idx),
                    'raw_text': entry,
                    'in_text_refs': []
                })
        
        return citations
    
    def extract_metadata_from_citation(self, citation_text: str) -> Dict:
        """Extract structured metadata from citation text using enhanced regex patterns"""
        metadata: Dict[str, Any] = {
            'title': None,
            'authors': [],
            'year': None,
            'doi': None,
            'venue': None,
            'citation_type': 'reference',  # Default type
            'relevance_summary': None
        }
        
        # Extract DOI
        doi_match = re.search(r'(?:doi[:\s]+|https?://doi\.org/)(10\.\d{4,}/[^\s,]+)', citation_text, re.IGNORECASE)
        if doi_match:
            metadata['doi'] = doi_match.group(1)
        
        # Extract year with improved patterns
        year_patterns = [
            r'\((\d{4})\)',           # (2020)
            r',\s*(\d{4})[,.]',       # , 2020,
            r'\s(\d{4})\.',           #  2020.
            r'\s(\d{4})\s',           #  2020 
        ]
        for pattern in year_patterns:
            year_match = re.search(pattern, citation_text)
            if year_match:
                year = int(year_match.group(1))
                if 1900 <= year <= 2030:  # Validate year range
                    metadata['year'] = year
                    break
        
        # Extract title with improved patterns
        # Try quoted text first
        title_match = re.search(r'["""](.+?)["""]', citation_text)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
        else:
            # Try finding text between year and venue markers
            # Pattern: (Year) Title. Journal/Conference
            title_fallback = re.search(r'\(\d{4}\)\s*([^.]+)\.', citation_text)
            if title_fallback:
                metadata['title'] = title_fallback.group(1).strip()
            else:
                # Last resort: text between authors and year
                title_last = re.search(r'[A-Z][a-z]+,?\s+[A-Z]\.\s+(.+?)\s+\(\d{4}\)', citation_text)
                if title_last:
                    metadata['title'] = title_last.group(1).strip()
        
        # Extract authors with improved parsing
        # Pattern 1: LastName, F., LastName, F., ... (Year)
        author_pattern = r'^(.+?)\s*\(\d{4}\)'
        author_match = re.search(author_pattern, citation_text)
        if author_match:
            author_text = author_match.group(1)
            # Remove common prefixes
            author_text = re.sub(r'^\d+\.\s*', '', author_text)  # Remove numbering
            author_text = re.sub(r'^\[\d+\]\s*', '', author_text)  # Remove [1]
            
            # Split by "and" or commas
            authors = re.split(r',\s*(?:and\s+)?|and\s+|\s+&\s+', author_text)
            metadata['authors'] = [self._clean_author_name(a) for a in authors if a.strip()][:10]  # Limit to 10
        
        # Extract venue (journal/conference)
        # Look for text after title and year
        venue_patterns = [
            r'\.\s*([A-Z][^.]+?),\s*\d+',  # . Journal Name, Volume
            r'\.\s*In\s+([^,]+)',          # . In Conference Name
            r'\.\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+\d{4}',  # . Journal 2020
        ]
        for pattern in venue_patterns:
            venue_match = re.search(pattern, citation_text)
            if venue_match:
                venue = venue_match.group(1).strip()
                # Clean up venue name
                venue = re.sub(r'\s+vol\.?\s+\d+', '', venue, flags=re.IGNORECASE)
                metadata['venue'] = venue[:200]  # Truncate
                break
        
        # Determine citation type based on keywords
        metadata['citation_type'] = self._classify_citation_type(citation_text)
        
        return metadata
    
    def _clean_author_name(self, name: str) -> str:
        """Clean and standardize author names"""
        name = name.strip()
        # Remove extra whitespace
        name = re.sub(r'\s+', ' ', name)
        # Remove trailing periods and commas
        name = name.rstrip('.,')
        return name
    
    def _classify_citation_type(self, citation_text: str) -> str:
        """Classify citation type based on common patterns"""
        text_lower = citation_text.lower()
        
        # Keywords for different citation types
        if any(kw in text_lower for kw in ['dataset', 'data', 'benchmark', 'corpus']):
            return 'data'
        elif any(kw in text_lower for kw in ['method', 'algorithm', 'approach', 'technique']):
            return 'method'
        elif any(kw in text_lower for kw in ['comparison', 'survey', 'review', 'analysis']):
            return 'comparison'
        elif any(kw in text_lower for kw in ['background', 'introduction', 'overview']):
            return 'background'
        else:
            return 'reference'

    def find_in_text_citations(self, full_text: str, citation_entries: List[Dict]) -> Dict[str, List[str]]:
        """Find where each citation appears in the main text"""
        citation_contexts = {}
        
        for citation in citation_entries:
            ref_num = citation.get('ref_number', '')
            contexts = []
            
            # Find all occurrences of [ref_num] in text
            for pattern in self.in_text_patterns:
                matches = re.finditer(pattern, full_text)
                for match in matches:
                    if ref_num in match.group(0):
                        # Extract surrounding context (150 chars before/after for better context)
                        start = max(0, match.start() - 150)
                        end = min(len(full_text), match.end() + 150)
                        context = full_text[start:end].strip()
                        contexts.append(context)
            
            # Increased limit from 3 to 10 to capture more citation contexts
            # Users can now see up to 10 places where citation appears in paper
            citation_contexts[ref_num] = contexts[:10]
        
        return citation_contexts
    
    async def calculate_importance_score(self, citation: Dict, contexts: List[str]) -> float:
        """Calculate importance score based on mention frequency and context"""
        base_score = min(len(contexts) / 10.0, 1.0)  # Normalize by 10 mentions
        
        # Boost score if cited in abstract or introduction
        for context in contexts:
            if any(keyword in context.lower() for keyword in ['abstract', 'introduction', 'key', 'important', 'significant']):
                base_score = min(base_score * 1.5, 1.0)
                break
        
        return round(base_score, 2)
    
    def detect_duplicate_citations(self, citations: List[Dict], similarity_threshold: float = 0.85) -> List[Tuple[int, int]]:
        """Detect duplicate or near-duplicate citations using text similarity
        
        Returns list of (index1, index2) tuples indicating duplicate pairs
        """
        duplicates = []
        
        for i in range(len(citations)):
            for j in range(i + 1, len(citations)):
                text1 = citations[i].get('raw_text', '').lower()
                text2 = citations[j].get('raw_text', '').lower()
                
                # Calculate similarity ratio
                similarity = SequenceMatcher(None, text1, text2).ratio()
                
                if similarity >= similarity_threshold:
                    duplicates.append((i, j, similarity))
                    logger.info(f"Detected duplicate citations: #{i} and #{j} ({similarity:.1%} match)")
        
        return duplicates
    
    def merge_duplicate_citations(self, citations: List[Dict], duplicates: List[Tuple[int, int, float]]) -> List[Dict]:
        """Merge duplicate citations, keeping the more complete version"""
        # Sort duplicates to process in reverse order (prevents index shifting)
        for dup_i, dup_j, similarity in sorted(duplicates, reverse=True, key=lambda x: x[0]):
            cit_i = citations[dup_i]
            cit_j = citations[dup_j]
            
            # Keep citation with more metadata
            metadata_count_i = sum(1 for v in cit_i.values() if v and v != [])
            metadata_count_j = sum(1 for v in cit_j.values() if v and v != [])
            
            if metadata_count_i >= metadata_count_j:
                # Keep cit_i, merge in_text_refs from cit_j
                if 'in_text_refs' in cit_j:
                    cit_i['in_text_refs'] = list(set(cit_i.get('in_text_refs', []) + cit_j.get('in_text_refs', [])))
                # Remove duplicate
                citations.pop(dup_j)
            else:
                # Keep cit_j, merge in_text_refs from cit_i
                if 'in_text_refs' in cit_i:
                    cit_j['in_text_refs'] = list(set(cit_i.get('in_text_refs', []) + cit_j.get('in_text_refs', [])))
                # Remove duplicate
                citations.pop(dup_i)
        
        return citations

citation_extraction_service = CitationExtractionService()