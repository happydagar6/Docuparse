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

def store_embedding(text: str, metadata: dict):
    from workflow.db import qdrant
    import os
    import requests
    vector = generate_embeddings(text)
    point = PointStruct(id=uuid.uuid4().hex, vector=vector, payload=metadata)
    collection = "litwise_collection"
    # Try several upsert methods for compatibility
    success = False
    last_exc = None
    # 1) Try qdrant.upsert
    if hasattr(qdrant, "upsert"):
        try:
            qdrant.upsert(collection_name=collection, points=[point])
            success = True
        except Exception as e:
            last_exc = e
    # 2) Try qdrant.http.points_api.upsert
    if not success and hasattr(qdrant, "http") and hasattr(qdrant.http, "points_api"):
        api = qdrant.http.points_api
        if hasattr(api, "upsert"):
            try:
                from qdrant_client.http.models import UpsertPoints
                upsert_body = UpsertPoints(points=[point])
                api.upsert(collection_name=collection, body=upsert_body)
                success = True
            except Exception as e:
                last_exc = e
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
            # Convert PointStruct to dict
            payload = {
                "points": [{
                    "id": point.id,
                    "vector": point.vector,
                    "payload": point.payload
                }]
            }
            resp = requests.put(url, json=payload, headers=headers, timeout=15)
            if resp.status_code >= 400:
                last_exc = RuntimeError(f"Qdrant REST upsert failed: {resp.status_code} {resp.text}")
            else:
                success = True
        except Exception as e:
            last_exc = e
    if not success:
        print(f"Failed to upsert embedding to Qdrant: {last_exc}")