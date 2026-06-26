"""
Production-Grade Markdown Element Indexing for Financial Documents
Implements MarkdownElementNodeParser strategy for superior retrieval

Why MarkdownElementNodeParser?
- Preserves document structure (headers, tables, lists)
- Creates element-aware chunks (complete tables, sections)
- Better semantic boundaries vs naive text splitting
- Critical for financial docs where table integrity matters
"""

import logging
import hashlib
from typing import List, Dict, Any, Tuple, Optional
import re

logger = logging.getLogger(__name__)


class MarkdownElementNodeParser:
    """`
    Advanced parser that creates nodes from markdown elements (headers, tables, paragraphs)
    instead of arbitrary character-based chunks.
    
    Critical for financial documents where:
    - Tables must stay intact (Balance Sheet, Income Statement)
    - Headers provide context for sections
    - Lists contain structured data (risk factors, footnotes)
    """
    
    def __init__(
        self,
        max_table_tokens: int = 6000,  # ~24KB - smart chunking will handle oversized tables
        max_section_tokens: int = 1500,  # ~6KB - complete sections
        overlap_sections: int = 2,  # Number of previous headers to include for context
        chunk_overlap_rows: int = 5  # Rows to overlap between table chunks for continuity
    ):
        """
        Args:
            max_table_tokens: Maximum tokens per table chunk (larger = fewer chunks needed)
            max_section_tokens: Maximum tokens for text sections between elements
            overlap_sections: Number of parent headers to include for hierarchical context
            chunk_overlap_rows: Number of rows to overlap between table chunks for retrieval continuity
        """
        self.max_table_tokens = max_table_tokens
        self.max_section_tokens = max_section_tokens
        self.overlap_sections = overlap_sections
        self.chunk_overlap_rows = chunk_overlap_rows
        
    def parse_markdown_to_nodes(
        self,
        markdown_text: str,
        page_info: Optional[List[Dict]] = None,
        base_metadata: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse markdown text into structured nodes based on elements.
        
        Strategy:
        1. Extract tables as complete units (NEVER split mid-table)
        2. Extract headers and create hierarchical context
        3. Group paragraphs into sections based on headers
        4. Create overlap via header repetition
        
        Args:
            markdown_text: Full markdown content from document
            page_info: Page mapping information
            base_metadata: Base metadata to attach to all nodes
            
        Returns:
            List of node dictionaries with content, type, metadata
        """
        logger.info(f"🔍 Parsing markdown into element-based nodes ({len(markdown_text)} chars)")
        
        nodes = []
        base_metadata = base_metadata or {}
        
        # Step 1: Extract all tables first (highest priority - must stay intact)
        tables, text_without_tables = self._extract_tables(markdown_text)
        logger.info(f"Extracted {len(tables)} complete tables")
        
        # Step 2: Parse remaining text into sections based on headers
        sections = self._parse_sections(text_without_tables)
        logger.info(f"Extracted {len(sections)} text sections")
        
        # Step 3: Create nodes from tables with SMART CHUNKING for oversized tables
        table_node_id = 0
        for i, table in enumerate(tables):
            # Check if table is oversized and needs chunking
            table_tokens = len(table['raw_markdown']) // 4
            
            if table_tokens > self.max_table_tokens:
                # Table is too large: split into row-based chunks (preserves ALL data)
                logger.info(f"🔄 Table {i} is oversized ({table['row_count']} rows, {table_tokens} tokens). Splitting into chunks...")
                table_chunks = self._smart_chunk_table(
                    table['raw_markdown'],
                    table_index=i,
                    max_tokens=self.max_table_tokens
                )
                
                # Create a node for each chunk
                for chunk_idx, chunk in enumerate(table_chunks):
                    chunk_tokens = len(chunk['content']) // 4
                    table_node = {
                        'content': chunk['content'],
                        'type': 'table',
                        'element_type': 'financial_table_chunk',
                        'metadata': {
                            **base_metadata,
                            'node_id': f"table_{i}_chunk_{chunk_idx}",
                            'table_index': i,
                            'chunk_index': chunk_idx,
                            'total_chunks': len(table_chunks),
                            'row_count': chunk['row_count'],
                            'col_count': table['col_count'],
                            'row_range': f"{chunk['row_start']}-{chunk['row_end']}",
                            'is_chunk': True,
                            'table_hash': hashlib.md5(table['raw_markdown'].encode()).hexdigest()[:8],
                            'estimated_tokens': chunk_tokens
                        }
                    }
                    nodes.append(table_node)
                    table_node_id += 1
                    logger.debug(f"Created table chunk {chunk_idx}/{len(table_chunks)} for table {i}: rows {chunk['row_start']}-{chunk['row_end']} ({chunk_tokens} tokens)")
            else:
                # Table is within limit: store as single node
                table_node = {
                    'content': table['raw_markdown'],
                    'type': 'table',
                    'element_type': 'financial_table',
                    'metadata': {
                        **base_metadata,
                        'node_id': f"table_{i}",
                        'table_index': i,
                        'row_count': table['row_count'],
                        'col_count': table['col_count'],
                        'is_chunk': False,
                        'table_hash': hashlib.md5(table['raw_markdown'].encode()).hexdigest()[:8],
                        'estimated_tokens': table_tokens
                    }
                }
                nodes.append(table_node)
                table_node_id += 1
                logger.debug(f"Created table node {i}: {table['row_count']}x{table['col_count']} ({table_tokens} tokens)")
        
        # Step 4: Create nodes from sections with hierarchical context and SMART CHUNKING
        header_stack = []  # Track nested headers for context
        section_node_id = 0
        
        for i, section in enumerate(sections):
            # Update header stack based on section level
            if section['type'] == 'header':
                # Pop headers of same or lower level
                while header_stack and header_stack[-1]['level'] >= section['level']:
                    header_stack.pop()
                # Add current header
                header_stack.append({'level': section['level'], 'text': section['header']})
            
            # Build hierarchical context from header stack
            context_headers = [h['text'] for h in header_stack[-self.overlap_sections:]] if header_stack else []
            hierarchical_context = " > ".join(context_headers) if context_headers else ""
            
            # Create section node
            section_content = section['content']
            
            # Prepend hierarchical context for better retrieval
            if hierarchical_context:
                full_content = f"# {hierarchical_context}\n\n{section_content}"
            else:
                full_content = section_content
            
            # Check if section is oversized and needs smart chunking
            section_tokens = len(full_content) // 4
            
            if section_tokens > self.max_section_tokens:
                # Section is too large: split into paragraph-based chunks
                logger.info(f"🔄 Section {i} is oversized ({section_tokens} tokens). Splitting into chunks...")
                section_chunks = self._smart_chunk_section(
                    full_content,
                    section_index=i,
                    max_tokens=self.max_section_tokens
                )
                
                # Create a node for each chunk
                for chunk_idx, chunk in enumerate(section_chunks):
                    chunk_tokens = len(chunk['content']) // 4
                    section_node = {
                        'content': chunk['content'],
                        'type': 'section',
                        'element_type': 'section_chunk',
                        'metadata': {
                            **base_metadata,
                            'node_id': f"section_{i}_chunk_{chunk_idx}",
                            'section_index': i,
                            'chunk_index': chunk_idx,
                            'total_chunks': len(section_chunks),
                            'header_level': section.get('level', 0),
                            'header_text': section.get('header', ''),
                            'hierarchical_context': hierarchical_context,
                            'is_chunk': True,
                            'estimated_tokens': chunk_tokens
                        }
                    }
                    nodes.append(section_node)
                    section_node_id += 1
                    logger.debug(f"Created section chunk {chunk_idx}/{len(section_chunks)} for section {i} ({chunk_tokens} tokens)")
            else:
                # Section is within limit: store as single node
                section_node = {
                    'content': full_content,
                    'type': 'section',
                    'element_type': section['type'],
                    'metadata': {
                        **base_metadata,
                        'node_id': f"section_{i}",
                        'section_index': i,
                        'header_level': section.get('level', 0),
                        'header_text': section.get('header', ''),
                        'hierarchical_context': hierarchical_context,
                        'is_chunk': False,
                        'estimated_tokens': section_tokens
                    }
                }
                nodes.append(section_node)
                section_node_id += 1
            logger.debug(f"Created section node {i}: {section['type']} - {hierarchical_context}")
        
        logger.info(f"✅ Created {len(nodes)} element-based nodes ({len([n for n in nodes if n['type']=='table'])} tables, {len([n for n in nodes if n['type']=='section'])} sections)")
        
        return nodes
    
    def _smart_chunk_table(self, table_markdown: str, table_index: int, max_tokens: int = 6000) -> List[Dict[str, Any]]:
        """
        Intelligently split a large table into smaller chunks by rows, preserving ALL data.
        
        Strategy:
        1. Calculate how many rows fit in max_tokens
        2. Split table into chunks with row overlap for retrieval continuity
        3. Each chunk is a complete markdown table with header
        
        Args:
            table_markdown: Full markdown table
            table_index: Index of table in document
            max_tokens: Maximum tokens per chunk
            
        Returns:
            List of chunks with row information
        """
        rows = table_markdown.split('\n')
        
        if len(rows) < 3:  # No data rows
            return [{
                'content': table_markdown,
                'row_count': 0,
                'row_start': 0,
                'row_end': 0
            }]
        
        header_row = rows[0]
        separator_row = rows[1]
        data_rows = rows[2:]
        
        # Calculate tokens per row from header size
        header_tokens = len(header_row) // 4
        row_tokens = len(header_row) // 4  # Rough estimate: same as header
        
        # Calculate how many rows fit per chunk
        # Leave margin: max_tokens - header_tokens - separator_tokens - 200 buffer
        available_tokens = (max_tokens * 4) - len(header_row) - len(separator_row) - 200
        rows_per_chunk = max(5, available_tokens // (len(header_row)))  # At least 5 rows per chunk
        
        # Split into chunks with overlap
        chunks = []
        i = 0
        
        while i < len(data_rows):
            # Determine chunk boundary
            chunk_end = min(i + rows_per_chunk, len(data_rows))
            
            # Create chunk rows
            chunk_rows = data_rows[i:chunk_end]
            
            # Build chunk markdown
            chunk_markdown = f"{header_row}\n{separator_row}\n" + "\n".join(chunk_rows)
            
            chunks.append({
                'content': chunk_markdown,
                'row_count': len(chunk_rows),
                'row_start': i + 1,  # 1-indexed
                'row_end': chunk_end  # 1-indexed
            })
            
            # Move to next chunk with overlap
            i = chunk_end - self.chunk_overlap_rows
        
        logger.info(f"📊 Split table {table_index} into {len(chunks)} chunks ({len(data_rows)} total rows, {rows_per_chunk} rows/chunk)")
        return chunks
    
    def _smart_chunk_section(self, section_markdown: str, section_index: int, max_tokens: int = 1500) -> List[Dict[str, Any]]:
        """
        Intelligently split a large section (text) into smaller chunks by paragraphs.
        Preserves all content while respecting token limits.
        
        Strategy:
        1. Split by paragraphs (double newlines)
        2. Group paragraphs into chunks that fit within max_tokens
        3. Add header context to each chunk
        
        Args:
            section_markdown: Full section markdown text (with header)
            section_index: Index of section in document
            max_tokens: Maximum tokens per chunk
            
        Returns:
            List of chunks with text content
        """
        # Extract header if present
        lines = section_markdown.split('\n')
        header_line = ""
        content_start_idx = 0
        
        if lines and lines[0].startswith('#'):
            header_line = lines[0]
            content_start_idx = 1
        
        # Split content into paragraphs (by double newline)
        content = '\n'.join(lines[content_start_idx:])
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        if not paragraphs:
            # Return as-is if no paragraphs
            return [{
                'content': section_markdown,
                'para_count': 0
            }]
        
        # Group paragraphs into chunks
        chunks = []
        current_chunk_paras = []
        current_chunk_chars = len(header_line) if header_line else 0
        
        for para in paragraphs:
            para_chars = len(para) + 2  # +2 for newlines
            
            # Check if adding this paragraph exceeds limit
            projected_chars = current_chunk_chars + para_chars
            
            if projected_chars > (max_tokens * 4) and current_chunk_paras:
                # Finalize current chunk
                chunk_text = "\n\n".join(current_chunk_paras)
                if header_line:
                    chunk_text = f"{header_line}\n\n{chunk_text}"
                
                chunks.append({
                    'content': chunk_text,
                    'para_count': len(current_chunk_paras)
                })
                
                # Start new chunk
                current_chunk_paras = [para]
                current_chunk_chars = len(header_line) + para_chars if header_line else para_chars
            else:
                # Add paragraph to current chunk
                current_chunk_paras.append(para)
                current_chunk_chars = projected_chars

        # Add final chunk — trim to last complete sentence for clean boundary
        if current_chunk_paras:
            chunk_text = "\n\n".join(current_chunk_paras)
            if header_line:
                chunk_text = f"{header_line}\n\n{chunk_text}"
            
            chunks.append({
                'content': chunk_text,
                'para_count': len(current_chunk_paras)
            })
        
        logger.info(f"📝 Split section {section_index} into {len(chunks)} chunks ({sum(c['para_count'] for c in chunks)} total paragraphs, sentence-boundary aware)")
        return chunks
    
    def _extract_tables(self, markdown_text: str) -> Tuple[List[Dict], str]:
        """
        Extract all markdown tables from text and return tables + text without tables.
        
        Returns:
            Tuple of (tables_list, text_without_tables)
        """
        tables = []
        
        # Regex pattern for markdown tables
        # Matches: header row | separator | data rows
        table_pattern = r'(?:^\|.+\|$\n)+^\|[\s\-:|]+\|$\n(?:^\|.+\|$\n?)+'
        
        matches = list(re.finditer(table_pattern, markdown_text, re.MULTILINE))
        
        for match in matches:
            table_text = match.group(0).strip()
            rows = table_text.split('\n')
            
            # Parse table structure
            header_row = rows[0] if rows else ""
            data_rows = [r for r in rows[2:] if r.strip()]  # Skip separator row
            
            col_count = header_row.count('|') - 1 if header_row else 0
            row_count = len(data_rows)
            
            tables.append({
                'raw_markdown': table_text,
                'start_pos': match.start(),
                'end_pos': match.end(),
                'row_count': row_count,
                'col_count': col_count
            })
        
        # Remove tables from text
        text_without_tables = markdown_text
        for table in reversed(tables):  # Reverse to maintain positions
            text_without_tables = (
                text_without_tables[:table['start_pos']] +
                f"\n[TABLE_{len(tables) - tables.index(table) - 1}_EXTRACTED]\n" +  # Placeholder
                text_without_tables[table['end_pos']:]
            )
        
        return tables, text_without_tables
    
    def _parse_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse text into sections based on markdown headers.
        
        Returns:
            List of section dictionaries with type, content, level, header
        """
        sections = []
        
        # Split by markdown headers (#, ##, ###, etc.)
        lines = text.split('\n')
        
        current_section = []
        current_header = None
        current_level = 0
        
        for line in lines:
            # Check if line is a header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            if header_match:
                # Save previous section if exists
                if current_section:
                    sections.append({
                        'type': 'header' if current_header else 'paragraph',
                        'content': '\n'.join(current_section).strip(),
                        'header': current_header,
                        'level': current_level
                    })
                
                # Start new section
                current_level = len(header_match.group(1))
                current_header = header_match.group(2).strip()
                current_section = [line]
            else:
                current_section.append(line)
        
        # Save last section
        if current_section:
            sections.append({
                'type': 'header' if current_header else 'paragraph',
                'content': '\n'.join(current_section).strip(),
                'header': current_header,
                'level': current_level
            })
        
        # Filter out empty sections
        sections = [s for s in sections if s['content'].strip()]
        
        return sections


# Singleton instance
markdown_parser = MarkdownElementNodeParser(
    max_table_tokens=2500,
    max_section_tokens=2500,  # Raised from 1500 — fewer sections need splitting
    overlap_sections=2
)
