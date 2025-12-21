"""
APA 7th Edition Document Export Service
Converts research paper content to formatted .docx files
"""

from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from typing import List, Dict, Optional
import re
from io import BytesIO


class APAExportService:
    """Generate APA 7th Edition formatted Word documents"""
    
    def __init__(self):
        self.font_name = "Times New Roman"
        self.font_size = Pt(12)
        self.margin = Inches(1)
        self.line_spacing = 2.0  # Double spacing
        self.paragraph_indent = Inches(0.5)
        self.hanging_indent = Inches(0.5)
    
    def generate_document(
        self,
        title: str,
        running_head: str,
        authors: List[str],
        content: List[Dict],
        references_metadata: Dict[str, Dict],
        affiliation: str = "Independent Researcher"
    ) -> BytesIO:
        """
        Generate APA formatted document
        
        Args:
            title: Paper title
            running_head: Short title for header (max 50 chars)
            authors: List of author names
            content: List of paragraph objects with 'text' and optional 'citations'
            references_metadata: Dict mapping paper_id to metadata
            affiliation: Author affiliation (default: Independent Researcher)
        
        Returns:
            BytesIO object containing the .docx file
        """
        doc = Document()
        
        # Set document margins
        self._set_margins(doc)
        
        # Track cited papers for reference list
        cited_papers = set()
        
        # Add title page
        self._add_title_page(doc, title, authors, affiliation)
        
        # Add running head and page numbers to all sections
        self._add_header(doc, running_head)
        
        # Add body content
        for para_obj in content:
            text = para_obj.get("text", "")
            citations = para_obj.get("citations", [])
            
            # Replace citation placeholders with formatted citations
            formatted_text, cited_ids = self._process_citations(
                text, 
                references_metadata
            )
            cited_papers.update(cited_ids)
            
            # Add paragraph with formatting
            self._add_body_paragraph(doc, formatted_text)
        
        # Add page break before references
        doc.add_page_break()
        
        # Add reference list
        self._add_references(doc, cited_papers, references_metadata)
        
        # Save to BytesIO
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        return buffer
    
    def _set_margins(self, doc: Document):
        """Set 1-inch margins on all sides"""
        sections = doc.sections
        for section in sections:
            section.top_margin = self.margin
            section.bottom_margin = self.margin
            section.left_margin = self.margin
            section.right_margin = self.margin
    
    def _add_header(self, doc: Document, running_head: str):
        """Add running head (left) and page number (right) to header"""
        section = doc.sections[0]
        header = section.header
        
        # Create header paragraph
        header_para = header.paragraphs[0]
        header_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
        
        # Add running head (uppercase, left-aligned)
        run = header_para.add_run(running_head.upper())
        run.font.name = self.font_name
        run.font.size = self.font_size
        
        # Add tab for page number alignment
        header_para.add_run("\t")
        
        # Add page number field (right-aligned)
        self._add_page_number(header_para)
        
        # Set tab stop for right alignment
        tab_stops = header_para.paragraph_format.tab_stops
        tab_stops.add_tab_stop(Inches(6.0), WD_ALIGN_PARAGRAPH.RIGHT)
    
    def _add_page_number(self, paragraph):
        """Add page number field to paragraph"""
        run = paragraph.add_run()
        
        # Create page number field
        fldChar1 = OxmlElement('w:fldChar')
        fldChar1.set(qn('w:fldCharType'), 'begin')
        
        instrText = OxmlElement('w:instrText')
        instrText.set(qn('xml:space'), 'preserve')
        instrText.text = "PAGE"
        
        fldChar2 = OxmlElement('w:fldChar')
        fldChar2.set(qn('w:fldCharType'), 'end')
        
        run._r.append(fldChar1)
        run._r.append(instrText)
        run._r.append(fldChar2)
        
        run.font.name = self.font_name
        run.font.size = self.font_size
    
    def _add_title_page(
        self, 
        doc: Document, 
        title: str, 
        authors: List[str], 
        affiliation: str
    ):
        """Create APA-style title page (Student Paper format)"""
        # Title (centered, bold, middle of page)
        # Add some spacing from top
        for _ in range(10):
            doc.add_paragraph()
        
        # Title
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.add_run(title)
        title_run.bold = True
        title_run.font.name = self.font_name
        title_run.font.size = self.font_size
        self._set_line_spacing(title_para, self.line_spacing)
        
        # Author(s)
        for author in authors:
            author_para = doc.add_paragraph()
            author_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            author_run = author_para.add_run(author)
            author_run.font.name = self.font_name
            author_run.font.size = self.font_size
            self._set_line_spacing(author_para, self.line_spacing)
        
        # Affiliation
        affiliation_para = doc.add_paragraph()
        affiliation_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        affiliation_run = affiliation_para.add_run(affiliation)
        affiliation_run.font.name = self.font_name
        affiliation_run.font.size = self.font_size
        self._set_line_spacing(affiliation_para, self.line_spacing)
        
        # Page break after title page
        doc.add_page_break()
    
    def _add_body_paragraph(self, doc: Document, text: str):
        """Add formatted body paragraph with APA styling"""
        para = doc.add_paragraph()
        run = para.add_run(text)
        
        # Font formatting
        run.font.name = self.font_name
        run.font.size = self.font_size
        
        # Paragraph formatting
        para_format = para.paragraph_format
        para_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        para_format.first_line_indent = self.paragraph_indent
        para_format.space_before = Pt(0)
        para_format.space_after = Pt(0)
        
        # Line spacing
        self._set_line_spacing(para, self.line_spacing)
    
    def _process_citations(
        self, 
        text: str, 
        references_metadata: Dict[str, Dict]
    ) -> tuple[str, set]:
        """
        Replace citation placeholders with formatted citations
        
        Replaces {{paper_123}} with (Smith et al., 2021)
        
        Returns:
            (formatted_text, set of cited paper_ids)
        """
        cited_papers = set()
        
        # Find all citation placeholders: {{paper_id}}
        pattern = r'\{\{([^}]+)\}\}'
        
        def replace_citation(match):
            paper_id = match.group(1)
            cited_papers.add(paper_id)
            
            # Get metadata
            metadata = references_metadata.get(paper_id)
            if not metadata:
                return f"(Unknown Source)"
            
            # Generate in-text citation
            return self._format_inline_citation(metadata)
        
        formatted_text = re.sub(pattern, replace_citation, text)
        
        return formatted_text, cited_papers
    
    def _format_inline_citation(self, metadata: Dict) -> str:
        """
        Format inline citation (Author, Year)
        
        Examples:
            - Single author: (Smith, 2021)
            - Two authors: (Smith & Jones, 2021)
            - 3+ authors: (Smith et al., 2021)
        """
        authors = metadata.get("author_list", [])
        year = metadata.get("year", "n.d.")
        
        if not authors:
            return f"(Unknown, {year})"
        
        # Extract last names
        last_names = [self._extract_last_name(author) for author in authors]
        
        if len(last_names) == 1:
            author_part = last_names[0]
        elif len(last_names) == 2:
            author_part = f"{last_names[0]} & {last_names[1]}"
        else:
            author_part = f"{last_names[0]} et al."
        
        return f"({author_part}, {year})"
    
    def _extract_last_name(self, author: str) -> str:
        """Extract last name from author string"""
        author = author.strip()
        
        # If already in "LastName, FirstName" format
        if "," in author:
            return author.split(",")[0].strip()
        
        # Otherwise, assume "FirstName LastName" format
        parts = author.split()
        return parts[-1] if parts else author
    
    def _add_references(
        self, 
        doc: Document, 
        cited_papers: set, 
        references_metadata: Dict[str, Dict]
    ):
        """Add APA-formatted reference list"""
        # "References" heading (centered, bold)
        ref_heading = doc.add_paragraph()
        ref_heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ref_run = ref_heading.add_run("References")
        ref_run.bold = True
        ref_run.font.name = self.font_name
        ref_run.font.size = self.font_size
        self._set_line_spacing(ref_heading, self.line_spacing)
        
        # Get cited references and sort alphabetically by first author last name
        references = []
        for paper_id in cited_papers:
            if paper_id in references_metadata:
                metadata = references_metadata[paper_id]
                formatted_ref = self._format_reference(metadata)
                references.append(formatted_ref)
        
        references.sort()
        
        # Add each reference with hanging indent
        for reference in references:
            ref_para = doc.add_paragraph()
            ref_run = ref_para.add_run(reference)
            
            # Font
            ref_run.font.name = self.font_name
            ref_run.font.size = self.font_size
            
            # Hanging indent
            ref_format = ref_para.paragraph_format
            ref_format.left_indent = self.hanging_indent
            ref_format.first_line_indent = -self.hanging_indent
            ref_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            ref_format.space_before = Pt(0)
            ref_format.space_after = Pt(0)
            
            # Line spacing
            self._set_line_spacing(ref_para, self.line_spacing)
    
    def _format_reference(self, metadata: Dict) -> str:
        """
        Format full reference entry for reference list
        
        APA 7th Format:
        Author, A. A., & Author, B. B. (Year). Title of article. 
        Journal Name, volume(issue), pages. https://doi.org/xx.xxxx
        """
        # Authors
        authors = metadata.get("author_list", [])
        if not authors:
            author_str = "Unknown Author"
        elif len(authors) == 1:
            author_str = self._format_reference_author(authors[0])
        elif len(authors) == 2:
            author_str = f"{self._format_reference_author(authors[0])} & {self._format_reference_author(authors[1])}"
        elif len(authors) <= 20:
            formatted = [self._format_reference_author(a) for a in authors[:-1]]
            author_str = ", ".join(formatted) + f", & {self._format_reference_author(authors[-1])}"
        else:
            # 21+ authors: first 19, ellipsis, last author
            formatted = [self._format_reference_author(a) for a in authors[:19]]
            author_str = ", ".join(formatted) + f", ... {self._format_reference_author(authors[-1])}"
        
        # Year
        year = metadata.get("year", "n.d.")
        
        # Title (italicized in actual formatting, but here we use plain text)
        title = metadata.get("title", "Untitled").rstrip(".")
        
        # Publisher/Journal
        publisher = metadata.get("publisher", "")
        
        # DOI
        doi = metadata.get("doi", "")
        
        # Build reference
        parts = [f"{author_str} ({year}). {title}."]
        
        if publisher:
            parts.append(f"{publisher}.")
        
        if doi:
            parts.append(f"https://doi.org/{doi}")
        
        return " ".join(parts)
    
    def _format_reference_author(self, author: str) -> str:
        """
        Format author for reference list: LastName, F. M.
        """
        author = author.strip()
        
        # If already formatted with comma
        if "," in author:
            parts = author.split(",", 1)
            last_name = parts[0].strip()
            first_part = parts[1].strip()
            
            # Extract initials
            initials = self._extract_initials(first_part)
            return f"{last_name}, {initials}"
        
        # Otherwise split by space
        parts = author.split()
        if len(parts) == 1:
            return parts[0]
        
        last_name = parts[-1]
        first_names = parts[:-1]
        initials = " ".join([f"{name[0].upper()}." for name in first_names])
        
        return f"{last_name}, {initials}"
    
    def _extract_initials(self, name_part: str) -> str:
        """Extract initials from name part"""
        parts = name_part.replace(".", " ").split()
        return " ".join([f"{p[0].upper()}." for p in parts if p])
    
    def _set_line_spacing(self, paragraph, spacing: float):
        """Set line spacing for paragraph"""
        paragraph.paragraph_format.line_spacing = spacing


# Singleton instance
apa_export_service = APAExportService()