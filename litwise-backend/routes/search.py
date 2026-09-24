"""
Search Routes
Endpoints for semantic hybrid search across research papers and Qdrant diagnostics
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
import os
import traceback

from models import SearchQuery, SearchFilters
from middleware import get_current_user, AuthUser
from workflow.db import qdrant, supabase
from workflow.enhanced_search import enhanced_search
from services.nl_query_parser import nl_query_parser
from langchain_openai import OpenAIEmbeddings

router = APIRouter(tags=["Search"])


@router.post("/search")
async def search_papers(query: SearchQuery, current_user: AuthUser = Depends(get_current_user)):
    """
    Advanced semantic search across user's papers using hybrid search

    Only searches papers owned by the authenticated user.

    Features:
    - Natural language query parsing (Stage 1: years, venues, content flags)
    - Vector similarity search (semantic understanding)
    - BM25 keyword search (lexical matching) when available
    - Query expansion (acronyms + synonyms)
    - Metadata filtering (author, year, keywords, venue, content)
    - Result diversity scoring (prefer results from different papers)

    Args:
        query: SearchQuery with query text, filters, and options
        current_user: Authenticated user (from JWT)

    Returns:
        List of search results with relevance scores and metadata
    """
    try:
        # Phase 2 Stage 1: Natural Language Query Parsing
        parsed_query_info = None
        search_query_text = query.query

        if query.use_nl_parsing:
            print(f"🧠   Parsing natural language query: '{query.query}'")
            parsed = await nl_query_parser.parse_query(query.query, enable_ai=False)  # Regex-only for speed

            if parsed.get('parsed_elements'):
                print(f"✅  Parsed filters: {', '.join(parsed['parsed_elements'])}")
                search_query_text = parsed['semantic_query']

                # Merge parsed filters with existing filters
                if not query.filters:
                    query.filters = SearchFilters.model_construct()

                # Apply parsed filters (don't override manually set filters)
                for key, value in parsed.get('filters', {}).items():
                    if hasattr(query.filters, key) and not getattr(query.filters, key, None):
                        setattr(query.filters, key, value)

                # Store parsed info for response
                parsed_query_info = {
                    'original_query': query.query,
                    'semantic_query': search_query_text,
                    'parsed_elements': parsed['parsed_elements'],
                    'confidence': parsed['confidence']
                }
            else:
                print(f"ℹ️  No filters detected in query, using as-is")

        # Initialize embeddings model
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY")  # type: ignore
        )

        # Get paper IDs from filters if specified
        filtered_paper_ids = None
        filters = getattr(query, "filters", None)

        if filters and getattr(filters, "paper_ids", None):
            filtered_paper_ids = filters.paper_ids

        # Apply database-level metadata filters (author, year, keywords, content, venue)
        db_filters = []
        if filters:
            if getattr(filters, "author", None):
                # Search for author name in JSONB authors field
                author_filter = (
                    f'authors @> \'[{{"name": "{filters.author}"}}]\'::jsonb'
                )
                db_filters.append(author_filter)

            if getattr(filters, "year_from", None):
                db_filters.append(f"publication_year >= {filters.year_from}")

            if getattr(filters, "year_to", None):
                db_filters.append(f"publication_year <= {filters.year_to}")

            if getattr(filters, "keywords", None):
                # Match any of the provided keywords
                for keyword in filters.keywords:
                    db_filters.append(f"'{keyword}' = ANY(keywords)")

            # Phase 1.1: Content filters - use boolean columns
            if getattr(filters, "has_images", None) is True:
                db_filters.append("has_images = TRUE")

            if getattr(filters, "has_tables", None) is True:
                db_filters.append("has_tables = TRUE")

            if getattr(filters, "has_equations", None) is True:
                db_filters.append("has_equations = TRUE")

            # Phase 1.2: Venue filter - filter by conference or journal name
            if getattr(filters, "venue", None):
                # Case-insensitive partial match on journal_or_conference field
                venue_filter = f"LOWER(journal_or_conference) LIKE LOWER('%{filters.venue}%')"
                db_filters.append(venue_filter)

        # Fetch filtered papers from database if filters applied
        # Always filter by user_id for data isolation
        if filters and not filtered_paper_ids:
            try:
                sb_query = supabase.table("papers").select("id").eq("user_id", current_user.id)
                if getattr(filters, "year_from", None):
                    sb_query = sb_query.gte("publication_year", filters.year_from)
                if getattr(filters, "year_to", None):
                    sb_query = sb_query.lte("publication_year", filters.year_to)
                if getattr(filters, "has_images", None) is True:
                    sb_query = sb_query.eq("has_images", True)
                if getattr(filters, "has_tables", None) is True:
                    sb_query = sb_query.eq("has_tables", True)
                if getattr(filters, "has_equations", None) is True:
                    sb_query = sb_query.eq("has_equations", True)
                if getattr(filters, "venue", None):
                    sb_query = sb_query.ilike("journal_or_conference", f"%{filters.venue}%")

                result = sb_query.execute()
                filtered_paper_ids = [paper["id"] for paper in (result.data or []) if isinstance(paper, dict)]

                if not filtered_paper_ids:
                    print(f"[WARNING]   No papers match the metadata filters")
                    return []

                print(f"📋  Filtered to {len(filtered_paper_ids)} papers by metadata")
            except Exception as e:
                print(f"[WARNING]   Metadata filtering failed: {e}, proceeding without filters")
                filtered_paper_ids = None
        elif not filtered_paper_ids:
            # No specific filters, but still need to limit to user's papers
            try:
                result = supabase.table("papers").select("id").eq("user_id", current_user.id).execute()
                filtered_paper_ids = [paper["id"] for paper in (result.data or []) if isinstance(paper, dict) and "id" in paper]

                if not filtered_paper_ids:
                    print(f"ℹ️  User has no papers uploaded yet")
                    return []

                print(f"📋  Searching across {len(filtered_paper_ids)} papers owned by user")
            except Exception as e:
                print(f"[WARNING]   Failed to fetch user's papers: {e}")
                raise HTTPException(status_code=500, detail="Failed to fetch user's papers")

        # Perform hybrid search across all papers (or filtered subset)
        results = await enhanced_search.hybrid_search(
            qdrant_client=qdrant,
            embeddings_model=embeddings,
            paper_id=None,  # Cross-paper search
            query=search_query_text,  # Use cleaned query from NL parsing
            top_k=query.limit,
            use_query_expansion=True,
        )

        # Filter results by paper_ids if specified
        if filtered_paper_ids:
            results = [
                result
                for result in results
                if result.get("paper_id") in filtered_paper_ids
            ]

        # Collect unique paper IDs from results
        unique_paper_ids = list(
            set(result.get("paper_id") for result in results if result.get("paper_id"))
        )

        # Fetch all paper metadata in one batch query (optimization)
        paper_metadata_map = {}
        if unique_paper_ids:
            try:
                # Batch fetch paper metadata for all unique paper IDs
                paper_data = (
                    supabase.table("papers")
                    .select(
                        "id, title, authors, publication_year, doi, keywords, journal_or_conference"
                    )
                    .in_("id", unique_paper_ids)
                    .execute()
                )

                # Create a map for quick lookup
                for paper in (paper_data.data or []):
                    if isinstance(paper, dict) and "id" in paper:
                        paper_metadata_map[paper["id"]] = paper

                print(
                    f"📚  Fetched metadata for {len(paper_metadata_map)} unique papers"
                )
            except Exception as e:
                print(f"[WARNING]   Failed to fetch paper metadata: {e}")

        # Enrich results with paper metadata from database
        enriched_results = []
        for result in results:
            paper_id = result.get("paper_id")
            if not paper_id:
                continue

            # Clamp relevance score to [0, 1] range (prevent negative percentages)
            relevance_score = result.get("relevance_score", result.get("score", 0))
            if isinstance(relevance_score, (int, float)):
                result["relevance_score"] = max(0.0, min(1.0, float(relevance_score)))

            # Get metadata from pre-fetched map
            paper_info = paper_metadata_map.get(paper_id)
            if paper_info:
                result["paper_title"] = paper_info.get("title", "Unknown")
                result["authors"] = paper_info.get("authors", [])
                result["publication_year"] = paper_info.get("publication_year")
                result["doi"] = paper_info.get("doi")
                result["keywords"] = paper_info.get("keywords", [])
                result["journal_or_conference"] = paper_info.get("journal_or_conference")

            # Ensure both paper_id and id are present for frontend compatibility
            result["id"] = paper_id  # Add explicit id field for frontend
            enriched_results.append(result)

        return enriched_results

    except Exception as e:
        print(f" Search failed: {e}")
        traceback.print_exc()

        if query.debug:
            return []

        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/debug/qdrant")
def debug_qdrant():
    """Return basic Qdrant collection diagnostics to help debug empty search results."""
    collection = "litwise_collection"
    info: Dict[str, Any] = {
        "collection": collection,
        "exists": None,
        "count": None,
        "sample_points": [],
        "errors": [],
    }

    # 1) Try getting collection info
    try:
        if hasattr(qdrant, "get_collection"):
            coll = getattr(qdrant, "get_collection")(collection_name=collection)
            info["exists"] = True
            info["collection_info"] = getattr(coll, "to_dict", lambda: coll)()
        else:
            info["exists"] = None
    except Exception as e:
        info["exists"] = False
        info["errors"].append(f"get_collection failed: {e}")

    # 2) Try counting points
    try:
        for kw in ("collection_name", "collection"):
            try:
                cnt = getattr(qdrant, "count")(**{kw: collection})
                info["count"] = cnt
                break
            except TypeError:
                try:
                    cnt = getattr(qdrant, "count")(**{kw: collection})
                    info["count"] = getattr(cnt, "count", cnt)
                    break
                except Exception:
                    continue
    except Exception as e:
        info["errors"].append(f"count failed: {e}")

    # 3) Try to fetch a few sample points
    try:
        samples = None
        if hasattr(qdrant, "scroll"):
            try:
                s = qdrant.scroll(collection_name=collection, limit=5)
                samples = s
            except Exception:
                pass

        if samples is None:
            try:
                api = getattr(qdrant.http, "points_api", None)
                if api is not None and hasattr(api, "scroll"):
                    resp = api.scroll(collection_name=collection, limit=5)
                    samples = getattr(resp, "result", resp)
            except Exception:
                pass

        if samples is None and info.get("count") and info["count"] > 0:
            try:
                s = qdrant.scroll(collection_name=collection, limit=5)
                samples = s
            except Exception as e:
                info["errors"].append(f"sample fetch failed: {e}")

        info["sample_points"] = samples or []
    except Exception as e:
        info["sample_points"] = []
        info["errors"].append(f"sample points failed: {e}")

    return info
