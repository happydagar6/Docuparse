# Enhanced Search System with Hybrid Retrieval and Re-ranking

from typing import List, Dict, Tuple, Optional
import asyncio
from rank_bm25 import BM25Okapi
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re
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

# Query expansion mappings for common acronyms and synonyms
QUERY_EXPANSIONS = {
    # Machine Learning & AI
    'ML': ['machine learning', 'ML'],
    'AI': ['artificial intelligence', 'AI'],
    'DL': ['deep learning', 'DL'],
    'NN': ['neural network', 'NN'],
    'CNN': ['convolutional neural network', 'CNN'],
    'RNN': ['recurrent neural network', 'RNN'],
    'LSTM': ['long short-term memory', 'LSTM'],
    'GAN': ['generative adversarial network', 'GAN'],
    'RL': ['reinforcement learning', 'RL'],
    
    # Natural Language Processing
    'NLP': ['natural language processing', 'NLP'],
    'LLM': ['large language model', 'LLM'],
    'GPT': ['generative pre-trained transformer', 'GPT'],
    'BERT': ['bidirectional encoder representations from transformers', 'BERT'],
    
    # Computer Vision
    'CV': ['computer vision', 'CV'],
    'YOLO': ['you only look once', 'YOLO'],
    'R-CNN': ['region-based convolutional neural network', 'R-CNN'],
    
    # General CS
    'API': ['application programming interface', 'API'],
    'UI': ['user interface', 'UI'],
    'UX': ['user experience', 'UX'],
    'DB': ['database', 'DB'],
    'SQL': ['structured query language', 'SQL'],
    
    # Research Methods
    'RCT': ['randomized controlled trial', 'RCT'],
    'SLR': ['systematic literature review', 'SLR'],
}

# Synonym groups for query expansion
SYNONYM_GROUPS = [
    ['method', 'approach', 'technique', 'methodology'],
    ['result', 'outcome', 'finding', 'conclusion'],
    ['model', 'architecture', 'framework', 'system'],
    ['improve', 'enhance', 'optimize', 'boost'],
    ['analyze', 'examine', 'investigate', 'study'],
    ['dataset', 'data', 'corpus'],
    ['accuracy', 'performance', 'effectiveness'],
    ['train', 'learn', 'fit'],
    ['predict', 'forecast', 'estimate'],
]

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
        
        # Build synonym lookup for faster query expansion
        self.synonym_map = {}
        for group in SYNONYM_GROUPS:
            for word in group:
                self.synonym_map[word] = [w for w in group if w != word]
        
        print("✅ Enhanced search system initialized with BM25 + Vector hybrid search")
        print(f"📚 Loaded {len(QUERY_EXPANSIONS)} acronym expansions and {len(SYNONYM_GROUPS)} synonym groups")
    
    def expand_query(self, query: str) -> str:
        """
        Expand query with acronyms and synonyms for better recall
        
        Args:
            query: Original search query
            
        Returns:
            Expanded query with additional terms
        """
        expanded_terms = [query]  # Start with original query
        query_lower = query.lower()
        words = query_lower.split()
        
        # 1. Expand acronyms
        for word in words:
            word_upper = word.upper()
            if word_upper in QUERY_EXPANSIONS:
                expanded_terms.extend(QUERY_EXPANSIONS[word_upper])
        
        # 2. Add synonyms for key terms (limit to avoid over-expansion)
        added_synonyms = 0
        for word in words:
            if word in self.synonym_map and added_synonyms < 3:  # Limit synonyms
                expanded_terms.extend(self.synonym_map[word][:2])  # Add top 2 synonyms
                added_synonyms += 1
        
        expanded_query = ' '.join(expanded_terms)
        
        if expanded_query != query:
            print(f"🔍 Query expanded: '{query}' → '{expanded_query[:100]}...'")
        
        return expanded_query
    
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
    
    async def vector_search(self, qdrant_client, paper_id: Optional[str], query: str, 
                          embeddings_model, top_k: int = 50) -> List[Tuple[Dict, float]]:
        """
        Perform vector similarity search
        
        Args:
            qdrant_client: Qdrant client instance
            paper_id: Paper ID to filter by (None for cross-paper search)
            query: Search query
            embeddings_model: Model for generating embeddings
            top_k: Number of results to return
            
        Returns:
            List of (document, score) tuples
        """
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        
        # Generate query embedding
        query_embedding = await asyncio.to_thread(
            embeddings_model.embed_query, 
            query
        )
        
        # Build filter if paper_id provided
        query_filter = None
        if paper_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="paper_id",
                        match=MatchValue(value=paper_id)
                    )
                ]
            )
        
        # Search in Qdrant
        try:
            search_result = await asyncio.to_thread(
                qdrant_client.query_points,
                collection_name="litwise_collection",
                query=query_embedding,
                limit=top_k,
                query_filter=query_filter
            )
        except Exception as e:
            print(f"⚠️ Vector search failed: {e}")
            return []
        
        # Convert to document format
        vector_results = []
        for result in search_result.points:
            doc = {
                'content': result.payload.get('content', ''),
                'metadata': result.payload,
                'chunk_id': result.payload.get('chunk_id', 0),
                'page': result.payload.get('page', 1),
                'paper_id': result.payload.get('paper_id', 'unknown')
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
                           top_k: int = 25, boost_tables: bool = False) -> List[Tuple[Dict, float]]:
        """
        Simple re-ranking based on query term overlap and diversity
        
        ✅ FIX: Add table boosting for financial queries
        
        Args:
            query: User query
            results: Combined search results
            top_k: Number of results to return
            boost_tables: Whether to boost table chunks (for financial queries)
        """
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
                
                # ✅ FIX: Boost table chunks for financial queries
                table_bonus = 0.0
                if boost_tables:
                    metadata = doc.get('metadata', {})
                    content_type = metadata.get('type', '')
                    
                    # Strong boost for table chunks
                    if content_type == 'table':
                        table_bonus = 0.3  # 30% bonus for tables
                    
                    # Additional boost for financial table types
                    table_type = metadata.get('table_type', '')
                    if table_type in ['balance_sheet', 'income_statement', 'cash_flow', 'segment_report']:
                        table_bonus += 0.2  # Extra 20% for financial statements
                
                final_score = score + overlap_bonus + content_quality + table_bonus
                enhanced_results.append((doc, final_score))
            
            # Sort by enhanced score
            enhanced_results.sort(key=lambda x: x[1], reverse=True)
            
            print(f"✅ Re-ranked to top {min(len(enhanced_results), top_k)} results")
            return enhanced_results[:top_k]
            
        except Exception as e:
            print(f"Re-ranking failed: {e}, returning original order")
            return results[:top_k]
    
    async def hybrid_search(self, qdrant_client, embeddings_model, paper_id: Optional[str], 
                          query: str, top_k: int = 25, use_query_expansion: bool = True) -> List[Dict]:
        """
        Complete hybrid search pipeline with smart top_k for financial queries:
        1. Query expansion (acronyms + synonyms)
        2. Vector + BM25 search (retrieve ~50 candidates)
        3. Simple re-ranking (narrow to top_k)
        
        ✅ FIX: Increase top_k for financial/table queries to prevent data loss
        
        Args:
            qdrant_client: Qdrant client instance
            embeddings_model: Model for generating embeddings
            paper_id: Paper ID to search within (None for cross-paper search)
            query: Search query
            top_k: Number of final results (will be adjusted for financial queries)
            use_query_expansion: Whether to expand query with synonyms/acronyms
            
        Returns:
            List of enhanced documents with relevance scores
        """
        # ✅ FIX: Detect financial queries and increase top_k
        is_financial_query = self._is_financial_query(query)
        if is_financial_query:
            original_top_k = top_k
            top_k = max(50, top_k * 2)  # At least 50 results for financial queries
            print(f"💰 Financial query detected! Increasing top_k: {original_top_k} → {top_k}")
        
        search_type = "cross-paper" if paper_id is None else f"paper-specific ({paper_id})"
        print(f"🔍 Starting hybrid search ({search_type}) for: '{query}'")
        
        # Step 1: Expand query if enabled
        expanded_query = self.expand_query(query) if use_query_expansion else query
        
        # Step 2: Retrieve larger candidate set
        candidate_size = 50 if not is_financial_query else 75  # More candidates for financial
        
        # Parallel vector and BM25 search
        vector_task = self.vector_search(
            qdrant_client, paper_id, expanded_query, embeddings_model, candidate_size
        )
        
        # BM25 only works for single paper (requires pre-built index)
        if paper_id and paper_id in self.bm25_indices:
            bm25_task = asyncio.to_thread(
                self.bm25_search, paper_id, expanded_query, candidate_size
            )
            vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)
        else:
            # Cross-paper search: vector only (BM25 requires per-paper indexes)
            vector_results = await vector_task
            bm25_results = []
            if paper_id:
                print(f"⚠️ BM25 index not found for paper {paper_id}, using vector-only search")
        
        print(f"📊 Vector search: {len(vector_results)} results")
        print(f"📊 BM25 search: {len(bm25_results)} results")
        
        # Step 3: Combine results (70% vector, 30% BM25)
        combined_results = self.combine_search_results(vector_results, bm25_results, alpha=0.7)
        print(f"🔗 Combined: {len(combined_results)} unique results")
        
        # Step 4: Re-rank with simple overlap scoring + table boosting
        final_results = await self.simple_rerank(query, combined_results, top_k, boost_tables=is_financial_query)
        
        # Step 5: Add diversity scoring for cross-paper search
        if paper_id is None and len(final_results) > 0:
            final_results = self._apply_diversity_scoring(final_results, top_k)
        
        # Convert to final format
        enhanced_documents = []
        for i, (doc, score) in enumerate(final_results):
            doc_copy = doc.copy()
            doc_copy['score'] = score  # Use 'score' for frontend compatibility
            doc_copy['relevance_score'] = score  # Keep for backwards compatibility
            doc_copy['rank'] = i + 1
            doc_copy['search_method'] = 'hybrid+rerank' if bm25_results else 'vector+rerank'
            enhanced_documents.append(doc_copy)
        
        print(f"✅ Enhanced hybrid search found {len(enhanced_documents)} relevant results")
        return enhanced_documents
    
    def _is_financial_query(self, query: str) -> bool:
        """
        Detect if query is asking for financial/numeric data
        
        ✅ FIX: Identify queries that need comprehensive table retrieval
        """
        query_lower = query.lower()
        
        financial_keywords = [
            'margin', 'revenue', 'profit', 'sales', 'utop', 'ebitda', 'ebit',
            'cash flow', 'capex', 'opex', 'balance sheet', 'assets', 'liabilities',
            'equity', 'debt', 'ratio', 'calculate', 'compare', 'growth',
            'change', 'delta', 'difference', 'reconcil', 'movement',
            'yoy', 'year-over-year', 'bps', 'basis points', 'percentage',
            'increase', 'decrease', 'total', 'net', 'gross',
            'financial', 'accounting', 'fiscal', 'quarter', 'annual'
        ]
        
        return any(kw in query_lower for kw in financial_keywords)
    
    def _apply_diversity_scoring(self, results: List[Tuple[Dict, float]], 
                                 top_k: int) -> List[Tuple[Dict, float]]:
        """
        Apply diversity scoring to prefer results from different papers
        
        Args:
            results: List of (document, score) tuples
            top_k: Number of results to return
            
        Returns:
            Re-ranked results with diversity bonus
        """
        paper_counts = {}
        diverse_results = []
        
        for doc, score in results:
            paper_id = doc.get('paper_id', 'unknown')
            
            # Apply penalty for papers already represented
            count = paper_counts.get(paper_id, 0)
            diversity_penalty = 0.1 * count  # 10% penalty per existing result from same paper
            adjusted_score = score * (1.0 - diversity_penalty)
            
            diverse_results.append((doc, adjusted_score))
            paper_counts[paper_id] = count + 1
        
        # Re-sort by adjusted scores
        diverse_results.sort(key=lambda x: x[1], reverse=True)
        
        print(f"🎯 Applied diversity scoring: {len(set(paper_counts.keys()))} unique papers in results")
        return diverse_results[:top_k]

# Global instance
enhanced_search = EnhancedSearchSystem()