"""
=============================================================================
Literature Review Service (`services/literature_review_service.py`)
=============================================================================
This service generates comprehensive, grounded Literature Reviews across 
multiple research papers.

Key Architectural Innovations:
1. Closed-World System Prompt: Enforces zero hallucinations by restricting 
   the LLM's knowledge strictly to the provided source texts.
2. Query Decomposition (`decompose_topic`): Breaks a broad topic into 4-6 
   specialized sub-queries to prevent semantic dilution during vector search.
3. Hybrid Retrieval & Quota Balancing (`get_paper_context`): Guarantees 
   fair representation for each sub-query.
4. Cross-Encoder Reranking (`rerank_chunks`): Uses FlashRank (ms-marco-MiniLM-L-12-v2)
   to re-score vector results against the original query.
5. Structured JSON Output: Returns validated Pydantic models for the UI.
=============================================================================
"""

import json
import uuid
import asyncio
from datetime import datetime, timezone
from typing import List, Dict
from openai import OpenAI
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from flashrank import Ranker, RerankRequest
from models.literature_review import (
    LiteratureReviewRequest,
    LiteratureReviewResponse,
    ReviewContent,
    ThemeAnalysis,
    ReviewStyle,
)
import os

# =============================================================================
# CLOSED-WORLD SYSTEM PROMPT FOR LITERATURE REVIEW
# =============================================================================
# This prompt enforces strict grounding - the AI can ONLY use information
# explicitly present in the provided source texts. No pre-trained knowledge.
# =============================================================================

CLOSED_WORLD_SYSTEM_PROMPT = """You are a literature review assistant operating under STRICT CLOSED-WORLD CONSTRAINTS.

## CRITICAL RULES - VIOLATION MEANS FAILURE

### 1. ABSOLUTE GROUNDING REQUIREMENT
- You have TOTAL AMNESIA about the world. You know NOTHING except what is written in the <SOURCES> section below.
- If a fact, name, date, statistic, or claim is NOT explicitly stated in the provided sources, it DOES NOT EXIST for you.
- Do NOT use any pre-trained knowledge, general facts, or common knowledge about the topic.
- Pretend you have never heard of the topic before reading these sources.

### 2. FORBIDDEN ACTIONS (Immediate Failure)
- ❌ Adding historical context not in the sources (e.g., "founded in 2009", "created by X")
- ❌ Mentioning people, companies, or events not explicitly named in the sources
- ❌ Stating statistics or numbers not directly quoted from the sources
- ❌ Making claims about industry adoption, popularity, or usage not in the sources
- ❌ Comparing to technologies/methods not discussed in the sources
- ❌ Adding "well-known" facts that seem obvious but aren't in the text

### 3. MANDATORY CITATION FORMAT
- Every factual claim MUST include an inline citation: [Source: "Paper Title"]
- If you cannot cite a source for a claim, DELETE that claim entirely.
- Acceptable: "The event-driven architecture enables non-blocking I/O [Source: 'Node.js Technical Overview']."
- UNACCEPTABLE: "Node.js was created by Ryan Dahl." (No source = hallucination)

### 4. HANDLING INSUFFICIENT CONTEXT
If the provided sources do not contain enough information about the requested topic:
- State clearly: "The provided sources contain limited information about [specific aspect]."
- Only write about what IS covered in the sources.
- Do NOT pad the review with outside knowledge to meet word counts.
- A shorter, accurate review is better than a longer, hallucinated one.

### 5. WRITING STYLE
- Academic, objective, and scholarly tone
- Narrative prose (avoid bullet points in the main text)
- Synthesize across sources rather than summarizing each one separately
- Use smooth transitions between ideas
- Every paragraph should have at least one citation

### 6. SELF-CHECK BEFORE RESPONDING
Before outputting, verify each sentence:
□ Can I point to the exact text in <SOURCES> that supports this?
□ Am I adding any "common knowledge" not in the sources?
□ Does every factual claim have a [Source: "Title"] citation?
□ Would a researcher be able to verify this in the provided PDFs?

If any answer is NO, revise or remove that content.

You are a GROUNDED EXTRACTION SYSTEM, not a knowledge base. Output ONLY what the sources say."""


class LiteratureReviewService:
    def __init__(self):
        """Initialize OpenAI, Qdrant Vector DB, Embeddings, and FlashRank Reranker."""
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
            check_compatibility=False,
        )
        # Initialize OpenAI text-embedding-3-small for 1536-dimensional embeddings
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # Initialize FlashRank cross-encoder reranker (ms-marco-MiniLM-L-12-v2) for precision scoring
        print("🔄 Initializing FlashRank reranker...")
        self.reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/flashrank_cache")
        print("✅ FlashRank reranker initialized")
        
    async def decompose_topic(self, topic: str) -> List[str]:
        """
        STAGE 1: Query Decomposition
        --------------------------------------------------
        Decomposes a broad topic into 4-6 targeted sub-queries.
        
        Why this is important:
        A broad query like 'Restrictions on X' causes 'semantic dilution' in vector search.
        By breaking it down into Conceptual, Procedural, Keyword Sniper, Inverse, and Clause queries,
        we retrieve specific paragraphs covering all angles of the topic.
        """
        decomposition_prompt = f"""You are a Legal Document Search Query Generator. Your task is to decompose a user's topic into 4-6 highly targeted search queries optimized for retrieving specific clauses from legal/regulatory documents.

USER TOPIC: {topic}

## ANALYSIS INSTRUCTIONS

1. **Detect Query Intent**: Analyze the topic for intent signals:
   - RESTRICTION intent: words like "restrictions", "limits", "cannot", "prohibited", "blocked"
   - CONDITION intent: words like "conditions", "requirements", "eligibility", "criteria"
   - PROCEDURE intent: words like "how to", "process", "steps", "claim", "apply"
   - EXCEPTION intent: words like "exceptions", "exempt", "exclusions", "unless"
   - PENALTY intent: words like "penalty", "fine", "consequence", "violation"

2. **Generate Query Spectrum**: Create queries ranging from broad to specific:
   
   a) **Conceptual Query** (Broad): Natural language describing the general topic
   b) **Procedural Query** (Process-focused): How the mechanism works, steps involved
   c) **Keyword Sniper Query** (Specific): Combine topic terms with HIGH-SIGNAL legal keywords:
      - For restrictions: "prohibited", "not allowed", "blocked", "cap", "ceiling", "maximum", "limit", "threshold", "exceeding", "ineligible"
      - For conditions: "provided that", "subject to", "where", "if", "shall", "must", "mandatory", "required"
      - For exceptions: "except", "unless", "notwithstanding", "exemption", "exclusion"
      - For amounts: "percentage", "ratio", "amount", "value", "quantum", "proportion"
   d) **Negative/Inverse Query**: Search for what is NOT allowed or disqualified
   e) **Clause-Targeting Query**: Include terms like "rule", "section", "clause", "provision", "regulation", "subsection" combined with topic keywords

3. **Query Construction Rules**:
   - Each query should contain 4-8 words
   - Include core topic keywords in EVERY query for context
   - Use specific legal/regulatory vocabulary, not conversational language
   - Avoid questions - use declarative keyword phrases
   - Target exact phrases that would appear in legal text

## OUTPUT FORMAT
Return ONLY a JSON array of 4-6 search query strings. No explanations.
["query 1", "query 2", "query 3", "query 4", ...]"""

        try:
            from typing import Any
            response: Any = self.client.chat.completions.create(
                model="gpt-5-mini-2025-08-07",
                messages=[{"role": "user", "content": decomposition_prompt}],
                max_completion_tokens=800,
            )
            
            result = (response.choices[0].message.content or "").strip()
            # Clean up response if wrapped in markdown code blocks
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            
            sub_queries = json.loads(result)
            print(f"📋 Decomposed topic into {len(sub_queries)} sub-queries:")
            for i, sq in enumerate(sub_queries, 1):
                print(f"   {i}. {sq}")
            return sub_queries
            
        except Exception as e:
            print(f"⚠️ Topic decomposition failed: {e}, using original topic")
            return [topic]  # Fallback to original topic
    
    async def semantic_search_chunks(
        self, paper_id: str, query: str, top_k: int = 15
    ) -> List[Dict]:
        """
        STAGE 2: Vector Similarity Search
        --------------------------------------------------
        Generates OpenAI embeddings for a sub-query and executes a Cosine Similarity 
        search against Qdrant, filtered by the specific `paper_id`.
        """
        try:
            # Generate query embedding vector (1536 dimensions)
            query_embedding = await asyncio.to_thread(
                self.embeddings.embed_query, query
            )
            
            # Query Qdrant vector database with paper_id payload filter
            search_result = await asyncio.to_thread(
                self.qdrant_client.query_points,
                collection_name="litwise_collection",
                query=query_embedding,
                limit=top_k,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="paper_id", match=MatchValue(value=paper_id)
                        )
                    ]
                ),
            )
            
            results = []
            for point in search_result.points:
                payload = point.payload or {}
                results.append({
                    "content": payload.get("content", ""),
                    "chunk_id": payload.get("chunk_id", 0),
                    "page": payload.get("page", 1),
                    "score": point.score,
                })
            
            return results
            
        except Exception as e:
            print(f"⚠️ Semantic search failed for query '{query[:50]}...': {e}")
            return []

    def rerank_chunks(
        self, chunks: List[Dict], query: str, top_k: int = 50
    ) -> List[Dict]:
        """
        STAGE 3: Cross-Encoder Re-ranking (FlashRank)
        --------------------------------------------------
        Reranks vector candidates using FlashRank (`ms-marco-MiniLM-L-12-v2`) against the original query.
        
        Why this is important:
        Vector search (Cosine) finds broad similarity, but Cross-Encoders evaluate full text context 
        jointly with the query. This boosts precise matches (like specific clauses or numbers).
        """
        if not chunks:
            return []
        
        try:
            # Format passages for FlashRank Reranker
            passages = [
                {"id": i, "text": chunk["content"], "meta": chunk}
                for i, chunk in enumerate(chunks)
            ]
            
            # Execute Cross-Encoder re-ranking
            rerank_request = RerankRequest(query=query, passages=passages)
            reranked_results = self.reranker.rerank(rerank_request)
            
            # Extract top_k re-ranked chunks with updated scores
            reranked_chunks = []
            for result in reranked_results[:top_k]:
                chunk = result["meta"].copy()
                chunk["rerank_score"] = result["score"]
                chunk["original_score"] = chunk.get("score", 0)
                reranked_chunks.append(chunk)
            
            print(f"   🔄 Reranked {len(chunks)} chunks → top {len(reranked_chunks)}")
            return reranked_chunks
            
        except Exception as e:
            print(f"⚠️ Reranking failed: {e}, using original order")
            return chunks[:top_k]

    async def get_paper_context(
        self, paper_ids: List[str], topic: str, chunks_per_paper: int = 50
    ) -> dict:
        """
        MULTI-QUERY RETRIEVAL ENGINE
        --------------------------------------------------
        Combines:
        1. Query Decomposition
        2. Quota-Based Balancing (Guarantees every sub-query gets equal representation)
        3. Full-Topic Backup Search
        4. FlashRank Re-ranking
        5. Chronological Sorting by page number for coherent reading.
        """
        paper_content = {}
        
        # Step 1: Decompose the topic into sub-queries
        sub_queries = await self.decompose_topic(topic)
        num_queries = len(sub_queries)
        
        # Calculate quota per sub-query to guarantee balanced retrieval
        quota_per_query = max(12, chunks_per_paper // (num_queries + 1))
        
        print(f"\n📊 Retrieval Strategy:")
        print(f"   Sub-queries: {num_queries}")
        print(f"   Quota per query: {quota_per_query} chunks")
        print(f"   Target per paper: {chunks_per_paper} chunks")
        
        for paper_id in paper_ids:
            print(f"\n📄 Retrieving context for paper: {paper_id}")
            
            # PHASE 1: Quota-Based Collection (Guarantees query diversity)
            quota_chunks: List[Dict] = []
            all_chunks: Dict[int, Dict] = {}  # Deduplication dictionary
            
            for query_idx, query in enumerate(sub_queries):
                results = await self.semantic_search_chunks(
                    paper_id=paper_id,
                    query=query,
                    top_k=quota_per_query + 5
                )
                
                added_for_query = 0
                for chunk in results:
                    chunk_id = chunk["chunk_id"]
                    chunk["source_query"] = query_idx
                    
                    if chunk_id not in all_chunks:
                        all_chunks[chunk_id] = chunk
                        if added_for_query < quota_per_query:
                            quota_chunks.append(chunk)
                            added_for_query += 1
                    elif chunk["score"] > all_chunks[chunk_id]["score"]:
                        all_chunks[chunk_id] = chunk
                
                print(f"   Query {query_idx + 1}: '{query[:40]}...' → {added_for_query} quota chunks")
            
            # PHASE 2: Full Topic Search (Catch any remaining relevant text)
            full_topic_results = await self.semantic_search_chunks(
                paper_id=paper_id,
                query=topic,
                top_k=20
            )
            for chunk in full_topic_results:
                chunk_id = chunk["chunk_id"]
                chunk["source_query"] = -1
                if chunk_id not in all_chunks:
                    all_chunks[chunk_id] = chunk
            
            # PHASE 3: Combine quota chunks with top remaining pool
            quota_chunk_ids = {c["chunk_id"] for c in quota_chunks}
            remaining_chunks = [
                c for c in all_chunks.values() 
                if c["chunk_id"] not in quota_chunk_ids
            ]
            remaining_chunks.sort(key=lambda x: x["score"], reverse=True)
            combined_pool = quota_chunks + remaining_chunks
            
            # PHASE 4: FlashRank Cross-Encoder Re-ranking against ORIGINAL query
            reranked_chunks = self.rerank_chunks(
                chunks=combined_pool,
                query=topic,
                top_k=chunks_per_paper
            )
            
            # PHASE 5: Sort chunks by page number for natural reading flow
            reranked_chunks.sort(key=lambda x: (x.get("page", 0), x.get("chunk_id", 0)))
            
            # Combine chunk text blocks into paper context
            chunk_texts = [chunk["content"] for chunk in reranked_chunks]
            paper_content[paper_id] = "\n\n".join(chunk_texts)
            
        return paper_content

    def _get_style_instructions(self, style: str) -> str:
        """Returns specific writing style guidelines (Narrative, Systematic, or Critical)."""
        instructions = {
            ReviewStyle.NARRATIVE: """
STYLE: Narrative Literature Review
- Write in flowing prose that connects ideas from the sources
- Use transitions to show relationships between findings in the provided texts
- Synthesize information across the sources thematically
- Maintain academic tone while being readable
- REMEMBER: Only discuss what the sources explicitly mention
""",
            ReviewStyle.SYSTEMATIC: """
STYLE: Systematic Literature Review
- Structure findings methodically based on what the sources contain
- Present information objectively as stated in the sources
- Categorize findings using categories that emerge FROM the sources
- Include only statistics and numbers explicitly stated in the sources
- REMEMBER: If a methodology detail isn't in the sources, don't invent it
""",
            ReviewStyle.CRITICAL: """
STYLE: Critical Literature Review
- Analyze and evaluate claims made within the provided sources
- Identify contradictions or debates ONLY if explicitly present in the sources
- Evaluate evidence quality based on what the sources themselves describe
- Note limitations that the sources themselves acknowledge
- REMEMBER: Do not critique based on outside knowledge of the field
""",
        }
        for k, v in instructions.items():
            if k.value == style:
                return v
        return instructions[ReviewStyle.NARRATIVE]
    
    async def generate_review(
        self, request: LiteratureReviewRequest, paper_titles: dict
    ) -> LiteratureReviewResponse:
        """
        STAGE 4: Closed-World Grounded Synthesis
        --------------------------------------------------
        Generates the final Literature Review JSON object using OpenAI.
        Enforces strict [Source: 'Title'] citations and zero hallucinations.
        """
        print(f"\n🔬 Starting Literature Review Generation")
        print(f"   Topic: {request.topic}")
        print(f"   Papers: {len(request.paper_ids)}")
        
        # 1. Fetch context chunks using multi-query retrieval + reranking
        paper_context = await self.get_paper_context(
            paper_ids=request.paper_ids,
            topic=request.topic,
            chunks_per_paper=50
        )
        
        # 2. Build XML blocks for source documents
        source_blocks = []
        total_chars = 0
        max_total_chars = 25000  # Character budget across all papers
        chars_per_paper = max_total_chars // max(len(paper_context), 1)
        
        for idx, (pid, content) in enumerate(paper_context.items(), 1):
            title = paper_titles.get(pid, f"Paper {idx}")
            truncated_content = content[:chars_per_paper] if len(content) > chars_per_paper else content
            total_chars += len(truncated_content)
            source_blocks.append(
                f'<SOURCE id="{idx}" title="{title}">\n{truncated_content}\n</SOURCE>'
            )
        
        sources_xml = "\n\n".join(source_blocks)
        style_instructions = self._get_style_instructions(request.review_style)
        paper_titles_list = [f'{idx}. "{title}"' for idx, title in enumerate(paper_titles.values(), 1)]
        
        focus_areas_text = (
            f"\nFOCUS AREAS (only if covered in sources): {', '.join(request.focus_areas)}"
            if request.focus_areas
            else ""
        )
        
        # 3. Construct Grounded Prompt
        prompt = f"""<TASK>
Generate a literature review on the topic below using ONLY the information in the <SOURCES> section.
</TASK>

<TOPIC>{request.topic}</TOPIC>

<CONSTRAINTS>
- Word limit: ~{request.word_limit} words
- Style: {request.review_style.value}
- Papers provided: {len(request.paper_ids)}
{focus_areas_text}
</CONSTRAINTS>

{style_instructions}

<AVAILABLE_SOURCES>
These are the ONLY sources you may reference. You know NOTHING beyond these texts:

{sources_xml}
</AVAILABLE_SOURCES>

<PAPER_TITLES_FOR_CITATION>
Use these exact titles in your [Source: "Title"] citations:
{chr(10).join(paper_titles_list)}
</PAPER_TITLES_FOR_CITATION>

<OUTPUT_FORMAT>
Respond with ONLY valid JSON (no markdown, no code blocks):
{{
    "introduction": "Introduce the topic based ONLY on what the sources discuss. Include [Source: 'Title'] citations.",
    "methodology": "Describe: 'This review synthesizes findings from [N] provided sources...'",
    "thematic_analysis": [
        {{
            "theme_name": "Theme derived FROM the source content",
            "description": "Synthesize findings across sources with [Source: 'Title'] citations.",
            "supporting_papers": ["Exact Title 1"],
            "key_points": ["Finding explicitly stated in Source X"]
        }}
    ],
    "discussion": "Synthesize patterns across themes. Discuss implications ONLY as stated by sources.",
    "conclusion": "Summarize key findings from the sources.",
    "references": ["Full Paper Title 1"],
    "source_coverage_note": "Brief note on what aspects were covered vs not addressed"
}}
</OUTPUT_FORMAT>
"""
        
        # 4. Invoke LLM with System Prompt + Grounded User Prompt
        from typing import Any
        response: Any = self.client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=[
                {"role": "user", "content": f"{CLOSED_WORLD_SYSTEM_PROMPT}\n\n{prompt}"},
            ],
            max_completion_tokens=18000,
        )
        
        # 5. Clean and parse JSON response
        response_text = response.choices[0].message.content or ""
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        review_json = json.loads(response_text)
        
        # 6. Build structured Pydantic response models
        thematic_analysis = None
        if review_json.get("thematic_analysis"):
            thematic_analysis = [
                ThemeAnalysis(**theme) for theme in review_json["thematic_analysis"]
            ]

        content = ReviewContent(
            introduction=review_json.get("introduction"),
            methodology=review_json.get("methodology"),
            thematic_analysis=thematic_analysis,
            discussion=review_json.get("discussion"),
            conclusion=review_json.get("conclusion"),
            references=review_json.get("references", []),
            source_coverage_note=review_json.get("source_coverage_note"),
        )

        word_count = self._calculate_word_count(content)

        return LiteratureReviewResponse(
            id=str(uuid.uuid4()),
            topic=request.topic,
            review_style=request.review_style.value,
            paper_count=len(request.paper_ids),
            content=content,
            word_count=word_count,
            created_at=datetime.now(timezone.utc),
        )

    def _calculate_word_count(self, content: ReviewContent) -> int:
        """Calculates total word count of the generated literature review."""
        total = 0

        if content.introduction:
            total += len(content.introduction.split())
        if content.methodology:
            total += len(content.methodology.split())
        if content.discussion:
            total += len(content.discussion.split())
        if content.conclusion:
            total += len(content.conclusion.split())

        if content.thematic_analysis:
            for theme in content.thematic_analysis:
                total += len(theme.description.split())
                for point in theme.key_points:
                    total += len(point.split())

        return total


# Instantiate singleton service instance
literature_review_service = LiteratureReviewService()