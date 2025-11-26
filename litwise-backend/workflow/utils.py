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

def extract_text_from_pdf(file_path: str) -> tuple[str, list[dict]]:
    """
    Extract text from PDF with accurate page tracking.
    
    Returns:
        tuple: (full_text, page_info_list)
        - full_text: Complete document text
        - page_info_list: List of {"page_num": int, "start_pos": int, "end_pos": int, "text": str}
    """
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        full_text = ""
        page_info = []
        
        print(f"📖 PDF contains {len(reader.pages)} pages")
        
        for page_num, page in enumerate(reader.pages, 1):
            page_text = page.extract_text()
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

def generate_embeddings(text: str) -> list:
    return model.embed_query(text)

def generate_embeddings_batch(texts: list[str], batch_size: int = 100) -> list[list]:
    """
    Generate embeddings for multiple texts in batches using direct OpenAI API.
    This ensures guaranteed batching and better performance.
    *** VERSION 2.0 - DIRECT API BATCHING ***
    
    Args:
        texts: List of text strings to embed
        batch_size: Number of texts to process in each batch (OpenAI supports up to 2048)
        
    Returns:
        List of embedding vectors in the same order as input texts
    """
    print(f"🚀 [VERSION 2.0] Starting DIRECT OpenAI batch embedding for {len(texts)} texts (batch size: {batch_size})")
    print(f"🔧 Using direct openai_client.embeddings.create() for guaranteed batching")
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_num = i//batch_size + 1
        total_batches = (len(texts) + batch_size - 1)//batch_size
        
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
            print(f"❌ Direct API batch {batch_num} failed: {str(e)}")
            print(f"🔄 Falling back to LangChain method for batch {batch_num}")
            
            try:
                # Fallback to LangChain batch method
                batch_embeddings = model.embed_documents(batch)
                all_embeddings.extend(batch_embeddings)
                print(f"✅ LangChain fallback successful for batch {batch_num}")
            except Exception as e2:
                print(f"❌ LangChain batch also failed: {str(e2)}")
                print(f"🔄 Final fallback to individual processing for batch {batch_num}")
                
                # Final fallback: process individually
                for j, text in enumerate(batch):
                    try:
                        embedding = model.embed_query(text)
                        all_embeddings.append(embedding)
                        if j % 10 == 0:  # Log every 10th item
                            print(f"   ✓ Individual embedding {j+1}/{len(batch)} in batch {batch_num}")
                    except Exception as single_e:
                        print(f"   ❌ Failed to embed text {j+1}: {single_e}")
                        # Add a zero vector as placeholder
                        all_embeddings.append([0.0] * 1536)  # OpenAI embedding dimension
    
    print(f"🎉 Batch embedding generation completed! Total embeddings: {len(all_embeddings)}")
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

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[tuple[str, int, int]]:
    """
    Split text into chunks with position tracking.
    
    Returns:
        List of tuples: (chunk_text, start_position, end_position)
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
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
    
    # Chunk the text with position tracking
    chunks_with_positions = chunk_text(text, chunk_size=1000, chunk_overlap=200)
    print(f"Created {len(chunks_with_positions)} chunks for paper: {paper_id}")
    
    try:
        # Deduplicate chunks to improve quality
        print("🔄 Starting deduplication process...")
        chunk_texts = [chunk[0] for chunk in chunks_with_positions]
        deduplicated_texts = deduplicate_chunks(chunk_texts, similarity_threshold=0.85)
        print(f"✅ Deduplication completed: {len(chunk_texts)} -> {len(deduplicated_texts)} chunks")
        
        # Filter chunks_with_positions to keep only deduplicated ones
        deduplicated_chunks_with_positions = []
        for dedup_text in deduplicated_texts:
            for original_chunk, start_pos, end_pos in chunks_with_positions:
                if original_chunk == dedup_text:
                    deduplicated_chunks_with_positions.append((original_chunk, start_pos, end_pos))
                    break
        
        print(f"After deduplication: {len(deduplicated_chunks_with_positions)} unique chunks")
        
        # Filter out empty chunks first
        valid_chunks_with_positions = [(chunk, start_pos, end_pos) for chunk, start_pos, end_pos in deduplicated_chunks_with_positions if chunk.strip()]
        print(f"📊 Valid chunks after filtering: {len(valid_chunks_with_positions)}")
        
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