"""
Natural Language Query Parser Service

Parses natural language search queries into structured filters using GPT-4o-mini.
Stage 1 (MVP): Parses years, venues, and content flags.

Examples:
- "transformers from NeurIPS after 2020" → venue="NeurIPS", year_from=2020
- "papers with tables about BERT" → has_tables=True, keywords="BERT"
- "ICLR 2022 papers on GANs" → venue="ICLR", year=2022, keywords="GANs"
"""

import os
import re
from typing import Dict, Optional, List
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

class NLQueryParser:
    """Parse natural language queries into structured search filters"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Common venue abbreviations and full names
        self.venue_aliases = {
            "neurips": ["NeurIPS", "NIPS", "Neural Information Processing Systems"],
            "icml": ["ICML", "International Conference on Machine Learning"],
            "iclr": ["ICLR", "International Conference on Learning Representations"],
            "cvpr": ["CVPR", "Computer Vision and Pattern Recognition"],
            "iccv": ["ICCV", "International Conference on Computer Vision"],
            "eccv": ["ECCV", "European Conference on Computer Vision"],
            "acl": ["ACL", "Association for Computational Linguistics"],
            "emnlp": ["EMNLP", "Empirical Methods in Natural Language Processing"],
            "naacl": ["NAACL", "North American Chapter of ACL"],
            "aaai": ["AAAI", "Association for the Advancement of Artificial Intelligence"],
            "ijcai": ["IJCAI", "International Joint Conference on Artificial Intelligence"],
            "kdd": ["KDD", "Knowledge Discovery and Data Mining"],
            "www": ["WWW", "World Wide Web Conference"],
            "sigir": ["SIGIR", "Special Interest Group on Information Retrieval"],
            "nature": ["Nature"],
            "science": ["Science"],
            "cell": ["Cell"],
            "pnas": ["PNAS", "Proceedings of the National Academy of Sciences"],
            "jmlr": ["JMLR", "Journal of Machine Learning Research"],
        }
    
    def _normalize_venue(self, venue: str) -> str:
        """Normalize venue name to standard format"""
        venue_lower = venue.lower().strip()
        
        # Check if it matches any known venue
        for standard, aliases in self.venue_aliases.items():
            if venue_lower in [a.lower() for a in aliases]:
                return aliases[0]  # Return canonical name
        
        # Return original if no match (might be valid venue not in our list)
        return venue.strip()
    
    def _extract_year_patterns(self, query: str) -> Dict:
        """Fast regex-based year extraction before AI parsing"""
        result = {}
        
        # Pattern 1: "after 2020", "since 2020", "from 2020"
        after_match = re.search(r'\b(?:after|since|from)\s+(\d{4})\b', query, re.IGNORECASE)
        if after_match:
            result['year_from'] = int(after_match.group(1))
        
        # Pattern 2: "before 2022", "until 2022"
        before_match = re.search(r'\b(?:before|until)\s+(\d{4})\b', query, re.IGNORECASE)
        if before_match:
            result['year_to'] = int(before_match.group(1))
        
        # Pattern 3: "2020-2022", "2020 to 2022", "between 2020 and 2022"
        range_match = re.search(r'\b(\d{4})\s*(?:-|to)\s*(\d{4})\b', query, re.IGNORECASE)
        if range_match:
            result['year_from'] = int(range_match.group(1))
            result['year_to'] = int(range_match.group(2))
        
        # Pattern 4: "in 2021", "published in 2021", "2021 papers"
        single_year_match = re.search(r'\b(?:in|published in|year)\s+(\d{4})\b', query, re.IGNORECASE)
        if single_year_match and not result:
            year = int(single_year_match.group(1))
            result['year_from'] = year
            result['year_to'] = year
        
        # Pattern 5: Just a standalone year (e.g., "transformers 2020")
        if not result:
            year_only = re.search(r'\b(20\d{2})\b', query)
            if year_only:
                year = int(year_only.group(1))
                result['year_from'] = year
                result['year_to'] = year
        
        return result
    
    def _extract_content_flags(self, query: str) -> Dict:
        """Fast regex-based content flag extraction"""
        result = {}
        
        # Pattern: "with tables", "has tables", "containing tables"
        if re.search(r'\b(?:with|has|containing|include[s]?)\s+tables?\b', query, re.IGNORECASE):
            result['has_tables'] = True
        
        # Pattern: "with images", "has figures", "containing images"
        if re.search(r'\b(?:with|has|containing|include[s]?)\s+(?:images?|figures?)\b', query, re.IGNORECASE):
            result['has_images'] = True
        
        # Pattern: "with equations", "has formulas", "mathematical"
        if re.search(r'\b(?:with|has|containing|include[s]?)\s+(?:equations?|formulas?|math)\b', query, re.IGNORECASE):
            result['has_equations'] = True
        
        return result
    
    def _extract_venue_patterns(self, query: str) -> Optional[str]:
        """Fast regex-based venue extraction"""
        
        # Pattern 1: "from NeurIPS", "in ICML", "at ACL", "published in CVPR"
        venue_match = re.search(r'\b(?:from|in|at|published in)\s+([A-Z]{3,}(?:\s+\d{4})?)\b', query)
        if venue_match:
            venue = venue_match.group(1).strip()
            # Remove year if present (e.g., "NeurIPS 2020" -> "NeurIPS")
            venue = re.sub(r'\s+\d{4}', '', venue)
            return self._normalize_venue(venue)
        
        # Pattern 2: Check for known venue names (case-insensitive)
        query_lower = query.lower()
        for standard, aliases in self.venue_aliases.items():
            for alias in aliases:
                if alias.lower() in query_lower:
                    return aliases[0]  # Return canonical name
        
        return None
    
    async def parse_query(self, query: str, enable_ai: bool = True) -> Dict:
        """
        Parse natural language query into structured filters
        
        Args:
            query: Natural language search query
            enable_ai: Use AI for parsing (set False for regex-only fallback)
        
        Returns:
            {
                'semantic_query': str,  # Clean query for semantic search
                'filters': {
                    'year_from': int,
                    'year_to': int,
                    'venue': str,
                    'has_images': bool,
                    'has_tables': bool,
                    'has_equations': bool
                },
                'confidence': float,  # 0-1 confidence in parsing
                'parsed_elements': list  # What was detected (for UI display)
            }
        """
        
        # Step 1: Fast regex extraction (always run, even with AI)
        year_filters = self._extract_year_patterns(query)
        content_filters = self._extract_content_flags(query)
        venue_filter = self._extract_venue_patterns(query)
        
        # Combine regex results
        filters = {**year_filters, **content_filters}
        if venue_filter:
            filters['venue'] = venue_filter
        
        parsed_elements = []
        
        # Track what was parsed for UI display
        if year_filters.get('year_from') and year_filters.get('year_to'):
            if year_filters['year_from'] == year_filters['year_to']:
                parsed_elements.append(f"Year: {year_filters['year_from']}")
            else:
                parsed_elements.append(f"Years: {year_filters['year_from']}-{year_filters['year_to']}")
        elif year_filters.get('year_from'):
            parsed_elements.append(f"From: {year_filters['year_from']}")
        elif year_filters.get('year_to'):
            parsed_elements.append(f"Until: {year_filters['year_to']}")
        
        if venue_filter:
            parsed_elements.append(f"Venue: {venue_filter}")
        
        if content_filters.get('has_images'):
            parsed_elements.append("Has Images")
        if content_filters.get('has_tables'):
            parsed_elements.append("Has Tables")
        if content_filters.get('has_equations'):
            parsed_elements.append("Has Equations")
        
        # Step 2: Clean query for semantic search (remove parsed filter terms)
        semantic_query = query
        
        # Remove year mentions
        semantic_query = re.sub(r'\b(?:after|since|from|before|until|in|published in|year)\s+\d{4}\b', '', semantic_query, flags=re.IGNORECASE)
        semantic_query = re.sub(r'\b\d{4}\s*(?:-|to)\s*\d{4}\b', '', semantic_query, flags=re.IGNORECASE)
        semantic_query = re.sub(r'\b20\d{2}\b', '', semantic_query)
        
        # Remove venue mentions
        if venue_filter:
            semantic_query = re.sub(rf'\b(?:from|in|at|published in)\s+{re.escape(venue_filter)}\b', '', semantic_query, flags=re.IGNORECASE)
            semantic_query = re.sub(rf'\b{re.escape(venue_filter)}\b', '', semantic_query, flags=re.IGNORECASE)
        
        # Remove content flags
        semantic_query = re.sub(r'\b(?:with|has|containing|include[s]?)\s+(?:tables?|images?|figures?|equations?|formulas?|math)\b', '', semantic_query, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        semantic_query = ' '.join(semantic_query.split()).strip()
        
        # If query becomes empty after cleaning, use original
        if not semantic_query or len(semantic_query) < 3:
            semantic_query = query
        
        # Step 3: AI enhancement (optional, for complex queries)
        confidence = 0.9 if parsed_elements else 0.5  # High confidence if regex found anything
        
        if enable_ai and not parsed_elements:
            # Only use AI if regex found nothing (saves API costs)
            try:
                ai_result = await self._ai_parse_query(query)
                if ai_result.get('filters'):
                    filters.update(ai_result['filters'])
                    semantic_query = ai_result.get('semantic_query', semantic_query)
                    parsed_elements = ai_result.get('parsed_elements', [])
                    confidence = 0.85  # AI confidence
            except Exception as e:
                logger.warning(f"AI parsing failed, using regex fallback: {e}")
        
        return {
            'semantic_query': semantic_query,
            'filters': filters,
            'confidence': confidence,
            'parsed_elements': parsed_elements
        }
    
    async def _ai_parse_query(self, query: str) -> Dict:
        """AI-based parsing for complex queries (fallback)"""
        
        prompt = f"""Parse this academic search query into structured filters.

Query: "{query}"

Extract ONLY these filters if present:
1. year_from: Earliest year (e.g., "after 2020" → 2020)
2. year_to: Latest year (e.g., "before 2022" → 2022)
3. venue: Conference/Journal name (e.g., "NeurIPS", "ICML", "Nature")
4. has_images: Boolean (if mentions "with images", "has figures")
5. has_tables: Boolean (if mentions "with tables", "contains tables")
6. has_equations: Boolean (if mentions "with equations", "mathematical")

Also extract:
- semantic_query: The core topic query after removing filter terms

Return JSON ONLY:
{{
    "semantic_query": "core topic without filters",
    "filters": {{
        "year_from": 2020 or null,
        "year_to": 2022 or null,
        "venue": "NeurIPS" or null,
        "has_images": true or null,
        "has_tables": true or null,
        "has_equations": true or null
    }},
    "parsed_elements": ["Year: 2020", "Venue: NeurIPS"]
}}

Rules:
- Only include filters if explicitly mentioned
- Use null for missing filters
- Normalize venue names (e.g., "nips" → "NeurIPS")
- Extract core semantic query without filter terms
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-5-mini-2025-08-07",
                messages=[
                    {"role": "user", "content": f"You are an expert at parsing academic search queries. Return ONLY valid JSON.\n\n{prompt}"}
                ],
                max_tokens=400
            )
            
            import json
            raw_content = response.choices[0].message.content or ""
            result = json.loads(raw_content)
            
            # Clean up filters (remove null values)
            if 'filters' in result:
                result['filters'] = {k: v for k, v in result['filters'].items() if v is not None}
            
            # Normalize venue if present
            if result.get('filters', {}).get('venue'):
                result['filters']['venue'] = self._normalize_venue(result['filters']['venue'])
            
            return result
            
        except Exception as e:
            logger.error(f"AI parsing failed: {e}")
            return {}


# Global instance
nl_query_parser = NLQueryParser();