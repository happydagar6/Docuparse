"""
Multi-Modal Content Extractor for PDFs
Extracts: Images, Tabled, Figures with page tracking
Uses: PyMuPDF (fitz) for images, pdfplumber for tables and figures
"""

import fitz  # PyMuPDF
import pdfplumber
import base64
import io
from typing import List, Dict, Optional
from PIL import Image
import hashlib

class MultiModalExtractor:
    """Extract multi-modal content (images, tables) from PDF files."""
    
    def __init__(self):
        self.min_image_size = 50  # Minimum size in bytes to consider an image valid
        self.min_table_rows = 2  # Minimum number of rows to consider a table valid
        
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
        
    def extract_tables(self, pdf_path: str) -> List[Dict]:
        """
        Extract tables from PDF using pdfplumber
        
        Returns:
            List of dicts with: page, table_data, row_count, col_count, text_repr
        """
        print(f"📊 Starting table extraction from: {pdf_path}")
        tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf: # Open PDF with pdfplumber
                for page_num, page in enumerate(pdf.pages): # Iterate over pages
                    try:
                        page_tables = page.extract_tables() # List of tables on the page
                        
                        for table_index, table in enumerate(page_tables):
                            if not table or len(table) < self.min_table_rows:
                                continue # Skip small tables
                            
                            # Convert to structured format
                            headers = table[0] if table else []
                            rows = table[1:] if len(table) > 1 else []
                            
                            # Create text representation for embeddings
                            text_repr = self._table_to_text(headers, rows)
                            
                            # Create content hash for deduplication
                            content_hash = hashlib.md5(text_repr.encode('utf-8')).hexdigest()
                            
                            tables.append({
                                'page': page_num + 1,
                                'table_index': table_index,
                                'headers': headers,
                                'rows': rows,
                                'row_count': len(rows),
                                'col_count': len(headers) if headers else 0,
                                'text_representation': text_repr,
                                'hash': content_hash
                            })
                    except Exception as table_e:
                        print(f"⚠️ Failed to extract table from page {page_num + 1}: {table_e}")
                        continue
            print(f"✅ Extracted {len(tables)} tables from {pdf_path}")
            return tables
        
        except Exception as e:
            print(f"❌ Failed to extract tables from {pdf_path}: {e}")
            return []
        
    def _table_to_text(self, headers: List, rows: List[List]) -> str:
        """Convert table to searchable text representation."""
        from workflow.utils import sanitize_text
        
        text_parts = []
        
        # Add headers
        if headers:
            header_text = " | ".join(str(h) for h in headers if h)
            text_parts.append("Table Headers: " + sanitize_text(header_text))
            
        # Add rows
        for i, row in enumerate(rows[:10]): # Limit to first 10 rows for brevity
            row_text = " | ".join(str(cell) for cell in row if cell)
            if row_text.strip():
                text_parts.append(f"Row {i + 1}: {sanitize_text(row_text)}")
        
        return "\n".join(text_parts) # Join all parts into single string
    
    def extract_all(self, pdf_path: str) -> Dict:
        """
        Extract all multi-modal content from PDF
        
        Returns:
            Dict with 'images' and 'tables' keys
        """
        print(f"🚀 Starting multi-modal extraction from: {pdf_path}")
        
        images = self.extract_images(pdf_path)
        tables = self.extract_tables(pdf_path)
        
        print(f"✅ Multi-modal extraction complete: {len(images)} images, {len(tables)} tables")
        
        return {
            'images': images,
            'tables': tables,
            'total_items': len(images) + len(tables)
        }


# Singleton instance
multimodal_extractor = MultiModalExtractor()