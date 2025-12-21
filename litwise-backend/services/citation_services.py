import re # Regular expression operations
from typing import List, Optional
from datetime import datetime
from models.citation import PaperMetadata, CitationFormat

class CitationService:
    """Generate citations in multiple formats"""
    
    def generate(self, metadata: PaperMetadata, format: CitationFormat) -> str:
        """Generate citation in sepecified format"""
        formatters = {
            CitationFormat.APA: self._format_apa,
            CitationFormat.IEEE: self._format_ieee,
            CitationFormat.BIBTEX: self._format_bibtex,
            CitationFormat.VANCOUVER: self._format_vancouver,
            CitationFormat.MLA: self._format_mla,
        }
        return formatters[format](metadata)
    
    def _format_authors_apa(self, authors: List[str]) -> str:
        if not authors:
            return "Unknown Author"
        if len(authors) == 1:
            return self._last_first(authors[0])
        if len(authors) == 2:
            return f"{self._last_first(authors[0])} & {self._last_first(authors[1])}"
        if len(authors) <= 20:
            formatted = ", ".join(self._last_first(a) for a in authors[:-1])
            return f"{formatted}, & {self._last_first(authors[-1])}"
        # More than 20 authors
        formatted = ", ".join(self._last_first(a) for a in authors[:19])
        return f"{formatted}, ... {self._last_first(authors[-1])}"
    
    def _last_first(self, name: str) -> str:
        """Convert "John Smith" to "Smith, J." or preserve "Smith, J." if already formatted"""
        name = name.strip()
        # Check if already in "LastName, I." format (contains comma)
        if "," in name:
            return name  # Already formatted by AI service
        
        parts = name.split()
        if len(parts) == 1:
            return parts[0]
        last = parts[-1]
        initials = ". ".join(p[0].upper() for p in parts[:-1]) + "."
        return f"{last}, {initials}"  # Single space after comma
    
    def _format_apa(self, m: PaperMetadata) -> str:
        """APA 7th Edition format - Enhanced with complete metadata"""
        authors = self._format_authors_apa(m.authors) if m.authors else "Unknown Author"
        year = f"({m.year})" if m.year else "(n.d.)"
        title = m.title.rstrip(".")
        
        # Build citation parts
        parts = [f"{authors} {year}. {title}."]
        
        # Journal or Publisher information
        if m.journal:
            journal_part = f"*{m.journal}*" # Italicize journal name
            if m.volume:
                journal_part += f", *{m.volume}*" # Italicize volume
            if m.issue:
                journal_part += f"({m.issue})" # Issue in parentheses
            if m.pages:
                # Format pages properly (e.g., "123-145" or "e12345")
                journal_part += f", {m.pages}"
            parts.append(journal_part + ".") # End journal part
        elif m.publisher:
            # If no journal, include publisher
            parts.append(f"{m.publisher}.")
        
        # Add DOI or URL (DOI preferred)
        if m.doi:
            parts.append(f"https://doi.org/{m.doi}")
        elif m.url:
            parts.append(m.url)
        
        return " ".join(parts)
    
    def _format_ieee(self, m: PaperMetadata) -> str:
        """IEEE format - Enhanced for technical publications"""
        
        # Format authors (up to 3, then et al.)
        if m.authors:
            if len(m.authors) <= 3:
                authors = ", ".join(self._first_last_ieee(a) for a in m.authors)
            else:
                authors = f"{self._first_last_ieee(m.authors[0])} et al."
        else:
            authors = "Unknown Author"
        
        # Title in quotes
        title = f'"{m.title.rstrip(".")}"'
        parts = [f"{authors}, {title}"]
        
        # Journal and volume information
        if m.journal:
            parts.append(f"*{m.journal}*")
            
        if m.volume or m.issue or m.pages:
            vol_part = ""
            if m.volume:
                vol_part = f"vol. {m.volume}"
            if m.issue:
                vol_part += f", no. {m.issue}" if vol_part else f"no. {m.issue}"
            if m.pages:
                vol_part += f", pp. {m.pages}" if vol_part else f"pp. {m.pages}"
            if vol_part:
                parts.append(vol_part)
        
        # Year and identifiers
        if m.year:
            parts.append(str(m.year))
        if m.doi:
            parts.append(f"doi: {m.doi}")
        elif m.url:
            parts.append(f"Available: {m.url}")
            
        return ", ".join(parts) + "."
    
    def _first_last_ieee(self, name: str) -> str:
        """Convert "John Smith" to "J. Smith" or handle "Smith, J." format"""
        name = name.strip()
        # Check if already formatted as "LastName, I."
        if "," in name:
            # Convert "Smith, J." to "J. Smith"
            parts = name.split(",", 1)
            last = parts[0].strip()
            initials = parts[1].strip()
            return f"{initials} {last}"
        
        parts = name.split()
        if len(parts) == 1:
            return parts[0]
        initials = " ".join(p[0].upper() + "." for p in parts[:-1])
        return f"{initials} {parts[-1]}"
    
    def _format_bibtex(self, m: PaperMetadata) -> str:
        """BibTeX format for LaTeX"""
        # Generate citation key
        first_author = m.authors[0].split()[-1] if m.authors else "Unknown"
        year = m.year or datetime.now().year
        key = f"{first_author.lower()}{year}"
        key = re.sub(r'[^a-z0-9]', '', key) # Remove non-alphanumeric
        
        entry_type = "article" if m.journal else "misc"
        
        lines = [f"@{entry_type}{{{key},"]
        lines.append(f"  title={{ {m.title} }},")
        
        if m.authors:
            lines.append(f"  author = {{{' and '.join(m.authors)}}},")
        if m.year:
            lines.append(f"  year = {{{m.year}}},")
        if m.journal:
            lines.append(f"  journal = {{{m.journal}}},")
        if m.volume:
            lines.append(f"  volume = {{{m.volume}}},")
        if m.issue:
            lines.append(f"  number = {{{m.issue}}},")
        if m.pages:
            lines.append(f"  pages = {{{m.pages}}},")
        if m.doi:
            lines.append(f"  doi = {{{m.doi}}},")
        if m.url:
            lines.append(f"  url = {{{m.url}}},")
        if m.publisher:
            lines.append(f"  publisher = {{{m.publisher}}},")
            
        lines.append("}")
        return "\n".join(lines)
    
    def _format_vancouver(self, m: PaperMetadata) -> str:
        """Vancouver format (medical/scientific journals) - Enhanced"""
        # Authors (up to 6, then et al.)
        if m.authors:
            if len(m.authors) <= 6:
                authors = ", ".join(self._vancouver_author(a) for a in m.authors)
            else:
                authors = ", ".join(self._vancouver_author(a) for a in m.authors[:6])
                authors += ", et al."
        else:
            authors = "Unknown Author"
        
        # Title (remove period if exists)
        title = m.title.rstrip(".")
        parts = [f"{authors}. {title}."]
        
        # Journal abbreviation (Vancouver uses abbreviated journal names)
        if m.journal:
            journal_part = m.journal
            
            # Year and volume/issue/pages on same line
            if m.year:
                journal_part += f" {m.year}"
                
            if m.volume:
                journal_part += f";{m.volume}"
                if m.issue:
                    journal_part += f"({m.issue})"
                if m.pages:
                    journal_part += f":{m.pages}"
                    
            parts.append(journal_part + ".")
        elif m.year:
            # If no journal, just add year
            parts.append(f"{m.year}.")
            
        # DOI (preferred) or URL
        if m.doi:
            parts.append(f"doi:{m.doi}")
        elif m.url:
            parts.append(f"Available from: {m.url}")
        
        return " ".join(parts)
    
    def _vancouver_author(self, name: str) -> str:
        """Convert "John Smith" to "Smith J" or handle "Smith, J." format"""
        name = name.strip()
        # Check if already formatted as "LastName, I."
        if "," in name:
            # Convert "Smith, J." to "Smith J" (remove dots and comma)
            parts = name.split(",", 1)
            last = parts[0].strip()
            initials = parts[1].strip().replace(".", "").replace(" ", "")
            return f"{last} {initials}"
        
        parts = name.split() # Split by spaces
        if len(parts) == 1:
            return parts[0] # Single name, return as is
        last = parts[-1] # Last name
        initials = "".join(p[0].upper() for p in parts[:-1]) # Initials without dots
        return f"{last} {initials}"
    
    def _format_mla(self, m: PaperMetadata) -> str:
        """MLA 9th Edition format - Enhanced with complete metadata"""
        # Format authors (first author inverted, others normal)
        if m.authors:
            if len(m.authors) == 1:
                authors = self._mla_author(m.authors[0])
            elif len(m.authors) == 2:
                # Two authors: invert first, normal second
                authors = f"{self._mla_author(m.authors[0])}, and {m.authors[1]}"
            else:
                # Three or more: first author inverted, then et al.
                authors = f"{self._mla_author(m.authors[0])}, et al."
        else:
            authors = "Unknown Author"
        
        # Title in quotes
        parts = [f'{authors}. "{m.title.rstrip(".")}"']
        
        # Container (journal/publication)
        if m.journal:
            parts.append(f"*{m.journal}*,")
        elif m.publisher:
            parts.append(f"{m.publisher},")
            
        # Volume and issue
        if m.volume:
            vol = f"vol. {m.volume}"
            if m.issue:
                vol += f", no. {m.issue}"
            parts.append(vol + ",")
            
        # Year
        if m.year:
            parts.append(f"{m.year},")
            
        # Pages
        if m.pages:
            parts.append(f"pp. {m.pages}.")
        else:
            # Remove trailing comma from year if no pages
            if parts[-1].endswith(","):
                parts[-1] = parts[-1].rstrip(",") + "."
                
        # DOI or URL
        if m.doi:
            parts.append(f"https://doi.org/{m.doi}")
        elif m.url:
            parts.append(m.url)
        
        return " ".join(parts)
    
    def _mla_author(self, name: str) -> str:
        """Convert 'John Smith' to 'Smith, John' or handle 'Smith, J.' format"""
        name = name.strip()
        # Check if already formatted as "LastName, I."
        if "," in name:
            # Already has comma, return as is (MLA accepts initials)
            return name
        
        parts = name.split()
        if len(parts) == 1:
            return parts[0]
        return f"{parts[-1]}, {' '.join(parts[:-1])}"
    
citation_service = CitationService()