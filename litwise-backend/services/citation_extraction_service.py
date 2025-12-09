import re
from typing import List, Dict, Optional, Tuple
from openai import OpenAI
from difflib import SequenceMatcher
import os
import logging

logger = logging.getLogger(__name__)

class CitationExtractionService:
    """Extract and enrich citations from research papers"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
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
        """Extract structured metadata from citation text using regex"""
        metadata = {
            'title': None,
            'authors': [],
            'year': None,
            'doi': None,
            'venue': None
        }
        
        # Extract DOI
        doi_match = re.search(r'(?:doi[:\s]+|https?://doi\.org/)(10\.\d{4,}/[^\s,]+)', citation_text, re.IGNORECASE)
        if doi_match:
            metadata['doi'] = doi_match.group(1)
        
        # Extract year
        year_match = re.search(r'\((\d{4})\)|,\s*(\d{4})[,.]', citation_text)
        if year_match:
            metadata['year'] = int(year_match.group(1) or year_match.group(2))
        
        # Extract title (quoted text or between year and venue)
        title_match = re.search(r'["""](.+?)["""]', citation_text)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
        
        # Extract authors (complex, simplified version)
        # Look for pattern: LastName, F., LastName, F., ... (Year)
        author_pattern = r'^(.+?)\s*\(\d{4}\)'
        author_match = re.search(author_pattern, citation_text)
        if author_match:
            author_text = author_match.group(1)
            # Split by "and" or commas
            authors = re.split(r',\s*(?:and\s+)?|and\s+', author_text)
            metadata['authors'] = [a.strip() for a in authors if a.strip()][:5]  # Limit to 5
        
        return metadata
    
    async def enrich_citation_with_ai(self, citation_text: str, paper_context: str = "") -> Dict:
        """Use AI to extract metadata and relevance from citation"""
        try:
            prompt = f"""Extract structured metadata from this citation and explain its relevance.

Citation:
{citation_text}

{f"Paper context:\n{paper_context[:500]}" if paper_context else ""}

Respond in JSON format:
{{
    "title": "Full paper title",
    "authors": ["Author 1", "Author 2"],
    "year": 2020,
    "venue": "Journal/Conference name",
    "doi": "10.xxxx/xxxx or null",
    "relevance_summary": "One sentence explaining why this citation is relevant (e.g., 'Introduces the Transformer architecture used in this paper')",
    "citation_type": "background|method|comparison|data"
}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at parsing academic citations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"AI enrichment failed: {e}")
            return {}
    
    async def enrich_citations_batch(self, citations: List[Dict], paper_context: str = "", batch_size: int = 5) -> List[Dict]:
        """Batch AI enrichment for multiple citations to reduce API calls
        
        Process 5-10 citations in a single API call instead of one call per citation.
        This reduces API calls by 80%+ for papers with many citations.
        """
        enriched = []
        
        # Process in batches
        for i in range(0, len(citations), batch_size):
            batch = citations[i:i+batch_size]
            
            try:
                # Create a batch enrichment prompt
                citations_text = "\n\n".join([
                    f"Citation {idx+1}:\n{cit['raw_text']}" 
                    for idx, cit in enumerate(batch)
                ])
                
                prompt = f"""Extract structured metadata from these citations and explain their relevance.

Citations to process ({len(batch)} total):
{citations_text}

{f"Paper context:\n{paper_context[:300]}" if paper_context else ""}

Respond in JSON format with an array of objects:
[
  {{
    "index": 0,
    "title": "Paper title",
    "authors": ["Author 1", "Author 2"],
    "year": 2020,
    "venue": "Journal/Conference",
    "doi": "10.xxxx/xxxx or null",
    "relevance_summary": "One sentence",
    "citation_type": "background|method|comparison|data"
  }}
]"""

                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert at parsing academic citations. Return ONLY valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                import json
                results = json.loads(response.choices[0].message.content)
                
                # Handle both single object and array responses
                if isinstance(results, dict) and "results" in results:
                    enriched.extend(results["results"])
                elif isinstance(results, list):
                    enriched.extend(results)
                    
            except Exception as e:
                logger.error(f"Batch enrichment failed for citations {i}-{i+len(batch)}: {e}")
                # Fall back to individual enrichment for this batch
                for cit in batch:
                    result = await self.enrich_citation_with_ai(cit['raw_text'], paper_context)
                    enriched.append(result)
        
        return enriched
    
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