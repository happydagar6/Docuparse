"""
Table Normalization Module
Extracts tables from retrieved chunks and converts to structured data
"""

import re
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class TableNormalizer:
    """
    Converts raw table text (markdown or plain text) into structured JSON/DataFrame
    with normalized numeric values
    """
    
    def __init__(self):
        self.normalization_rules = {
            'parentheses_to_negative': True,
            'remove_currency_symbols': True,
            'convert_percentages': True,
            'standardize_thousands_separator': True
        }
    
    def extract_tables_from_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract all tables from retrieved chunks
        
        Args:
            chunks: List of retrieved chunks with metadata
            
        Returns:
            List of extracted tables with metadata
        """
        tables = []
        
        for chunk in chunks:
            content_type = chunk.get('metadata', {}).get('type', 'text')
            
            if content_type == 'table':
                # Already a table chunk
                table_data = self._parse_table_chunk(chunk)
                if table_data:
                    tables.append(table_data)
            else:
                # Try to extract tables from text content
                extracted = self._extract_tables_from_text(chunk.get('content', ''))
                for table in extracted:
                    table['source_page'] = chunk.get('page', None)
                    table['source_chunk'] = chunk.get('chunk_id', None)
                    tables.append(table)
        
        return tables
    
    def _parse_table_chunk(self, chunk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """❌ ISSUE #3: Parse table with UNIT DETECTION and normalization"""
        try:
            metadata = chunk.get('metadata', {})
            content = chunk.get('content', '')
            
            # Try to get structured data first
            headers = metadata.get('table_headers', [])
            rows_data = metadata.get('table_rows_data', [])
            markdown_table = metadata.get('table_markdown', content)
            
            if headers and rows_data:
                # Use structured data directly
                df = pd.DataFrame(rows_data, columns=headers)
            else:
                # Parse markdown table
                df = self._parse_markdown_table(markdown_table)
            
            if df is None or df.empty:
                logger.debug(f"Empty table after parsing, page {metadata.get('page', 'unknown')}")
                return None
            
            # ✅ FIX #3: DETECT UNIT from headers/metadata
            detected_unit, unit_multiplier = self._detect_table_unit(df, content, metadata)
            logger.info(
                f"📊 Table unit detected: {detected_unit} (multiplier: {unit_multiplier}x) "
                f"on page {metadata.get('page', '?')}"
            )
            
            # Normalize numeric values
            df = self._normalize_dataframe(df)
            
            # ✅ FIX #3: NORMALIZE to standard unit (millions)
            if unit_multiplier != 1.0:
                df = self._apply_unit_normalization(df, unit_multiplier)
                logger.info(f"✅ Normalized table values by {unit_multiplier}x to millions")
            
            table_info = {
                'dataframe': df,
                'headers': list(df.columns),
                'data': df.to_dict('records'),
                'source_page': metadata.get('page'),
                'source_table': metadata.get('table_hash'),
                'row_count': len(df),
                'col_count': len(df.columns),
                'unit': detected_unit,  # ✅ NEW: Store detected unit
                'unit_multiplier': unit_multiplier,  # ✅ NEW: Store multiplier
                'normalized_to': 'millions' if unit_multiplier != 1.0 else detected_unit  # ✅ NEW
            }
            
            logger.debug(
                f"✅ Parsed table: {len(df)} rows × {len(df.columns)} cols "
                f"(page {metadata.get('page', '?')}, unit: {detected_unit})"
            )
            
            return table_info
        
        except Exception as e:
            logger.warning(
                f"Failed to parse table chunk (page {chunk.get('metadata', {}).get('page', 'unknown')}): {e}",
                exc_info=True  # ✅ Show full traceback for debugging
            )
            return None
    
    def _parse_markdown_table(self, markdown: str) -> Optional[pd.DataFrame]:
        """Parse markdown table string into DataFrame with smart header detection"""
        try:
            lines = [line.strip() for line in markdown.split('\n') if line.strip()]
            
            if len(lines) < 3:
                return None
            
            # Extract header
            header_line = lines[0]
            headers = [h.strip() for h in header_line.split('|')[1:-1]]
            
            # Skip separator line (line 1)
            
            # Extract data rows (skip descriptor/unit rows)
            data = []
            for line in lines[2:]:
                if '|' in line:
                    row = [cell.strip() for cell in line.split('|')[1:-1]]
                    
                    # ✅ FIX: Skip descriptor rows
                    if self._is_descriptor_row(row, headers):
                        logger.debug(f"Skipping descriptor row: {row}")
                        continue
                    
                    if row:
                        data.append(row)
            
            if not data:
                logger.warning("No data rows found after filtering descriptors")
                return None
            
            df = pd.DataFrame(data, columns=headers)
            return df
        
        except Exception as e:
            logger.warning(f"Failed to parse markdown table: {e}")
            return None
    
    def _is_descriptor_row(self, row: List[str], headers: List[str]) -> bool:
        """
        Detect if row is a descriptor/unit row (not actual data)
        
        Common patterns:
        - (in millions of CHF)
        - (in thousands)
        - (unaudited)
        - Empty cells with just currency/unit info
        - All cells are text with no numbers
        """
        # Convert row to list if it's a Pandas Series
        if hasattr(row, 'tolist'):
            row = row.tolist()
        
        # Convert all cells to strings for safety
        row_str = [str(cell) if cell is not None else '' for cell in row]
        
        # Check if row is mostly empty
        non_empty_cells = [cell for cell in row_str if cell and cell != '-']
        if len(non_empty_cells) <= 1:
            return True
        
        # Join all cells to check for descriptor patterns
        row_text = ' '.join(row_str).lower()
        
        # Common descriptor patterns
        descriptor_patterns = [
            r'\(in (millions?|thousands?|billions?)\)',
            r'\(in (CHF|USD|EUR|GBP)\)',
            r'\((un)?audited\)',
            r'\(note \d+\)',
            r'\(restated\)',
            r'^currency:',
            r'^unit:',
            r'^as of',
            r'^for the (year|period)',
        ]
        
        for pattern in descriptor_patterns:
            if re.search(pattern, row_text):
                logger.debug(f"Descriptor pattern matched: {pattern}")
                return True
        
        # Check if row has no numeric values (likely a sub-header)
        # ✅ FIX: Safely iterate over string list
        has_numbers = any(
            re.search(r'\d', str(cell)) for cell in row_str
        )
        
        # If first cell looks like a label but rest are empty/text-only
        if row_str[0] and not has_numbers and len(non_empty_cells) == 1:
            return True
        
        return False
    
    def _extract_tables_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract markdown tables from plain text"""
        tables = []
        
        # Pattern for markdown tables
        table_pattern = r'(\|[^\n]+\|\n)+\|[\s\-:|]+\|(\n\|[^\n]+\|)*'
        
        matches = re.finditer(table_pattern, text)
        
        for match in matches:
            table_text = match.group(0).strip()
            df = self._parse_markdown_table(table_text)
            
            if df is not None and not df.empty:
                df = self._normalize_dataframe(df)
                tables.append({
                    'dataframe': df,
                    'headers': list(df.columns),
                    'data': df.to_dict('records'),
                    'source_page': None,
                    'source_table': None,
                    'row_count': len(df),
                    'col_count': len(df.columns)
                })
        
        return tables
    
    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize all numeric columns in DataFrame
        - Convert parentheses to negative numbers
        - Remove currency symbols
        - Parse percentages
        - Standardize thousands separators
        """
        df = df.copy()
        
        for col in df.columns:
            df[col] = df[col].apply(self._normalize_value)
        
        return df
    
    def _normalize_value(self, value: Any) -> Any:
        """
        Normalize a single value
        
        Examples:
            "(1,234.56)" → -1234.56
            "$1,234.56" → 1234.56
            "22.27%" → 0.2227
            "1,234" → 1234
        """
        # ✅ FIX: Handle Series/array inputs (edge case in nested DataFrames)
        if isinstance(value, pd.Series):
            # If it's a Series, return it as-is or convert first element
            if len(value) == 0:
                return None
            # For single-element Series, extract the value
            if len(value) == 1:
                value = value.iloc[0]
            else:
                # Multi-element Series shouldn't happen in normalization
                logger.warning(f"Unexpected Series in _normalize_value: {value}")
                return str(value)
        
        # ✅ FIX: Use pd.isna() safely for scalar values only
        try:
            if pd.isna(value):
                return None
        except (ValueError, TypeError):
            # If pd.isna() fails, value is likely not a standard type
            pass
        
        # Check for empty or placeholder values
        if value == '' or value == '-':
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        value_str = str(value).strip()
        
        # Check for parentheses (negative numbers in accounting)
        is_negative = False
        if value_str.startswith('(') and value_str.endswith(')'):
            is_negative = True
            value_str = value_str[1:-1].strip()
        
        # Remove currency symbols
        value_str = re.sub(r'[$€£¥₹฿]', '', value_str)
        
        # Check for percentage
        is_percentage = False
        if '%' in value_str:
            is_percentage = True
            value_str = value_str.replace('%', '').strip()
        
        # Remove thousands separators
        value_str = value_str.replace(',', '').replace(' ', '')
        
        # Try to convert to float
        try:
            numeric_value = float(value_str)
            
            # Apply percentage conversion (22.27% → 0.2227)
            if is_percentage:
                numeric_value = numeric_value / 100.0
            
            # Apply sign
            if is_negative:
                numeric_value = -numeric_value
            
            return numeric_value
        
        except ValueError:
            # Not a numeric value, return as-is
            return value
    
    def find_table_by_content(
        self,
        tables: List[Dict[str, Any]],
        keywords: List[str],
        row_contains: Optional[str] = None,
        col_contains: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find a specific table by keywords in headers or content
        
        Args:
            tables: List of extracted tables
            keywords: Keywords to search for
            row_contains: String that should appear in row values
            col_contains: String that should appear in column names
            
        Returns:
            Matching table or None
        """
        for table in tables:
            df = table['dataframe']
            headers = table['headers']
            
            # Check column names
            if col_contains:
                if not any(col_contains.lower() in str(h).lower() for h in headers):
                    continue
            
            # Check keywords in headers or content
            if keywords:
                table_text = ' '.join(str(h) for h in headers) + ' ' + df.to_string()
                if not any(kw.lower() in table_text.lower() for kw in keywords):
                    continue
            
            # Check row content
            if row_contains:
                if not df.apply(lambda row: any(row_contains.lower() in str(v).lower() for v in row), axis=1).any():
                    continue
            
            return table
        
        return None
    
    def extract_value(
        self,
        table: Dict[str, Any],
        row_label: str,
        col_label: str,
        fuzzy_match: bool = True
    ) -> Optional[float]:
        """
        Extract a specific value from a table
        
        Args:
            table: Structured table dictionary
            row_label: Label to find in first column (row identifier)
            col_label: Column header name
            fuzzy_match: Allow partial matching
            
        Returns:
            Numeric value or None
        """
        df = table['dataframe']
        
        # Find column
        col_idx = None
        for i, col in enumerate(df.columns):
            if fuzzy_match:
                if col_label.lower() in str(col).lower():
                    col_idx = col
                    break
            else:
                if str(col) == col_label:
                    col_idx = col
                    break
        
        if col_idx is None:
            return None
        
        # Find row (assume first column contains row labels)
        first_col = df.columns[0]
        for idx, row in df.iterrows():
            row_val = str(row[first_col])
            if fuzzy_match:
                if row_label.lower() in row_val.lower():
                    return row[col_idx]
            else:
                if row_val == row_label:
                    return row[col_idx]
        
        return None


    def _detect_table_unit(self, df: pd.DataFrame, content: str, metadata: Dict) -> Tuple[str, float]:
        """
        ❌ ISSUE #3: DETECT unit from table headers, content, or metadata
        
        Returns:
            Tuple of (unit_name, multiplier_to_millions)
            
        Examples:
            ('thousands', 0.001)  # thousands → millions: multiply by 0.001
            ('millions', 1.0)     # already millions: multiply by 1.0
            ('billions', 1000.0)  # billions → millions: multiply by 1000.0
        """
        # Combine headers and content for search
        search_text = ' '.join(str(h) for h in df.columns) + ' ' + content[:500]
        search_text_lower = search_text.lower()
        
        # Unit patterns with multipliers to convert TO millions
        unit_patterns = [
            (r'\(in thousands\b', 'thousands', 0.001),
            (r'\(thousands\b', 'thousands', 0.001),
            (r'\bin thousands\b', 'thousands', 0.001),
            (r"'000", 'thousands', 0.001),
            (r'\(in millions\b', 'millions', 1.0),
            (r'\(millions\b', 'millions', 1.0),
            (r'\bin millions\b', 'millions', 1.0),
            (r"millions of (CHF|USD|EUR|GBP)", 'millions', 1.0),
            (r'\(in billions\b', 'billions', 1000.0),
            (r'\(billions\b', 'billions', 1000.0),
            (r'\bin billions\b', 'billions', 1000.0),
        ]
        
        for pattern, unit_name, multiplier in unit_patterns:
            if re.search(pattern, search_text_lower):
                logger.debug(f"Unit detected: {unit_name} (pattern: {pattern})")
                return unit_name, multiplier
        
        # Default: assume no scaling needed (values as-is)
        logger.debug("No unit detected in table - assuming values are in base units (millions)")
        return 'unknown', 1.0
    
    def _apply_unit_normalization(self, df: pd.DataFrame, multiplier: float) -> pd.DataFrame:
        """
        ❌ ISSUE #3: NORMALIZE all numeric columns by multiplier
        
        Args:
            df: DataFrame with numeric values
            multiplier: Conversion factor (e.g., 0.001 for thousands→millions)
            
        Returns:
            DataFrame with normalized values
        """
        df = df.copy()
        
        for col in df.columns:
            # Only normalize numeric columns (skip text labels)
            if df[col].dtype in ['float64', 'int64'] or pd.api.types.is_numeric_dtype(df[col]):
                # Apply multiplier, handling None/NaN gracefully
                df[col] = df[col].apply(
                    lambda x: x * multiplier if pd.notna(x) and isinstance(x, (int, float)) else x
                )
        
        return df


# Global normalizer instance
normalizer = TableNormalizer()
