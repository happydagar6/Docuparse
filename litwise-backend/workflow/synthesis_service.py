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
        
        # Step 2: Gather metadata for analysis
        papers_by_year = self._group_by_year(limited_results)
        paper_summaries = self._prepare_paper_summaries(limited_results)
        
        # Step 3: Run parallel LLM analysis
        themes = await self._extract_themes(query, paper_summaries)
        key_findings = await self._generate_key_findings(query, paper_summaries)
        research_gaps = await self._identify_research_gaps(query, paper_summaries, themes)
        trends = self._analyze_trends(papers_by_year)
        
        # Step 4: Compile synthesis
        synthesis = {
            "query": query,
            "paper_count": len(limited_results),
            "themes": themes,
            "key_findings": key_findings,
            "research_gaps": research_gaps,
            "trends": trends,
            "top_papers": self._get_top_papers(limited_results, top_n=5),
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return synthesis
    
    def _prepare_paper_summaries(self, results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract key information from each paper for LLM analysis.
        
        Args:
            results: Raw search results
            
        Returns:
            List of paper summaries with title, text snippet, metadata
        """
        summaries = []
        
        for result in results:
            # Get paper metadata - check multiple possible fields
            paper_id = result.get('paper_id') or result.get('id', 'unknown')
            
            # Try multiple title fields: paper_title (from search), title, or metadata.title
            title = (
                result.get('paper_title') or 
                result.get('title') or 
                (result.get('metadata', {}).get('title') if isinstance(result.get('metadata'), dict) else None) or
                'Untitled'
            )
            
            text = result.get('text', '')
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
        
        return summaries
    
    async def _extract_themes(
        self, 
        query: str, 
        paper_summaries: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to identify common themes across papers.
        
        Args:
            query: Search query
            paper_summaries: Prepared paper data
            
        Returns:
            List of themes with counts: [{"name": str, "count": int, "papers": List[str]}]
        """
        
        # Prepare context for LLM
        papers_text = self._format_papers_for_prompt(paper_summaries)
        
        prompt = f"""You are a research synthesis assistant. Analyze these papers about "{query}" and identify the main themes.

Papers:
{papers_text}

Task: Identify 3-5 main themes discussed across these papers.

Return ONLY a JSON array with this exact structure:
[
  {{"name": "Theme Name", "description": "Brief description", "paper_ids": ["id1", "id2"]}},
  ...
]

Focus on:
- Methodologies used
- Key concepts discussed
- Application domains
- Research approaches

Return ONLY the JSON array, no other text."""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a research analysis assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Lower temperature for more consistent output
                max_tokens=1800
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean markdown code blocks if present
            content = clean_json_response(content)
            
            # Debug: Print what we got from GPT-4
            print(f"📝 GPT-4 themes response (first 200 chars): {content[:200]}")
            
            # Parse JSON response
            themes_raw = json.loads(content)
            
            # Format themes with counts
            themes = []
            for theme in themes_raw:
                themes.append({
                    "name": theme.get("name", "Unknown Theme"),
                    "description": theme.get("description", ""),
                    "count": len(theme.get("paper_ids", [])),
                    "papers": theme.get("paper_ids", [])
                })
            
            return themes
            
        except Exception as e:
            print(f"❌ Error extracting themes: {e}")
            # Fallback: Return simple keyword-based themes
            return self._fallback_theme_extraction(paper_summaries)
    
    async def _generate_key_findings(
        self, 
        query: str, 
        paper_summaries: List[Dict[str, str]]
    ) -> List[str]:
        """
        Extract key findings that appear consistently across papers.
        
        Args:
            query: Search query
            paper_summaries: Prepared paper data
            
        Returns:
            List of key findings as strings
        """
        
        papers_text = self._format_papers_for_prompt(paper_summaries)
        
        prompt = f"""You are a research synthesis assistant. Analyze these papers about "{query}" and identify the most important research findings.

Papers:
{papers_text}

Task: Extract 3-5 key findings from the research. Focus on:
1. Important results, conclusions, or discoveries mentioned in the papers
2. Significant insights about {query}
3. Practical implications or notable outcomes
4. Findings can be from one paper or across multiple papers

Return a JSON array with 3-5 clear findings:
["Finding 1", "Finding 2", "Finding 3"]

Each finding should be a clear, specific statement (1-2 sentences). 

IMPORTANT: Return ONLY the JSON array, nothing else. No explanations, no markdown, just the array."""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a research analysis assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1900
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean markdown code blocks if present
            content = clean_json_response(content)
            
            # Debug: Print what we got from GPT-4
            print(f"📝 LLM findings response (first 200 chars): {content[:200]}")
            
            findings = json.loads(content)
            
            # Check if we got valid findings
            if isinstance(findings, list) and len(findings) > 0:
                return findings
            else:
                print("⚠️ Empty findings array received, using fallback")
                return [
                    f"Research on {query} demonstrates diverse methodologies and approaches across {len(paper_summaries)} papers",
                    "Multiple technical implementations and architectural patterns have been explored",
                    "Significant interest in performance optimization and scalability challenges"
                ]
            
        except Exception as e:
            print(f"❌ Error generating key findings: {e}")
            return [
                f"Analysis of {len(paper_summaries)} papers about {query}",
                "Multiple approaches and methodologies identified",
                "Further synthesis requires successful LLM processing"
            ]
    
    async def _identify_research_gaps(
        self, 
        query: str, 
        paper_summaries: List[Dict[str, str]],
        themes: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Identify underexplored areas or research gaps.
        
        Args:
            query: Search query
            paper_summaries: Prepared paper data
            themes: Already identified themes
            
        Returns:
            List of research gaps as strings
        """
        
        papers_text = self._format_papers_for_prompt(paper_summaries[:10])  # Limit for token efficiency
        themes_text = ", ".join([t["name"] for t in themes])
        
        prompt = f"""You are a research analysis assistant. Identify research gaps in papers about "{query}".

Main themes found: {themes_text}

Papers:
{papers_text}

Task: Identify 2-4 research gaps or underexplored areas:
1. Topics mentioned but not deeply explored
2. Contradictions or unresolved questions
3. Methodological limitations noted
4. Future work suggestions from authors

Return ONLY a JSON array of strings:
["Gap 1", "Gap 2", ...]

Each gap should be specific and actionable.

Return ONLY the JSON array, no other text."""

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a research analysis assistant. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,  # Slightly higher for creative gap identification
                max_tokens=900
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean markdown code blocks if present
            content = clean_json_response(content)
            
            # Debug: Print what we got from GPT-4
            print(f"📝 GPT-4 gaps response (first 200 chars): {content[:200]}")
            
            gaps = json.loads(content)
            
            return gaps if isinstance(gaps, list) else []
            
        except Exception as e:
            print(f"❌ Error identifying research gaps: {e}")
            return ["Research gap analysis requires successful LLM processing"]
    
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
            authors_str = ", ".join(paper.get('authors', [])[:3])  # First 3 authors
            if len(paper.get('authors', [])) > 3:
                authors_str += " et al."
            
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
