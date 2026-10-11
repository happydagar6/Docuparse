"""
CSV File Processor

Processes CSV and TSV files with tabular data.
Converts data to searchable text representation.
"""

import os
import pandas as pd
from typing import Dict, List, Tuple
from .base_processor import BaseDocumentProcessor
from ..utils import sanitize_text


# [LITWISE ARCHITECTURE]: CSV & Tabular Data Processor
# Why we do this: LLMs and vector databases struggle with raw spreadsheets. If you simply dump
# comma-separated rows into an embedder, the model misses high-level insights (averages, distributions).
# This processor solves that by:
# 1. Generating statistical summaries (mean, min, max, std dev) for numeric columns.
# 2. Creating 'Virtual Pages' (chunks of 100 rows) so citations can cite specific row ranges.
# 3. Exporting structured table metadata so our Financial RAG pipeline can perform exact math.
class CSVProcessor(BaseDocumentProcessor):
    """Process CSV files with tabular data."""
    
    SUPPORTED_EXTENSIONS = ['.csv', '.tsv']
    SUPPORTED_MIME_TYPES = ['text/csv', 'text/tab-separated-values']
    MAX_FILE_SIZE_MB = 100  # Allow larger data files
    
    def extract_text(self, file_path: str) -> Tuple[str, List[Dict]]:
        """Convert CSV to searchable text representation enriched with statistics."""
        try:
            # [LITWISE RAG LOGIC]: Delimiter Auto-Detection
            # Why we do this: Users upload both Comma-Separated (.csv) and Tab-Separated (.tsv) files.
            # Reading the first line lets us adapt dynamically without crashing.
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                first_line = f.readline()
                delimiter = ',' if ',' in first_line else '\t'
            
            self.logger.info(f"Detected delimiter: '{delimiter}'")
            
            # Read CSV
            df = pd.read_csv(
                file_path, 
                delimiter=delimiter, 
                encoding='utf-8',
                on_bad_lines='skip',
                low_memory=False
            )
            
            # Create text representation
            text_parts = []
            
            # Add column headers
            headers = ' | '.join(str(col) for col in df.columns)
            text_parts.append(f"Data Columns: {headers}")
            text_parts.append("")
            
            # Add sample rows (first 100 for context)
            sample_size = min(100, len(df))
            for idx, row in df.head(sample_size).iterrows():
                row_text = ' | '.join(str(val) for val in row.values)
                text_parts.append(f"Row {idx + 1}: {row_text}")
            
            # Add summary statistics
            text_parts.append("")
            text_parts.append(f"Dataset Summary: {len(df)} rows, {len(df.columns)} columns")
            text_parts.append("")
            
            # [LITWISE RAG LOGIC]: Statistical Feature Enrichment
            # Why we do this: If a user asks "What was the average revenue?", vector search on raw rows
            # would fail. By pre-computing mean, std, min, and max, the answers to statistical questions
            # are directly indexed into the vector database!
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                text_parts.append("Numeric Column Statistics:")
                for col in numeric_cols:
                    stats = df[col].describe()
                    text_parts.append(
                        f"  {col}: mean={stats['mean']:.2f}, std={stats['std']:.2f}, "
                        f"min={stats['min']}, max={stats['max']}"
                    )
            
            # Add categorical column value counts
            categorical_cols = df.select_dtypes(include=['object']).columns
            if len(categorical_cols) > 0:
                text_parts.append("")
                text_parts.append("Categorical Column Value Counts:")
                for col in categorical_cols:
                    value_counts = df[col].value_counts().head(5)
                    text_parts.append(f"  {col}: {dict(value_counts)}")
            
            full_text = sanitize_text('\n'.join(text_parts))
            
            # Create "pages" as row ranges (100 rows per page)
            page_info = self._create_row_ranges(df)
            
            self.logger.info(
                f"CSV extraction complete: {len(df)} rows, {len(df.columns)} columns, "
                f"{len(page_info)} pages"
            )
            
            return full_text, page_info
        
        except Exception as e:
            self.logger.error(f"CSV extraction failed: {e}")
            raise
    
    # [LITWISE RAG LOGIC]: Virtual Pages for Spreadsheets
    # Why we do this: A CSV file has no physical pages. But our frontend citation UI expects a 'page number'.
    # We partition rows into 100-row blocks: Rows 1-100 = Page 1, Rows 101-200 = Page 2.
    # This allows the AI to cite: "Source: Page 2 (Rows 101-200)".
    def _create_row_ranges(self, df: pd.DataFrame) -> List[Dict]:
        """Create page-like ranges for CSV rows."""
        page_info = []
        rows_per_page = 100
        
        for page_num, start_idx in enumerate(range(0, len(df), rows_per_page), 1):
            end_idx = min(start_idx + rows_per_page, len(df))
            page_data = df.iloc[start_idx:end_idx]
            
            # Create text representation for this range
            page_text_parts = []
            for idx, row in page_data.iterrows():
                row_text = ' | '.join(str(val) for val in row.values)
                page_text_parts.append(row_text)
            
            page_text = sanitize_text('\n'.join(page_text_parts))
            
            page_info.append({
                "page_num": page_num,
                "start_pos": 0,  # Will be recalculated during chunking
                "end_pos": len(page_text),
                "text": page_text,
                "type": "data_range",
                "row_range": f"{start_idx}-{end_idx}",
                "row_count": end_idx - start_idx
            })
        
        return page_info
    
    # [LITWISE RAG LOGIC]: Multimodal Table Extraction
    # Why we do this: For our Financial RAG Pipeline, we need the raw structured data (headers and rows).
    # Instead of making the LLM parse a text block, we hand it a structured dictionary with headers & values.
    def extract_multimodal(self, file_path: str, page_info: List[Dict] = None) -> Dict:
        """Extract table structure as multimodal content for deterministic calculations."""
        try:
            df = pd.read_csv(file_path, on_bad_lines='skip', low_memory=False)
            
            # Convert first 50 rows to table format (list of lists)
            sample_rows = df.head(50).values.tolist()
            
            return {
                'images': [],
                'tables': [{
                    'page': 1,
                    'table_index': 0,
                    'headers': list(df.columns),
                    'rows': sample_rows,
                    'row_count': len(df),
                    'col_count': len(df.columns),
                    'text_representation': (
                        f"CSV data with {len(df)} rows and {len(df.columns)} columns"
                    )
                }],
                'has_equations': False
            }
        
        except Exception as e:
            self.logger.warning(f"Table extraction failed: {e}")
            return {
                'images': [],
                'tables': [],
                'has_equations': False
            }
    
    def extract_metadata(self, file_path: str) -> Dict:
        """Extract metadata from CSV.
        
        Args:
            file_path: Path to CSV file
        
        Returns:
            Dict with metadata about the CSV structure
        
        Raises:
            Exception: If metadata extraction fails
        """
        try:
            df = pd.read_csv(file_path, on_bad_lines='skip', low_memory=False)
            
            return {
                'title': os.path.basename(file_path),
                'authors': [],
                'columns': list(df.columns),
                'row_count': len(df),
                'column_count': len(df.columns),
                'data_types': {col: str(dtype) for col, dtype in df.dtypes.items()},
                'extraction_source': 'csv_analysis'
            }
        
        except Exception as e:
            self.logger.warning(f"Metadata extraction failed: {e}")
            return {
                'title': os.path.basename(file_path),
                'authors': [],
                'extraction_source': 'filename'
            }
