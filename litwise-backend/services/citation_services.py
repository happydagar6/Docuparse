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
        """Convert "John Smith" to "Smith, J." """
        parts = name.strip().split()
        if len(parts) == 1:
            return parts[0]
        last = parts[-1]
        initials = ". ".join(p[0].upper() for p in parts[:-1]) + "."
        return f"{last},  {initials}"
    
    def _format_apa(self, m: PaperMetadata) -> str:
        """APA 7th Edition format"""
        authors = self._format_authors_apa(m.authors) if m.authors else "Unknown Author"
        year = f"({m.year})" if m.year else "(n.d.)"
        title = m.title.rstrip(".")
        
        parts = [f"{authors} {year}. {title}."]
        
        # Journal or Publisher
        if m.journal:
            journal_part = f"*{m.journal}*" # Italicize journal name
            if m.volume:
                journal_part += f", *{m.volume}*" # Italicize volume
            if m.issue:
                journal_part += f"({m.issue})" # No period yet
            if m.pages:
                journal_part += f", {m.pages}" # No period yet
            parts.append(journal_part + ".") # End journal part
        
        if m.doi:
            parts.append(f"https://doi.org/{m.doi}") # DOI link
        elif m.url:
            parts.append(m.url) # URL
        return " ".join(parts)
    
    def _format_ieee(self, m: PaperMetadata) -> str:
        """IEEE format"""
        
        if m.authors:
            if len(m.authors) <= 3:
                authors = ", ".join(self._first_last_ieee(a) for a in m.authors)
            else:
                authors = f"{self._first_last_ieee(m.authors[0])} et al."
        else:
            authors = "Unknown Author"
        
        title = f'"{m.title}."'
        parts = [f"{authors}, {title}"]
        
        if m.journal:
            parts.append(f"*{m.journal}*")
        if m.volume:
            vol_part = f"vol. {m.volume}"
            if m.issue:
                vol_part += f", no. {m.issue}"
            if m.pages:
                vol_part += f", pp. {m.pages}"
            parts.append(vol_part)
        if m.year:
            parts.append(str(m.year))
        if m.doi:
            parts.append(f"doi: {m.doi}")
        return ", ".join(parts) + "."
    
    def _first_last_ieee(self, name: str) -> str:
        """Convert "John Smith" to "Smith, J." """
        parts = name.strip().split()
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
        """Vancouver format (medical journals)"""
        if m.authors:
            if len(m.authors) <= 6:
                authors = ", ".join(self._vancouver_author(a) for a in m.authors)
            else:
                authors = ", ".join(self._vancouver_author(a) for a in m.authors[:6])
                authors += ", et al." # More than 6 authors
        else:
            authors = "Unknown Author"
        
        parts = [f"{authors}. {m.title}."]
        
        
        if m.journal:
            parts.append(m.journal)
        if m.year:
            parts.append(f"{m.year}")
        if m.volume:
            vol = m.volume
            if m.issue:
                vol += f"({m.issue})"
            if m.pages:
                vol += f":{m.pages}"
            parts.append(vol)
        if m.doi:
            parts.append(f"doi:{m.doi}")
        
        return " ".join(parts) + "."
    
    def _vancouver_author(self, name: str) -> str:
        """Convert "John Smith" to "Smith J" """
        parts = name.strip().split() # Split by spaces
        if len(parts) == 1:
            return parts[0] # Single name, return as is
        last = parts[-1] # Last name
        initials = "".join(p[0].upper() for p in parts[:-1]) # Initials without dots
        return f"{last} {initials}"
    
    def _format_mla(self, m: PaperMetadata) -> str:
        """MLA 9th Edition format"""
        if m.authors:
            if len(m.authors) == 1:
                authors = self._mla_author(m.authors[0])
            elif len(m.authors) == 2:
                authors = f"{self._mla_author(m.authors[0])}, and {m.authors[1]}"
            else:
                authors = f"{self._mla_author(m.authors[0])}, et al."
        else:
            authors = "Unknown Author"
        
        parts = [f'{authors}. "{m.title}."']
        
        if m.journal:
            parts.append(f"*{m.journal}*,")
        if m.volume:
            vol = f"vol. {m.volume}"
            if m.issue:
                vol += f", no. {m.issue}"
            parts.append(vol + ",")
        if m.year:
            parts.append(f"{m.year},")
        if m.pages:
            parts.append(f"pp. {m.pages}.")
        if m.doi:
            parts.append(f"https://doi.org/{m.doi}.")
        
        return " ".join(parts)
    
    def _mla_author(self, name: str) -> str:
        """Convert 'John Smith' to 'Smith, John'"""
        parts = name.strip().split()
        if len(parts) == 1:
            return parts[0]
        return f"{parts[-1]}, {' '.join(parts[:-1])}"
    
citation_service = CitationService()