"""
services/rag/vector_store.py
=============================================================================
Qdrant Vector Store & Embeddings Service
=============================================================================
This module is responsible for:
1. Connecting to the Qdrant Cloud Vector Database.
2. Generating 1,536-dimensional dense vector embeddings using OpenAI.
3. Upserting document chunks with paper_id payloads.
4. Performing cosine similarity vector search with strict paper isolation.
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
import uuid

# Qdrant client models
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance, 
    VectorParams, 
    PointStruct, 
    Filter, 
    FieldCondition, 
    MatchValue
)

# OpenAI embeddings from LangChain
from langchain_openai import OpenAIEmbeddings

# Import DocumentChunk from Step 1.1
from services.rag.ingestion import DocumentChunk
# Re-use existing initialized Qdrant connection from workflow.db
from workflow.db import qdrant as default_qdrant_client

logger = logging.getLogger(__name__)

COLLECTION_NAME = "litwise_collection"
VECTOR_DIMENSION = 1536  # text-embedding-3-small produces 1,536 dimensions


class VectorStoreService:
    def __init__(self, qdrant_client: Optional[QdrantClient] = None):
        """
        Initialize Qdrant client and OpenAI Embeddings model.
        """
        # Re-use global connection or custom client
        self.client = qdrant_client or default_qdrant_client
        self.collection_name = COLLECTION_NAME
        
        # Initialize OpenAI text-embedding-3-small model
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY")
        )

    def ensure_collection_exists(self) -> None:
        """
        Check if the 'litwise_collection' collection exists in Qdrant.
        If not, create it with 1,536 dimensions and Cosine Distance.
        """
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=VECTOR_DIMENSION,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Collection '{self.collection_name}' created successfully")
            else:
                logger.info(f"Qdrant collection '{self.collection_name}' already exists")
        except Exception as e:
            logger.error(f"Error checking/creating Qdrant collection: {e}")

    async def upsert_chunks(self, chunks: List[DocumentChunk], batch_size: int = 50) -> int:
        """
        Generates vector embeddings for chunks and upserts them into Qdrant.
        
        Args:
            chunks (List[DocumentChunk]): Clean chunk objects from Step 1.1.
            batch_size (int): Max number of vectors to send per batch (prevents API timeouts).
            
        Returns:
            int: Total number of successfully upserted vectors.
        """
        if not chunks:
            logger.warning("No chunks provided for vector upsert.")
            return 0

        # Ensure collection exists before inserting
        self.ensure_collection_exists()

        total_upserted = 0
        total_chunks = len(chunks)
        logger.info(f"Starting vector embedding & upsert for {total_chunks} chunks...")

        # Process in batches of 50 to avoid memory spikes and API rate limits
        for i in range(0, total_chunks, batch_size):
            batch = chunks[i : i + batch_size]
            batch_texts = [c.content for c in batch]

            try:
                # 1. Generate embeddings in a background thread (network I/O call)
                embeddings_list = await asyncio.to_thread(
                    self.embeddings.embed_documents,
                    batch_texts
                )

                # 2. Package into Qdrant PointStruct objects
                points = []
                for chunk, vector in zip(batch, embeddings_list):
                    # Qdrant requires a valid UUID or integer as the point ID
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.chunk_id))

                    point = PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=chunk.to_dict()  # Stores content, page_number, paper_id
                    )
                    points.append(point)

                # 3. Upsert points into Qdrant Cloud
                await asyncio.to_thread(
                    self.client.upsert,
                    collection_name=self.collection_name,
                    points=points
                )

                total_upserted += len(points)
                logger.info(f"✅ Upserted batch: {total_upserted}/{total_chunks} chunks")

            except Exception as e:
                logger.error(f"❌ Failed to upsert batch {i} to {i+batch_size}: {e}")
                raise

        return total_upserted

    async def search(
        self, 
        query: str, 
        paper_id: str, 
        top_k: int = 5,
        score_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic vector search filtered to a specific research paper.
        
        Args:
            query (str): The user's question (e.g., "What was the conclusion?").
            paper_id (str): The ID of the paper to search inside (strict isolation).
            top_k (int): Number of most relevant passages to return (default: 5).
            score_threshold (float): Minimum cosine similarity score (0.0 to 1.0).
            
        Returns:
            List[Dict]: List of matching chunks with content, page_number, and score.
        """
        if not query or not paper_id:
            return []

        try:
            # 1. Convert the user's question into a 1,536-dimensional vector
            query_vector = await asyncio.to_thread(
                self.embeddings.embed_query,
                query
            )

            # 2. Build a strict Qdrant filter so we ONLY search this specific paper
            paper_filter = Filter(
                must=[
                    FieldCondition(
                        key="paper_id",
                        match=MatchValue(value=paper_id)
                    )
                ]
            )

            # 3. Query Qdrant for the closest vectors
            search_results = await asyncio.to_thread(
                self.client.query_points,
                collection_name=self.collection_name,
                query=query_vector,

                query_filter=paper_filter,
                limit=top_k,
                score_threshold=score_threshold
            )

            # 4. Format the results cleanly for the RAG retriever
            formatted_results = []
            for hit in search_results.points:
                payload = hit.payload or {}
                formatted_results.append({
                    "content": payload.get("content", ""),
                    "page_number": payload.get("page_number", 1),
                    "chunk_id": payload.get("chunk_id", ""),
                    "chunk_index": payload.get("chunk_index", 0),
                    "score": float(hit.score),  # Cosine similarity score (e.g., 0.85)
                    "paper_id": paper_id
                })

            logger.info(f"🔍 Vector search found {len(formatted_results)} results for paper {paper_id}")
            return formatted_results

        except Exception as e:
            logger.error(f"❌ Vector search error: {e}")
            return []

# Default singleton instance for easy import across the backend
vector_store_service = VectorStoreService()
