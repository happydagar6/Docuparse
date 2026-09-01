"""
Layout-Aware PDF Parser
Solves: Row Blindness, Page-Spanning Tables, and Missing Headers in Chunks

This module provides advanced table extraction and chunking strategies
specifically designed for complex financial PDFs like annual reports.
"""

import re
import hashlib
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class LayoutAwareParser:
    """
    Advanced PDF parser that preserves table layout and handles page spans
    """
    
    def __init__(self, max_rows_per_chunk: int = 30, overlap_rows: int = 2):
        """
        Args:
            max_rows_per_chunk: Maximum table rows per chunk (prevents "row blindness")
            overlap_rows: Number of rows to overlap between chunks for context
        """
        self.max_rows_per_chunk = max_rows_per_chunk
        self.overlap_rows = overlap_rows
        self.min_table_rows = 1
    
    def merge_page_spanning_tables(
        self,
        tables: List[Dict],
        page_info: List[Dict]
    ) -> List[Dict]:
        """
        Merge tables that span across pages
        
        Strategy:
        1. Detect if last table on page N has same column structure as first table on page N+1
        2. Check if table appears to be "incomplete" (no total row, mid-section)
        3. Merge tables by concatenating rows
        
        Args:
            tables: List of extracted tables with page numbers
            page_info: List of page metadata
            
        Returns:
            List of tables with page-spanning tables merged
        """
        # [LITWISE RAG LOGIC]: Handling Page-Spanning Tables
        # Why we do this: If a massive income statement starts on page 4 but finishes on page 5,
        # the PDF parser thinks they are two separate tables! The second table will have NO headers,
        # so the LLM won't know what the numbers mean. This function sews them back together.
        
        if not tables or len(tables) <= 1:
            return tables
        
        logger.info(f"Analyzing {len(tables)} tables for page spans...")
        
        # 1. Sort tables by page number so we can process them sequentially (page 1, then 2, etc.)
        sorted_tables = sorted(tables, key=lambda t: t.get('page', 0))
        
        merged_tables = []
        skip_next = set()  # Track indices to skip (already merged)
        
        for i in range(len(sorted_tables) - 1):
            if i in skip_next:
                continue
            
            # 2. Look at two tables side-by-side (Current and Next)
            current_table = sorted_tables[i]
            next_table = sorted_tables[i + 1]
            
            current_page = current_table.get('page', 0)
            next_page = next_table.get('page', 0)
            
            # 3. If they are not on consecutive pages (e.g. Page 4 and Page 6), we skip.
            if next_page - current_page != 1:
                merged_tables.append(current_table)
                continue
            
            # 4. Check if they should be merged.
            # (e.g. Do they have the same number of columns? Are the headers identical?)
            if self._should_merge_tables(current_table, next_table):
                logger.info(
                    f"✅ Merging page-spanning table: "
                    f"Page {current_page} ({len(current_table['rows'])} rows) + "
                    f"Page {next_page} ({len(next_table['rows'])} rows)"
                )
                
                # 5. Concatenate the rows together into one massive, fixed table
                merged = self._merge_tables(current_table, next_table)
                merged_tables.append(merged)
                skip_next.add(i + 1)  # Skip the next table because we just ate it!
            else:
                merged_tables.append(current_table)
        
        # 6. Don't forget to add the very last table in the document
        if len(sorted_tables) - 1 not in skip_next:
            merged_tables.append(sorted_tables[-1])
        
        logger.info(
            f"Merge complete: {len(tables)} original tables → "
            f"{len(merged_tables)} after merging page spans"
        )
        
        return merged_tables
    
    def _should_merge_tables(self, table1: Dict, table2: Dict) -> bool:
        """
        Determine if two tables should be merged
        
        Criteria:
        1. Same number of columns
        2. Similar column headers (fuzzy match)
        3. No "total" or summary row at end of table1
        4. Table2 doesn't have a title/caption row
        """
        headers1 = table1.get('headers', [])
        headers2 = table2.get('headers', [])
        
        # Check 1: Same column count
        if len(headers1) != len(headers2):
            return False
        
        # Check 2: Column headers match (exact or fuzzy)
        if self._headers_match(headers1, headers2):
            # Check 3: No total row at end of table1
            if not self._has_total_row(table1):
                # Check 4: Table2 doesn't start with a caption
                if not self._has_caption_row(table2):
                    return True
        
        return False
    
    def _headers_match(self, headers1: List[str], headers2: List[str]) -> bool:
        """Check if headers match (exact or fuzzy)"""
        if headers1 == headers2:
            return True
        
        # Fuzzy match: normalize and compare
        normalize = lambda h: ''.join(h.lower().split())
        normalized1 = [normalize(h) for h in headers1]
        normalized2 = [normalize(h) for h in headers2]
        
        # Allow up to 20% mismatch for OCR errors
        matches = sum(1 for h1, h2 in zip(normalized1, normalized2) if h1 == h2)
        match_ratio = matches / len(headers1)
        
        return match_ratio >= 0.8
    
    def _has_total_row(self, table: Dict) -> bool:
        """Check if table ends with a total/summary row"""
        rows = table.get('rows', [])
        if not rows:
            return False
        
        last_row = rows[-1]
        first_cell = str(last_row[0]).lower() if last_row else ""
        
        # Common total row indicators
        total_indicators = [
            'total', 'sum', 'subtotal', 'grand total',
            'net', 'balance', 'ending balance', 'closing'
        ]
        
        return any(indicator in first_cell for indicator in total_indicators)
    
    def _has_caption_row(self, table: Dict) -> bool:
        """Check if table starts with a caption/title row"""
        rows = table.get('rows', [])
        if not rows:
            return False
        
        first_row = rows[0]
        
        # Caption rows typically have:
        # - Only one cell with content
        # - No numeric values
        # - Long descriptive text
        non_empty_cells = [cell for cell in first_row if str(cell).strip()]
        
        if len(non_empty_cells) == 1:
            cell_text = str(non_empty_cells[0])
            # Check if it's descriptive (no numbers, long text)
            has_numbers = bool(re.search(r'\d', cell_text))
            is_long = len(cell_text) > 30
            return not has_numbers and is_long
        
        return False
    
    def _merge_tables(self, table1: Dict, table2: Dict) -> Dict:
        """Merge two tables by concatenating rows"""
        merged = table1.copy()
        
        # Concatenate rows
        merged['rows'] = table1['rows'] + table2['rows']
        merged['row_count'] = len(merged['rows'])
        
        # Update page range
        merged['page'] = table1['page']
        merged['page_end'] = table2.get('page', table1['page'])
        merged['page_span'] = f"{table1['page']}-{table2.get('page', table1['page'])}"
        
        # Recreate markdown table
        merged['markdown_table'] = self._create_markdown_table(
            merged['headers'],
            merged['rows']
        )
        
        # Update hash
        merged['hash'] = hashlib.md5(
            merged['markdown_table'].encode('utf-8')
        ).hexdigest()
        
        # Mark as merged
        merged['is_merged'] = True
        merged['source_tables'] = 2
        
        return merged
    
    def chunk_large_tables(
        self,
        tables: List[Dict],
        max_rows_per_chunk: Optional[int] = None
    ) -> List[Dict]:
        """
        Split large tables into chunks with repeated headers
        
        This solves the "row blindness" problem where middle/bottom rows
        are invisible to the RAG system.
        
        Strategy:
        1. If table has > max_rows_per_chunk rows, split it
        2. Each chunk includes:
           - Full table headers
           - Subset of rows
           - Overlap with previous chunk for context
           - Metadata indicating chunk position
        
        Args:
            tables: List of tables
            max_rows_per_chunk: Maximum rows per chunk (default: self.max_rows_per_chunk)
            
        Returns:
            List of table chunks with repeated headers
        """
        # [LITWISE RAG LOGIC]: Chunking Tables (Curing Row Blindness)
        # Why we do this: LLMs have context limits. If you feed an LLM a table with 2,000 rows,
        # it suffers from "Middle-out amnesia" (Row Blindness) and forgets the middle rows entirely.
        # This function splits a 2,000-row table into 20 separate 100-row chunks.
        
        max_rows = max_rows_per_chunk or self.max_rows_per_chunk
        chunked_tables = []
        
        for table in tables:
            rows = table.get('rows', [])
            row_count = len(rows)
            
            # 1. If it's a tiny table (like 5 rows), don't touch it. Just save it.
            if row_count <= max_rows:
                chunked_tables.append(table)
                continue
            
            # 2. If it's a massive table, we need to split it up!
            logger.info(
                f"📊 Chunking large table ({row_count} rows) on page {table.get('page')} "
                f"into chunks of {max_rows} rows"
            )
            
            # 3. Calculate how many chunks we need to make (e.g. 500 rows / 100 max = 5 chunks)
            headers = table.get('headers', [])
            num_chunks = (row_count + max_rows - 1) // max_rows
            
            for chunk_idx in range(num_chunks):
                # 4. Calculate the start and end row for this specific chunk.
                # Notice we subtract `self.overlap_rows` (e.g., 2). This ensures that Chunk 2 shares 
                # the last 2 rows of Chunk 1. This prevents us from splitting a sentence in half!
                start_row = max(0, chunk_idx * max_rows - self.overlap_rows)
                end_row = min(row_count, (chunk_idx + 1) * max_rows)
                
                # 5. Extract those specific rows
                chunk_rows = rows[start_row:end_row]
                
                # 6. Build the new chunk
                # ✅ CRITICAL: We attach the original `headers` to EVERY single chunk.
                # So even if Chunk 5 is just rows 400-500, it still has the correct column titles!
                table_type = self._detect_table_type(headers, chunk_rows)
                fiscal_year = self._extract_fiscal_year(headers, chunk_rows)
                
                chunk = {
                    'page': table.get('page'),
                    'table_index': table.get('table_index', 0),
                    'chunk_index': chunk_idx,
                    'total_chunks': num_chunks,
                    'headers': headers,
                    'rows': chunk_rows,
                    'row_count': len(chunk_rows),
                    'col_count': len(headers),
                    'row_range': f"{start_row + 1}-{end_row}",
                    'total_table_rows': row_count,
                    'is_chunk': True,
                    'parent_table_hash': table.get('hash'),
                    'table_type': table_type,  # ✅ NEW: Financial table classification
                    'fiscal_year': fiscal_year,  # ✅ NEW: Year detection for multi-year queries
                    'type': 'table',  # ✅ NEW: Chunk type (table vs text vs image)
                    'markdown_table': self._create_markdown_table(headers, chunk_rows),
                    'text_representation': self._create_chunk_text_representation(
                        headers,
                        chunk_rows,
                        chunk_idx,
                        num_chunks,
                        table.get('page', 1),
                        table_type,  # Pass for enhanced formatting
                        fiscal_year  # Pass for year-aware context
                    )
                }
                
                # Add hash
                chunk['hash'] = hashlib.md5(
                    chunk['markdown_table'].encode('utf-8')
                ).hexdigest()
                
                # Add context about chunk position
                if chunk_idx == 0:
                    chunk['position'] = 'start'
                elif chunk_idx == num_chunks - 1:
                    chunk['position'] = 'end'
                else:
                    chunk['position'] = 'middle'
                
                chunked_tables.append(chunk)
                
                logger.debug(
                    f"   Chunk {chunk_idx + 1}/{num_chunks}: "
                    f"rows {start_row + 1}-{end_row} ({len(chunk_rows)} rows)"
                )
            
            logger.info(
                f"   ✅ Created {num_chunks} chunks for table "
                f"(original: {row_count} rows)"
            )
        
        logger.info(
            f"Chunking complete: {len(tables)} tables → "
            f"{len(chunked_tables)} chunks"
        )
        
        return chunked_tables
    
    def _create_markdown_table(self, headers: List[str], rows: List[List[str]]) -> str:
        """Create markdown table from headers and rows"""
        if not headers or not rows:
            return ""
        
        lines = []
        
        # Header row
        lines.append("| " + " | ".join(headers) + " |")
        
        # Separator row
        lines.append("|" + "|".join(["---" for _ in headers]) + "|")
        
        # Data rows
        for row in rows:
            # Pad row if needed
            padded_row = list(row) + [""] * (len(headers) - len(row))
            lines.append("| " + " | ".join(cell for cell in padded_row[:len(headers)]) + " |")
        
        return "\n".join(lines)
    
    def _create_chunk_text_representation(
        self,
        headers: List[str],
        rows: List[List[str]],
        chunk_idx: int,
        total_chunks: int,
        page: int,
        table_type: str = 'general',  # ✅ NEW: Table type parameter
        fiscal_year: Optional[str] = None  # ✅ NEW: Fiscal year parameter
    ) -> str:
        """
        Create text representation with explicit header context and metadata
        
        ✅ FIX: Make headers UNMISTAKABLE so LLM/calculator knows what's data vs headers
        ✅ ENHANCEMENT: Add table type and fiscal year for better context
        """
        parts = []
        
        # ✅ CRITICAL: Add explicit header with table type
        table_type_display = table_type.replace('_', ' ').title()
        parts.append(f"### {table_type_display} - CHUNK {chunk_idx + 1}/{total_chunks} (Page {page})")
        if fiscal_year:
            parts.append(f"### FISCAL YEAR: {fiscal_year}")
        parts.append(f"### ROW RANGE: {chunk_idx * self.max_rows_per_chunk + 1} to {min((chunk_idx + 1) * self.max_rows_per_chunk, len(rows))}")
        parts.append("")
        
        # ✅ CRITICAL: Explicitly mark column headers
        parts.append("### COLUMN HEADERS (DO NOT USE AS DATA):")
        parts.append("**" + " | ".join(headers) + "**")
        parts.append("")
        
        # ✅ CRITICAL: Explicitly mark data section
        parts.append("### DATA ROWS:")
        parts.append("")
        
        # Add markdown table with clear structure
        parts.append("| " + " | ".join(headers) + " |")
        parts.append("|" + "|".join([" --- "] * len(headers)) + "|")
        
        for row in rows:
            # Pad row if needed
            padded_row = list(row) + [""] * (len(headers) - len(row))
            parts.append("| " + " | ".join(cell for cell in padded_row[:len(headers)]) + " |")
        
        return "\n".join(parts)
    
    def detect_table_type(self, table: Dict) -> str:
        """
        Detect the type of financial table
        
        Returns one of:
        - balance_sheet
        - income_statement
        - cash_flow
        - segment_report
        - reconciliation
        - note
        - general
        """
        headers = [str(h).lower() for h in table.get('headers', [])]
        rows = table.get('rows', [])
        
        if not rows:
            return 'general'
        
        first_column = [str(row[0]).lower() if row else "" for row in rows]
        all_text = " ".join(headers + first_column).lower()
        
        # Balance sheet indicators
        if any(term in all_text for term in ['assets', 'liabilities', 'equity', 'shareholders']):
            if 'total assets' in all_text or 'total equity' in all_text:
                return 'balance_sheet'
        
        # Income statement indicators
        if any(term in all_text for term in ['revenue', 'operating income', 'net income', 'ebitda']):
            return 'income_statement'
        
        # Cash flow indicators
        if any(term in all_text for term in ['cash flow', 'operating activities', 'investing activities']):
            return 'cash_flow'
        
        # Segment report indicators
        if any(term in all_text for term in ['segment', 'zone', 'region', 'geographic']):
            return 'segment_report'
        
        # Reconciliation indicators
        if any(term in all_text for term in ['reconciliation', 'movement', 'opening', 'closing']):
            return 'reconciliation'
        
        # Note indicators
        if 'note' in all_text:
            return 'note'
        
        return 'general'
    
    def _detect_table_type(self, headers: List[str], rows: List[List[str]]) -> str:
        """Internal wrapper for detect_table_type"""
        return self.detect_table_type({'headers': headers, 'rows': rows})
    
    def _extract_fiscal_year(self, headers: List[str], rows: List[List[str]]) -> Optional[str]:
        """
        Extract fiscal year from headers or data
        
        Returns:
            Year string (e.g., "2024", "2023-2024") or None
        """
        years = []
        
        # Check headers for year patterns
        for header in headers:
            header_str = header
            # Match 4-digit years (2020-2029)
            year_matches = re.findall(r'20[2-3]\d', header_str)
            years.extend(year_matches)
        
        # Check first few rows for year indicators
        for row in rows[:3]:
            for cell in row:
                cell_str = cell
                year_matches = re.findall(r'20[2-3]\d', cell_str)
                years.extend(year_matches)
        
        if not years:
            return None
        
        # Deduplicate and sort
        unique_years = sorted(set(years))
        
        # If multiple years, return as range (e.g., "2023-2024")
        if len(unique_years) > 1:
            return f"{unique_years[0]}-{unique_years[-1]}"
        else:
            return unique_years[0]
    
    def enrich_table_metadata(self, table: Dict) -> Dict:
        """
        Add enriched metadata to help RAG retrieval
        """
        enriched = table.copy()
        
        # Detect table type
        enriched['table_type'] = self.detect_table_type(table)
        
        # Extract years from headers (for temporal queries)
        headers = table.get('headers', [])
        years = []
        for header in headers:
            year_match = re.search(r'20\d{2}', str(header))
            if year_match:
                years.append(int(year_match.group()))
        enriched['years'] = sorted(set(years))
        
        # Extract currency from content
        all_text = " ".join([str(h) for h in headers])
        for row in table.get('rows', [])[:5]:  # Check first 5 rows
            all_text += " " + " ".join([str(cell) for cell in row])
        
        currency_match = re.search(r'\b(USD|EUR|CHF|GBP|JPY|CNY)\b', all_text, re.IGNORECASE)
        if currency_match:
            enriched['currency'] = currency_match.group().upper()
        
        # Check if table has totals
        enriched['has_totals'] = self._has_total_row(table)
        
        # Calculate table density (how full is it)
        total_cells = len(table.get('rows', [])) * len(table.get('headers', []))
        empty_cells = sum(
            1 for row in table.get('rows', [])
            for cell in row
            if not str(cell).strip()
        )
        enriched['density'] = 1.0 - (empty_cells / total_cells) if total_cells > 0 else 0
        
        return enriched


# Singleton instance
layout_parser = LayoutAwareParser(
    max_rows_per_chunk=30,  # Chunk tables larger than 30 rows
    overlap_rows=2  # 2 rows overlap between chunks
)
