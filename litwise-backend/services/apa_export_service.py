"""
APA 7th Edition Document Export Service
Converts research paper content to formatted .docx files
"""

from docx import Document
from docx.document import Document as DocxDocument
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
        affiliation: str = "Independent Researcher",
        abstract: Optional[str] = None,
        keywords: Optional[List[str]] = None
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
            abstract: Optional abstract text (max 250 words recommended)
            keywords: Optional list of keywords (3-5 recommended)
        
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
        
        # Add abstract page (if provided)
        if abstract:
            self._add_abstract_page(doc, abstract, keywords)
        
        # Add body content
        for item in content:
            content_type = item.get("type", "paragraph")
            
            if content_type == "heading":
                # Handle heading content
                level = item.get("level", 1)
                heading_text = item.get("text", "")
                self._add_heading(doc, level, heading_text)
                
            elif content_type == "paragraph":
                # Handle paragraph content
                text = item.get("text", "")
                citations = item.get("citations", [])
                
                # Replace citation placeholders with formatted citations
                formatted_text, cited_ids = self._process_citations(
                    text, 
                    references_metadata
                )
                cited_papers.update(cited_ids)
                
                # Add paragraph with formatting
                self._add_body_paragraph(doc, formatted_text)
                
            elif content_type == "table":
                # Handle table content
                number = item.get("number", 1)
                title = item.get("title", "")
                rows = item.get("rows", [])
                header_rows = item.get("header_rows", 1)
                note = item.get("note", None)
                self._add_table(doc, number, title, rows, header_rows, note)
                
            elif content_type == "figure":
                # Handle figure content
                number = item.get("number", 1)
                file_id = item.get("file_id", "")
                filename = item.get("filename", "")
                caption = item.get("caption", "")
                alt_text = item.get("alt_text", "")
                width_percent = item.get("width_percent", 100)
                self._add_figure(doc, number, file_id, filename, caption, alt_text, width_percent)
        
        # Add page break before references
        doc.add_page_break()
        
        # Add reference list
        self._add_references(doc, cited_papers, references_metadata)
        
        # Save to BytesIO
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        return buffer
    
    def _set_margins(self, doc: DocxDocument):
        """Set 1-inch margins on all sides"""
        sections = doc.sections
        for section in sections:
            section.top_margin = self.margin
            section.bottom_margin = self.margin
            section.left_margin = self.margin
            section.right_margin = self.margin
    
    def _add_header(self, doc: DocxDocument, running_head: str):
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
        doc: DocxDocument, 
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
    
    def _add_abstract_page(
        self, 
        doc: DocxDocument, 
        abstract: str, 
        keywords: Optional[List[str]] = None
    ):
        """
        Create APA-style abstract page (Page 2)
        
        APA 7th Edition Requirements:
        - Starts on Page 2 (separate page after title page)
        - Label "Abstract" centered and bolded at top
        - Abstract text is NOT indented (flush left)
        - Single block paragraph, double-spaced
        - Max 250 words recommended
        - Keywords appear on same page, one line below abstract
        - Keywords format: "Keywords: word1, word2, word3"
        
        Implementation Notes:
        - Uses APA spacing (double-spaced throughout)
        - Keywords label is italicized per APA 7th guidelines
        - Keywords are lowercase unless proper nouns
        - No closing punctuation after keywords
        """
        # Abstract heading (centered, bold)
        abstract_heading = doc.add_paragraph()
        abstract_heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        heading_run = abstract_heading.add_run("Abstract")
        heading_run.bold = True
        heading_run.font.name = self.font_name
        heading_run.font.size = self.font_size
        self._set_line_spacing(abstract_heading, self.line_spacing)
        
        # Abstract text (flush left, NO indent)
        abstract_para = doc.add_paragraph()
        abstract_run = abstract_para.add_run(abstract)
        abstract_run.font.name = self.font_name
        abstract_run.font.size = self.font_size
        
        # Paragraph formatting - NO first line indent for abstract
        abstract_format = abstract_para.paragraph_format
        abstract_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        abstract_format.first_line_indent = Inches(0)  # Flush left, no indent
        abstract_format.space_before = Pt(0)
        abstract_format.space_after = Pt(0)
        self._set_line_spacing(abstract_para, self.line_spacing)
        
        # Keywords (if provided)
        if keywords and len(keywords) > 0:
            keywords_para = doc.add_paragraph()
            
            # Keywords label (italicized, indented)
            keywords_format = keywords_para.paragraph_format
            keywords_format.first_line_indent = self.paragraph_indent  # 0.5" indent
            keywords_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            keywords_format.space_before = Pt(0)
            keywords_format.space_after = Pt(0)
            self._set_line_spacing(keywords_para, self.line_spacing)
            
            # Add "Keywords:" label (italicized)
            label_run = keywords_para.add_run("Keywords:")
            label_run.italic = True
            label_run.font.name = self.font_name
            label_run.font.size = self.font_size
            
            # Add keywords text (lowercase, comma-separated, no period at end)
            keywords_text = ", ".join([kw.lower() if not kw[0].isupper() or len(kw) < 3 else kw for kw in keywords])
            keywords_run = keywords_para.add_run(f" {keywords_text}")
            keywords_run.font.name = self.font_name
            keywords_run.font.size = self.font_size
        
        # Page break after abstract page (before body content)
        doc.add_page_break()
    
    def _add_body_paragraph(self, doc: DocxDocument, text: str):
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
    
    def _add_heading(self, doc: DocxDocument, level: int, text: str):
        """
        Add APA 7th Edition formatted heading
        
        APA 7th Edition Heading Levels:
        
        Level 1: Centered, Bold, Title Case
                 Use for major sections (e.g., Method, Results, Discussion)
        
        Level 2: Left-Aligned, Bold, Title Case
                 Use for subsections within Level 1 sections
        
        Level 3: Left-Aligned, Bold Italic, Title Case
                 Use for sub-subsections within Level 2
        
        Level 4: Indented, Bold, Title Case, Ending with Period
                 Text begins on same line after the heading
        
        Level 5: Indented, Bold Italic, Title Case, Ending with Period
                 Text begins on same line after the heading
        
        Args:
            doc: DocxDocument object
            level: Heading level (1-5)
            text: Heading text
        
        Implementation Notes:
        - Levels 1-3: Standalone headings (text on next line)
        - Levels 4-5: Run-in headings (text continues on same line)
        - All headings use double spacing consistent with body text
        - Title case is applied automatically by this method
        """
        # Apply title case to heading text
        title_cased_text = self._to_title_case(text)
        
        if level == 1:
            # Level 1: Centered, Bold, Title Case
            para = doc.add_paragraph()
            run = para.add_run(title_cased_text)
            run.bold = True
            run.font.name = self.font_name
            run.font.size = self.font_size
            
            para_format = para.paragraph_format
            para_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para_format.space_before = Pt(0)
            para_format.space_after = Pt(0)
            self._set_line_spacing(para, self.line_spacing)
            
        elif level == 2:
            # Level 2: Left-Aligned, Bold, Title Case
            para = doc.add_paragraph()
            run = para.add_run(title_cased_text)
            run.bold = True
            run.font.name = self.font_name
            run.font.size = self.font_size
            
            para_format = para.paragraph_format
            para_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            para_format.space_before = Pt(0)
            para_format.space_after = Pt(0)
            self._set_line_spacing(para, self.line_spacing)
            
        elif level == 3:
            # Level 3: Left-Aligned, Bold Italic, Title Case
            para = doc.add_paragraph()
            run = para.add_run(title_cased_text)
            run.bold = True
            run.italic = True
            run.font.name = self.font_name
            run.font.size = self.font_size
            
            para_format = para.paragraph_format
            para_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            para_format.space_before = Pt(0)
            para_format.space_after = Pt(0)
            self._set_line_spacing(para, self.line_spacing)
            
        elif level == 4:
            # Level 4: Indented, Bold, Title Case, Ending with Period
            # Run-in heading: text continues on same line
            para = doc.add_paragraph()
            
            # Add heading with period
            heading_run = para.add_run(f"{title_cased_text}. ")
            heading_run.bold = True
            heading_run.font.name = self.font_name
            heading_run.font.size = self.font_size
            
            # Note: The actual paragraph text will be added separately
            # This creates the heading structure; content follows in generate_document
            
            para_format = para.paragraph_format
            para_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            para_format.first_line_indent = self.paragraph_indent
            para_format.space_before = Pt(0)
            para_format.space_after = Pt(0)
            self._set_line_spacing(para, self.line_spacing)
            
        elif level == 5:
            # Level 5: Indented, Bold Italic, Title Case, Ending with Period
            # Run-in heading: text continues on same line
            para = doc.add_paragraph()
            
            # Add heading with period
            heading_run = para.add_run(f"{title_cased_text}. ")
            heading_run.bold = True
            heading_run.italic = True
            heading_run.font.name = self.font_name
            heading_run.font.size = self.font_size
            
            # Note: The actual paragraph text will be added separately
            # This creates the heading structure; content follows in generate_document
            
            para_format = para.paragraph_format
            para_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            para_format.first_line_indent = self.paragraph_indent
            para_format.space_before = Pt(0)
            para_format.space_after = Pt(0)
            self._set_line_spacing(para, self.line_spacing)
    
    def _to_title_case(self, text: str) -> str:
        """
        Convert text to Title Case for APA headings
        
        APA title case rules:
        - Capitalize major words (nouns, verbs, adjectives, adverbs, pronouns)
        - Lowercase articles (a, an, the), coordinating conjunctions (and, but, or)
        - Lowercase prepositions of 3 letters or fewer (of, to, in, for, on, at, by)
        - Always capitalize first and last word
        - Capitalize words of 4 letters or more
        
        This is a simplified implementation that capitalizes all words except
        common short words that should be lowercase (unless first/last).
        """
        # Words that should be lowercase in title case (unless first/last word)
        lowercase_words = {
            'a', 'an', 'the',                    # Articles
            'and', 'but', 'or', 'nor', 'for',   # Conjunctions
            'at', 'by', 'in', 'of', 'on', 'to', 'up', 'as', 'is'  # Short prepositions
        }
        
        words = text.split()
        if not words:
            return text
        
        title_cased = []
        for i, word in enumerate(words):
            # Always capitalize first and last word
            if i == 0 or i == len(words) - 1:
                title_cased.append(word.capitalize())
            # Lowercase specific short words in the middle
            elif word.lower() in lowercase_words:
                title_cased.append(word.lower())
            # Capitalize all other words
            else:
                title_cased.append(word.capitalize())
        
        return ' '.join(title_cased)
    
    def _add_table(
        self,
        doc: DocxDocument,
        number: int,
        title: str,
        rows: List[List[str]],
        header_rows: int = 1,
        note: Optional[str] = None
    ):
        """
        Add APA 7th Edition formatted table to document
        
        APA 7th Edition Table Requirements:
        - Numbered sequentially (Table 1, Table 2, etc.)
        - Title is italicized and placed above table
        - Double-spaced
        - Minimal lines: top border, bottom border, line under header
        - No vertical lines (clean columnar layout)
        - All content left-aligned
        - Optional note below table starting with "Note."
        
        Table Structure:
        - First `header_rows` rows are formatted as headers (bold, top border)
        - Data rows are left-aligned
        - Bottom border closes the table
        
        Args:
            doc: DocxDocument object
            number: Table number for ordering
            title: Table title (will be italicized)
            rows: List of rows, where each row is list of cell strings
            header_rows: Number of header rows (usually 1)
            note: Optional table note/footer
        """
        # Add table number and title (italicized)
        title_para = doc.add_paragraph()
        title_run = title_para.add_run(f"Table {number}.")
        title_run.bold = True
        title_run.font.name = self.font_name
        title_run.font.size = self.font_size
        
        # Add space then italicized title
        title_para.add_run(" ")
        title_text_run = title_para.add_run(title)
        title_text_run.italic = True
        title_text_run.font.name = self.font_name
        title_text_run.font.size = self.font_size
        
        # Paragraph formatting
        title_format = title_para.paragraph_format
        title_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        title_format.space_before = Pt(12)  # Space above table
        title_format.space_after = Pt(0)
        self._set_line_spacing(title_para, self.line_spacing)
        
        # Create table (rows x columns)
        if rows:
            num_cols = len(rows[0])
            table = doc.add_table(rows=len(rows), cols=num_cols)
            table.style = 'Light Grid Accent 1'  # Professional table style
            
            # Configure table borders - APA style (top, bottom, under header only)
            # Set table properties
            tblPr = table._element.tblPr
            
            # Create table borders
            tblBorders = OxmlElement('w:tblBorders')
            
            # Top border (solid black)
            top = OxmlElement('w:top')
            top.set(qn('w:val'), 'single')
            top.set(qn('w:sz'), '12')
            top.set(qn('w:space'), '0')
            top.set(qn('w:color'), '000000')
            tblBorders.append(top)
            
            # Bottom border (solid black)
            bottom = OxmlElement('w:bottom')
            bottom.set(qn('w:val'), 'single')
            bottom.set(qn('w:sz'), '12')
            bottom.set(qn('w:space'), '0')
            bottom.set(qn('w:color'), '000000')
            tblBorders.append(bottom)
            
            # Left border (none)
            left = OxmlElement('w:left')
            left.set(qn('w:val'), 'none')
            tblBorders.append(left)
            
            # Right border (none)
            right = OxmlElement('w:right')
            right.set(qn('w:val'), 'none')
            tblBorders.append(right)
            
            # Inside horizontal (between rows)
            insideH = OxmlElement('w:insideH')
            insideH.set(qn('w:val'), 'none')
            tblBorders.append(insideH)
            
            # Inside vertical (between columns - none for clean look)
            insideV = OxmlElement('w:insideV')
            insideV.set(qn('w:val'), 'none')
            tblBorders.append(insideV)
            
            tblPr.append(tblBorders)
            
            # Format header row with top border
            for row_idx, row in enumerate(table.rows):
                for cell_idx, cell in enumerate(row.cells):
                    # Get cell content from data
                    if row_idx < len(rows) and cell_idx < len(rows[row_idx]):
                        cell_text = rows[row_idx][cell_idx]
                    else:
                        cell_text = ""
                    
                    # Clear default paragraph
                    for paragraph in cell.paragraphs:
                        paragraph.clear()
                    
                    # Add formatted text to cell
                    para = cell.paragraphs[0]
                    run = para.add_run(cell_text)
                    run.font.name = self.font_name
                    run.font.size = self.font_size
                    
                    # Format header row (bold)
                    if row_idx < header_rows:
                        run.bold = True
                    
                    # Alignment
                    para.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    para_format = para.paragraph_format
                    para_format.space_before = Pt(0)
                    para_format.space_after = Pt(0)
                    self._set_line_spacing(para, self.line_spacing)
            
            # Add line under header row
            if header_rows > 0:
                header_row = table.rows[header_rows - 1]
                for cell in header_row.cells:
                    tcPr = cell._element.tcPr
                    if tcPr is None:
                        tcPr = OxmlElement('w:tcPr')
                        cell._element.insert(0, tcPr)
                    
                    # Add bottom border to header cells
                    tcBorders = OxmlElement('w:tcBorders')
                    tcBottom = OxmlElement('w:bottom')
                    tcBottom.set(qn('w:val'), 'single')
                    tcBottom.set(qn('w:sz'), '12')
                    tcBottom.set(qn('w:color'), '000000')
                    tcBorders.append(tcBottom)
                    tcPr.append(tcBorders)
        
        # Add table note if provided
        if note:
            note_para = doc.add_paragraph()
            note_run = note_para.add_run(note)
            note_run.italic = True
            note_run.font.name = self.font_name
            note_run.font.size = Pt(11)  # Slightly smaller for notes
            
            note_format = note_para.paragraph_format
            note_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            note_format.space_before = Pt(6)
            note_format.space_after = Pt(0)
            note_format.first_line_indent = Inches(0)  # No indent for note
            self._set_line_spacing(note_para, self.line_spacing)
    
    def _add_figure(
        self,
        doc: DocxDocument,
        number: int,
        file_id: str,
        filename: str,
        caption: str,
        alt_text: Optional[str] = None,
        width_percent: int = 100
    ):
        """
        Add APA 7th Edition formatted figure to document
        
        APA 7th Edition Figure Requirements:
        - Numbered sequentially (Figure 1, Figure 2, etc.)
        - Placed near relevant text in document
        - Caption below figure (starts with 'Figure #.')
        - Caption in sentence case (only first word and proper nouns capitalized)
        - Double-spaced
        - All figures must be referenced in text
        
        Figure Structure:
        - Image is embedded with APA sizing
        - Caption paragraph follows with: Figure #. Caption text.
        - Spacing maintained for professional appearance
        
        Args:
            doc: DocxDocument object
            number: Figure number for ordering
            file_id: Unique file ID from media upload
            filename: Original filename
            caption: Figure caption (APA sentence case)
            alt_text: Alternative text for accessibility
            width_percent: Width as percentage of page (10-100)
        """
        try:
            # Construct path to uploaded figure
            # The figure should be saved in uploads/figures/ directory
            import os
            from pathlib import Path
            
            upload_dir = Path("uploads/figures")
            figure_path = None
            
            # Find figure file matching the file_id
            if upload_dir.exists():
                for filepath in upload_dir.iterdir():
                    if filepath.name.startswith(file_id):
                        figure_path = str(filepath)
                        break
            
            if not figure_path or not os.path.exists(figure_path):
                # Fallback: try direct path construction
                figure_path = f"uploads/figures/{file_id}{Path(filename).suffix}"
            
            # Add figure with spacing
            # Top spacing
            spacing_para = doc.add_paragraph()
            spacing_para.paragraph_format.space_before = Pt(12)
            spacing_para.paragraph_format.space_after = Pt(0)
            
            # Add figure image
            fig_para = doc.add_paragraph()
            fig_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Calculate width based on percentage (standard Word page is 6.5" wide with 1" margins)
            # At 100%, use 6 inches; adjust based on percentage
            max_width = Inches(6.0)
            actual_width = Inches(6.0 * (width_percent / 100))
            
            try:
                # Add image only if file exists
                if os.path.exists(figure_path):
                    run = fig_para.add_run()
                    run.add_picture(figure_path, width=actual_width)
                else:
                    # Placeholder if image not found
                    placeholder_run = fig_para.add_run(f"[Figure {number}: {filename}]")
                    placeholder_run.font.size = Pt(10)
                    placeholder_run.font.color.rgb = RGBColor(128, 128, 128)
            except Exception as e:
                # Fallback placeholder
                placeholder_run = fig_para.add_run(f"[Image not available: {filename}]")
                placeholder_run.font.size = Pt(10)
                placeholder_run.font.color.rgb = RGBColor(128, 128, 128)
            
            # Figure formatting
            fig_format = fig_para.paragraph_format
            fig_format.space_before = Pt(0)
            fig_format.space_after = Pt(6)  # Space before caption
            self._set_line_spacing(fig_para, self.line_spacing)
            
            # Add figure caption below image
            # Caption format: "Figure #. Caption text."
            caption_para = doc.add_paragraph()
            
            # Figure number (bold)
            figure_num_run = caption_para.add_run(f"Figure {number}.")
            figure_num_run.bold = True
            figure_num_run.font.name = self.font_name
            figure_num_run.font.size = self.font_size
            
            # Space and caption text
            caption_para.add_run(" ")
            caption_text_run = caption_para.add_run(caption)
            caption_text_run.font.name = self.font_name
            caption_text_run.font.size = self.font_size
            
            # Caption formatting (centered and italicized per some APA styles)
            caption_format = caption_para.paragraph_format
            caption_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            caption_format.space_before = Pt(0)
            caption_format.space_after = Pt(12)  # Space after caption
            self._set_line_spacing(caption_para, self.line_spacing)
            
        except Exception as e:
            # Graceful degradation - add text placeholder
            error_para = doc.add_paragraph()
            error_run = error_para.add_run(f"[Figure {number}: Unable to embed image - {str(e)[:50]}...]")
            error_run.font.color.rgb = RGBColor(192, 0, 0)  # Red for error
            error_para.paragraph_format.space_before = Pt(12)
            error_para.paragraph_format.space_after = Pt(12)
    
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
        doc: DocxDocument, 
        cited_papers: set, 
        references_metadata: Dict[str, Dict]
    ):
        """
        Add APA-formatted reference list with proper formatting
        
        APA 7th Edition Requirements:
        - Alphabetically sorted by first author's last name
        - Hanging indent (0.5 inches)
        - Journal names and volume numbers italicized
        - DOIs as blue hyperlinks
        - Proper punctuation and spacing
        """
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
                # Store metadata with sort key
                first_author = metadata.get("author_list", ["Unknown"])[0]
                sort_key = self._extract_last_name(first_author)
                references.append((sort_key, metadata))
        
        references.sort(key=lambda x: x[0].lower())
        
        # Add each reference with rich text formatting
        for _, metadata in references:
            self._add_formatted_reference(doc, metadata)
    
    def _add_formatted_reference(self, doc: DocxDocument, metadata: Dict):
        """
        Add a single formatted reference with rich text (italics, hyperlinks)
        
        APA 7th Edition Format Examples:
        
        Journal Article:
        Author, A. A., & Author, B. B. (Year). Title of article. Journal Name, 
        volume(issue), pages. https://doi.org/xx.xxxx
        
        Book:
        Author, A. A. (Year). Title of book. Publisher.
        
        Formatting Rules:
        - Journal name: Italicized
        - Volume number: Italicized
        - Issue number: In parentheses, NOT italicized
        - Article title: Sentence case, NOT italicized
        - DOI: Clickable blue hyperlink
        """
        ref_para = doc.add_paragraph()
        
        # Paragraph formatting (hanging indent)
        ref_format = ref_para.paragraph_format
        ref_format.left_indent = self.hanging_indent
        ref_format.first_line_indent = -self.hanging_indent
        ref_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        ref_format.space_before = Pt(0)
        ref_format.space_after = Pt(0)
        self._set_line_spacing(ref_para, self.line_spacing)
        
        # 1. Authors
        author_str = self._format_authors_for_reference(metadata.get("author_list", []))
        run = ref_para.add_run(author_str)
        run.font.name = self.font_name
        run.font.size = self.font_size
        
        # 2. Year
        year = metadata.get("year", "n.d.")
        run = ref_para.add_run(f" ({year}). ")
        run.font.name = self.font_name
        run.font.size = self.font_size
        
        # 3. Title (sentence case, NOT italicized for articles)
        title = metadata.get("title", "Untitled").rstrip(".")
        # Convert to sentence case if needed
        title = self._to_sentence_case(title)
        
        publication_type = metadata.get("publication_type", "journal")
        
        if publication_type == "book":
            # Book titles are italicized
            run = ref_para.add_run(title)
            run.font.name = self.font_name
            run.font.size = self.font_size
            run.italic = True
        else:
            # Article titles are NOT italicized
            run = ref_para.add_run(title)
            run.font.name = self.font_name
            run.font.size = self.font_size
        
        run = ref_para.add_run(". ")
        run.font.name = self.font_name
        run.font.size = self.font_size
        
        # 4. Journal name (italicized) and volume/issue/pages
        publisher = metadata.get("publisher", "")
        volume = metadata.get("volume", "")
        issue = metadata.get("issue", "")
        pages = metadata.get("pages", "")
        
        if publisher:
            # Journal/Publisher name (italicized)
            run = ref_para.add_run(publisher)
            run.font.name = self.font_name
            run.font.size = self.font_size
            run.italic = True
            
            # Volume number (italicized) and issue (not italicized)
            if volume:
                run = ref_para.add_run(", ")
                run.font.name = self.font_name
                run.font.size = self.font_size
                
                # Volume (italicized)
                run = ref_para.add_run(volume)
                run.font.name = self.font_name
                run.font.size = self.font_size
                run.italic = True
                
                # Issue (in parentheses, NOT italicized)
                if issue:
                    run = ref_para.add_run(f"({issue})")
                    run.font.name = self.font_name
                    run.font.size = self.font_size
                
                # Pages
                if pages:
                    run = ref_para.add_run(f", {pages}")
                    run.font.name = self.font_name
                    run.font.size = self.font_size
            
            run = ref_para.add_run(". ")
            run.font.name = self.font_name
            run.font.size = self.font_size
        
        # 5. DOI as hyperlink (blue, underlined)
        doi = metadata.get("doi", "")
        if doi:
            # Clean DOI (remove any existing URL prefix)
            doi_clean = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
            doi_url = f"https://doi.org/{doi_clean}"
            
            # Add hyperlink
            self._add_hyperlink(ref_para, doi_url, doi_url)
    
    def _add_hyperlink(self, paragraph, url: str, text: str):
        """
        Add a clickable hyperlink to a paragraph
        
        Creates a blue, underlined hyperlink in APA style
        """
        # Get the paragraph's XML element
        p = paragraph._element
        
        # Create a new hyperlink element
        hyperlink = OxmlElement('w:hyperlink')
        
        # Create relationship ID for the hyperlink
        part = paragraph.part
        r_id = part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
        hyperlink.set(qn('r:id'), r_id)
        
        # Create run with hyperlink text
        new_run = OxmlElement('w:r')
        rPr = OxmlElement('w:rPr')
        
        # Set font
        rFonts = OxmlElement('w:rFonts')
        rFonts.set(qn('w:ascii'), self.font_name)
        rFonts.set(qn('w:hAnsi'), self.font_name)
        rPr.append(rFonts)
        
        # Set size
        sz = OxmlElement('w:sz')
        sz.set(qn('w:val'), str(int(self.font_size.pt * 2)))  # Half-points
        rPr.append(sz)
        
        # Set color (blue)
        color = OxmlElement('w:color')
        color.set(qn('w:val'), '0563C1')  # APA blue color
        rPr.append(color)
        
        # Set underline
        u = OxmlElement('w:u')
        u.set(qn('w:val'), 'single')
        rPr.append(u)
        
        new_run.append(rPr)
        
        # Add text
        t = OxmlElement('w:t')
        t.text = text
        new_run.append(t)
        
        hyperlink.append(new_run)
        p.append(hyperlink)
    
    def _format_authors_for_reference(self, authors: List[str]) -> str:
        """
        Format authors for reference list following APA 7th Edition rules
        
        Rules:
        - 1 author: Author, A. A.
        - 2 authors: Author, A. A., & Author, B. B.
        - 3-20 authors: Author, A. A., Author, B. B., & Author, C. C.
        - 21+ authors: First 19 authors, ..., Last Author
        """
        if not authors:
            return "Unknown Author"
        
        if len(authors) == 1:
            return self._format_reference_author(authors[0])
        
        if len(authors) == 2:
            return f"{self._format_reference_author(authors[0])} & {self._format_reference_author(authors[1])}"
        
        if len(authors) <= 20:
            # 3-20 authors: list all with & before last
            formatted = [self._format_reference_author(a) for a in authors[:-1]]
            return ", ".join(formatted) + f", & {self._format_reference_author(authors[-1])}"
        
        # 21+ authors: first 19, ellipsis, last author
        formatted = [self._format_reference_author(a) for a in authors[:19]]
        return ", ".join(formatted) + f", ... {self._format_reference_author(authors[-1])}"
    
    def _to_sentence_case(self, text: str) -> str:
        """
        Convert title to sentence case for APA references
        
        Rules:
        - First word capitalized
        - First word after colon capitalized
        - Proper nouns remain capitalized (we preserve existing capitalization for words with internal caps)
        """
        if not text:
            return text
        
        # Don't modify if already in sentence case or has proper formatting
        words = text.split()
        if len(words) == 0:
            return text
        
        # Capitalize first word
        result = []
        for i, word in enumerate(words):
            if i == 0:
                # First word - capitalize
                result.append(word[0].upper() + word[1:] if len(word) > 1 else word.upper())
            elif ':' in result[-1]:
                # Word after colon - capitalize
                result.append(word[0].upper() + word[1:] if len(word) > 1 else word.upper())
            else:
                # Keep existing capitalization (preserves proper nouns)
                result.append(word)
        
        return ' '.join(result)
    
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