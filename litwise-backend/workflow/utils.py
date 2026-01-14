# PDF extraction + embeddings

import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from qdrant_client.http.models import PointStruct
import uuid
import openai
import os


model = OpenAIEmbeddings(model="text-embedding-3-small")

# Also initialize direct OpenAI client for guaranteed batching
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def sanitize_text(text: str) -> str:
    """
    Remove null bytes and other problematic Unicode characters that PostgreSQL doesn't accept.
    
    Args:
        text: Raw text that may contain null bytes
        
    Returns:
        Sanitized text safe for database storage
    """
    if not text:
        return ""
    
    # Remove null bytes (U+0000)
    text = text.replace('\x00', '')
    
    # Remove other control characters except newlines, tabs, and carriage returns
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    return text

def extract_text_from_pdf(file_path: str) -> tuple[str, list[dict]]:
    """
    Extract text from PDF with accurate page tracking.
    
    Returns:
        tuple: (full_text, page_info_list)
        - full_text: Complete document text
        - page_info_list: List of {"page_num": int, "start_pos": int, "end_pos": int, "text": str}
    """
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            
            # Check if PDF is encrypted
            if reader.is_encrypted:
                print("⚠️  PDF is encrypted, attempting to decrypt...")
                try:
                    # Try to decrypt with empty password (common for PDFs with restrictions but no password)
                    reader.decrypt('')
                except Exception as decrypt_error:
                    raise Exception(f"PDF is encrypted and cannot be decrypted. Please use an unencrypted PDF. Error: {decrypt_error}")
            
            full_text = ""
            page_info = []
            
            print(f"📖 PDF contains {len(reader.pages)} pages")
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                # Sanitize text to remove null bytes and control characters
                page_text = sanitize_text(page_text)
                
                start_pos = len(full_text)
                full_text += page_text + "\n"  # Add page break
                end_pos = len(full_text) - 1  # Don't include the newline in range
                
                page_info.append({
                    "page_num": page_num,
                    "start_pos": start_pos,
                    "end_pos": end_pos,
                    "text": page_text
                })
                
                if page_num <= 3 or page_num > len(reader.pages) - 3:  # Debug first/last few pages
                    print(f"📄 Page {page_num}: pos {start_pos}-{end_pos} ({len(page_text)} chars)")
            
            print(f"✅ PDF extraction complete: {len(page_info)} pages, {len(full_text)} total chars")
            return full_text, page_info
    
    except Exception as e:
        print(f"❌ PDF extraction failed: {e}")
        raise
    

def extract_multimodal_from_pdf(file_path: str) -> tuple[str, list[dict], dict]:
    """
    Extract text AND multi-modal content from PDF with layout-aware processing
    
    Returns:
        tuple: (full_text, page_info_list, multimodal_content)
        - full_text: Complete document text
        - page_info_list: List of page information
        - multimodal_content: Dict with 'images', 'tables', 'markdown_full'
    """
    print(f"🚀 Starting full multi-modal extraction from: {file_path}")
    
    # Extract text (existing function)
    full_text, page_info = extract_text_from_pdf(file_path)
    
    # Extract multi-modal content with page information for layout awareness
    from workflow.multimodal_extractor import multimodal_extractor
    multimodal_content = multimodal_extractor.extract_all(file_path, page_info)  # ✨ Pass page_info
    
    print(f"✅ Multi-modal extraction complete")
    print(f"   Text: {len(full_text)} chars")
    print(f"   Markdown: {len(multimodal_content.get('markdown_full', ''))} chars")
    print(f"   Images: {len(multimodal_content['images'])}")
    print(f"   Tables: {len(multimodal_content['tables'])}")
    
    return full_text, page_info, multimodal_content


def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """
    Calculate semantic similarity between two text chunks using embeddings.
    Returns similarity score between 0 and 1.
    """
    if not text1.strip() or not text2.strip():
        return 0.0
    
    try:
        # Generate embeddings for both texts
        emb1 = model.embed_query(text1)
        emb2 = model.embed_query(text2)
        
        # Calculate cosine similarity
        import numpy as np
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return max(0.0, similarity)  # Ensure non-negative
    except Exception as e:
        print(f"Similarity calculation error: {e}")
        return 0.0

def deduplicate_chunks(chunks: list[str], similarity_threshold: float = 0.85) -> list[str]:
    """
    Remove similar chunks using FAST text-based deduplication.
    This avoids expensive embedding API calls during processing.
    
    Args:
        chunks: List of text chunks
        similarity_threshold: Not used - kept for compatibility
    
    Returns:
        List of deduplicated chunks
    """
    if len(chunks) <= 1:
        return chunks
    
    print(f"🚀 Using FAST text-based deduplication (avoiding API calls)")
    
    # Use simple text-based deduplication to avoid API calls
    seen_chunks = set()
    deduplicated = []
    
    for chunk in chunks:
        # Create a normalized fingerprint of the chunk
        normalized = ' '.join(chunk.lower().split())  # Normalize whitespace and case
        chunk_hash = hash(normalized[:200])  # Use first 200 chars as fingerprint
        
        if chunk_hash not in seen_chunks:
            seen_chunks.add(chunk_hash)
            deduplicated.append(chunk)
    
    print(f"📊 Fast deduplication: {len(chunks)} → {len(deduplicated)} chunks (-{len(chunks) - len(deduplicated)} duplicates)")
    return deduplicated

def truncate_to_token_limit(text: str, max_tokens: int = 8000) -> str:
    """
    Truncate text to stay within token limit for embeddings.
    Uses rough approximation: 1 token ≈ 4 characters.
    
    Args:
        text: Text to truncate
        max_tokens: Maximum token limit (default 8000 for text-embedding-3-small's 8191 limit)
        
    Returns:
        Truncated text that fits within token limit
    """
    # Rough estimate: 1 token ≈ 4 characters
    max_chars = max_tokens * 4
    
    if len(text) <= max_chars:
        return text
    
    # Truncate and add marker
    truncated = text[:max_chars]
    # Try to truncate at a word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.9:  # If we can find a space in the last 10%
        truncated = truncated[:last_space]
    
    return truncated + "\n\n[... content truncated due to size ...]"

def generate_embeddings(text: str) -> list:
    return model.embed_query(text)

def generate_embeddings_batch(texts: list[str], batch_size: int = 100) -> list[list]:
    """
    Generate embeddings for multiple texts in batches using direct OpenAI API.
    This ensures guaranteed batching and better performance.
    *** VERSION 3.0 - SMART CHUNKING + FALLBACK FOR OVERSIZED *** 
    
    Args:
        texts: List of text strings to embed (pre-chunked by smart_chunk_table)
        batch_size: Number of texts to process in each batch (OpenAI supports up to 2048)
        
    Returns:
        List of embedding vectors in the same order as input texts
    """
    print(f"🚀 [VERSION 3.0] Starting DIRECT OpenAI batch embedding for {len(texts)} texts (batch size: {batch_size})")
    print(f"🔧 Using direct openai_client.embeddings.create() for guaranteed batching")
    print(f"📋 All texts pre-chunked by smart_chunk_table (table oversizing handled)")
    
    # ✅ IMPROVED: Smart truncation with warnings (should rarely occur now)
    # Smart chunking handles large tables, so truncation should be extremely rare
    truncated_texts = []
    truncation_count = 0
    oversized_texts = []
    
    for idx, text in enumerate(texts):
        text_tokens = len(text) // 4  # Rough estimate: 1 token ≈ 4 chars
        if text_tokens > 8000:
            # Log warning - this should be VERY rare now with smart chunking
            oversized_texts.append((idx, text_tokens))
            truncated = truncate_to_token_limit(text, max_tokens=8000)
            truncation_count += 1
        else:
            truncated = text
        truncated_texts.append(truncated)
    
    if truncation_count > 0:
        print(f"⚠️  WARNING: {truncation_count} STILL oversized despite smart chunking:")
        for idx, tokens in oversized_texts[:5]:  # Show first 5
            print(f"   - Text {idx}: ~{tokens} tokens (double-check table parsing)")
        if len(oversized_texts) > 5:
            print(f"   ... and {len(oversized_texts) - 5} more")
    
    all_embeddings = []
    
    for i in range(0, len(truncated_texts), batch_size):
        batch = truncated_texts[i:i + batch_size]
        batch_num = i//batch_size + 1
        total_batches = (len(truncated_texts) + batch_size - 1)//batch_size
        
        print(f"⏳ Processing batch {batch_num}/{total_batches} with {len(batch)} texts...")
        
        try:
            # Use direct OpenAI API for guaranteed batching
            response = openai_client.embeddings.create(
                input=batch,
                model="text-embedding-3-small"
            )
            
            # Extract embeddings in order
            batch_embeddings = [embedding.embedding for embedding in response.data]
            all_embeddings.extend(batch_embeddings)
            print(f"✅ Batch {batch_num}/{total_batches} completed successfully ({len(batch_embeddings)} embeddings)")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Direct API batch {batch_num} failed: {error_msg}")
            
            # Check if error is token limit related
            if "8192 tokens" in error_msg or "maximum context length" in error_msg:
                print(f"⚠️  Token limit exceeded in batch - likely a single oversized text")
                print(f"🔄 Falling back to LangChain async method for batch {batch_num}")
                
                try:
                    # LangChain method handles oversized texts better
                    batch_embeddings = model.embed_documents(batch)
                    all_embeddings.extend(batch_embeddings)
                    print(f"✅ LangChain fallback successful for batch {batch_num}")
                except Exception as e2:
                    print(f"❌ LangChain batch also failed: {str(e2)}")
                    # Fallback to processing individually
                    batch_embeddings = _embed_texts_individually(batch, batch_num)
                    all_embeddings.extend(batch_embeddings)
            else:
                # Generic error - try LangChain
                print(f"🔄 Falling back to LangChain method for batch {batch_num}")
                
                try:
                    # Fallback to LangChain batch method
                    batch_embeddings = model.embed_documents(batch)
                    all_embeddings.extend(batch_embeddings)
                    print(f"✅ LangChain fallback successful for batch {batch_num}")
                except Exception as e2:
                    print(f"❌ LangChain batch also failed: {str(e2)}")
                    # Fallback to individual processing
                    batch_embeddings = _embed_texts_individually(batch, batch_num)
                    all_embeddings.extend(batch_embeddings)
    
    print(f"🎉 Batch embedding generation completed! Total embeddings: {len(all_embeddings)}")
    return all_embeddings

def _embed_texts_individually(texts: list[str], batch_num: int = 0) -> list[list]:
    """
    Fallback method: embed each text individually.
    Used when batch methods fail.
    """
    print(f"🔄 Final fallback: processing {len(texts)} texts individually")
    all_embeddings = []
    
    for j, text in enumerate(texts):
        try:
            embedding = model.embed_query(text)
            all_embeddings.append(embedding)
            if (j + 1) % 5 == 0:
                print(f"   ✓ Individual embedding {j+1}/{len(texts)}")
        except Exception as single_e:
            print(f"   ❌ Failed to embed text {j+1}: {single_e}")
            # Add a zero vector as placeholder
            all_embeddings.append([0.0] * 1536)  # OpenAI embedding dimension
    
    return all_embeddings

def find_chunk_page(chunk_start_pos: int, chunk_end_pos: int, page_info: list[dict]) -> int:
    """
    Find the actual page number for a chunk based on its position in the document.
    
    Args:
        chunk_start_pos: Starting position of chunk in full text
        chunk_end_pos: Ending position of chunk in full text
        page_info: List of page information dictionaries
    
    Returns:
        Page number (1-indexed) where the chunk primarily belongs
    """
    if not page_info:
        return 1
    
    chunk_mid_pos = (chunk_start_pos + chunk_end_pos) // 2
    
    # First, try exact match
    for page in page_info:
        if page["start_pos"] <= chunk_mid_pos <= page["end_pos"]:
            print(f"📄 Chunk at pos {chunk_start_pos}-{chunk_end_pos} → Page {page['page_num']}")
            return page["page_num"]
    
    # Fallback: find closest page
    min_distance = float('inf')
    closest_page = 1
    
    for page in page_info:
        distance = min(
            abs(chunk_mid_pos - page["start_pos"]),
            abs(chunk_mid_pos - page["end_pos"])
        )
        if distance < min_distance:
            min_distance = distance
            closest_page = page["page_num"]
    
    print(f"📄 Chunk at pos {chunk_start_pos}-{chunk_end_pos} → Closest Page {closest_page} (fallback)")
    
    # Safety check: ensure page number is reasonable
    max_page = max(p["page_num"] for p in page_info)
    if closest_page > max_page:
        print(f"⚠️  Page {closest_page} exceeds max page {max_page}, using page {max_page}")
        return max_page
    
    return closest_page

def chunk_text(text: str, chunk_size: int = 3000, chunk_overlap: int = 400) -> list[tuple[str, int, int]]:
    """
    Split text into chunks with position tracking.
    
    Optimized for financial documents:
    - chunk_size=3000 (~750 tokens) - larger for complete financial context
    - chunk_overlap=400 (~100 tokens, 13% overlap) - reduced waste vs 19%
    
    Returns:
        List of tuples: (chunk_text, start_position, end_position)
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],  # Added period-space for better sentence breaks
    )
    
    # Get chunks with metadata (includes start positions)
    chunks_with_metadata = text_splitter.create_documents([text])
    
    chunks_with_positions = []
    current_pos = 0
    
    for doc in chunks_with_metadata:
        chunk_text = doc.page_content
        start_pos = text.find(chunk_text, current_pos)
        if start_pos == -1:  # Fallback if exact match not found
            start_pos = current_pos
        end_pos = start_pos + len(chunk_text)
        
        chunks_with_positions.append((chunk_text, start_pos, end_pos))
        current_pos = start_pos + len(chunk_text) - chunk_overlap
    
    return chunks_with_positions

def store_embedding(text: str, metadata: dict, paper_id: str = None, embedding_type: str = "basic", page_info: list[dict] = None):
    """
    Store document embeddings in Qdrant with proper chunking and accurate page mapping.
    Also builds BM25 index for hybrid search.
    
    Args:
        text: Full document text
        metadata: Base metadata for all chunks
        paper_id: Paper ID for consistent chunk identification
        embedding_type: Either 'basic' (for immediate chat) or 'enhanced' (with AI insights)
        page_info: List of page information from PDF extraction
    """
    print(f"🎯 [STORE_EMBEDDING V2.0] Called with {len(text)} characters, paper_id: {paper_id}")
    print(f"🎯 About to process embeddings with BATCH PROCESSING v2.0")
    
    from workflow.db import qdrant
    from workflow.enhanced_search import enhanced_search
    import os
    import requests
    
    # If paper_id not provided, use metadata id
    if not paper_id and "id" in metadata:
        paper_id = metadata["id"]
    
    # Clear existing embeddings for this paper first
    if paper_id:
        try:
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue
            
            # First, count existing embeddings
            search_result = qdrant.scroll(
                collection_name="litwise_collection",
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="paper_id",
                            match=MatchValue(value=paper_id)
                        )
                    ]
                ),
                limit=1
            )
            
            existing_count = len(search_result[0]) if search_result else 0
            
            # Delete existing embeddings
            delete_result = qdrant.delete(
                collection_name="litwise_collection",
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="paper_id",  # Use paper_id field in payload
                            match=MatchValue(value=paper_id)
                        )
                    ]
                )
            )
            print(f"🗑️  Cleared {existing_count} existing embeddings for paper: {paper_id}")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not clear existing embeddings: {e}")
            # If collection doesn't exist, that's fine - we'll create it
    
    # Chunk the text with position tracking - PRODUCTION-OPTIMIZED FOR FINANCIAL DOCS
    chunks_with_positions = chunk_text(text, chunk_size=3000, chunk_overlap=400)
    print(f"Created {len(chunks_with_positions)} chunks for paper: {paper_id}")
    
    # ✅ REMOVED GARBAGE DEDUPLICATION - Financial documents have legitimate repetition
    # (e.g., same table headers across pages, recurring terminology, year-over-year comparisons)
    # Deduplication breaks financial context and loses critical data points
    print("🔄 Skipping deduplication to preserve financial context integrity...")
    
    # Use all chunks without deduplication
    valid_chunks_with_positions = [(chunk, start_pos, end_pos) for chunk, start_pos, end_pos in chunks_with_positions if chunk.strip()]
    print(f"📊 Valid chunks after filtering: {len(valid_chunks_with_positions)}")
    
    try:
        # Extract texts for batch embedding generation
        chunk_texts = [chunk for chunk, _, _ in valid_chunks_with_positions]
        
        # Generate all embeddings in batches
        print(f"🔄 Generating embeddings for {len(chunk_texts)} chunks using DIRECT OpenAI API batching...")
        all_embeddings = generate_embeddings_batch(chunk_texts, batch_size=100)
        
        if len(all_embeddings) != len(chunk_texts):
            print(f"Warning: Embedding count mismatch. Expected {len(chunk_texts)}, got {len(all_embeddings)}")
            return
        
        print(f"✅ Batch processing successful! Generated {len(all_embeddings)} embeddings")
        
    except Exception as e:
        print(f"❌ BATCH PROCESSING FAILED: {str(e)}")
        print(f"🔄 Falling back to legacy individual embedding processing...")
        import traceback
        traceback.print_exc()
        
        # Fallback to old approach
        valid_chunks_with_positions = [(chunk, start_pos, end_pos) for chunk, start_pos, end_pos in chunks_with_positions if chunk.strip()]
        all_embeddings = []
        
        for i, (chunk, start_pos, end_pos) in enumerate(valid_chunks_with_positions):
            try:
                embedding = model.embed_query(chunk)
                all_embeddings.append(embedding)
                if i % 10 == 0:
                    print(f"   Legacy embedding {i+1}/{len(valid_chunks_with_positions)}")
            except Exception as embed_e:
                print(f"   Failed embedding {i+1}: {embed_e}")
                all_embeddings.append([0.0] * 1536)
    
    # Prepare documents for BM25 indexing
    documents_for_bm25 = []
    
    # Store each chunk as a separate vector
    points = []
    max_page_in_doc = max(p["page_num"] for p in page_info) if page_info else 1
    
    for i, ((chunk, start_pos, end_pos), vector) in enumerate(zip(valid_chunks_with_positions, all_embeddings)):
        
        # Determine accurate page number
        if page_info:
            actual_page = find_chunk_page(start_pos, end_pos, page_info)
            
            # Validation: ensure page number is within document bounds
            if actual_page > max_page_in_doc:
                print(f"⚠️  Invalid page {actual_page} for chunk {i}, using page {max_page_in_doc}")
                actual_page = max_page_in_doc
            elif actual_page < 1:
                print(f"⚠️  Invalid page {actual_page} for chunk {i}, using page 1")
                actual_page = 1
        else:
            actual_page = 1  # Fallback when no page info
        
        # Create metadata for this chunk
        chunk_metadata = metadata.copy()
        chunk_metadata.update({
            "content": chunk,  # Store the actual chunk content
            "chunk_id": i,
            "total_chunks": len(valid_chunks_with_positions),
            "page": actual_page,  # Now accurate page number
            "start_position": start_pos,
            "end_position": end_pos,
            "paper_id": paper_id,  # Store paper_id in payload for filtering
            "embedding_type": embedding_type,  # Track if basic or enhanced
            "last_updated": metadata.get("created_at") or metadata.get("processing_date")
        })
        
        # Generate a proper UUID for this chunk
        chunk_uuid = str(uuid.uuid4())
        
        # Create point with valid UUID
        point = PointStruct(
            id=chunk_uuid,
            vector=vector,
            payload=chunk_metadata
        )
        points.append(point)
        
        # Add to BM25 documents
        documents_for_bm25.append({
            'content': chunk,
            'metadata': chunk_metadata,
            'chunk_id': i,
            'page': actual_page
        })
    
    if not points:
        print("Warning: No valid chunks created for embedding storage")
        return
    
    # Store all points in Qdrant
    collection = "litwise_collection"
    success = False
    last_exc = None
    
    # 1) Try qdrant.upsert
    if hasattr(qdrant, "upsert"):
        try:
            qdrant.upsert(collection_name=collection, points=points)
            success = True
            print(f"Successfully stored {len(points)} embedding chunks using upsert method")
        except Exception as e:
            last_exc = e
            print(f"Upsert method failed: {e}")
            
    # 2) Try qdrant.http.points_api.upsert (fallback)
    if not success and hasattr(qdrant, "http") and hasattr(qdrant.http, "points_api"):
        api = qdrant.http.points_api
        if hasattr(api, "upsert"):
            try:
                from qdrant_client.http.models import UpsertPoints
                upsert_body = UpsertPoints(points=points)
                api.upsert(collection_name=collection, body=upsert_body)
                success = True
                print(f"Successfully stored {len(points)} embedding chunks using HTTP API")
            except Exception as e:
                last_exc = e
                print(f"HTTP API method failed: {e}")
                
    # 3) Direct HTTP REST API fallback
    if not success:
        try:
            QDRANT_URL = os.getenv("QDRANT_URL")
            QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
            if not QDRANT_URL:
                raise RuntimeError("QDRANT_URL not configured in environment")
            url = QDRANT_URL.rstrip("/") + f"/collections/{collection}/points"
            headers = {"Content-Type": "application/json"}
            if QDRANT_API_KEY:
                headers.update({"api-key": QDRANT_API_KEY, "x-api-key": QDRANT_API_KEY})
            
            # Convert PointStruct objects to dict format
            payload = {
                "points": [{
                    "id": point.id,
                    "vector": point.vector,
                    "payload": point.payload
                } for point in points]
            }
            
            resp = requests.put(url, json=payload, headers=headers, timeout=30)
            if resp.status_code >= 400:
                last_exc = RuntimeError(f"Qdrant REST upsert failed: {resp.status_code} {resp.text}")
            else:
                success = True
                print(f"Successfully stored {len(points)} embedding chunks using REST API")
        except Exception as e:
            last_exc = e
            print(f"REST API method failed: {e}")
    
    if not success:
        print(f"CRITICAL: Failed to store embeddings using all methods. Last error: {last_exc}")
        raise RuntimeError(f"Failed to store embeddings: {last_exc}")
    
    # Build BM25 index for hybrid search
    if documents_for_bm25:
        try:
            print(f"Building BM25 index for {len(documents_for_bm25)} documents...")
            enhanced_search.build_bm25_index(paper_id, documents_for_bm25)
            print(f"✅ BM25 index built successfully for paper: {paper_id}")
        except Exception as e:
            print(f"Warning: Failed to build BM25 index: {e}")
            # Don't fail the entire operation if BM25 indexing fails


def store_multimodal_embeddings(
    text: str,
    multimodal_content: dict,
    metadata: dict,
    paper_id: str,
    page_info: list[dict]
):
    """
    Store text + image + table embeddings in Qdrant
    Uses same collection with 'type' field to distinguish content types
    
    Args:
        text: Full document text
        multimodal_content: Dict with 'images' and 'tables'
        metadata: Base metadata
        paper_id: Paper ID
        page_info: Page information
    """
    print(f"🎯 [MULTIMODAL STORE] Starting for paper: {paper_id}")
    
    from workflow.db import qdrant
    from workflow.vision_service import vision_service
    from workflow.enhanced_search import enhanced_search
    from qdrant_client.http.models import PointStruct
    
    # Step 1: Store TEXT embeddings (existing logic)
    print("📝 Step 1: Storing text embeddings...")
    chunks_with_positions = chunk_text(text, chunk_size=1000, chunk_overlap=250)
    chunk_texts = [chunk[0] for chunk in chunks_with_positions]
    deduplicated_texts = deduplicate_chunks(chunk_texts)
    
    # Filter to keep only deduplicated
    deduplicated_chunks_with_positions = []
    for dedup_text in deduplicated_texts:
        for original_chunk, start_pos, end_pos in chunks_with_positions:
            if original_chunk == dedup_text:
                deduplicated_chunks_with_positions.append((original_chunk, start_pos, end_pos))
                break
    
    valid_chunks = [(c, s, e) for c, s, e in deduplicated_chunks_with_positions if c.strip()]
    chunk_texts = [c for c, _, _ in valid_chunks]
    
    # Generate text embeddings in batch
    print(f"🔄 Generating embeddings for {len(chunk_texts)} text chunks...")
    text_embeddings = generate_embeddings_batch(chunk_texts, batch_size=100)
    
    points = []
    documents_for_bm25 = []
    
    # Create text points
    for i, ((chunk, start_pos, end_pos), vector) in enumerate(zip(valid_chunks, text_embeddings)):
        actual_page = find_chunk_page(start_pos, end_pos, page_info) if page_info else 1
        
        chunk_metadata = metadata.copy()
        chunk_metadata.update({
            "content": chunk,
            "chunk_id": f"text_{i}",
            "type": "text",  # IMPORTANT: Mark as text
            "page": actual_page,
            "paper_id": paper_id,
            "start_position": start_pos,
            "end_position": end_pos
        })
        
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload=chunk_metadata
        ))
        
        documents_for_bm25.append({
            'content': chunk,
            'metadata': chunk_metadata,
            'chunk_id': f"text_{i}",
            'page': actual_page
        })
    
    print(f"✅ Prepared {len(points)} text chunks")
    
    # Step 2: Process IMAGES with Vision API
    images = multimodal_content.get('images', [])
    if images:
        print(f"🖼️  Step 2: Processing {len(images)} images...")
        
        # Generate captions using GPT-4 Vision
        captioned_images = vision_service.caption_batch(images)
        
        # Generate embeddings for image captions
        image_captions = [img['caption'] for img in captioned_images]
        print(f"🔄 Generating embeddings for {len(image_captions)} image captions...")
        image_embeddings = generate_embeddings_batch(image_captions, batch_size=100)
        
        # Create image points
        for i, (img, vector) in enumerate(zip(captioned_images, image_embeddings)):
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                "content": img['caption'],
                "chunk_id": f"image_{i}",
                "type": "image",  # IMPORTANT: Mark as image
                "page": img['page'],
                "paper_id": paper_id,
                "image_hash": img['hash'],
                "image_width": img['width'],
                "image_height": img['height'],
                "image_format": img['format'],
                # Store base64 for retrieval (can be large!)
                "image_base64": img['image_base64'][:5000]  # Store truncated for size
            })
            
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload=chunk_metadata
            ))
            
            documents_for_bm25.append({
                'content': img['caption'],
                'metadata': chunk_metadata,
                'chunk_id': f"image_{i}",
                'page': img['page']
            })
        
        print(f"✅ Prepared {len(captioned_images)} image chunks")
    
    # Step 3: Process TABLES with AGGRESSIVE smart chunking for oversized tables
    tables = multimodal_content.get('tables', [])
    if tables:
        print(f"📊 Step 3: Processing {len(tables)} tables...")
        
        # Check for oversized tables and chunk them if needed
        all_table_texts = []
        all_table_chunks = []  # Track original table for each chunk
        
        def smart_chunk_table_by_rows(table_markdown: str, max_tokens: int = 6000) -> list[str]:
            """
            Intelligently split large tables by rows to stay under token limit.
            Uses aggressive chunking: 1 token ≈ 4 chars, so 6000 tokens ≈ 24000 chars
            But we validate actual token count and re-chunk if needed.
            """
            rows = table_markdown.split('\n')
            
            if len(rows) <= 3:  # Just header and maybe 1-2 rows
                return [table_markdown]
            
            header = rows[0]
            separator = rows[1]
            data_rows = rows[2:]
            
            # Start with conservative guess: 10-15 rows per chunk (more aggressive than 24K approach)
            rows_per_chunk = 12  # Start conservative
            chunks = []
            
            while True:
                current_chunks = []
                for chunk_start in range(0, len(data_rows), rows_per_chunk):
                    chunk_end = min(chunk_start + rows_per_chunk, len(data_rows))
                    chunk_rows = data_rows[chunk_start:chunk_end]
                    chunk_markdown = f"{header}\n{separator}\n" + "\n".join(chunk_rows)
                    current_chunks.append(chunk_markdown)
                
                # Validate all chunks
                all_valid = True
                for chunk in current_chunks:
                    chunk_tokens = len(chunk) // 4
                    if chunk_tokens > max_tokens:
                        all_valid = False
                        break
                
                if all_valid:
                    chunks = current_chunks
                    break
                else:
                    # Be more aggressive: reduce rows per chunk
                    rows_per_chunk = max(5, rows_per_chunk - 2)
                    if rows_per_chunk <= 5:
                        # Last resort: validate and warn about any oversized chunks
                        print(f"   ⚠️  WARNING: Could not chunk table small enough. Using 5-row chunks.")
                        chunks = []
                        for chunk_start in range(0, len(data_rows), 5):
                            chunk_end = min(chunk_start + 5, len(data_rows))
                            chunk_rows = data_rows[chunk_start:chunk_end]
                            chunk_markdown = f"{header}\n{separator}\n" + "\n".join(chunk_rows)
                            chunks.append(chunk_markdown)
                        break
            
            return chunks
        
        for table_idx, table in enumerate(tables):
            # Get table markdown
            table_markdown = table.get('markdown_table') or table['text_representation']
            table_tokens = len(table_markdown) // 4  # Rough estimate
            
            # Use aggressive threshold of 5000 tokens (more buffer before 8192 limit)
            if table_tokens > 5000:
                print(f"⚠️  Table {table_idx} is oversized ({table['row_count']} rows, ~{table_tokens} tokens). Applying smart chunking...")
                chunks = smart_chunk_table_by_rows(table_markdown, max_tokens=5000)
                
                for chunk_idx, chunk_markdown in enumerate(chunks):
                    chunk_tokens = len(chunk_markdown) // 4
                    all_table_texts.append(chunk_markdown)
                    all_table_chunks.append({
                        'original_table': table,
                        'table_idx': table_idx,
                        'chunk_idx': chunk_idx,
                        'row_range': 'split',
                        'actual_tokens': chunk_tokens
                    })
                    print(f"   ✅ Created chunk {chunk_idx+1} (~{chunk_tokens} tokens)")
            else:
                # Table is normal size, add as-is
                all_table_texts.append(table_markdown)
                all_table_chunks.append({
                    'original_table': table,
                    'table_idx': table_idx,
                    'chunk_idx': 0,
                    'row_range': 'full',
                    'actual_tokens': table_tokens
                })
        
        if all_table_texts:
            print(f"🔄 Generating embeddings for {len(all_table_texts)} table chunks...")
            table_embeddings = generate_embeddings_batch(all_table_texts, batch_size=100)
            
            # Create table points
            for table_text, chunk_info, vector in zip(all_table_texts, all_table_chunks, table_embeddings):
                table = chunk_info['original_table']
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "content": table_text,  # ✅ Use markdown table (or chunk of it)
                    "chunk_id": f"table_{chunk_info['table_idx']}_chunk_{chunk_info['chunk_idx']}",
                    "type": "table",  # IMPORTANT: Mark as table
                    "page": table.get('page', 1),
                    "paper_id": paper_id,
                    "table_hash": table['hash'],
                    "table_rows": table['row_count'],
                    "table_cols": table['col_count'],
                    "is_chunked": chunk_info['row_range'] != 'full',
                    "row_range": chunk_info['row_range'],
                    # Store structured data for precise retrieval
                    "table_headers": table['headers'],
                    "table_rows_data": table['rows'],  # ✅ Store ALL rows (not limited)
                    "table_markdown": table.get('markdown_table', ''),  # ✅ Full markdown
                    "table_format": "markdown" if 'markdown_table' in table else "text"
                })
                
                points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=chunk_metadata
                ))
                
                documents_for_bm25.append({
                    'content': table_text,  # ✅ Use chunked table content
                    'metadata': chunk_metadata,
                    'chunk_id': f"table_{chunk_info['table_idx']}_chunk_{chunk_info['chunk_idx']}",
                    'page': table.get('page', 1)
                })
        
        print(f"✅ Prepared {len(all_table_texts)} table chunks with smart chunking for oversized tables")
    
    # Step 4: Upsert all points to Qdrant in batches to avoid timeout
    print(f"💾 Step 4: Storing {len(points)} total chunks (text + images + tables) to Qdrant...")
    
    try:
        # Use batching for large uploads to avoid timeout
        batch_size = 150
        total_points = len(points)
        
        for i in range(0, total_points, batch_size):
            batch = points[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_points + batch_size - 1) // batch_size
            
            print(f"   Uploading batch {batch_num}/{total_batches} ({len(batch)} points)...")
            
            qdrant.upsert(
                collection_name="litwise_collection",
                points=batch,
                wait=False  # Don't wait - let Qdrant index asynchronously
            )
        
        print(f"✅ Successfully stored all multi-modal embeddings")
    except Exception as e:
        print(f"❌ Failed to store embeddings: {e}")
        raise
    
    # Step 5: Build BM25 index
    if documents_for_bm25:
        try:
            print(f"📚 Step 5: Building BM25 index for {len(documents_for_bm25)} documents...")
            enhanced_search.build_bm25_index(paper_id, documents_for_bm25)
            print(f"✅ BM25 index built successfully")
        except Exception as e:
            print(f"⚠️  BM25 indexing failed: {e}")
    
    print(f"🎉 Multi-modal embedding storage complete!")
    print(f"   Text chunks: {len([p for p in points if p.payload.get('type') == 'text'])}")
    print(f"   Image chunks: {len([p for p in points if p.payload.get('type') == 'image'])}")
    print(f"   Table chunks: {len([p for p in points if p.payload.get('type') == 'table'])}")


def store_markdown_embeddings(
    markdown_text: str,
    metadata: dict,
    paper_id: str,
    page_info: list[dict] = None
):
    """
    ✅ PRODUCTION-GRADE: Store embeddings using MarkdownElementNodeParser strategy.
    
    This function provides SUPERIOR indexing for financial documents by:
    - Keeping tables intact (no mid-table splits)
    - Preserving hierarchical structure (sections, headers)
    - Creating semantic boundaries at element level
    - Providing hierarchical context for better retrieval
    
    Args:
        markdown_text: Full markdown text from PDF extraction
        metadata: Base metadata for all nodes
        paper_id: Paper ID for filtering
        page_info: Page mapping information
    """
    print(f"📑 [MARKDOWN INDEXING] Using MarkdownElementNodeParser for {len(markdown_text)} chars")
    
    from workflow.markdown_indexer import markdown_parser
    from workflow.db import qdrant
    from workflow.enhanced_search import enhanced_search
    from qdrant_client.http.models import PointStruct, Filter, FieldCondition, MatchValue
    import uuid
    
    # Clear existing embeddings for this paper
    if paper_id:
        try:
            qdrant.delete(
                collection_name="litwise_collection",
                points_selector=Filter(
                    must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]
                )
            )
            print(f"🗑️  Cleared existing embeddings for paper: {paper_id}")
        except Exception as e:
            print(f"⚠️  Could not clear existing embeddings: {e}")
    
    # Parse markdown into element-based nodes
    nodes = markdown_parser.parse_markdown_to_nodes(
        markdown_text=markdown_text,
        page_info=page_info,
        base_metadata=metadata
    )
    
    print(f"📊 Created {len(nodes)} element-based nodes")
    print(f"   Tables: {len([n for n in nodes if n['type']=='table'])}")
    print(f"   Sections: {len([n for n in nodes if n['type']=='section'])}")
    
    # Generate embeddings for all nodes
    node_texts = [node['content'] for node in nodes]
    print(f"🔄 Generating embeddings for {len(node_texts)} nodes...")
    node_embeddings = generate_embeddings_batch(node_texts, batch_size=100)
    
    if len(node_embeddings) != len(node_texts):
        print(f"❌ Embedding count mismatch: {len(node_embeddings)} vs {len(node_texts)}")
        return
    
    # Create points for Qdrant
    points = []
    documents_for_bm25 = []
    
    for i, (node, vector) in enumerate(zip(nodes, node_embeddings)):
        # Merge base metadata with node metadata
        chunk_metadata = {**metadata, **node['metadata']}
        chunk_metadata.update({
            "content": node['content'],
            "chunk_id": f"node_{i}",
            "total_chunks": len(nodes),
            "paper_id": paper_id,
            "indexing_strategy": "markdown_element_parser",  # Track indexing method
            "node_type": node['type'],
            "element_type": node['element_type']
        })
        
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload=chunk_metadata
        ))
        
        documents_for_bm25.append({
            'content': node['content'],
            'metadata': chunk_metadata,
            'chunk_id': f"node_{i}",
            'page': chunk_metadata.get('page', 1)
        })
    
    # Store in Qdrant
    try:
        qdrant.upsert(collection_name="litwise_collection", points=points)
        print(f"✅ Stored {len(points)} markdown nodes in Qdrant")
    except Exception as e:
        print(f"❌ Failed to store markdown embeddings: {e}")
        raise
    
    # Build BM25 index
    try:
        enhanced_search.build_bm25_index(paper_id, documents_for_bm25)
        print(f"✅ BM25 index built for markdown nodes")
    except Exception as e:
        print(f"⚠️  BM25 indexing failed: {e}")
    
    print(f"🎉 Markdown embedding storage complete!")
    print(f"   Strategy: MarkdownElementNodeParser")
    print(f"   Table nodes: {len([p for p in points if p.payload.get('node_type')=='table'])}")
    print(f"   Section nodes: {len([p for p in points if p.payload.get('node_type')=='section'])}")
