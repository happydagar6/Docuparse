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
        nltk.data.find('tokenizers/punkt') # Used for tokenization (splitting text into words)
        nltk.data.find('corpora/stopwords') # Used for removing common words (like 'the', 'is', 'in')
    except LookupError:
        print("Downloading NLTK data...") # If the data is not found, download it
        nltk.download('punkt', quiet=True) # Download the punkt tokenizer. What is this nltk and punkt ? 
        # nltk is a python library for natural language processing. 
        # punkt is a tokenizer that splits text into words. 
        nltk.download('stopwords', quiet=True) # Download the stopwords corpus
        # stopwords are common words that are not important for search. 

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
        # [LITWISE RAG LOGIC]: Query Expansion
        # Why we do this: If a user types "ML", the AI might miss documents that only say "Machine Learning".
        # This function catches those missed opportunities by expanding the search query before hitting the database.
        
        # 1. Initialize a list with the user's original query as the first element
        expanded_terms = [query]  
        
        # 2. Convert the entire query to lowercase so our matching is case-insensitive
        query_lower = query.lower()
        
        # 3. Split the query into individual words (e.g., "what is ML" -> ["what", "is", "ml"])
        words = query_lower.split()
        
        # 4. Loop through each word to check for acronyms
        for word in words:
            # Convert back to uppercase to match our QUERY_EXPANSIONS dictionary keys
            word_upper = word.upper()
            
            # If the uppercase word exists in our dictionary (like "ML" or "AI")
            if word_upper in QUERY_EXPANSIONS:
                # Add the expanded version (e.g., "machine learning") to our list of terms
                expanded_terms.extend(QUERY_EXPANSIONS[word_upper])
        
        # 5. Loop through again to add synonyms
        added_synonyms = 0
        for word in words:
            # Check if the word has synonyms AND we haven't added too many yet (limit to 3 to prevent overwhelming the search)
            if word in self.synonym_map and added_synonyms < 3:  
                # Add only the top 2 synonyms for this word to our list
                expanded_terms.extend(self.synonym_map[word][:2])  
                added_synonyms += 1  # Increment our safety counter
        
        # 6. Join all the collected terms back into a single long string separated by spaces
        expanded_query = ' '.join(expanded_terms)
        
        # 7. If the query actually changed, print a log message for debugging
        if expanded_query != query:
            print(f"🔍 Query expanded: '{query}' → '{expanded_query[:100]}...'")
        
        # 8. Return the massive, expanded query string to the search engine
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
        # [LITWISE RAG LOGIC]: BM25 Lexical Search (Keyword Matching)
        # Why we do this: Vector search is great for "vibes" and meanings, but terrible at exact matches 
        # (like finding a specific patient ID or chemical formula). BM25 acts like a traditional Google Search
        # to guarantee exact keywords are found.
        
        # 1. Safety check: If we haven't built a BM25 index for this specific paper yet, return nothing.
        if paper_id not in self.bm25_indices:
            return []
        
        # 2. Preprocess the user's query (remove punctuation, lowercase it, tokenize it)
        query_tokens = self.preprocess_text(query)
        
        # 3. If the query is completely empty after preprocessing (e.g., they only typed stopwords like "the"), return nothing.
        if not query_tokens:
            return []
        
        # 4. Use the BM25 algorithm to assign a mathematical score to every document chunk based on keyword frequency.
        bm25_scores = self.bm25_indices[paper_id].get_scores(query_tokens)
        
        # 5. Retrieve the actual raw text documents for this paper.
        documents = self.document_stores[paper_id]
        
        # 6. Create a paired list of (Document, Score) using Python's zip function.
        scored_results = [
            (doc, float(score)) 
            for doc, score in zip(documents, bm25_scores)
            if score > 0  # Only keep documents that actually had a keyword match (score > 0)
        ]
        
        # 7. Sort the results in descending order (highest BM25 score first)
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # 8. Return only the top 'K' best matching results to save memory
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
        
        # [LITWISE RAG LOGIC]: Vector Search (Semantic Meaning)
        # Why we do this: This converts the user's text into an array of 1,536 numbers (an embedding).
        # It then asks Qdrant to find the closest matching numbers in the database using Cosine Distance.
        # This allows us to find answers even if the exact keywords don't match.
        
        # 1. Ask the OpenAI embeddings model to convert the user's text query into a mathematical vector.
        # We wrap this in asyncio.to_thread because the embedding API call is a blocking network request.
        query_embedding = await asyncio.to_thread(
            embeddings_model.embed_query, 
            query
        )
        
        # 2. Initialize a Qdrant query filter. This is like a WHERE clause in SQL.
        query_filter = None
        
        # 3. If a specific paper_id was provided, we construct the filter.
        if paper_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="paper_id",  # We only want chunks from this specific paper
                        match=MatchValue(value=paper_id)
                    )
                ]
            )
        
        # 4. Execute the actual Vector Search against the Qdrant database
        try:
            search_result = await asyncio.to_thread(
                qdrant_client.query_points,
                collection_name="litwise_collection", # Our specific collection
                query=query_embedding,                # The math vector we generated
                limit=top_k,                          # Max results to return
                query_filter=query_filter             # The paper_id filter we built
            )
        except Exception as e:
            # If the database connection fails, catch the error so the app doesn't crash
            print(f"⚠️ Vector search failed: {e}")
            return []
        
        # 5. Create an empty list to store our final formatted results
        vector_results = []
        
        # 6. Loop through the raw results returned by Qdrant
        for result in search_result.points:
            # 7. Extract the metadata payload that we attached when we uploaded the document
            doc = {
                'content': result.payload.get('content', ''),
                'metadata': result.payload,
                'chunk_id': result.payload.get('chunk_id', 0),
                'page': result.payload.get('page', 1),
                'paper_id': result.payload.get('paper_id', 'unknown')
            }
            # 8. Append a tuple of (Document, Score) to our results list
            vector_results.append((doc, float(result.score)))
        
        # 9. Return the formatted list of semantic matches
        return vector_results
    
    def combine_search_results(self, vector_results: List[Tuple[Dict, float]], 
                             bm25_results: List[Tuple[Dict, float]],
                             alpha: float = 0.7) -> List[Tuple[Dict, float]]:
        """Combine vector and BM25 results using weighted fusion"""
        # [LITWISE RAG LOGIC]: Hybrid Search Fusion
        # Why we do this: We just got two lists of results (one from BM25, one from Vector).
        # We need to combine them fairly. We normalize both scores so they are between 0 and 1,
        # then we merge them using a formula: (Alpha * VectorScore) + ((1 - Alpha) * BM25Score)
        # This gives us the absolute best of both worlds!
        
        # 1. Helper function to normalize scores to a [0.0, 1.0] scale
        def normalize_scores(results):
            if not results:
                return []
            
            # Extract all the raw scores from the results
            scores = [score for _, score in results]
            min_score, max_score = min(scores), max(scores)
            
            # Prevent division by zero if all scores are identical
            if max_score == min_score:
                return [(doc, 1.0) for doc, _ in results]
            
            normalized = []
            # Apply Min-Max Normalization formula: (score - min) / (max - min)
            for doc, score in results:
                norm_score = (score - min_score) / (max_score - min_score)
                normalized.append((doc, norm_score))
            
            return normalized
        
        # 2. Normalize both sets of results independently so they can be fairly compared
        norm_vector_results = normalize_scores(vector_results)
        norm_bm25_results = normalize_scores(bm25_results)
        
        # 3. Create a dictionary to hold the combined scores, using chunk_id to prevent duplicates
        combined_scores = {}
        
        # 4. First, insert all the Vector Search results into our dictionary
        for doc, score in norm_vector_results:
            chunk_id = doc.get('chunk_id', id(doc))
            combined_scores[chunk_id] = {
                'doc': doc,
                'vector_score': score,
                'bm25_score': 0.0 # Default BM25 to 0 (in case it wasn't found by keyword search)
            }
        
        # 5. Next, insert or update with the BM25 Search results
        for doc, score in norm_bm25_results:
            chunk_id = doc.get('chunk_id', id(doc))
            # If the vector search ALREADY found this chunk, just update the bm25_score!
            if chunk_id in combined_scores:
                combined_scores[chunk_id]['bm25_score'] = score
            else:
                # If vector search missed it, add it fresh
                combined_scores[chunk_id] = {
                    'doc': doc,
                    'vector_score': 0.0,
                    'bm25_score': score
                }
        
        # 6. Apply the Fusion Formula: Final Score = (Vector * Alpha) + (BM25 * (1 - Alpha))
        # Example: if Alpha is 0.7, Vector is worth 70% of the final score, BM25 is worth 30%.
        final_results = []
        for scores in combined_scores.values():
            final_score = (alpha * scores['vector_score']) + ((1 - alpha) * scores['bm25_score'])
            final_results.append((scores['doc'], final_score))
        
        # 7. Sort the combined list so the absolute best matches are at the top
        final_results.sort(key=lambda x: x[1], reverse=True)
        
        # 8. Return the fused list!
        return final_results
    
    async def simple_rerank(self, query: str, results: List[Tuple[Dict, float]],
                           top_k: int = 25, boost_tables: bool = False) -> List[Tuple[Dict, float]]:
        """
        Re-ranking with three scoring layers:

        1. Tokenized overlap bonus (raised cap 0.2→0.35) — rewards chunks whose
           preprocessed tokens overlap with the query.
        2. Verbatim exact-match boost (+0.25) — awards chunks that contain the raw
           query words literally (catches specific terms/acronyms the tokenizer strips).
        3. Table boosting for financial queries (unchanged).
        """
        if not results:
            return []

        print(f"Re-ranking {len(results)} candidates using query term overlap + verbatim match...")

        try:
            query_tokens = set(self.preprocess_text(query))
            # Raw lower-cased words from query for verbatim matching (no stopword removal)
            query_raw_words = set(w.lower() for w in query.split() if len(w) > 2)

            enhanced_results = []
            seen_content = set()

            for doc, score in results:
                content = doc.get('content', '')
                content_tokens = set(self.preprocess_text(content))
                content_lower = content.lower()

                # Skip near-duplicate content
                content_hash = hash(content[:100])
                if content_hash in seen_content:
                    continue
                seen_content.add(content_hash)

                # 1. Tokenized overlap bonus (cap raised 0.2→0.35)
                overlap = len(query_tokens.intersection(content_tokens))
                overlap_bonus = overlap / max(len(query_tokens), 1) * 0.35

                # 2. Verbatim exact-match boost (+0.25 if any raw query word found literally)
                verbatim_matches = sum(1 for w in query_raw_words if w in content_lower)
                verbatim_boost = 0.25 if verbatim_matches > 0 else 0.0
                # Scale up if many words match verbatim
                if verbatim_matches > 2:
                    verbatim_boost = 0.35

                # 3. Content quality bonus (unchanged)
                content_quality = min(len(content) / 1000, 1.0) * 0.1

                # 4. Table boost for financial queries (unchanged)
                table_bonus = 0.0
                if boost_tables:
                    metadata = doc.get('metadata', {})
                    content_type = metadata.get('type', '')
                    if content_type == 'table':
                        table_bonus = 0.3
                    table_type = metadata.get('table_type', '')
                    if table_type in ['balance_sheet', 'income_statement', 'cash_flow', 'segment_report']:
                        table_bonus += 0.2

                final_score = score + overlap_bonus + verbatim_boost + content_quality + table_bonus
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
            top_k = max(50, top_k * 2)
            print(f"💰 Financial query detected! Increasing top_k: {original_top_k} → {top_k}")

        # Detect specific/precise queries to use a keyword-heavier alpha
        is_specific_query = self._is_specific_query(query)
        # Dynamic alpha: shift toward BM25 (keywords) for precise term queries
        alpha = 0.5 if is_specific_query else 0.7
        if is_specific_query:
            print(f"🔍 Specific/technical query detected! Using keyword-heavy alpha={alpha}")

        search_type = "cross-paper" if paper_id is None else f"paper-specific ({paper_id})"
        print(f"🔍 Starting hybrid search ({search_type}) for: '{query}'")

        # Step 1: Expand query if enabled
        expanded_query = self.expand_query(query) if use_query_expansion else query

        # Step 2: Retrieve larger candidate set
        candidate_size = 50 if not is_financial_query else 75

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
            vector_results = await vector_task
            bm25_results = []
            if paper_id:
                print(f"⚠️ BM25 index not found for paper {paper_id}, using vector-only search")

        print(f"📊 Vector search: {len(vector_results)} results")
        print(f"📊 BM25 search: {len(bm25_results)} results")

        # Step 3: Combine results with dynamic alpha
        combined_results = self.combine_search_results(vector_results, bm25_results, alpha=alpha)
        print(f"🔗 Combined: {len(combined_results)} unique results (vector {int(alpha*100)}% / BM25 {int((1-alpha)*100)}%)")

        # Step 4: Re-rank with overlap + verbatim boost + table boosting
        final_results = await self.simple_rerank(query, combined_results, top_k, boost_tables=is_financial_query)

        # Step 5: Apply diversity scoring for cross-paper search
        if paper_id is None and len(final_results) > 0:
            final_results = self._apply_diversity_scoring(final_results, top_k)
        
        # Convert to final format
        enhanced_documents = []
        for i, (doc, score) in enumerate(final_results):
            doc_copy = doc.copy()
            # Clamp score to [0, 1] range to prevent negative percentages
            clamped_score = max(0.0, min(1.0, float(score)))
            doc_copy['score'] = clamped_score  # Use 'score' for frontend compatibility
            doc_copy['relevance_score'] = clamped_score  # Keep for backwards compatibility
            doc_copy['rank'] = i + 1
            doc_copy['search_method'] = 'hybrid+rerank' if bm25_results else 'vector+rerank'
            enhanced_documents.append(doc_copy)
        
        print(f"✅ Enhanced hybrid search found {len(enhanced_documents)} relevant results")
        return enhanced_documents
    
    def _is_financial_query(self, query: str) -> bool:
        """Detect if query is asking for financial/numeric data"""
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

    def _is_specific_query(self, query: str) -> bool:
        """
        Detect queries that ask for a specific technical term, acronym, quoted phrase,
        or proper noun — these benefit from a higher BM25 weight (lower alpha).

        Heuristics:
        - Query contains ALL-CAPS words (acronyms: GAN, LSTM, Rule 86B)
        - Query contains quoted phrases ("exact term")
        - Query is short and mostly noun-like (3 words or fewer after stopwords)
        - Query contains digits (version numbers, section references, years)
        """
        import re
        # Quoted phrase
        if re.search(r'["\'].+["\']', query):
            return True
        # Contains digits (e.g. "Rule 86B", "Section 4.2", "gpt-4")
        if re.search(r'\d', query):
            return True
        # Contains all-caps token of 2+ chars (acronym)
        tokens = query.split()
        if any(t.isupper() and len(t) >= 2 for t in tokens):
            return True
        # Very short precise query (1-3 meaningful words) — likely looking for a specific term
        meaningful_words = [t for t in tokens if len(t) > 3]
        if len(meaningful_words) <= 3:
            return True
        return False

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