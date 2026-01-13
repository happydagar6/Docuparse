import json
import uuid
import asyncio
from datetime import datetime
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
        self.client = OpenAI(
            api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1"
        )
        self.qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
            check_compatibility=False,
        )
        # Initialize embeddings for semantic search
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
        
        # Initialize FlashRank reranker for cross-encoder reranking
        # Using nano model for speed, can upgrade to "ms-marco-MiniLM-L-12-v2" for quality
        print("🔄 Initializing FlashRank reranker...")
        self.reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/flashrank_cache")
        print("✅ FlashRank reranker initialized")
        
    async def decompose_topic(self, topic: str) -> List[str]:
        """
        Decompose a broad topic into specific sub-queries for better retrieval.
        This prevents semantic dilution by searching for each concept individually.
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

## EXAMPLES (Abstract - DO NOT copy these literally)

Topic: "restrictions on X"
→ "restrictions on X general provisions"
→ "conditions eligibility X requirements"  
→ "X blocked limit maximum percentage threshold"
→ "X ineligible disqualified prohibited"
→ "X rule provision restriction clause"

Topic: "conditions for claiming Y"
→ "conditions claiming Y eligibility"
→ "Y claim requirements mandatory criteria"
→ "Y entitled claim provided that subject to"
→ "Y claim disallowed ineligible conditions"
→ "Y section clause conditions provisions"

## OUTPUT FORMAT
Return ONLY a JSON array of 4-6 search query strings. No explanations.
["query 1", "query 2", "query 3", "query 4", ...]"""

        try:
            response = self.client.chat.completions.create(
                model="grok-3-fast",
                messages=[{"role": "user", "content": decomposition_prompt}],
                temperature=0.4,  # Slightly higher for query variety
                max_tokens=600,
            )
            
            result = response.choices[0].message.content.strip()
            # Clean up response
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
        Perform semantic vector search for a specific query within a paper.
        """
        try:
            # Generate query embedding
            query_embedding = await asyncio.to_thread(
                self.embeddings.embed_query, query
            )
            
            # Search in Qdrant
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
                results.append({
                    "content": point.payload.get("content", ""),
                    "chunk_id": point.payload.get("chunk_id", 0),
                    "page": point.payload.get("page", 1),
                    "score": float(point.score),
                })
            
            return results
            
        except Exception as e:
            print(f"⚠️ Semantic search failed for query '{query[:50]}...': {e}")
            return []

    def rerank_chunks(
        self, chunks: List[Dict], query: str, top_k: int = 50
    ) -> List[Dict]:
        """
        Rerank chunks using FlashRank cross-encoder against the original query.
        This ensures chunks that specifically match the query get boosted,
        even if they had lower vector similarity scores.
        """
        if not chunks:
            return []
        
        try:
            # Prepare passages for reranking
            passages = [
                {"id": i, "text": chunk["content"], "meta": chunk}
                for i, chunk in enumerate(chunks)
            ]
            
            # Create rerank request
            rerank_request = RerankRequest(query=query, passages=passages)
            
            # Rerank using FlashRank
            reranked_results = self.reranker.rerank(rerank_request)
            
            # Extract reranked chunks with new scores
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
        Retrieve diverse, relevant content using:
        1. Query Decomposition - breaks topic into sub-queries
        2. Quota-Based Balancing - guarantees each sub-query gets representation
        3. FlashRank Reranking - reranks final pool against original query
        
        This solves both Semantic Dilution AND Context Window Overflow.
        """
        paper_content = {}
        
        # Decompose topic into sub-queries
        sub_queries = await self.decompose_topic(topic)
        num_queries = len(sub_queries)
        
        # Calculate quota per sub-query (ensure each gets fair representation)
        # Reserve some slots for full-topic search and reranking flexibility
        # Minimum 10 chunks per query for better coverage
        quota_per_query = max(12, chunks_per_paper // (num_queries + 1))
        
        print(f"\n📊 Retrieval Strategy:")
        print(f"   Sub-queries: {num_queries}")
        print(f"   Quota per query: {quota_per_query} chunks")
        print(f"   Target per paper: {chunks_per_paper} chunks")
        
        for paper_id in paper_ids:
            print(f"\n📄 Retrieving context for paper: {paper_id}")
            
            # PHASE 1: Quota-Based Collection (guarantees diversity)
            quota_chunks: List[Dict] = []  # Chunks with guaranteed slots
            all_chunks: Dict[int, Dict] = {}  # All chunks for deduplication
            
            for query_idx, query in enumerate(sub_queries):
                results = await self.semantic_search_chunks(
                    paper_id=paper_id,
                    query=query,
                    top_k=quota_per_query + 5  # Get extra for dedup buffer
                )
                
                # Add quota chunks (guaranteed representation)
                added_for_query = 0
                for chunk in results:
                    chunk_id = chunk["chunk_id"]
                    chunk["source_query"] = query_idx  # Track which query found it
                    
                    if chunk_id not in all_chunks:
                        all_chunks[chunk_id] = chunk
                        if added_for_query < quota_per_query:
                            quota_chunks.append(chunk)
                            added_for_query += 1
                    elif chunk["score"] > all_chunks[chunk_id]["score"]:
                        all_chunks[chunk_id] = chunk
                
                print(f"   Query {query_idx + 1}: '{query[:40]}...' → {added_for_query} quota chunks")
            
            # PHASE 2: Full Topic Search (catch any missed content)
            full_topic_results = await self.semantic_search_chunks(
                paper_id=paper_id,
                query=topic,
                top_k=20
            )
            for chunk in full_topic_results:
                chunk_id = chunk["chunk_id"]
                chunk["source_query"] = -1  # Mark as from full topic
                if chunk_id not in all_chunks:
                    all_chunks[chunk_id] = chunk
            
            print(f"   Full topic search added {len([c for c in all_chunks.values() if c.get('source_query') == -1])} more chunks")
            
            # PHASE 3: Combine quota chunks with remaining top chunks
            # Quota chunks are guaranteed, fill remaining slots with best from pool
            quota_chunk_ids = {c["chunk_id"] for c in quota_chunks}
            remaining_chunks = [
                c for c in all_chunks.values() 
                if c["chunk_id"] not in quota_chunk_ids
            ]
            remaining_chunks.sort(key=lambda x: x["score"], reverse=True)
            
            # Combine: quota chunks + top remaining chunks
            combined_pool = quota_chunks + remaining_chunks
            
            # PHASE 4: FlashRank Reranking against original query
            # This re-scores ALL chunks against the full original topic
            # Specific mentions like "Rule 86B" get boosted if they match the query
            print(f"   📦 Combined pool: {len(combined_pool)} chunks before reranking")
            
            reranked_chunks = self.rerank_chunks(
                chunks=combined_pool,
                query=topic,  # Rerank against ORIGINAL full query
                top_k=chunks_per_paper
            )
            
            # PHASE 5: Sort by page order for coherent reading
            reranked_chunks.sort(key=lambda x: (x.get("page", 0), x.get("chunk_id", 0)))
            
            # Join chunks into paper content
            chunk_texts = [chunk["content"] for chunk in reranked_chunks]
            paper_content[paper_id] = "\n\n".join(chunk_texts)
            
            # Log coverage statistics
            query_coverage = {}
            for chunk in reranked_chunks:
                sq = chunk.get("source_query", -1)
                query_coverage[sq] = query_coverage.get(sq, 0) + 1
            
            print(f"   ✅ Final: {len(reranked_chunks)} chunks")
            print(f"   📊 Coverage by sub-query: {dict(sorted(query_coverage.items()))}")

        return paper_content

    def _get_style_instructions(self, style: str) -> str:
        """Get writing style instructions based on review type - grounded version"""
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
        return instructions.get(style, instructions[ReviewStyle.NARRATIVE])
    
    async def generate_review(
        self, request: LiteratureReviewRequest, paper_titles: dict
    ) -> LiteratureReviewResponse:
        """Generate Literature Review with strict grounding to source texts"""
        
        # Get content from all papers using Query Decomposition for diverse retrieval
        print(f"\n🔬 Starting Literature Review Generation")
        print(f"   Topic: {request.topic}")
        print(f"   Papers: {len(request.paper_ids)}")
        
        paper_context = await self.get_paper_context(
            paper_ids=request.paper_ids,
            topic=request.topic,  # Pass topic for intelligent retrieval
            chunks_per_paper=50   # Get more chunks for comprehensive coverage
        )
        
        # Build structured source blocks with clear labels
        source_blocks = []
        total_chars = 0
        max_total_chars = 25000  # Total character budget across all papers
        chars_per_paper = max_total_chars // max(len(paper_context), 1)
        
        for idx, (pid, content) in enumerate(paper_context.items(), 1):
            title = paper_titles.get(pid, f"Paper {idx}")
            # Dynamically allocate characters based on number of papers
            truncated_content = content[:chars_per_paper] if len(content) > chars_per_paper else content
            total_chars += len(truncated_content)
            source_blocks.append(
                f'<SOURCE id="{idx}" title="{title}">\n{truncated_content}\n</SOURCE>'
            )
        
        print(f"   📊 Total source content: {total_chars:,} characters across {len(source_blocks)} papers")
        
        sources_xml = "\n\n".join(source_blocks)
        style_instructions = self._get_style_instructions(request.review_style)
        
        # Build the paper titles list for reference
        paper_titles_list = [f'{idx}. "{title}"' for idx, title in enumerate(paper_titles.values(), 1)]
        
        focus_areas_text = (
            f"\nFOCUS AREAS (only if covered in sources): {', '.join(request.focus_areas)}"
            if request.focus_areas
            else ""
        )
        
        # Grounded user prompt
        prompt = f"""<TASK>
Generate a literature review on the topic below using ONLY the information in the <SOURCES> section.
</TASK>

<TOPIC>{request.topic}</TOPIC>

<CONSTRAINTS>
- Word limit: ~{request.word_limit} words (shorter is acceptable if sources lack information)
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
    "introduction": "Introduce the topic based ONLY on what the sources discuss. State the scope of this review. If sources cover limited aspects, acknowledge this. Include [Source: 'Title'] citations. (100-250 words)",
    
    "methodology": "Describe: 'This review synthesizes findings from [N] provided sources focusing on [aspects actually covered in sources].' (50-100 words)",
    
    "thematic_analysis": [
        {{
            "theme_name": "Theme derived FROM the source content",
            "description": "Synthesize what multiple sources say about this theme. Every claim must have [Source: 'Title'] citation. Use narrative prose, not bullets. (200-400 words)",
            "supporting_papers": ["Exact Title 1", "Exact Title 2"],
            "key_points": ["Finding explicitly stated in Source X", "Finding explicitly stated in Source Y"]
        }}
    ],
    
    "discussion": "Synthesize patterns across themes. Discuss implications ONLY as stated or directly implied by the sources. Note any gaps: 'The sources do not address...' (150-300 words)",
    
    "conclusion": "Summarize key findings from the sources. For future directions, only mention those suggested BY the sources themselves. (100-200 words)",
    
    "references": ["Full Paper Title 1", "Full Paper Title 2"],
    
    "source_coverage_note": "Brief note on what aspects of the topic the sources covered well vs. what was not addressed"
}}
</OUTPUT_FORMAT>

<FINAL_CHECKLIST>
Before responding, verify:
✓ Every factual statement has a [Source: "Title"] citation
✓ No dates, names, or statistics appear that aren't in the sources
✓ No "common knowledge" about the topic was added
✓ If sources lack info on the topic, I stated this honestly
</FINAL_CHECKLIST>"""
        
        response = self.client.chat.completions.create(
            model="grok-4-1-fast-reasoning",
            messages=[
                {
                    "role": "system",
                    "content": CLOSED_WORLD_SYSTEM_PROMPT,
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,  # Lower temperature for more deterministic, grounded output
            max_tokens=18000,
        )
        
        # Parse response - handle potential JSON issues
        response_text = response.choices[0].message.content
        
        # Clean up response if it contains markdown code blocks
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        review_json = json.loads(response_text)
        
        # Build ReviewContent from response
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

        # Calculate word count
        word_count = self._calculate_word_count(content)

        return LiteratureReviewResponse(
            id=str(uuid.uuid4()),
            topic=request.topic,
            review_style=request.review_style.value,
            paper_count=len(request.paper_ids),
            content=content,
            word_count=word_count,
            created_at=datetime.utcnow(),
        )

    def _calculate_word_count(self, content: ReviewContent) -> int:
        """Calculate total word count of the review"""
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

literature_review_service = LiteratureReviewService()

        