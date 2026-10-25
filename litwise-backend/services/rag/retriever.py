"""
=============================================================================
Litwise Hybrid Retriever (`services/rag/retriever.py`)
=============================================================================
This module implements the Hybrid Retrieval and Re-ranking layer:
1. BM25 Lexical Keyword Search (BM25Okapi with NLTK tokenization & stopwords)
2. Qdrant Dense Vector Search (via VectorStoreService)
3. Min-Max Score Normalization & Weighted Alpha Fusion (Vector + BM25)
4. Heuristic Re-ranking (verbatim exact match boost, query token overlap, deduplication)
"""

import re
import logging
from typing import List, Dict, Tuple, Optional, Any
from rank_bm25 import BM25Okapi
import nltk
from nltk.corpus import stopwords

from services.rag.vector_store import vector_store_service

logger = logging.getLogger(__name__)

# Ensure NLTK resources are available
def _init_nltk():
    try:
        stopwords.words("english")
    except LookupError:
        nltk.download("stopwords", quiet=True)

_init_nltk()


class HybridRetriever:
    """
    Hybrid Retriever that unifies Semantic Vector Search (Qdrant) and
    Lexical Keyword Search (BM25) with weighted alpha fusion and re-ranking.
    """

    def __init__(self, vector_store=vector_store_service):
        self.vector_store = vector_store
        # In-memory BM25 index per paper: paper_id -> BM25Okapi instance
        self.bm25_indices: Dict[str, BM25Okapi] = {}
        # Raw document stores per paper: paper_id -> list of chunk dicts
        self.document_stores: Dict[str, List[Dict[str, Any]]] = {}
        # English stopwords set for filtering noise tokens
        self.stop_words = set(stopwords.words("english"))
        logger.info("✅ HybridRetriever initialized with BM25 + Vector capabilities")

    def preprocess_text(self, text: str) -> List[str]:
        """
        Preprocesses raw text for BM25 indexing and querying:
        1. Converts to lowercase.
        2. Strips punctuation and special characters using regex.
        3. Splits into words and removes stopwords and single-character noise.
        """
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = clean.split()
        return [token for token in tokens if token not in self.stop_words and len(token) > 1]

    def index_paper(self, paper_id: str, chunks: List[Any]) -> None:
        """
        Builds and registers an in-memory BM25 index for a specific paper's chunks.
        Accepts either DocumentChunk objects or raw dictionaries.
        """
        if not chunks:
            logger.warning(f"No chunks provided to build BM25 index for paper: {paper_id}")
            return

        doc_dicts = []
        tokenized_corpus = []

        for chunk in chunks:
            # Support both DocumentChunk dataclass and plain dicts
            if hasattr(chunk, "to_dict"):
                doc = chunk.to_dict()
            elif isinstance(chunk, dict):
                doc = chunk
            else:
                doc = {
                    "content": getattr(chunk, "content", str(chunk)),
                    "page_number": getattr(chunk, "page_number", 1),
                    "chunk_id": getattr(chunk, "chunk_id", ""),
                    "paper_id": paper_id,
                }

            content = str(doc.get("content", "") or "")
            tokens = self.preprocess_text(content)
            tokenized_corpus.append(tokens)
            doc_dicts.append(doc)

        # Build BM25Okapi index
        self.bm25_indices[paper_id] = BM25Okapi(tokenized_corpus)
        self.document_stores[paper_id] = doc_dicts
        logger.info(f"✅ In-memory BM25 index built for paper '{paper_id}' ({len(doc_dicts)} chunks)")

    def bm25_search(self, paper_id: str, query: str, top_k: int = 50) -> List[Tuple[Dict[str, Any], float]]:
        """
        Performs BM25 lexical keyword search over the stored paper chunks.
        Returns a list of (document_dict, bm25_score) tuples sorted descending by score.
        """
        if paper_id not in self.bm25_indices:
            logger.debug(f"No BM25 index found in memory for paper_id='{paper_id}'")
            return []

        query_tokens = self.preprocess_text(query)
        if not query_tokens:
            return []

        bm25_scores = self.bm25_indices[paper_id].get_scores(query_tokens)
        documents = self.document_stores[paper_id]

        # Filter out chunks with 0 score (no keywords matched)
        scored_results = [
            (doc, float(score))
            for doc, score in zip(documents, bm25_scores)
            if score > 0.0
        ]

        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:top_k]

    @staticmethod
    def _normalize_scores(results: List[Tuple[Dict[str, Any], float]]) -> List[Tuple[Dict[str, Any], float]]:
        """
        Normalizes arbitrary scores into a [0.0, 1.0] range using Min-Max scaling.
        Formula: (score - min_score) / (max_score - min_score)
        """
        if not results:
            return []

        scores = [score for _, score in results]
        min_score, max_score = min(scores), max(scores)

        if max_score == min_score:
            # If all results have identical scores, assign 1.0
            return [(doc, 1.0) for doc, _ in results]

        normalized = []
        for doc, score in results:
            norm = (score - min_score) / (max_score - min_score)
            normalized.append((doc, norm))

        return normalized

    def combine_search_results(
        self,
        vector_results: List[Tuple[Dict[str, Any], float]],
        bm25_results: List[Tuple[Dict[str, Any], float]],
        alpha: float = 0.7
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Combines Dense Vector and Sparse BM25 search results using weighted fusion.
        Formula: Final Score = (alpha * vector_score) + ((1 - alpha) * bm25_score)
        """
        # Normalize both result sets independently to [0.0, 1.0]
        norm_vector = self._normalize_scores(vector_results)
        norm_bm25 = self._normalize_scores(bm25_results)

        combined: Dict[str, Dict[str, Any]] = {}

        # 1. Process vector results
        for doc, v_score in norm_vector:
            chunk_id = doc.get("chunk_id") or str(id(doc))
            combined[chunk_id] = {
                "doc": doc,
                "vector_score": v_score,
                "bm25_score": 0.0
            }

        # 2. Merge BM25 results
        for doc, b_score in norm_bm25:
            chunk_id = doc.get("chunk_id") or str(id(doc))
            if chunk_id in combined:
                combined[chunk_id]["bm25_score"] = b_score
            else:
                combined[chunk_id] = {
                    "doc": doc,
                    "vector_score": 0.0,
                    "bm25_score": b_score
                }

        # 3. Apply Alpha Fusion formula
        fused_results = []
        for item in combined.values():
            final_score = (alpha * item["vector_score"]) + ((1.0 - alpha) * item["bm25_score"])
            fused_results.append((item["doc"], final_score))

        fused_results.sort(key=lambda x: x[1], reverse=True)
        return fused_results

    def rerank(
        self,
        query: str,
        results: List[Tuple[Dict[str, Any], float]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Re-ranks candidate chunks using lexical heuristics:
        1. Query token overlap bonus (proportion of query words found in chunk)
        2. Verbatim exact-match boost (awards chunks containing exact search phrases)
        3. Deduplication (filters out near-identical content)
        """
        if not results:
            return []

        query_tokens = set(self.preprocess_text(query))
        query_raw_words = set(w.lower() for w in query.split() if len(w) > 2)

        enhanced = []
        seen_hashes = set()

        for doc, score in results:
            content = doc.get("content", "")
            content_lower = content.lower()

            # Deduplication: skip near-duplicate content by prefix hash
            content_prefix_hash = hash(content[:100])
            if content_prefix_hash in seen_hashes:
                continue
            seen_hashes.add(content_prefix_hash)

            content_tokens = set(self.preprocess_text(content))

            # 1. Tokenized overlap bonus (up to +0.35)
            overlap = len(query_tokens.intersection(content_tokens))
            overlap_bonus = (overlap / max(len(query_tokens), 1)) * 0.35

            # 2. Verbatim exact match boost
            verbatim_matches = sum(1 for word in query_raw_words if word in content_lower)
            verbatim_boost = 0.35 if verbatim_matches >= 2 else (0.25 if verbatim_matches == 1 else 0.0)

            final_score = score + overlap_bonus + verbatim_boost

            # Build standardized output format with page number attribution
            result_doc = dict(doc)
            result_doc["score"] = round(final_score, 4)
            # Ensure page_number is always present
            if "page_number" not in result_doc:
                result_doc["page_number"] = result_doc.get("metadata", {}).get("page_number", 1)

            enhanced.append(result_doc)

        # Sort by final re-ranked score descending
        enhanced.sort(key=lambda x: x["score"], reverse=True)
        return enhanced[:top_k]

    async def retrieve(
        self,
        query: str,
        paper_id: Optional[str] = None,
        top_k: int = 5,
        alpha: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Unified Hybrid Retrieval pipeline:
        1. Executes Qdrant Vector Search.
        2. Executes in-memory BM25 Search (if paper_id indexed).
        3. Combines via Weighted Alpha Fusion.
        4. Re-ranks candidates and returns the top-k chunks with page attribution.
        """
        logger.info(f"🔍 Hybrid retrieval query: '{query}' (paper_id={paper_id}, top_k={top_k}, alpha={alpha})")

        # 1. Dense Semantic Vector Search via Qdrant (fetch candidate pool of 25)
        candidate_k = max(top_k * 5, 25)
        raw_vector_matches = await self.vector_store.search(
            query=query,
            paper_id=paper_id or "",
            top_k=candidate_k
        )

        # Convert dictionary list into (doc, score) tuples so it matches BM25 format
        vector_results = [
            (doc, float(doc.get("score", 0.0)))
            for doc in raw_vector_matches
        ]

        # 2. Sparse Lexical BM25 Search (if paper_id provided and indexed)
        bm25_results = []
        if paper_id:
            bm25_results = self.bm25_search(paper_id=paper_id, query=query, top_k=candidate_k)

        # 3. If no BM25 results exist (e.g. server restarted or cross-paper search),
        # gracefully fall back to vector results
        if not bm25_results:
            logger.info("Running pure vector retrieval (no BM25 results available)")
            fused_candidates = vector_results
        else:
            logger.info(f"Fusing {len(vector_results)} vector results + {len(bm25_results)} BM25 results (alpha={alpha})")
            fused_candidates = self.combine_search_results(vector_results, bm25_results, alpha=alpha)

        # 4. Re-rank top candidates to produce final top-k
        final_ranked = self.rerank(query=query, results=fused_candidates, top_k=top_k)
        logger.info(f"✅ Hybrid retriever returning {len(final_ranked)} top-ranked chunks")
        return final_ranked


# Singleton instance ready for application-wide use
hybrid_retriever = HybridRetriever()