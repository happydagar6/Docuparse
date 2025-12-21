"""
Research Synthesis Service
==========================

This module provides AI-powered synthesis of search results across multiple papers.
It analyzes papers to extract themes, identify research gaps, and detect trends.

Key Functions:
- synthesize_search_results(): Main entry point for generating research synthesis
- _extract_themes(): Identifies common themes across papers using LLM
- _identify_research_gaps(): Finds underexplored areas in the literature
- _analyze_trends(): Detects patterns over time (year-based analysis)
- _generate_key_findings(): Extracts consensus findings across papers

Architecture:
1. Input: List of search results (paper metadata + chunks)
2. Processing: LLM analysis with structured prompts
3. Output: Structured synthesis data (themes, gaps, trends, findings)
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter, defaultdict
from openai import OpenAI
import os

# Initialize OpenAI client for Grok (XAI)
client = OpenAI(
    api_key=os.getenv("XAI_API_KEY") or os.getenv("OPENAI_API_KEY"),  # Try XAI first, fallback to OpenAI
    base_url=os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")  # Grok API endpoint
)

def clean_json_response(content: str) -> str:
    """
    Clean GPT-4 response by removing markdown code blocks.
    
    GPT-4 sometimes returns JSON wrapped in ```json ... ```
    This function extracts the actual JSON content.
    """
    content = content.strip()
    
    # Remove markdown code blocks
    if content.startswith('```'):
        # Find the first newline after ```json or ```
        first_newline = content.find('\n')
        if first_newline != -1:
            content = content[first_newline + 1:]
        
        # Remove closing ```
        if content.endswith('```'):
            content = content[:-3]
    
    return content.strip()

class SynthesisService:
    """
    Service for generating research synthesis from search results.
    
    This class uses LLM (Grok) to analyze multiple papers and generate
    actionable insights for researchers.
    """
    
    def __init__(self, model: str = "grok-4-1-fast-reasoning"):
        """
        Initialize synthesis service.
        
        Args:
            model: Grok model to use (default: grok-4-1-fast-reasoning)
                   Available: grok-4-1-fast-reasoning, grok-beta, grok-2-1212
        """
        self.model = model
        self.max_chunk_length = 1900  # Characters per chunk to include
    
    async def synthesize_search_results(
        self, 
        query: str, 
        search_results: List[Dict[str, Any]],
        max_papers: int = 20 # Add this parameter
    ) -> Dict[str, Any]:
        """
        Main synthesis function - orchestrates all analysis steps.
        
        Args:
            query: Original search query from user
            search_results: List of search results with paper metadata
            
        Returns:
            Dict with structure:
            {
                "query": str,
                "paper_count": int,
                "themes": List[{"name": str, "count": int, "papers": List[str]}],
                "key_findings": List[str],
                "research_gaps": List[str],
                "trends": {
                    "timeline": List[{"year": int, "count": int}],
                    "trend_description": str
                },
                "top_papers": List[{"title": str, "relevance": float}]
            }
        """
        
        # Step 1: Filter and prepare data
        limited_results = search_results[:max_papers]
        
        # Step 2: Calculate UNIQUE paper count (not chunk count)
        # CRITICAL: limited_results may contain multiple chunks from the same paper
        unique_paper_ids = set()
        for result in limited_results:
            paper_id = result.get('paper_id') or result.get('id', 'unknown')
            unique_paper_ids.add(paper_id)
        
        unique_paper_count = len(unique_paper_ids)
        
        print(f"📊 Processing {len(limited_results)} chunks from {unique_paper_count} unique document(s)")
        
        # Step 3: Gather metadata for analysis
        papers_by_year = self._group_by_year(limited_results)
        paper_summaries = self._prepare_paper_summaries(limited_results)
        
        # Step 4: Run parallel LLM analysis
        themes = await self._extract_themes(query, paper_summaries)
        key_findings = await self._generate_key_findings(query, paper_summaries)
        research_gaps = await self._identify_research_gaps(query, paper_summaries, themes)
        trends = self._analyze_trends(papers_by_year)
        
        # Step 5: Compile synthesis with CORRECT paper count
        synthesis = {
            "query": query,
            "paper_count": unique_paper_count,  # FIXED: Use unique count, not chunk count
            "themes": themes,
            "key_findings": key_findings,
            "research_gaps": research_gaps,
            "trends": trends,
            "top_papers": self._get_top_papers(limited_results, top_n=5),
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return synthesis
    
    def _group_chunks_by_document(self, results: List[Dict[str, Any]]) -> str:
        """
        Group text chunks by their source document/filename.
        This prevents the LLM from thinking each chunk is a separate paper.
        
        Args:
            results: Raw search results with paper_id/metadata
            
        Returns:
            Formatted string with clear document boundaries
        """
        # Group chunks by paper_id or filename
        documents = defaultdict(list)
        
        for result in results:
            paper_id = result.get('paper_id') or result.get('id', 'unknown')
            
            # Get document metadata
            title = (
                result.get('paper_title') or 
                result.get('title') or 
                (result.get('metadata', {}).get('title') if isinstance(result.get('metadata'), dict) else None) or
                f'Document {paper_id}'
            )
            
            authors = result.get('authors', [])
            year = result.get('publication_year', 'Unknown')
            text = result.get('text', '')
            
            documents[paper_id].append({
                'title': title,
                'authors': authors,
                'year': year,
                'text': text
            })
        
        # Format as delimited document sections
        formatted_docs = []
        
        for doc_id, chunks in documents.items():
            # Use first chunk's metadata for document header
            first_chunk = chunks[0]
            authors = first_chunk.get('authors', [])
            if authors:
                if isinstance(authors[0], dict):
                    author_names = [a.get('name', str(a)) for a in authors[:3]]
                    authors_str = ", ".join(author_names)
                else:
                    authors_str = ", ".join(authors[:3])
                if len(authors) > 3:
                    authors_str += " et al."
            else:
                authors_str = "Unknown Authors"
            
            # Combine all chunk texts
            combined_text = "\n\n".join([chunk['text'][:1900] for chunk in chunks[:10]])  # Limit chunks per doc
            
            doc_section = f"""--- DOCUMENT: {first_chunk['title']} ---
Authors: {authors_str}
Year: {first_chunk['year']}

CONTENT:
{combined_text}
--- END DOCUMENT ---"""
            
            formatted_docs.append(doc_section)
        
        # Add summary header
        doc_count = len(documents)
        header = f"""CONTEXT: You are analyzing {doc_count} document(s) from a research database.
Each document is clearly marked with '--- DOCUMENT:' delimiters.

"""
        
        return header + "\n\n".join(formatted_docs)
    
    def _prepare_paper_summaries(self, results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract key information from each paper for LLM analysis.
        
        CRITICAL: Uses robust fallback chain for text extraction to handle
        different data source formats (vector DB, search API, etc.)
        
        Args:
            results: Raw search results
            
        Returns:
            List of paper summaries with title, text snippet, metadata
        """
        summaries = []
        empty_text_count = 0
        
        for idx, result in enumerate(results):
            # Get paper metadata - check multiple possible fields
            paper_id = result.get('paper_id') or result.get('id', 'unknown')
            
            # Try multiple title fields: paper_title (from search), title, or metadata.title
            title = (
                result.get('paper_title') or 
                result.get('title') or 
                (result.get('metadata', {}).get('title') if isinstance(result.get('metadata'), dict) else None) or
                'Untitled'
            )
            
            # ROBUST TEXT EXTRACTION FALLBACK CHAIN
            # Different data sources use different field names for text content
            text = (
                result.get('text') or                    # Standard field
                result.get('page_content') or            # LangChain/vector store format
                result.get('content') or                 # Generic content field
                result.get('snippet') or                 # Search result snippet
                result.get('body') or                    # Alternative body field
                result.get('abstract') or                # Fallback to abstract if available
                (result.get('metadata', {}).get('text') if isinstance(result.get('metadata'), dict) else None) or
                ''  # Final fallback to empty string
            )
            
            # Debug logging for empty text
            if not text or len(text.strip()) == 0:
                empty_text_count += 1
                print(f"⚠️ Empty text for result #{idx}: paper_id={paper_id}, title={title[:50]}...")
                print(f"   Available keys: {list(result.keys())}")
            
            authors = result.get('authors', [])
            year = result.get('publication_year')
            
            # Truncate text to avoid token limits
            text_snippet = text[:self.max_chunk_length] if text else ""
            
            summary = {
                "id": paper_id,
                "title": title,
                "text": text_snippet,
                "authors": authors if isinstance(authors, list) else [],
                "year": year,
                "relevance": result.get('relevance_score', result.get('score', 0))
            }
            
            summaries.append(summary)
        
        # Summary logging
        if empty_text_count > 0:
            print(f"⚠️ WARNING: {empty_text_count}/{len(results)} results had no extractable text")
            print(f"   This may cause LLM to respond with 'no full text available'")
        
        return summaries
    
    def _build_grouped_context(
        self, 
        paper_summaries: List[Dict[str, str]], 
        max_docs: int = 10,
        max_chars_per_doc: int = 8000
    ) -> tuple[str, int]:
        """
        Group text chunks by paper_id to prevent LLM from counting chunks as separate papers.
        
        This is CRITICAL for RAG accuracy - without grouping, 5 chunks from 1 paper 
        appears as "5 papers analyzed" to the LLM.
        
        Args:
            paper_summaries: List of summaries (may contain multiple chunks per paper)
            max_docs: Maximum number of unique documents to include
            max_chars_per_doc: Character limit per document to prevent token overflow
            
        Returns:
            Tuple of (formatted_context_string, unique_document_count)
        """
        from collections import defaultdict
        
        # Group chunks by paper_id
        documents = defaultdict(list)
        
        for summary in paper_summaries:
            paper_id = summary.get('id', 'unknown')
            documents[paper_id].append(summary)
        
        # Build formatted document sections
        formatted_sections = []
        doc_count = 0
        
        for paper_id, chunks in list(documents.items())[:max_docs]:
            doc_count += 1
            
            # Use metadata from first chunk
            first_chunk = chunks[0]
            title = first_chunk.get('title', f'Document {paper_id}')
            authors = first_chunk.get('authors', [])
            year = first_chunk.get('year', 'N/A')
            
            # Format authors
            if authors:
                # CRITICAL: Handle both string lists and dict lists
                if isinstance(authors[0], dict):
                    # Authors are dicts like [{"name": "Smith, J."}, ...]
                    author_names = [a.get('name', str(a)) for a in authors[:3]]
                    authors_str = ", ".join(author_names)
                elif isinstance(authors[0], str):
                    # Authors are strings like ["Smith, J.", ...]
                    authors_str = ", ".join(authors[:3])
                else:
                    authors_str = "Unknown Authors"
                
                if len(authors) > 3:
                    authors_str += " et al."
            else:
                authors_str = "Unknown Authors"
            
            # Combine all chunk texts from this paper
            combined_text_parts = []
            total_chars = 0
            
            for chunk in chunks:
                chunk_text = chunk.get('text', '')
                if total_chars + len(chunk_text) <= max_chars_per_doc:
                    combined_text_parts.append(chunk_text)
                    total_chars += len(chunk_text)
                else:
                    # Add truncated final chunk
                    remaining = max_chars_per_doc - total_chars
                    if remaining > 500:  # Only add if meaningful text remains
                        combined_text_parts.append(chunk_text[:remaining] + "...")
                    break
            
            combined_text = "\n\n".join(combined_text_parts)
            
            # Format with clear delimiters
            doc_section = f"""--- DOCUMENT {doc_count}: {title} ---
Authors: {authors_str}
Year: {year}
Paper ID: {paper_id}

FULL TEXT (All Sections Combined):
{combined_text}

--- END DOCUMENT {doc_count} ---"""
            
            formatted_sections.append(doc_section)
        
        # Create header with explicit document count
        header = f"""CONTEXT: You are analyzing {doc_count} unique research document(s).
Each document below contains ALL text chunks from that paper combined.
Do NOT count sections/chunks as separate papers.

"""
        
        full_context = header + "\n\n".join(formatted_sections)
        
        return full_context, doc_count
    
    async def _extract_themes(
        self, 
        query: str, 
        paper_summaries: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to identify common themes across documents.
        Allows synthesis of information within provided text.
        
        Args:
            query: Search query
            paper_summaries: Prepared paper data
            
        Returns:
            List of themes with counts: [{"name": str, "count": int, "papers": List[str]}]
        """
        
        # Use grouped document format
        from collections import defaultdict
        documents_by_id = defaultdict(list)
        for summary in paper_summaries:
            documents_by_id[summary['id']].append(summary)
        
        doc_count = len(documents_by_id)
        
        # Create grouped text
        grouped_text = []
        for doc_id, summaries in list(documents_by_id.items())[:5]:  # Limit to 5 docs
            first = summaries[0]
            authors = first.get('authors', [])
            if authors:
                if isinstance(authors[0], dict):
                    author_names = [a.get('name', str(a)) for a in authors[:2]]
                    authors_str = ", ".join(author_names)
                else:
                    authors_str = ", ".join(authors[:2])
            else:
                authors_str = "Unknown"
            combined_text = "\n".join([s['text'] for s in summaries])
            
            grouped_text.append(
                f"--- DOCUMENT: {first['title']} ---\n"
                f"Authors: {authors_str} | Year: {first.get('year', 'N/A')}\n"
                f"CONTENT:\n{combined_text[:3000]}\n"
                f"--- END DOCUMENT ---"
            )
        
        context_text = "\n\n".join(grouped_text)
        
        # BALANCED SYSTEM PROMPT - Prevents hallucination BUT allows synthesis
        system_prompt = f"""You are a research synthesis assistant analyzing {doc_count} document(s).

CRITICAL RULES:
1. **SOURCE FIDELITY**: Extract themes ONLY from the provided text. Do NOT use external knowledge.
2. **SMART SYNTHESIS**: You SHOULD synthesize information within the text:
   - If text mentions "Method A: 60% accuracy" and "Method B: 45% accuracy", you CAN say "Method A outperformed Method B"
   - If sections discuss related concepts, you CAN identify connecting themes
3. **NO INVENTION**: Do not add themes not present in the text
4. **DOCUMENT COUNT**: There are {doc_count} document(s), not hundreds
5. **EVIDENCE-BASED**: Themes must have textual support"""

        prompt = f"""Analyze the provided document(s) about "{query}" and identify main themes.

DOCUMENT(S):
{context_text}

TASK: Identify 3-6 themes discussed in the text.

**SYNTHESIS INSTRUCTIONS**:
- If the text compares multiple approaches, identify "Comparative Analysis" as a theme
- If data points are scattered across sections, synthesize them into coherent themes
- If the text mentions outcomes/metrics, identify "Outcomes" or "Effectiveness" as themes

**OUTPUT FORMAT** (JSON array):
[
  {{
    "name": "Theme Name",
    "description": "Summary of what the document(s) discuss about this theme (2-3 sentences). Include specific data points if mentioned.",
    "count": 1
  }}
]

**EXAMPLE**:
If text says "Intervention A had effect size 0.6" and later "Intervention B had effect size 0.3", you can write:
{{
  "name": "Comparative Effectiveness",
  "description": "The document compares two interventions, finding Intervention A (effect size 0.6) outperformed Intervention B (effect size 0.3).",
  "count": 1
}}

Return ONLY the JSON array."""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Slightly higher to allow synthesis
                max_tokens=1200
            )
            
            content = response.choices[0].message.content.strip()
            content = clean_json_response(content)
            
            print(f"📝 LLM themes response (first 200 chars): {content[:200]}")
            
            themes_raw = json.loads(content)
            
            # Format themes with counts
            themes = []
            for theme in themes_raw:
                themes.append({
                    "name": theme.get("name", "Unknown Theme"),
                    "description": theme.get("description", ""),
                    "count": theme.get("count", 1),
                    "papers": []
                })
            
            return themes
            
        except Exception as e:
            print(f"❌ Error extracting themes: {e}")
            return self._fallback_theme_extraction(paper_summaries)
    
    async def _generate_key_findings(
        self, 
        query: str, 
        paper_summaries: List[Dict[str, str]]
    ) -> List[str]:
        """
        Extract and synthesize key findings from documents.
        
        CRITICAL IMPROVEMENTS:
        - Uses _build_grouped_context to prevent chunk-counting hallucination
        - Instructs LLM to hunt for moderator/subgroup analyses
        - Allows connecting data across document sections (Intro → Results)
        
        Args:
            query: Search query (may contain variables like "Intensity", "Duration")
            paper_summaries: List of paper summaries (may have multiple chunks per paper)
            
        Returns:
            List of key finding strings with specific data and moderator insights
        """
        
        # Use the grouped context builder to prevent "10 papers" hallucination
        context_text, doc_count = self._build_grouped_context(
            paper_summaries[:15],  # Limit to 15 most relevant
            max_docs=10,
            max_chars_per_doc=8000
        )
        
        # ADVANCED SYSTEM PROMPT - Handles moderators and cross-section synthesis
        system_prompt = f"""You are a Research Analyst examining {doc_count} cohesive research document(s).

**CRITICAL INSTRUCTIONS**:

1. **SOURCE FIDELITY**: Extract findings ONLY from the provided text. NO external knowledge or assumptions.

2. **MODERATOR HUNTING** (CRUCIAL for avoiding false negatives):
   - If the user query mentions a variable (e.g., "Intervention Intensity", "Treatment Duration", "Age", "Baseline Severity"):
     * Search for terms like: "moderator", "moderated by", "subgroup analysis", "stratified by", "predictor of"
     * Search table headers, figure captions, and subsection titles
     * If the text identifies the variable as a MODERATOR or PREDICTOR of outcomes, YOU MUST REPORT THIS
   - Example: If text says "Intensity emerged as a significant moderator (β=0.34, p<.01)" → Report this even without exact "Low vs High" breakdown

3. **CROSS-SECTION DATA CONNECTING**:
   - Connect hypotheses in Introduction/Background with results in Results/Discussion
   - If Intro states "We hypothesized X would predict Y" and Results shows "X: β=0.45, p=.002" → Synthesize this
   - Link abstract statements to specific statistics in tables/results

4. **SMART SYNTHESIS**:
   ✓ Compare data points: "Group A: 60%" + "Group B: 40%" → "Group A outperformed by 20 points"
   ✓ Interpret stats: "d=0.8" → "large effect size per Cohen's conventions"
   ✓ Combine related findings across sections

5. **DATA PRECISION**: Always include:
   - Exact numbers (percentages, means, effect sizes)
   - Statistical significance (p-values, confidence intervals)
   - Sample sizes when mentioned

6. **HONEST REPORTING**:
   - If data truly missing: "The document does not report specific [metric]"
   - If moderator mentioned but no stats: "Text identifies [X] as a moderator but does not provide effect sizes"

7. **DOCUMENT COUNT ACCURACY**: You are analyzing {doc_count} document(s), NOT dozens or hundreds.

**SPECIAL QUERY VARIABLES**: 
Parse the query "{query}" for key terms. If it contains concepts like "intensity", "duration", "frequency", "dose", prioritize hunting for these as moderators/predictors in the text."""

        prompt = f"""Extract key findings from the document(s) related to: "{query}"

DOCUMENTS:
{context_text}

**YOUR TASK**: Generate 4-8 key findings that answer the query.

**PRIORITIZATION**:
1. **Direct Answers**: If query asks about "Intensity", find explicit comparisons (High vs Low)
2. **Moderator Findings**: If query variable appears as a moderator/predictor, report the relationship
3. **Related Outcomes**: Other significant findings even if not directly answering query
4. **Methodological Notes**: Sample characteristics, design features if relevant

**FINDING STRUCTURE**:
- **Statement**: Clear, specific claim
- **Evidence**: Numbers, statistics, effect sizes
- **Context**: Brief interpretation if data supports it

**EXAMPLES** (assuming text contains this data):

✓ GOOD (Direct Answer):
"High-intensity interventions (≥3 sessions/week) produced significantly larger reductions in symptoms (d=0.82) compared to low-intensity interventions (d=0.34), p<.001."

✓ GOOD (Moderator Finding):
"Treatment duration emerged as a significant moderator of outcomes (β=0.41, p=.003), with each additional week associated with 0.41 SD improvement in effect size."

✓ GOOD (Cross-Section Synthesis):
"The study hypothesized that baseline severity would predict treatment response. Results confirmed this, showing severe cases achieved 45% remission vs. 67% for mild cases (OR=2.1, 95% CI: 1.3-3.4)."

✗ BAD (Too vague):
"The intervention was effective." (No data, no specifics)

✗ BAD (Hallucination):
"Research shows that CBT typically works well." (Using external knowledge)

**OUTPUT FORMAT**: JSON array of finding strings.
["Finding 1 with specific data", "Finding 2 about moderators if present", ...]

Return ONLY the JSON array, no markdown."""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.28,  # Slightly higher to enable moderator hunting
                max_tokens=2000  # Increased for detailed findings
            )
            
            content = response.choices[0].message.content.strip()
            content = clean_json_response(content)
            
            print(f"📝 LLM findings response (first 200 chars): {content[:200]}")
            print(f"📊 Analyzed {doc_count} unique document(s) (grouped from {len(paper_summaries)} chunks)")
            
            findings = json.loads(content)
            
            # CRITICAL: Validate that LLM returned strings, not dicts
            if isinstance(findings, list) and len(findings) > 0:
                # Convert dicts to strings if LLM misbehaved
                validated_findings = []
                for item in findings:
                    if isinstance(item, str):
                        validated_findings.append(item)
                    elif isinstance(item, dict):
                        # LLM returned dict format - extract the finding text
                        finding_text = (
                            item.get('finding') or 
                            item.get('text') or 
                            item.get('description') or 
                            str(item)
                        )
                        validated_findings.append(finding_text)
                        print(f"⚠️ LLM returned dict instead of string, converted: {finding_text[:50]}...")
                    else:
                        validated_findings.append(str(item))
                
                return validated_findings if validated_findings else [f"Analyzed {doc_count} document(s) about '{query}'"]
            else:
                print("⚠️ Empty findings array received, using fallback")
                return [f"Analyzed {doc_count} document(s) about '{query}' - detailed findings require text analysis"]
            
        except Exception as e:
            print(f"❌ Error generating key findings: {e}")
            import traceback
            traceback.print_exc()
            return [f"Analysis of {doc_count} document(s) about '{query}' - synthesis incomplete due to processing error"]
    
    async def _identify_research_gaps(
        self, 
        query: str, 
        paper_summaries: List[Dict[str, str]],
        themes: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Identify research gaps with smart synthesis.
        Allows inference from what's NOT covered when the text shows what IS covered.
        
        Args:
            query: Search query
            paper_summaries: Prepared paper data
            themes: Already identified themes
            
        Returns:
            List of research gaps as strings
        """
        
        # Group by document
        from collections import defaultdict
        documents_by_id = defaultdict(list)
        for summary in paper_summaries[:10]:
            documents_by_id[summary['id']].append(summary)
        
        doc_count = len(documents_by_id)
        
        # Create grouped text
        grouped_text = []
        for doc_id, summaries in list(documents_by_id.items()):
            first = summaries[0]
            combined_text = "\n".join([s['text'] for s in summaries])
            grouped_text.append(
                f"--- DOCUMENT: {first['title']} ---\n"
                f"{combined_text[:3000]}\n"
                f"--- END DOCUMENT ---"
            )
        
        context_text = "\n\n".join(grouped_text)
        themes_text = ", ".join([t["name"] for t in themes])
        
        # BALANCED SYSTEM PROMPT
        system_prompt = f"""You are a research gap analyst examining {doc_count} document(s).

**PRINCIPLES**:
1. **SOURCE-BASED**: Gaps must be grounded in the text
2. **SMART INFERENCE**: You CAN infer gaps from what's present:
   ✓ If text studies "adults only", you CAN note "pediatric populations not examined"
   ✓ If text tests "short-term outcomes", you CAN identify "long-term effects unexplored"
   ✓ If authors state limitations, expand on their implications
3. **NO INVENTION**: Don't add gaps from general field knowledge
4. **SYNTHESIS**: Combine related limitations into coherent gap statements
"""

        prompt = f"""Identify research gaps from the document(s) about "{query}".

**THEMES FOUND**: {themes_text}

DOCUMENT(S):
{context_text}

**YOUR TASK**: Identify 3-5 research gaps.

**GAP SOURCES** (prioritized):
1. **Explicit Limitations**: Author-stated limitations ("This study did not include...")
2. **Methodological Gaps**: What was NOT tested (if text shows what WAS tested)
3. **Unanswered Questions**: Questions raised but unresolved in the text
4. **Future Work**: Author suggestions for future research

**SYNTHESIS EXAMPLE**:
If text says "We studied adults aged 18-65" and "Follow-up was 3 months", you CAN write:
- "Long-term effects beyond 3 months remain unexplored"
- "Applicability to elderly populations (>65) was not examined"

**OUTPUT FORMAT** (JSON array of strings):
["Gap 1 with context", "Gap 2", ...]

Return ONLY the JSON array."""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low-moderate for balanced synthesis
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            content = clean_json_response(content)
            
            print(f"📝 LLM gaps response (first 200 chars): {content[:200]}")
            
            gaps = json.loads(content)
            
            # CRITICAL: Validate that LLM returned strings, not dicts
            if isinstance(gaps, list):
                validated_gaps = []
                for item in gaps:
                    if isinstance(item, str):
                        validated_gaps.append(item)
                    elif isinstance(item, dict):
                        # Extract text from dict
                        gap_text = (
                            item.get('gap') or 
                            item.get('text') or 
                            item.get('description') or 
                            str(item)
                        )
                        validated_gaps.append(gap_text)
                        print(f"⚠️ LLM returned dict for gap, converted: {gap_text[:50]}...")
                    else:
                        validated_gaps.append(str(item))
                
                return validated_gaps if validated_gaps else []
            
            return []
            
        except Exception as e:
            print(f"❌ Error identifying research gaps: {e}")
            return ["Research gap analysis incomplete due to processing error"]
    
    def _analyze_trends(self, papers_by_year: Dict[int, List[Dict]]) -> Dict[str, Any]:
        """
        Analyze publication trends over time (non-LLM analysis).
        
        Args:
            papers_by_year: Papers grouped by publication year
            
        Returns:
            Dict with timeline data and trend description
        """
        
        if not papers_by_year:
            return {
                "timeline": [],
                "trend_description": "No temporal data available"
            }
        
        # Build timeline
        timeline = []
        for year in sorted(papers_by_year.keys()):
            timeline.append({
                "year": year,
                "count": len(papers_by_year[year])
            })
        
        # Generate trend description
        years = sorted(papers_by_year.keys())
        if len(years) >= 3:
            recent_years = years[-3:]
            recent_count = sum(len(papers_by_year[y]) for y in recent_years)
            older_years = years[:-3] if len(years) > 3 else []
            older_count = sum(len(papers_by_year[y]) for y in older_years) if older_years else 0
            
            if recent_count > older_count * 1.5:
                trend_description = f"Increasing research activity: {recent_count} papers in recent years ({min(recent_years)}-{max(recent_years)})"
            elif recent_count < older_count * 0.5:
                trend_description = f"Declining research activity: Most papers published before {min(recent_years)}"
            else:
                trend_description = f"Steady research activity: {len(papers_by_year)} papers from {min(years)} to {max(years)}"
        else:
            trend_description = f"Papers span {min(years)} to {max(years)}"
        
        return {
            "timeline": timeline,
            "trend_description": trend_description
        }
    
    def _group_by_year(self, results: List[Dict[str, Any]]) -> Dict[int, List[Dict]]:
        """Group papers by publication year."""
        papers_by_year = defaultdict(list)
        
        for result in results:
            year = result.get('publication_year')
            if year and isinstance(year, int):
                papers_by_year[year].append(result)
        
        return dict(papers_by_year)
    
    def _get_top_papers(self, results: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        """Extract top N papers by relevance score."""
        sorted_results = sorted(
            results, 
            key=lambda x: x.get('relevance_score', x.get('score', 0)), 
            reverse=True
        )
        
        top_papers = []
        for result in sorted_results[:top_n]:
            # Try multiple title fields: paper_title (from search), title, or metadata.title
            title = (
                result.get('paper_title') or 
                result.get('title') or 
                (result.get('metadata', {}).get('title') if isinstance(result.get('metadata'), dict) else None) or
                'Untitled'
            )
            
            top_papers.append({
                "id": result.get('id', result.get('paper_id', '')),
                "title": title,
                "relevance": round(result.get('relevance_score', result.get('score', 0)), 2),
                "year": result.get('publication_year')
            })
        
        return top_papers
    
    def _format_papers_for_prompt(self, paper_summaries: List[Dict[str, str]]) -> str:
        """Format paper data for LLM prompt."""
        formatted = []
        
        for i, paper in enumerate(paper_summaries, 1):
            authors = paper.get('authors', [])
            if authors:
                if isinstance(authors[0], dict):
                    author_names = [a.get('name', str(a)) for a in authors[:3]]
                    authors_str = ", ".join(author_names)
                else:
                    authors_str = ", ".join(authors[:3])
                if len(authors) > 3:
                    authors_str += " et al."
            else:
                authors_str = ""
            
            formatted.append(
                f"[{i}] ID: {paper['id']}\n"
                f"    Title: {paper['title']}\n"
                f"    Authors: {authors_str}\n"
                f"    Year: {paper.get('year', 'Unknown')}\n"
                f"    Text: {paper['text'][:300]}...\n"
            )
        
        return "\n".join(formatted)
    
    def _fallback_theme_extraction(self, paper_summaries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Fallback theme extraction using keyword frequency (no LLM).
        Used when LLM call fails.
        """
        # Extract common words from titles
        words = []
        for paper in paper_summaries:
            title = paper.get('title', '').lower()
            # Simple tokenization
            words.extend([w for w in title.split() if len(w) > 4])
        
        # Count frequencies
        word_counts = Counter(words)
        top_words = word_counts.most_common(5)
        
        themes = []
        for word, count in top_words:
            themes.append({
                "name": word.capitalize(),
                "description": f"Appears in {count} paper titles",
                "count": count,
                "papers": []
            })
        
        return themes


# Singleton instance
synthesis_service = SynthesisService()
