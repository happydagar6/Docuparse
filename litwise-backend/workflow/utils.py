# PDF extraction + embeddings

import PyPDF2
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from qdrant_client.http.models import PointStruct
import uuid


model = OpenAIEmbeddings(model="text-embedding-3-small")

def extract_text_from_pdf(file_path: str) -> str:
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        return "\n".join(page.extract_text() for page in reader.pages)
    

def generate_embeddings(text: str) -> list:
    return model.embed_query(text)

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    return text_splitter.split_text(text)

def store_embedding(text: str, metadata: dict, paper_id: str = None):
    """
    Store document embeddings in Qdrant with proper chunking.
    
    Args:
        text: Full document text
        metadata: Base metadata for all chunks
        paper_id: Paper ID for consistent chunk identification
    """
    from workflow.db import qdrant
    import os
    import requests
    
    # If paper_id not provided, use metadata id
    if not paper_id and "id" in metadata:
        paper_id = metadata["id"]
    
    # Clear existing embeddings for this paper first
    if paper_id:
        try:
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue
            qdrant.delete(
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
            print(f"Cleared existing embeddings for paper: {paper_id}")
        except Exception as e:
            print(f"Warning: Could not clear existing embeddings: {e}")
    
    # Chunk the text for better retrieval
    chunks = chunk_text(text, chunk_size=1000, chunk_overlap=200)
    print(f"Created {len(chunks)} chunks for paper: {paper_id}")
    
    # Store each chunk as a separate vector
    points = []
    for i, chunk in enumerate(chunks):
        if not chunk.strip():  # Skip empty chunks
            continue
            
        # Generate embedding for this chunk
        try:
            vector = generate_embeddings(chunk)
        except Exception as e:
            print(f"Failed to generate embedding for chunk {i}: {e}")
            continue
        
        # Create metadata for this chunk
        chunk_metadata = metadata.copy()
        chunk_metadata.update({
            "content": chunk,  # Store the actual chunk content
            "chunk_id": i,
            "total_chunks": len(chunks),
            "page": i + 1,  # Approximate page number
            "paper_id": paper_id  # Store paper_id in payload for filtering
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