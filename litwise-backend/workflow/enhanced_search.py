# Enhanced Search System with Hybrid Retrieval and Re-ranking

from typing import List, Dict, Tuple, Optional
import numpy as np
import asyncio
from rank_bm25 import BM25Okapi
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re
import os
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Download required NLTK data
def setup_nltk():
    """Download required NLTK datasets"""
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        print("Downloading NLTK data...")
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)

# Initialize NLTK on import
setup_nltk()

class EnhancedSearchSystem:
    """
    Advanced search system combining:
    1. Vector similarity search (semantic)
    2. BM25 keyword search (lexical) 
    3. Similarity-based re-ranking
    """
    
    def __init__(self):
        self.bm25_indices = {}  # paper_id -> BM25Okapi instance
        self.document_stores = {}  # paper_id -> list of documents
        self.stop_words = set(stopwords.words('english'))
        
        print("✅ Enhanced search system initialized with BM25 + Vector hybrid search")
    
    def preprocess_text(self, text: str) -> List[str]:
        """Preprocess text for BM25 indexing"""
        # Convert to lowercase and remove special characters
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Tokenize
        try:
            tokens = word_tokenize(text)
        except:
            # Fallback tokenization
            tokens = text.split()
        
        # Remove stopwords and short tokens
        tokens = [token for token in tokens if token not in self.stop_words and len(token) > 2]
        
        return tokens
    
    def build_bm25_index(self, paper_id: str, documents: List[Dict]) -> None:
        """Build BM25 index for a specific paper"""
        print(f"Building BM25 index for paper: {paper_id}")
        
        # Extract and preprocess document contents
        doc_texts = [doc.get('content', '') for doc in documents]
        tokenized_docs = [self.preprocess_text(text) for text in doc_texts]
        
        # Create BM25 index
        self.bm25_indices[paper_id] = BM25Okapi(tokenized_docs)
        self.document_stores[paper_id] = documents
        
        print(f"✅ BM25 index built for {len(documents)} documents")
    
    def bm25_search(self, paper_id: str, query: str, top_k: int = 50) -> List[Tuple[Dict, float]]:
        """Perform BM25 keyword search"""
        if paper_id not in self.bm25_indices:
            return []
        
        # Preprocess query
        query_tokens = self.preprocess_text(query)
        if not query_tokens:
            return []
        
        # Get BM25 scores
        bm25_scores = self.bm25_indices[paper_id].get_scores(query_tokens)
        documents = self.document_stores[paper_id]
        
        # Create scored results
        scored_results = [
            (doc, float(score)) 
            for doc, score in zip(documents, bm25_scores)
            if score > 0
        ]
        
        # Sort by BM25 score
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        return scored_results[:top_k]
    
    async def vector_search(self, qdrant_client, paper_id: str, query: str, 
                          embeddings_model, top_k: int = 50) -> List[Tuple[Dict, float]]:
        """Perform vector similarity search"""
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        
        # Generate query embedding
        query_embedding = await asyncio.to_thread(
            embeddings_model.embed_query, 
            query
        )
        
        # Search in Qdrant
        search_result = await asyncio.to_thread(
            qdrant_client.query_points,
            collection_name="litwise_collection",
            query=query_embedding,
            limit=top_k,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="paper_id",
                        match=MatchValue(value=paper_id)
                    )
                ]
            )
        )
        
        # Convert to document format
        vector_results = []
        for result in search_result.points:
            doc = {
                'content': result.payload.get('content', ''),
                'metadata': result.payload,
                'chunk_id': result.payload.get('chunk_id', 0),
                'page': result.payload.get('page', 1)
            }
            vector_results.append((doc, float(result.score)))
        
        return vector_results
    
    def combine_search_results(self, vector_results: List[Tuple[Dict, float]], 
                             bm25_results: List[Tuple[Dict, float]],
                             alpha: float = 0.7) -> List[Tuple[Dict, float]]:
        """Combine vector and BM25 results using weighted fusion"""
        # Normalize scores to [0, 1] range
        def normalize_scores(results):
            if not results:
                return []
            
            scores = [score for _, score in results]
            min_score, max_score = min(scores), max(scores)
            
            if max_score == min_score:
                return [(doc, 1.0) for doc, _ in results]
            
            normalized = []
            for doc, score in results:
                norm_score = (score - min_score) / (max_score - min_score)
                normalized.append((doc, norm_score))
            
            return normalized
        
        # Normalize both result sets
        norm_vector_results = normalize_scores(vector_results)
        norm_bm25_results = normalize_scores(bm25_results)
        
        # Combine results by chunk_id to avoid duplicates
        combined_scores = {}
        
        # Add vector results
        for doc, score in norm_vector_results:
            chunk_id = doc.get('chunk_id', id(doc))
            combined_scores[chunk_id] = {
                'doc': doc,
                'vector_score': score,
                'bm25_score': 0.0
            }
        
        # Add BM25 results
        for doc, score in norm_bm25_results:
            chunk_id = doc.get('chunk_id', id(doc))
            if chunk_id in combined_scores:
                combined_scores[chunk_id]['bm25_score'] = score
            else:
                combined_scores[chunk_id] = {
                    'doc': doc,
                    'vector_score': 0.0,
                    'bm25_score': score
                }
        
        # Calculate combined scores
        final_results = []
        for chunk_data in combined_scores.values():
            combined_score = (
                alpha * chunk_data['vector_score'] + 
                (1 - alpha) * chunk_data['bm25_score']
            )
            final_results.append((chunk_data['doc'], combined_score))
        
        # Sort by combined score
        final_results.sort(key=lambda x: x[1], reverse=True)
        
        return final_results
    
    async def simple_rerank(self, query: str, results: List[Tuple[Dict, float]], 
                           top_k: int = 15) -> List[Tuple[Dict, float]]:
        """Simple re-ranking based on query term overlap and diversity"""
        if not results:
            return []
        
        print(f"Re-ranking {len(results)} candidates using query term overlap...")
        
        try:
            query_tokens = set(self.preprocess_text(query))
            
            enhanced_results = []
            seen_content = set()
            
            for doc, score in results:
                content = doc.get('content', '')
                content_tokens = set(self.preprocess_text(content))
                
                # Skip very similar content (simple deduplication)
                content_hash = hash(content[:100])  # First 100 chars as fingerprint
                if content_hash in seen_content:
                    continue
                seen_content.add(content_hash)
                
                # Calculate query term overlap bonus
                overlap = len(query_tokens.intersection(content_tokens))
                overlap_bonus = overlap / max(len(query_tokens), 1) * 0.2  # 20% bonus max
                
                # Calculate content quality score (longer content often better)
                content_quality = min(len(content) / 1000, 1.0) * 0.1  # 10% bonus max
                
                final_score = score + overlap_bonus + content_quality
                enhanced_results.append((doc, final_score))
            
            # Sort by enhanced score
            enhanced_results.sort(key=lambda x: x[1], reverse=True)
            
            print(f"✅ Re-ranked to top {min(len(enhanced_results), top_k)} results")
            return enhanced_results[:top_k]
            
        except Exception as e:
            print(f"Re-ranking failed: {e}, returning original order")
            return results[:top_k]
    
    async def hybrid_search(self, qdrant_client, embeddings_model, paper_id: str, 
                          query: str, top_k: int = 15) -> List[Dict]:
        """
        Complete hybrid search pipeline:
        1. Vector + BM25 search (retrieve ~50 candidates)
        2. Simple re-ranking (narrow to top_k)
        """
        print(f"🔍 Starting hybrid search for: '{query}' in paper: {paper_id}")
        
        # Step 1: Retrieve larger candidate set
        candidate_size = 50
        
        # Parallel vector and BM25 search
        vector_task = self.vector_search(
            qdrant_client, paper_id, query, embeddings_model, candidate_size
        )
        
        bm25_task = asyncio.to_thread(
            self.bm25_search, paper_id, query, candidate_size
        )
        
        vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)
        
        print(f"📊 Vector search: {len(vector_results)} results")
        print(f"📊 BM25 search: {len(bm25_results)} results")
        
        # Step 2: Combine results (70% vector, 30% BM25)
        combined_results = self.combine_search_results(vector_results, bm25_results, alpha=0.7)
        print(f"🔗 Combined: {len(combined_results)} unique results")
        
        # Step 3: Re-rank with simple overlap scoring
        final_results = await self.simple_rerank(query, combined_results, top_k)
        
        # Convert to final format
        enhanced_documents = []
        for i, (doc, score) in enumerate(final_results):
            doc_copy = doc.copy()
            doc_copy['relevance_score'] = score
            doc_copy['rank'] = i + 1
            doc_copy['search_method'] = 'hybrid+rerank'
            enhanced_documents.append(doc_copy)
        
        print(f"✅ Hybrid search complete: {len(enhanced_documents)} final results")
        return enhanced_documents

# Global instance
enhanced_search = EnhancedSearchSystem()