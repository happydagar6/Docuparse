"""
AI-Powered Citation Generator Service

Hybrid cost-saving architecture:
1. Extract text from first 2 pages of PDF
2. Try to find DOI with regex
3. If DOI found: Use free Crossref API
4. If no DOI: Use OpenAI to extract metadata
5. Format into APA 7th Edition

Author: Senior Backend Engineer
Date: December 2025
"""

import os
import re
import json
import fitz  # PyMuPDF
import httpx
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


class AICitationService:
    """Smart Citation Generator with Hybrid DOI + AI Extraction"""
    
    # Crossref API endpoint
    CROSSREF_API = "https://api.crossref.org/works/{doi}"
    
    # DOI Regex Pattern (matches most academic DOIs)
    DOI_PATTERN = r'10\.\d{4,9}/[-._;()/:A-Z0-9]+'
    
    def __init__(self):
        """Initialize the citation service with OpenAI model"""
        self.llm = ChatOpenAI(
            model="gpt-5-mini-2025-08-07",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        print("✅ AI Citation Service initialized with OpenAI model")
    
    async def generate_citation_from_pdf(self, pdf_path: str) -> Dict:
        """
        Main entry point: Generate citation from PDF using hybrid approach
        
        Args:
            pdf_path: Path to the uploaded PDF file
            
        Returns:
            {
                "citation": "APA 7th Edition formatted string",
                "source": "crossref" or "ai",
                "metadata": {...raw fields...},
                "success": True/False,
                "error": None or error message
            }
        """
        try:
            # Step 1: Extract text from first 2 pages only
            print("📄 Extracting text from first 2 pages...")
            text_chunk = self._extract_first_pages(pdf_path, num_pages=2)
            
            if not text_chunk or len(text_chunk) < 100:
                return {
                    "citation": None,
                    "source": None,
                    "metadata": None,
                    "success": False,
                    "error": "PDF is empty or unreadable"
                }
            
            print(f"✅ Extracted {len(text_chunk)} characters from PDF")
            
            # Step 2: Try to find DOI (FREE method first!)
            print("🔍 Searching for DOI in text...")
            doi = self._extract_doi(text_chunk)
            
            if doi:
                print(f"✅ Found DOI: {doi}")
                # Step 3a: Use Crossref API (FREE!)
                metadata = await self._fetch_crossref_metadata(doi)
                
                if metadata:
                    print("✅ Successfully fetched metadata from Crossref (free)")
                    citation = self._format_apa_citation(metadata)
                    return {
                        "citation": citation,
                        "source": "crossref",
                        "metadata": metadata,
                        "success": True,
                        "error": None
                    }
                else:
                    print("⚠️ Crossref lookup failed, falling back to AI")
            else:
                print("⚠️ No DOI found in text")
            
            # Step 3b: Fallback to AI extraction
            print("🤖 Using AI to extract metadata...")
            metadata = await self._extract_metadata_with_ai(text_chunk)
            
            if metadata and metadata.get('title'):
                print("✅ Successfully extracted metadata with AI")
                citation = self._format_apa_citation(metadata)
                return {
                    "citation": citation,
                    "source": "ai",
                    "metadata": metadata,
                    "success": True,
                    "error": None
                }
            else:
                return {
                    "citation": None,
                    "source": None,
                    "metadata": None,
                    "success": False,
                    "error": "AI extraction failed - could not extract valid metadata"
                }
                
        except Exception as e:
            print(f"❌ Error generating citation: {str(e)}")
            return {
                "citation": None,
                "source": None,
                "metadata": None,
                "success": False,
                "error": f"Citation generation failed: {str(e)}"
            }
    
    def _extract_first_pages(self, pdf_path: str, num_pages: int = 2) -> str:
        """
        Extract text from first N pages of PDF
        
        Args:
            pdf_path: Path to PDF file
            num_pages: Number of pages to extract (default: 2)
            
        Returns:
            Extracted text as string
        """
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            
            # Extract only first N pages
            for page_num in range(min(num_pages, len(doc))):
                page = doc[page_num]
                text_parts.append(page.get_text())
            
            doc.close()
            return "\n".join(text_parts)
            
        except Exception as e:
            print(f"❌ Error extracting PDF text: {str(e)}")
            return ""
    
    def _clean_doi(self, doi: str) -> str:
        """
        Clean DOI to ensure it's in standard format (just the identifier)
        Removes common prefixes and whitespace
        
        Args:
            doi: DOI string (may have prefixes)
            
        Returns:
            Cleaned DOI (e.g., '10.1234/example')
        """
        if not doi:
            return doi
            
        # Remove common prefixes (case-insensitive)
        doi = doi.strip()
        doi_lower = doi.lower()
        
        if 'doi.org/' in doi_lower:
            # Extract DOI after doi.org/
            doi = doi.split('doi.org/', 1)[-1]
        elif doi_lower.startswith('doi:'):
            # Remove 'doi:' prefix
            doi = doi[4:].strip()
        elif doi_lower.startswith('http'):
            # Extract DOI from any http/https URL
            parts = doi.split('/')
            # Find the part that starts with 10.
            for i, part in enumerate(parts):
                if part.startswith('10.'):
                    doi = '/'.join(parts[i:])
                    break
        
        # Remove trailing punctuation
        doi = doi.rstrip('.,;:')
        
        return doi
    
    def _extract_doi(self, text: str) -> Optional[str]:
        """
        Extract DOI from text using regex pattern
        
        Args:
            text: Text to search for DOI
            
        Returns:
            DOI string or None if not found
        """
        # Search for DOI pattern (case-insensitive)
        match = re.search(self.DOI_PATTERN, text, re.IGNORECASE)
        
        if match:
            doi = match.group(0)
            # Clean up DOI (remove trailing punctuation and prefixes)
            doi = self._clean_doi(doi)
            return doi
        
        return None
    
    async def _fetch_crossref_metadata(self, doi: str) -> Optional[Dict]:
        """
        Fetch metadata from Crossref API (FREE!)
        
        Args:
            doi: Digital Object Identifier
            
        Returns:
            Metadata dict or None if failed
        """
        try:
            url = self.CROSSREF_API.format(doi=doi)
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    message = data.get('message', {})
                    
                    # Parse Crossref response into our metadata format
                    authors = []
                    for author in message.get('author', []):
                        given = author.get('given', '')
                        family = author.get('family', '')
                        if family:
                            # Format as "LastName, F." (APA style)
                            initial = given[0] + '.' if given else ''
                            authors.append(f"{family}, {initial}")
                    
                    # Extract year from published date
                    year = None
                    date_parts = message.get('published', {}).get('date-parts', [[]])
                    if date_parts and date_parts[0]:
                        year = date_parts[0][0]
                    
                    # Build metadata
                    metadata = {
                        'title': message.get('title', [''])[0],
                        'authors': authors,
                        'year': year,
                        'journal': message.get('container-title', [''])[0],
                        'volume': message.get('volume'),
                        'issue': message.get('issue'),
                        'pages': message.get('page'),
                        'doi': self._clean_doi(doi),
                        'publisher': message.get('publisher')
                    }
                    
                    return metadata
                else:
                    print(f"⚠️ Crossref API returned status {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error fetching from Crossref: {str(e)}")
            return None
    
    async def _extract_metadata_with_ai(self, text_chunk: str) -> Optional[Dict]:
        """
        Use AI to extract metadata from PDF text
        
        Args:
            text_chunk: Text from first 2 pages
            
        Returns:
            Metadata dict or None if failed
        """
        try:
            # Prompt for AI to extract structured metadata
            prompt = f"""You are an expert academic librarian. Extract citation metadata from this academic paper's first pages.

**CRITICAL INSTRUCTIONS:**
1. Extract ONLY from the PAPER ITSELF (title, authors, year, journal on first page)
2. DO NOT extract from the References/Bibliography section
3. Remove ALL superscript numbers from author names (e.g., "Smith 1,2" → "Smith")
4. Format authors as "LastName, Initial." (e.g., "van Agteren, J.")
5. Extract the FULL paper title (not section headings)
6. Find the publication year (NOT the current year)
7. Return ONLY valid JSON, no extra text

**REQUIRED JSON FORMAT:**
{{
    "title": "Full article title in sentence case",
    "authors": ["LastName, I.", "LastName, I.", "LastName, I."],
    "year": 2021,
    "journal": "Journal Name",
    "volume": "5",
    "issue": "3",
    "pages": "123-145",
    "doi": "10.xxxx/xxxxx"
}}

**TEXT TO ANALYZE:**
{text_chunk[:4000]}

Return ONLY the JSON object, nothing else."""

            # Call AI
            response = await self.llm.ainvoke(prompt)
            response_text = response.content.strip()
            
            # Extract JSON from response (in case AI adds extra text)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                metadata = json.loads(json_str)
                
                # Validate metadata has required fields
                if metadata.get('title') and metadata.get('authors'):
                    # Clean DOI if present
                    if metadata.get('doi'):
                        metadata['doi'] = self._clean_doi(metadata['doi'])
                    print(f"✅ AI extracted: {len(metadata.get('authors', []))} authors, year: {metadata.get('year')}")
                    return metadata
                else:
                    print("⚠️ AI response missing required fields")
                    return None
            else:
                print("⚠️ Could not parse JSON from AI response")
                return None
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {str(e)}")
            print(f"AI response: {response_text[:200]}")
            return None
        except Exception as e:
            print(f"❌ AI extraction error: {str(e)}")
            return None
    
    def _format_apa_citation(self, metadata: Dict) -> str:
        """
        Format metadata into APA 7th Edition citation
        
        Format: Author, A. A., & Author, B. B. (Year). Title of article. 
                *Journal Name*, *Volume*(Issue), Pages. https://doi.org/xxxx
        
        Args:
            metadata: Dict with title, authors, year, journal, etc.
            
        Returns:
            Formatted APA citation string
        """
        parts = []
        
        # 1. Authors
        authors = metadata.get('authors', [])
        if authors:
            if len(authors) == 1:
                parts.append(authors[0])
            elif len(authors) == 2:
                parts.append(f"{authors[0]}, & {authors[1]}")
            else:
                # 3+ authors: join with commas, & before last
                author_list = ", ".join(authors[:-1])
                parts.append(f"{author_list}, & {authors[-1]}")
        else:
            parts.append("Unknown Author")
        
        # 2. Year
        year = metadata.get('year')
        if year:
            parts.append(f"({year}).")
        else:
            parts.append("(n.d.).")
        
        # 3. Title (sentence case)
        title = metadata.get('title', 'Untitled')
        # Ensure title ends with period
        if not title.endswith('.'):
            title += '.'
        parts.append(title)
        
        # 4. Journal (italicized with markdown)
        journal = metadata.get('journal')
        if journal:
            journal_part = f"*{journal}*"
            
            # 5. Volume and Issue
            volume = metadata.get('volume')
            issue = metadata.get('issue')
            
            if volume:
                journal_part += f", *{volume}*"
                if issue:
                    journal_part += f"({issue})"
            
            # 6. Pages
            pages = metadata.get('pages')
            if pages:
                journal_part += f", {pages}"
            
            journal_part += "."
            parts.append(journal_part)
        
        # 7. DOI or URL
        doi = metadata.get('doi')
        if doi:
            # Remove any existing doi: prefix
            doi_clean = doi.replace('doi:', '').strip()
            parts.append(f"https://doi.org/{doi_clean}")
        
        # Join all parts with spaces
        citation = " ".join(parts)
        
        return citation


# Global instance
ai_citation_service = AICitationService()
