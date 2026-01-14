"""
Multi-Modal Content Extractor for PDFs
Extracts: Images, Tables, Figures with page tracking
Uses: PyMuPDF (fitz) for images, tables (find_tables()), and equations
Features: Layout-aware parsing, page-spanning table merging, smart chunking
"""

import fitz  # PyMuPDF
import base64
import io
from typing import List, Dict
from PIL import Image
import hashlib
import re
import logging
import os
from dotenv import load_dotenv
load_dotenv()


logger = logging.getLogger(__name__)

class MultiModalExtractor:
    """Extract multi-modal content (images, tables) from PDF files with layout awareness."""
    
    def __init__(self):
        self.min_image_size = 50  # Minimum size in bytes to consider an image valid
        self.min_table_rows = 1  # Minimum number of rows (changed from 2 to 1 to capture all tables)
        
        # ✨ NEW: Initialize layout-aware parser
        from workflow.layout_aware_parser import layout_parser
        self.layout_parser = layout_parser
        
    def extract_images(self, pdf_path: str) -> List[Dict]:
        """Extract images from PDF with metadata.
        Returns:
        List of dicts with: page, image_bytes, widtg, height, format, hash
        """
        print(f"🌄 Starting image extraction from {pdf_path}")
        images = []
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)
                
                for img_index, img_info in enumerate(image_list):
                    try:
                        xref = img_info[0] # xref of the image
                        base_image = doc.extract_image(xref)
                        
                        if not base_image:
                            continue
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        # Open with PIL to get dimensions and validate
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        width, height = pil_image.size
                        
                        # Filter small images (likely logos/icons)
                        if width < self.min_image_size or height < self.min_image_size:
                            continue
                        
                        # Create content hash for deduplication
                        content_hash = hashlib.md5(image_bytes).hexdigest()
                        
                        # Check if already extracted (PDFs often deduplicate images)
                        if any(img["hash"] == content_hash for img in images):
                            continue # Skip duplicates
                        
                        # Convert to base64 for easier transport/storage
                        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                        
                        images.append({
                            'page': page_num + 1,
                            'image_index': img_index,
                            'image_bytes': image_bytes,
                            'image_base64': image_base64,
                            'width': width,
                            'height': height,
                            'format': image_ext,
                            'hash': content_hash,
                            'size_kb': len(image_bytes) / 1024
                        })
                        
                    except Exception as img_e:
                        print(f"⚠️ Failed to extract image {img_index} from page {page_num + 1}: {img_e}")
                        continue
            doc.close()
            print(f"✅ Extracted {len(images)} images from {pdf_path}")
            return images
        
        except Exception as e:
            print(f"❌ Failed to extract images from {pdf_path}: {e}")
            return []
        
    def extract_tables(self, pdf_path: str, page_info: List[Dict] = None) -> List[Dict]:
        """
        Extract tables from PDF using PyMuPDF's find_tables() + fallback markdown parsing.
        
        ✨ FEATURES:
        - Automatic table detection using PyMuPDF's find_tables() method (catches structured tables with borders)
        - FALLBACK: Extract tables from markdown content (catches tables without visible borders)
        - Merges tables that span across pages
        - Chunks large tables (>30 rows) with repeated headers
        - Enriches metadata for better retrieval
        
        PyMuPDF's find_tables() is limited - only detects tables with visible borders.
        The markdown fallback catches tables rendered without borders (common in financial reports).
        
        Args:
            pdf_path: Path to PDF file
            page_info: Optional page information from PDF extraction
        
        Returns:
            List of dicts with: page, headers, rows, row_count, col_count, 
            markdown_table (structured), text_representation (fallback)
        """
        logger.info(f"📊 Starting layout-aware table extraction from: {pdf_path}")
        print(f"📊 Starting layout-aware table extraction from: {pdf_path}")
        
        tables = []
        seen_tables = set()  # Track by hash to avoid duplicates
        
        try:
            # STEP 1: Try PyMuPDF find_tables() method (catches border-based tables)
            logger.info("📊 Extracting tables using PyMuPDF find_tables()...")
            print("📊 Extracting tables using PyMuPDF find_tables().")
            
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                try:
                    table_finder = page.find_tables()
                    
                    if table_finder and table_finder.tables:
                        logger.info(f"   Found {len(table_finder.tables)} tables on page {page_num + 1}")
                        
                        for table_index, table in enumerate(table_finder.tables):
                            try:
                                # Extract table to markdown format
                                markdown_table = table.to_markdown()
                                
                                # Parse markdown into structured format
                                structured_table = self._parse_markdown_table(markdown_table, len(tables))
                                
                                if structured_table:
                                    # Add page number
                                    structured_table['page'] = page_num + 1
                                    
                                    # Check for duplicates
                                    table_hash = hashlib.md5(markdown_table.encode()).hexdigest()
                                    if table_hash not in seen_tables:
                                        # Filter out tiny tables (likely artifacts)
                                        if len(structured_table['rows']) >= self.min_table_rows:
                                            tables.append(structured_table)
                                            seen_tables.add(table_hash)
                                            print(f"   ✅ Page {page_num + 1}, Table {table_index + 1}: {len(structured_table['rows'])} rows × {len(structured_table['headers'])} cols")
                                
                            except Exception as e:
                                logger.warning(f"Failed to extract table {table_index} on page {page_num + 1}: {e}")
                                continue
                                
                except Exception as e:
                    # Some pages may not have tables or find_tables() may fail
                    logger.debug(f"No tables found on page {page_num + 1}: {e}")
                    continue
            
            doc.close()
            
            print(f"📊 Found {len(tables)} tables using PyMuPDF find_tables()")
            
            # STEP 2: FALLBACK - Extract tables from markdown (catches tables without borders)
            logger.info("🔄 FALLBACK: Extracting tables from markdown content...")
            print("🔄 FALLBACK: Extracting tables from markdown content (for border-less tables)...")
            
            markdown_content = self.extract_full_markdown(pdf_path)
            if markdown_content:
                markdown_tables = self._extract_tables_from_markdown(markdown_content)
                
                # Add markdown-extracted tables that aren't duplicates
                for md_table in markdown_tables:
                    md_table_hash = hashlib.md5(md_table['markdown_table'].encode()).hexdigest()
                    if md_table_hash not in seen_tables:
                        tables.append(md_table)
                        seen_tables.add(md_table_hash)
                        print(f"   ✅ Found table in markdown: {md_table['row_count']} rows × {md_table['col_count']} cols")
                
                print(f"📊 Extracted {len(markdown_tables)} additional tables from markdown (total: {len(tables)})")
            
            logger.info(f"✅ Extracted {len(tables)} tables total from {pdf_path}")
            
            # STEP 3: Apply layout-aware processing
            print(f"🔄 Applying layout-aware processing...")
            
            # Merge page-spanning tables
            if page_info:
                tables = self.layout_parser.merge_page_spanning_tables(tables, page_info)
                print(f"   ✅ Merged page-spanning tables: {len(tables)} tables after merge")
            else:
                logger.warning("No page_info provided, skipping page-span detection")
            
            # Chunk large tables with header repetition
            original_count = len(tables)
            tables = self.layout_parser.chunk_large_tables(tables, max_rows_per_chunk=30)
            print(f"   ✅ Chunked large tables: {original_count} → {len(tables)} chunks")
            
            # Enrich metadata for better retrieval
            tables = [self.layout_parser.enrich_table_metadata(t) for t in tables]
            print(f"   ✅ Enriched metadata for all tables")
            
            print(f"✅ Layout-aware processing complete: {len(tables)} final table chunks")
            
            return tables
        
        except ImportError:
            logger.error("PyMuPDF not installed. Install with: pip install pymupdf")
            print("❌ PyMuPDF not installed. Falling back to empty table list.")
            print("   Install with: pip install pymupdf")
            return []
        
        except Exception as e:
            logger.error(f"Failed to extract tables with PyMuPDF: {e}")
            print(f"❌ Failed to extract tables with PyMuPDF: {e}")
            return []
    
    def _extract_tables_from_markdown(self, markdown_content: str) -> List[Dict]:
        """
        Extract tables from markdown content using regex pattern matching.
        
        FALLBACK method for PDFs that don't have visible table borders.
        Many PDFs (especially financial reports) render tables without borders,
        but pymupdf4llm converts them to markdown tables.
        
        Looks for markdown table patterns:
        | Header 1 | Header 2 |
        |----------|----------|
        | Value 1  | Value 2  |
        
        Args:
            markdown_content: Full markdown text extracted from PDF
        
        Returns:
            List of extracted table dicts in same format as PyMuPDF tables
        """
        logger.info("🔍 Extracting tables from markdown content...")
        tables = []
        
        if not markdown_content:
            return tables
        
        # Split content into lines
        lines = markdown_content.split('\n')
        
        current_table_lines = []
        table_start_idx = 0
        
        for idx, line in enumerate(lines):
            # Check if line is a table row (contains pipes)
            if '|' in line:
                # This might be a table header, separator, or data row
                if not current_table_lines:
                    table_start_idx = idx
                current_table_lines.append(line)
            else:
                # End of potential table
                if current_table_lines:
                    # Try to parse accumulated lines as a table
                    potential_table = '\n'.join(current_table_lines).strip()
                    
                    if self._is_valid_markdown_table(potential_table):
                        # Try to parse into structured format
                        structured = self._parse_markdown_table(potential_table, len(tables))
                        
                        if structured and (structured['row_count'] > 0 or structured['col_count'] >= 2):
                            # Try to detect page number from context
                            # Find the closest page marker in markdown before this table
                            page_num = 1
                            for back_idx in range(table_start_idx - 1, max(0, table_start_idx - 50), -1):
                                if '# Page' in lines[back_idx] or '## Page' in lines[back_idx]:
                                    try:
                                        page_str = lines[back_idx].split('Page ')[-1]
                                        page_num = int(page_str.split()[0])
                                        break
                                    except:
                                        pass
                            
                            structured['page'] = page_num
                            tables.append(structured)
                            logger.info(f"✅ Markdown table extracted: {structured['row_count']} rows × {structured['col_count']} cols on page {page_num}")
                    
                    current_table_lines = []
        
        # Don't forget the last potential table
        if current_table_lines:
            potential_table = '\n'.join(current_table_lines).strip()
            
            if self._is_valid_markdown_table(potential_table):
                structured = self._parse_markdown_table(potential_table, len(tables))
                
                if structured and (structured['row_count'] > 0 or structured['col_count'] >= 2):
                    page_num = 1
                    for back_idx in range(len(lines) - 1, max(0, len(lines) - 50), -1):
                        if '# Page' in lines[back_idx] or '## Page' in lines[back_idx]:
                            try:
                                page_str = lines[back_idx].split('Page ')[-1]
                                page_num = int(page_str.split()[0])
                                break
                            except:
                                pass
                    
                    structured['page'] = page_num
                    tables.append(structured)
                    logger.info(f"✅ Markdown table extracted: {structured['row_count']} rows × {structured['col_count']} cols on page {page_num}")
        
        logger.info(f"✅ Extracted {len(tables)} tables from markdown content")
        return tables
    
    def _is_valid_markdown_table(self, text: str) -> bool:
        """
        Validate if text is a markdown table.
        
        Requirements:
        - At least 2 lines (header + separator)
        - First line has pipes with content
        - Second line has pipes with dashes/colons (separator)
        
        Returns:
            True if valid markdown table, False otherwise
        """
        lines = text.strip().split('\n')
        
        if len(lines) < 2:
            return False
        
        # Check for pipes in first line
        if '|' not in lines[0]:
            return False
        
        # Check for separator pattern in second line
        if len(lines) > 1:
            second_line = lines[1]
            # Separator must have pipes and dashes/colons
            if '|' not in second_line or ('-' not in second_line and ':' not in second_line):
                return False
            
            # Ensure it looks like a proper separator (mostly dashes)
            pipe_sections = second_line.split('|')
            separator_cells = [s.strip() for s in pipe_sections if s.strip()]
            
            # At least one cell should be mostly dashes
            has_dash_cell = any(all(c in '-: ' for c in cell) for cell in separator_cells)
            if not has_dash_cell:
                return False
        
        return True
    
    def _extract_markdown_tables_from_documents(self, documents) -> List[str]:
        """
        Extract markdown tables from parsed PDF documents.
        
        Args:
            documents: List of Document objects from PDF parsing
        
        Returns:
            List of markdown table strings
        """
        markdown_tables = []
        seen_tables = set()  # For deduplication
        
        # Pattern 1: Standard markdown tables (most common)
        # Header row | separator row | data rows
        standard_pattern = r'(\|[^\n]*\|\n)+\|[\s\-:|]+\|(\n\|[^\n]+\|)*'
        
        # Pattern 2: Simple pipe-delimited tables (might have variations in spacing)
        # Looser pattern to catch tables with inconsistent formatting
        flexible_pattern = r'^\|.*\|.*\n\|[\s\-:| ]+\|\n(.*\n)*'
        
        for doc in documents:
            text = doc.text if hasattr(doc, 'text') else str(doc)
            
            # Try standard pattern first
            for match in re.finditer(standard_pattern, text, re.MULTILINE):
                table_text = match.group(0).strip()
                if table_text and self._is_valid_table(table_text):
                    table_hash = hashlib.md5(table_text.encode()).hexdigest()
                    if table_hash not in seen_tables:
                        markdown_tables.append(table_text)
                        seen_tables.add(table_hash)
            
            # Try flexible pattern for tables that might not match standard pattern exactly
            for match in re.finditer(flexible_pattern, text, re.MULTILINE):
                table_text = match.group(0).strip()
                if table_text and self._is_valid_table(table_text):
                    table_hash = hashlib.md5(table_text.encode()).hexdigest()
                    if table_hash not in seen_tables:
                        markdown_tables.append(table_text)
                        seen_tables.add(table_hash)
            
            # Last resort: manually scan for table-like structures
            lines = text.split('\n')
            current_table_lines = []
            
            for line in lines:
                # Check if line looks like a table row (contains pipes)
                if '|' in line and line.strip().startswith('|') and line.strip().endswith('|'):
                    current_table_lines.append(line)
                else:
                    # If we were building a table and hit a non-table line, save it
                    if current_table_lines and len(current_table_lines) >= 3:
                        potential_table = '\n'.join(current_table_lines).strip()
                        if self._is_valid_table(potential_table):
                            table_hash = hashlib.md5(potential_table.encode()).hexdigest()
                            if table_hash not in seen_tables:
                                markdown_tables.append(potential_table)
                                seen_tables.add(table_hash)
                    current_table_lines = []
            
            # Don't forget the last table if document ends with one
            if current_table_lines and len(current_table_lines) >= 3:
                potential_table = '\n'.join(current_table_lines).strip()
                if self._is_valid_table(potential_table):
                    table_hash = hashlib.md5(potential_table.encode()).hexdigest()
                    if table_hash not in seen_tables:
                        markdown_tables.append(potential_table)
                        seen_tables.add(table_hash)
        
        print(f"✅ Detected {len(markdown_tables)} unique markdown tables from documents")
        return markdown_tables
    
    def _is_valid_table(self, table_text: str) -> bool:
        """
        Validate if text looks like a valid markdown table.
        More lenient validation to avoid skipping valid tables.
        
        Returns:
            True if table is valid, False otherwise
        """
        lines = table_text.strip().split('\n')
        
        # Must have at least header and separator (data rows optional)
        if len(lines) < 2:
            return False
        
        # Check if has header with pipes
        has_header = '|' in lines[0] and lines[0].count('|') >= 2
        
        # Check if has separator row (dashes and/or colons)
        has_separator = False
        if len(lines) > 1:
            has_separator = '|' in lines[1] and ('-' in lines[1] or ':' in lines[1])
        
        # Valid if has both header and separator (data is optional)
        return has_header and has_separator
    
    def _parse_markdown_table(self, markdown_table: str, table_index: int = 0) -> Dict:
        """
        Parse markdown table string into structured format.
        More robust parsing to handle various markdown table formats.
        
        Markdown table format:
        | Header 1 | Header 2 | Header 3 |
        |----------|----------|----------|
        | Value 1  | Value 2  | Value 3  |
        | Value 4  | Value 5  | Value 6  |
        
        Args:
            markdown_table: Markdown formatted table string
            table_index: Index of this table in document
        
        Returns:
            Dict with structured table data or None if invalid
        """
        from workflow.utils import sanitize_text
        
        lines = markdown_table.strip().split('\n')
        
        # Need at least header and separator (data rows are optional now)
        if len(lines) < 2:
            return None
        
        try:
            # Parse header row
            header_line = lines[0]
            # Split by | and remove empty first/last elements
            header_parts = header_line.split('|')
            headers = [h.strip() for h in header_parts[1:-1] if header_parts[0] == '' and header_parts[-1].strip() == ''] or [h.strip() for h in header_parts if h.strip()]
            
            if not headers:
                return None
            
            # Skip separator line (line 1 with dashes)
            # Parse data rows (starting from line 2, but rows are optional)
            rows = []
            for line in lines[2:]:  # Start from line 2 (skip header and separator)
                if line.strip() and '|' in line:
                    row_parts = line.split('|')
                    row = [cell.strip() for cell in row_parts[1:-1] if row_parts[0] == '' and row_parts[-1].strip() == ''] or [cell.strip() for cell in row_parts if cell.strip() or cell == '']
                    # Ensure row has same number of columns as headers
                    if row and len(row) > 0:
                        # Pad or trim row to match header count
                        while len(row) < len(headers):
                            row.append('')
                        row = row[:len(headers)]
                        rows.append(row)
            
            # Allow tables with no data rows (header-only tables can still be useful)
            # But skip completely empty tables
            if len(headers) == 0:
                return None
            
            # Create text representation for hybrid search
            text_repr = self._markdown_table_to_text(headers, rows)
            
            # Create hash for deduplication
            content_hash = hashlib.md5(markdown_table.encode('utf-8')).hexdigest()
            
            return {
                'page': 1,  # PyMuPDF provides page numbers via page_num
                'table_index': table_index,
                'headers': headers,
                'rows': rows,
                'row_count': len(rows),
                'col_count': len(headers),
                'markdown_table': markdown_table,  # ✅ Full markdown preserved
                'text_representation': text_repr,  # Fallback for hybrid search
                'hash': content_hash
            }
        
        except Exception as e:
            logger.error(f"Failed to parse markdown table: {e}")
            return None
    
    def _markdown_table_to_text(self, headers: List[str], rows: List[List[str]]) -> str:
        """
        Convert structured table to searchable text representation.
        
        Preserves more context than the old pdfplumber approach:
        - All rows (not just first 10)
        - Maintains header-value relationships
        - Markdown formatting for better structure
        
        Args:
            headers: List of column headers
            rows: List of rows (each row is a list of cell values)
        
        Returns:
            Structured text representation of table
        """
        from workflow.utils import sanitize_text
        
        text_parts = []
        
        # Add headers with context
        if headers:
            header_line = " | ".join(str(h) for h in headers if h)
            text_parts.append("### Table Structure")
            text_parts.append(f"Columns: {sanitize_text(header_line)}")
            text_parts.append("")
        
        # Add all rows with column names (relationship preservation)
        text_parts.append("### Table Data")
        
        for row_idx, row in enumerate(rows):
            text_parts.append(f"\n**Row {row_idx + 1}:**")
            
            # Create header-value pairs for clarity
            for col_idx, (header, value) in enumerate(zip(headers, row)):
                if header and value:
                    text_parts.append(f"  - {sanitize_text(header)}: {sanitize_text(value)}")
        
        return "\n".join(text_parts)
    
    def detect_equations(self, pdf_path: str) -> bool:
        """
        Detect if PDF contains mathematical equations or formulas.
        Looks for LaTeX math delimiters, Unicode math symbols, and common equation patterns.
        
        Returns:
            bool: True if equations/formulas are detected, False otherwise
        """
        print(f"🔢 Starting equation detection from: {pdf_path}")
        
        try:
            import re
            doc = fitz.open(pdf_path)
            
            # Patterns to detect equations
            # 1. LaTeX math environments
            latex_patterns = [
                r'\\begin\{(equation|align|math|displaymath|eqnarray|gather)\}',
                r'\\end\{(equation|align|math|displaymath|eqnarray|gather)\}',
                r'\\\[.*?\\\]',  # Display math
                r'\$\$.*?\$\$',  # Display math alternative
                r'\$[^$]+\$',    # Inline math
                r'\\frac\{',     # Fractions
                r'\\int[_^]',    # Integrals
                r'\\sum[_^]',    # Summations
                r'\\prod[_^]',   # Products
                r'\\sqrt\{',     # Square roots
                r'\\alpha|\\beta|\\gamma|\\delta|\\theta|\\lambda|\\mu|\\sigma|\\pi',  # Greek letters
            ]
            
            # 2. Unicode math symbols (common in modern PDFs)
            # Mathematical Operators: ∀∂∃∅∇∈∉∋∏∑−∓∗∘∙√∝∞∟∠∧∨∩∪∫∬∭∮∴∵∼≃≅≈≉≠≡≤≥
            # Greek letters: αβγδεζηθικλμνξοπρστυφχψω
            unicode_math_ranges = [
                (0x2200, 0x22FF),  # Mathematical Operators
                (0x27C0, 0x27EF),  # Miscellaneous Mathematical Symbols-A
                (0x2980, 0x29FF),  # Miscellaneous Mathematical Symbols-B
                (0x2A00, 0x2AFF),  # Supplemental Mathematical Operators
                (0x0391, 0x03A9),  # Greek uppercase
                (0x03B1, 0x03C9),  # Greek lowercase
            ]
            
            # Combine LaTeX patterns
            combined_pattern = '|'.join(latex_patterns)
            
            # Check each page
            for page_num in range(min(len(doc), 50)):  # Check first 50 pages max
                page = doc[page_num]
                text = page.get_text()
                
                # Check for LaTeX patterns
                if re.search(combined_pattern, text):
                    doc.close()
                    print(f"✅ Equations detected (LaTeX pattern) on page {page_num + 1}")
                    return True
                
                # Check for Unicode math symbols
                for char in text:
                    char_code = ord(char)
                    for start, end in unicode_math_ranges:
                        if start <= char_code <= end:
                            doc.close()
                            print(f"✅ Equations detected (Unicode math symbol) on page {page_num + 1}")
                            return True
                
                # Check for common equation indicators
                # Multiple equals signs, inequality symbols, etc.
                if text.count('=') > 5 or text.count('≠') > 0 or text.count('≈') > 0:
                    # Further validation: check if they're in a mathematical context
                    equation_context = re.search(r'[a-zA-Z_][0-9]*\s*[=≠≈≤≥]\s*[0-9a-zA-Z_+\-*/()]+', text)
                    if equation_context:
                        doc.close()
                        print(f"✅ Equations detected (equation pattern) on page {page_num + 1}")
                        return True
            
            doc.close()
            print(f"❌ No equations detected in {pdf_path}")
            return False
            
        except Exception as e:
            print(f"⚠️ Error during equation detection: {e}")
            return False
    
    def extract_all(self, pdf_path: str, page_info: List[Dict] = None) -> Dict:
        """
        Extract all multi-modal content from PDF with layout-aware processing
        
        Args:
            pdf_path: Path to PDF file
            page_info: Optional page information for page-span detection
        
        Returns:
            Dict with 'images', 'tables', 'markdown_full', and 'has_equations' keys
        """
        print(f"🚀 Starting multi-modal extraction from: {pdf_path}")
        
        images = self.extract_images(pdf_path)
        tables = self.extract_tables(pdf_path, page_info)  # ✨ Pass page_info
        has_equations = self.detect_equations(pdf_path)
        
        # ✅ NEW: Extract full markdown for MarkdownElementNodeParser
        markdown_full = self.extract_full_markdown(pdf_path)
        
        print(f"✅ Multi-modal extraction complete: {len(images)} images, {len(tables)} tables, {len(markdown_full)} chars markdown, equations: {has_equations}")
        
        return {
            'images': images,
            'tables': tables,
            'markdown_full': markdown_full,  # Full markdown for advanced indexing
            'has_equations': has_equations,
            'total_items': len(images) + len(tables)
        }
    
    def extract_full_markdown(self, pdf_path: str) -> str:
        """
        Extract complete document as markdown using pymupdf4llm.
        This provides the full structured content for MarkdownElementNodeParser.
        
        Returns:
            Full markdown text of the entire document
        """
        logger.info(f"📄 Extracting full markdown from: {pdf_path}")
        print(f"📄 Extracting full markdown document...")
        
        try:
            import pymupdf4llm
            
            logger.info("📄 Using pymupdf4llm for markdown conversion...")
            print("📄 Using pymupdf4llm for markdown conversion.")
            
            # Convert PDF to markdown optimized for LLMs
            md_text = pymupdf4llm.to_markdown(pdf_path)
            
            if md_text:
                logger.info(f"✅ Extracted {len(md_text)} chars of markdown from PDF")
                print(f"✅ Extracted {len(md_text):,} chars of markdown")
                return md_text
            else:
                logger.warning("⚠️ pymupdf4llm returned empty markdown")
                print("⚠️ No markdown content extracted")
                return ""
                
        except ImportError:
            logger.error("pymupdf4llm not installed. Install with: pip install pymupdf4llm")
            print("❌ pymupdf4llm not installed. Install with: pip install pymupdf4llm")
            return ""
        except Exception as e:
            logger.error(f"Failed to extract markdown with pymupdf4llm: {e}")
            print(f"❌ Failed to extract markdown: {e}")
            return ""


# Singleton instance
multimodal_extractor = MultiModalExtractor()