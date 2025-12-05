from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import (
    PaperUpload,
    PaperSummary,
    SearchQuery,
    ProcessingRequest,
    ProcessingResponse,
    SynthesisRequest,
    SynthesisResponse,  # Phase 1: Synthesis models
    SaveSynthesisRequest,
    UpdateSynthesisTagsRequest,
)
from pipeline import workflow as graph_app
from workflow.utils import extract_text_from_pdf, store_embedding
from workflow.db import supabase
from async_pipeline import get_async_pipeline
from typing import Optional
import os
import tempfile
import uuid
import asyncio
import json
from datetime import datetime

# Import chat and study plan routes and other routes
from routes.chat import router as chat_router
from routes.study_plan import router as study_plan_router
from routes.citations import router as citations_router
from routes.literature_review import router as literature_review_router

# Import synthesis service (Phase 1)
from workflow.synthesis_service import synthesis_service


app = FastAPI(title="Litwise API", version="1.0.0")


@app.get("/health")
def health_check():
    """Health check endpoint to verify the server is running."""
    return {"status": "healthy", "message": "Litwise API is running"}


# Include chat router
app.include_router(chat_router)

# Include study plan router
app.include_router(study_plan_router)

# Include citations router
app.include_router(citations_router)

# Include literature review router
app.include_router(literature_review_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Litwise API"}


# Handle CORS preflight requests explicitly
@app.options("/{full_path:path}")
def options_handler():
    """Handle CORS preflight requests."""
    return {"message": "OK"}


# CORS configuration - more permissive for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",  # Alternative localhost
        "https://localhost:3000",  # HTTPS variant
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.post("/upload", response_model=dict)
async def upload_paper(file: UploadFile = File(...), title: str = None):
    """Upload and extract text and metadata from PDF (without AI processing)."""
    try:
        # Generate unique ID for paper
        paper_id = str(uuid.uuid4())

        # Validate file type
        if not file.content_type or file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Read file content first
        content = await file.read()
        file_size = len(content)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Extract text and page info
            text, page_info = extract_text_from_pdf(tmp_path)
            if not text or len(text.strip()) < 10:
                raise HTTPException(
                    status_code=400, detail="Could not extract meaningful text from PDF"
                )

            # Extract metadata from PDF
            from workflow.metadata_extractor import metadata_extractor

            paper_metadata = metadata_extractor.extract_from_pdf(tmp_path)

        finally:
            os.unlink(tmp_path)  # Cleanup

        # Extract clean filename without extension
        clean_filename = None
        if file.filename:
            clean_filename = os.path.splitext(file.filename)[0]

        # Use extracted title if not provided and available in metadata
        final_title = (
            title
            or paper_metadata.get("extracted_title")
            or clean_filename
            or "Untitled Document"
        )

        # Store in Supabase papers table (without AI summary)
        paper_data = {
            "id": paper_id,
            "title": final_title,
            "content_text": text,
            "page_info": json.dumps(page_info),
            "embedding_id": paper_id,
            "user_id": None,
            "file_size": file_size,
            "filename": file.filename,
            "processing_status": "uploaded",
            "created_at": datetime.utcnow().isoformat(),
            # Add extracted metadata
            "authors": json.dumps(paper_metadata.get("authors", [])),
            "publication_year": paper_metadata.get("publication_year"),
            "doi": paper_metadata.get("doi"),
            "keywords": paper_metadata.get("keywords", []),
            "journal_or_conference": paper_metadata.get("journal_or_conference"),
            "abstract": paper_metadata.get("abstract"),
        }

        # Insert into Supabase
        try:
            supabase_result = supabase.table("papers").insert(paper_data).execute()
            print(f"✅ Successfully uploaded paper: {paper_id}")
            print(
                f"📊 Metadata: {len(paper_metadata.get('authors', []))} authors, year: {paper_metadata.get('publication_year')}"
            )
        except Exception as e:
            print(f"❌ Database insertion error: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        # Note: Embeddings will be generated during processing stage for efficiency

        return {
            "id": paper_id,
            "title": paper_data["title"],
            "status": "uploaded",
            "message": "Paper uploaded successfully! Metadata extracted. You can start chatting now.",
            "metadata": {
                "authors": paper_metadata.get("authors", []),
                "year": paper_metadata.get("publication_year"),
                "doi": paper_metadata.get("doi"),
                "keywords": paper_metadata.get("keywords", []),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Upload error: {e}")
        import traceback  # What is traceback used for? It provides detailed error stack traces for debugging.

        traceback.print_exc()  # Print the full traceback to the console for debugging.
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/papers/{paper_id}/process", response_model=ProcessingResponse)
async def process_paper_ai(paper_id: str):
    """Generate AI summary for an uploaded paper."""
    try:
        # Get paper from database
        result = (
            supabase.table("papers")
            .select("id, title, content_text, page_info, processing_status")
            .eq("id", paper_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Paper not found")

        paper = result.data[0]

        # Check if paper is already processed
        if paper["processing_status"] == "completed":
            return ProcessingResponse(
                id=paper_id, status="completed", message="Paper already processed"
            )

        if paper["processing_status"] == "processing":
            raise HTTPException(
                status_code=409, detail="Paper is currently being processed"
            )

        # Update status to processing
        supabase.table("papers").update(
            {"processing_status": "processing", "processing_error": None}
        ).eq("id", paper_id).execute()

        try:
            # Start AI processing and embedding enhancement in parallel
            text = paper["content_text"]

            # Parse page_info from stored JSON
            stored_page_info = paper.get("page_info")
            page_info = None
            if stored_page_info:
                try:
                    page_info = json.loads(stored_page_info)
                    print(f"Loaded page_info for {paper_id}: {len(page_info)} pages")
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse page_info for paper {paper_id}")
                    page_info = None
            else:
                print(f"No page_info found for paper {paper_id}")

            # Use async pipeline for non-blocking AI processing
            async_pipeline = get_async_pipeline(graph_app)

            # Process with timeout to prevent hanging
            pipeline_result = await async_pipeline.process_with_timeout(
                text, timeout_seconds=300
            )

            if pipeline_result["status"] != "completed":
                # Handle timeout or error
                error_msg = pipeline_result.get("error", "Processing failed")
                raise HTTPException(
                    status_code=500, detail=f"AI processing failed: {error_msg}"
                )

            result = pipeline_result["result"]

            # Clean and structure the summary (reuse existing logic)
            summary_data = result.get("summary", {})

            if isinstance(summary_data, dict):
                if "summary" in summary_data and isinstance(
                    summary_data["summary"], dict
                ):
                    summary_data = summary_data["summary"]

                if not any(
                    key in summary_data
                    for key in ["key_points", "citations", "related_works"]
                ):
                    for value in summary_data.values():
                        if isinstance(value, dict) and any(
                            key in value
                            for key in ["key_points", "citations", "related_works"]
                        ):
                            summary_data = value
                            break

            clean_summary = {"key_points": [], "citations": [], "related_works": []}

            if isinstance(summary_data, dict):
                # Extract and clean key_points
                if "key_points" in summary_data:
                    kp = summary_data["key_points"]
                    if isinstance(kp, list):
                        clean_summary["key_points"] = [str(item) for item in kp if item]
                    elif isinstance(kp, str):
                        clean_summary["key_points"] = [kp] if kp.strip() else []

                # Extract and clean citations
                if "citations" in summary_data:
                    cit = summary_data["citations"]
                    if isinstance(cit, list):
                        clean_summary["citations"] = [str(item) for item in cit if item]
                    elif isinstance(cit, str):
                        clean_summary["citations"] = [cit] if cit.strip() else []

                # Extract and clean related_works
                if "related_works" in summary_data:
                    rw = summary_data["related_works"]
                    if isinstance(rw, list):
                        clean_summary["related_works"] = [
                            str(item) for item in rw if item
                        ]
                    elif isinstance(rw, str):
                        clean_summary["related_works"] = [rw] if rw.strip() else []

            # Validate JSON serialization
            try:
                json.dumps(clean_summary)
                final_summary = clean_summary
            except (TypeError, ValueError):
                final_summary = {
                    "key_points": ["Processing completed with errors"],
                    "citations": [],
                    "related_works": [],
                    "error": "JSON serialization failed",
                }

            # Update paper with AI summary
            supabase.table("papers").update(
                {
                    "summary": final_summary,
                    "processing_status": "completed",
                    "ai_generated_at": datetime.utcnow().isoformat(),
                }
            ).eq("id", paper_id).execute()

            # Generate enhanced embeddings with AI insights
            try:
                print(f"Enhancing embeddings with AI insights for paper: {paper_id}")

                # Create AI-enhanced content for superior retrieval
                enhanced_text = f"{text}\n\n=== AI SUMMARY ===\n"
                enhanced_text += (
                    f"Key Points: {'. '.join(final_summary.get('key_points', []))}\n"
                )
                enhanced_text += (
                    f"Citations: {'. '.join(final_summary.get('citations', []))}\n"
                )
                enhanced_text += f"Related Works: {'. '.join(final_summary.get('related_works', []))}"

                # Enhanced metadata with AI insights
                enhanced_metadata = {
                    "id": paper_id,
                    "title": paper["title"],
                    "summary": final_summary,
                    "status": "completed",
                    "has_ai_summary": True,
                    "processing_date": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                }

                # Store enhanced embeddings for optimal chat functionality
                store_embedding(
                    enhanced_text,
                    enhanced_metadata,
                    paper_id=paper_id,
                    embedding_type="enhanced",
                    page_info=page_info,
                )
                print(
                    f"Successfully enhanced embeddings with AI insights for paper: {paper_id}"
                )

            except Exception as e:
                print(f"Embedding enhancement error: {e}")
                # Don't fail processing if embedding generation fails
                print(
                    f"WARNING: AI processing completed but embedding enhancement failed for {paper_id}"
                )

            return ProcessingResponse(
                id=paper_id,
                status="completed",
                message="AI processing completed successfully",
                summary=final_summary,
            )

        except Exception as e:
            # Update status to failed
            supabase.table("papers").update(
                {"processing_status": "failed", "processing_error": str(e)}
            ).eq("id", paper_id).execute()

            print(f"AI processing failed for {paper_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"AI processing failed: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/search")
async def search_papers(query: SearchQuery):
    """
    Advanced semantic search across all papers using hybrid search

    Features:
    - Vector similarity search (semantic understanding)
    - BM25 keyword search (lexical matching) when available
    - Query expansion (acronyms + synonyms)
    - Metadata filtering (author, year, keywords)
    - Result diversity scoring (prefer results from different papers)

    Args:
        query: SearchQuery with query text, filters, and options

    Returns:
        List of search results with relevance scores and metadata
    """
    from workflow.db import qdrant, supabase
    from workflow.utils import generate_embeddings
    from workflow.enhanced_search import enhanced_search
    from langchain_openai import OpenAIEmbeddings
    from fastapi import HTTPException

    try:
        # Initialize embeddings model
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small", openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        # Get paper IDs from filters if specified
        filtered_paper_ids = None
        filters = getattr(query, "filters", None)

        if filters and getattr(filters, "paper_ids", None):
            filtered_paper_ids = filters.paper_ids

        # Apply database-level metadata filters (author, year, keywords)
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

        # Fetch filtered papers from database if filters applied
        if db_filters and not filtered_paper_ids:
            try:
                where_clause = " AND ".join(db_filters)
                result = (
                    supabase.table("papers").select("id").filter(where_clause).execute()
                )
                filtered_paper_ids = [paper["id"] for paper in result.data]

                if not filtered_paper_ids:
                    print(f"⚠️ No papers match the metadata filters")
                    return []

                print(f"📋 Filtered to {len(filtered_paper_ids)} papers by metadata")
            except Exception as e:
                print(f"⚠️ Metadata filtering failed: {e}, proceeding without filters")
                filtered_paper_ids = None

        # Perform hybrid search across all papers (or filtered subset)
        results = await enhanced_search.hybrid_search(
            qdrant_client=qdrant,
            embeddings_model=embeddings,
            paper_id=None,  # Cross-paper search
            query=query.query,
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
                for paper in paper_data.data:
                    paper_metadata_map[paper["id"]] = paper

                print(
                    f"📚 Fetched metadata for {len(paper_metadata_map)} unique papers"
                )
            except Exception as e:
                print(f"⚠️ Failed to fetch paper metadata: {e}")

        # Enrich results with paper metadata from database
        enriched_results = []
        for result in results:
            paper_id = result.get("paper_id")
            if not paper_id:
                continue

            # Get metadata from pre-fetched map
            paper_info = paper_metadata_map.get(paper_id)
            if paper_info:
                result["paper_title"] = paper_info.get("title", "Unknown")
                result["authors"] = paper_info.get("authors", [])
                result["publication_year"] = paper_info.get("publication_year")
                result["doi"] = paper_info.get("doi")
                result["keywords"] = paper_info.get("keywords", [])
                result["journal_or_conference"] = paper_info.get(
                    "journal_or_conference"
                )

            enriched_results.append(result)

        print(f"✅ Search complete: {len(enriched_results)} results returned")
        return enriched_results

    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback

        traceback.print_exc()

        if query.debug:
            return {"results": [], "error": str(e), "traceback": traceback.format_exc()}

        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

        print(f"✅ Search complete: {len(enriched_results)} results returned")
        return enriched_results

    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback

        traceback.print_exc()

        if query.debug:
            return {"results": [], "error": str(e), "traceback": traceback.format_exc()}

        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/search/synthesize", response_model=SynthesisResponse)
async def synthesize_search_results(request: SynthesisRequest):
    """
    Generate AI-powered research synthesis from search results.

    This endpoint:
    1. Takes search results from the /search endpoint
    2. Analyzes papers using LLM (GPT-4)
    3. Identifies themes, key findings, research gaps
    4. Analyzes publication trends over time
    5. Returns structured synthesis data

    Args:
        request: SynthesisRequest with query and search_results

    Returns:
        SynthesisResponse with themes, findings, gaps, trends

    Example Request:
        POST /search/synthesize
        {
            "query": "transformers in NLP",
            "search_results": [
                {
                    "id": "paper-123",
                    "title": "Attention is All You Need",
                    "text": "...",
                    "relevance_score": 0.92,
                    "publication_year": 2017,
                    "authors": ["Vaswani", "Shazeer"]
                },
                ...
            ]
        }

    Example Response:
        {
            "query": "transformers in NLP",
            "paper_count": 12,
            "themes": [
                {
                    "name": "Attention Mechanisms",
                    "description": "Self-attention and multi-head attention",
                    "count": 8,
                    "papers": ["paper-123", "paper-456"]
                }
            ],
            "key_findings": [
                "Transformers outperform RNNs on long sequences",
                "Pre-training improves downstream task performance"
            ],
            "research_gaps": [
                "Limited work on low-resource languages",
                "Computational efficiency remains a challenge"
            ],
            "trends": {
                "timeline": [
                    {"year": 2017, "count": 2},
                    {"year": 2018, "count": 5},
                    {"year": 2019, "count": 8}
                ],
                "trend_description": "Increasing research activity"
            },
            "top_papers": [
                {
                    "id": "paper-123",
                    "title": "Attention is All You Need",
                    "relevance": 0.92,
                    "year": 2017
                }
            ],
            "generated_at": "2025-11-29T12:34:56.789Z"
        }
    """
    try:
        print(f"🔬 Starting synthesis for query: '{request.query}'")
        print(f"📚 Analyzing {len(request.search_results)} papers")

        # Call synthesis service
        synthesis = await synthesis_service.synthesize_search_results(
            query=request.query,
            search_results=request.search_results,
            max_papers=request.max_papers if hasattr(request, "max_papers") else 20,
        )

        print(f"✅ Synthesis complete:")
        print(f"   - Themes: {len(synthesis.get('themes', []))}")
        print(f"   - Key Findings: {len(synthesis.get('key_findings', []))}")
        print(f"   - Research Gaps: {len(synthesis.get('research_gaps', []))}")

        return synthesis

    except Exception as e:
        print(f"❌ Synthesis failed: {e}")
        import traceback

        traceback.print_exc()

        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


# ============================================
# SYNTHESIS HISTORY ENDPOINTS
# ============================================

@app.post("/synthesis/save")
async def save_synthesis(request: SaveSynthesisRequest):
    """
    Save a synthesis to history for future reference.
    
    This endpoint stores the complete synthesis result including:
    - Query and settings used
    - All synthesis data (themes, findings, gaps, trends)
    - Original search results for reproducibility
    - Optional tags for organization
    
    Args:
        request: SaveSynthesisRequest with synthesis data
        
    Returns:
        Saved synthesis with ID and timestamps
        
    Example:
        POST /synthesis/save
        {
            "synthesis": {...},
            "search_results": [...],
            "max_papers": 20,
            "tags": ["literature-review", "deep-learning"]
        }
    """
    try:
        from models import (
            SaveSynthesisRequest,
            SynthesisHistoryItem
        )
        
        synthesis = request.synthesis
        
        # Extract paper IDs from search results
        paper_ids = list(set([
            str(result.get('paper_id', '')) # Extract paper IDs from search results
            for result in request.search_results # Iterate over search results
            if result.get('paper_id') # Ensure paper_id exists
        ]))
        
        # Prepare data for database
        synthesis_data = {
            "query": synthesis.query,
            "paper_count": synthesis.paper_count,
            "max_papers": request.max_papers,
            "themes": [theme.model_dump() for theme in synthesis.themes], # Why model_dump() used here?  # Convert Pydantic models to dicts for storage
            "key_findings": synthesis.key_findings,
            "research_gaps": synthesis.research_gaps,
            "trends": synthesis.trends.model_dump(),
            "top_papers": [paper.model_dump() for paper in synthesis.top_papers],
            "paper_ids": paper_ids,
            "search_results": request.search_results,
            "tags": request.tags
        }
        
        # Insert into Supabase
        result = supabase.table("synthesis_history").insert(synthesis_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to save synthesis")
        
        saved = result.data[0]
        
        print(f"✅ Synthesis saved: ID={saved['id']}, Query='{synthesis.query}'")
        
        return {
            "id": saved["id"],
            "message": "Synthesis saved successfully",
            "synthesis": saved
        }
        
    except Exception as e:
        print(f"❌ Save synthesis failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save synthesis: {str(e)}")


@app.get("/synthesis/history")
async def get_synthesis_history(
    limit: int = 20,
    offset: int = 0,
    tag: Optional[str] = None
):
    """
    Get list of saved syntheses from history.
    
    Returns lightweight list items with essential information.
    Use GET /synthesis/history/{id} to get full synthesis details.
    
    Args:
        limit: Maximum number of items to return (default: 20)
        offset: Number of items to skip (for pagination, default: 0)
        tag: Optional tag filter (returns only syntheses with this tag)
        
    Returns:
        List of synthesis history items with counts
        
    Example:
        GET /synthesis/history?limit=10&tag=literature-review
    """
    try:
        # Build query
        query = supabase.table("synthesis_history").select(
            "id, query, paper_count, themes, tags, created_at"
        )
        
        # Apply tag filter if provided
        if tag:
            query = query.contains("tags", [tag])
        
        # Apply pagination and ordering
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        # Transform to list items
        history_items = []
        for item in result.data:
            history_items.append({
                "id": item["id"],
                "query": item["query"],
                "paper_count": item["paper_count"],
                "theme_count": len(item.get("themes", [])),
                "tags": item.get("tags", []),
                "created_at": item["created_at"]
            })
        
        # Get total count for pagination
        count_result = supabase.table("synthesis_history").select("id", count="exact").execute()
        total_count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
        
        return {
            "items": history_items,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        print(f"❌ Get synthesis history failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


@app.get("/synthesis/history/{synthesis_id}")
async def get_synthesis_by_id(synthesis_id: str):
    """
    Get full details of a specific saved synthesis.
    
    Returns complete synthesis data including all themes, findings, gaps, and trends.
    
    Args:
        synthesis_id: UUID of the saved synthesis
        
    Returns:
        Complete synthesis object
        
    Example:
        GET /synthesis/history/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        result = supabase.table("synthesis_history").select("*").eq("id", synthesis_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Synthesis not found: {synthesis_id}")
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Get synthesis by ID failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to retrieve synthesis: {str(e)}")


@app.patch("/synthesis/history/{synthesis_id}/tags")
async def update_synthesis_tags(synthesis_id: str, request: UpdateSynthesisTagsRequest):
    """
    Update tags on a saved synthesis.
    
    Allows users to organize their saved syntheses with custom tags.
    
    Args:
        synthesis_id: UUID of the saved synthesis
        request: UpdateSynthesisTagsRequest with new tags
        
    Returns:
        Updated synthesis
        
    Example:
        PATCH /synthesis/history/{id}/tags
        {
            "tags": ["important", "literature-review", "2024"]
        }
    """
    try:
        from models import UpdateSynthesisTagsRequest
        
        # Check if synthesis exists
        check_result = supabase.table("synthesis_history").select("id").eq("id", synthesis_id).execute()
        if not check_result.data:
            raise HTTPException(status_code=404, detail=f"Synthesis not found: {synthesis_id}")
        
        # Update tags
        result = supabase.table("synthesis_history").update(
            {"tags": request.tags}
        ).eq("id", synthesis_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update tags")
        
        print(f"✅ Tags updated for synthesis {synthesis_id}: {request.tags}")
        
        return {
            "id": synthesis_id,
            "message": "Tags updated successfully",
            "tags": request.tags
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Update tags failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to update tags: {str(e)}")


@app.delete("/synthesis/history/{synthesis_id}")
async def delete_synthesis(synthesis_id: str):
    """
    Delete a saved synthesis from history.
    
    Args:
        synthesis_id: UUID of the synthesis to delete
        
    Returns:
        Success message
        
    Example:
        DELETE /synthesis/history/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        # Check if synthesis exists
        check_result = supabase.table("synthesis_history").select("id").eq("id", synthesis_id).execute()
        if not check_result.data:
            raise HTTPException(status_code=404, detail=f"Synthesis not found: {synthesis_id}")
        
        # Delete from database
        supabase.table("synthesis_history").delete().eq("id", synthesis_id).execute()
        
        print(f"🗑️ Synthesis deleted: {synthesis_id}")
        
        return {
            "message": "Synthesis deleted successfully",
            "id": synthesis_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Delete synthesis failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to delete synthesis: {str(e)}")


@app.get("/qdrant/diagnostics", response_model=dict)
def qdrant_diagnostics():
    """Return basic Qdrant collection diagnostics to help debug empty search results."""
    from workflow.db import qdrant

    collection = "litwise_collection"
    info = {
        "collection": collection,
        "exists": None,
        "count": None,
        "sample_points": [],
        "errors": [],
    }

    # 1) Try getting collection info
    try:
        # QdrantClient may expose get_collection or get_collection_info
        if hasattr(qdrant, "get_collection"):
            coll = qdrant.get_collection(collection_name=collection)
            info["exists"] = True
            info["collection_info"] = getattr(coll, "to_dict", lambda: coll)()
        elif hasattr(qdrant, "get_collection_info"):
            coll = qdrant.get_collection_info(collection_name=collection)
            info["exists"] = True
            info["collection_info"] = getattr(coll, "to_dict", lambda: coll)()
        else:
            info["exists"] = None
    except Exception as e:
        info["exists"] = False
        info["errors"].append(f"get_collection failed: {e}")

    # 2) Try counting points
    try:
        # different client versions accept different kwarg names
        for kw in ("collection_name", "collection"):
            try:
                cnt = getattr(qdrant, "count")(**{kw: collection})
                info["count"] = cnt
                break
            except TypeError:
                # maybe count returns object with .count
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
        # Try scroll (common helper)
        if hasattr(qdrant, "scroll"):
            try:
                s = qdrant.scroll(collection_name=collection, limit=5)
                samples = s
            except Exception:
                pass

        # Try get_point / retrieve or http.points_api scroll
        if samples is None:
            # try http.points_api if available
            try:
                api = getattr(qdrant.http, "points_api", None)
                if api is not None and hasattr(api, "scroll"):
                    resp = api.scroll(collection_name=collection, limit=5)
                    # resp may be a model with .result or direct dict
                    samples = getattr(resp, "result", resp)
            except Exception:
                pass

        # If still none, try get_point for ids  in a loop (not ideal)
        if samples is None and info.get("count") and info["count"] > 0:
            try:
                # use qdrant.scroll with no args as fallback
                s = qdrant.scroll(collection_name=collection, limit=5)
                samples = s
            except Exception as e:
                info["errors"].append(f"sample fetch failed: {e}")

        info["sample_points"] = samples or []
    except Exception as e:
        info["errors"].append(f"sample points failed: {e}")

    return info


@app.get("/papers", response_model=list)
def get_papers():
    """Get list of all uploaded papers with processing status."""
    try:
        result = (
            supabase.table("papers")
            .select(
                "id, title, summary, processing_status, ai_generated_at, created_at, updated_at, embedding_id, file_size, filename"
            )
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch papers: {str(e)}")


@app.get("/papers/{paper_id}", response_model=dict)
def get_paper(paper_id: str):
    """Get specific paper by ID with processing status."""
    try:
        result = (
            supabase.table("papers")
            .select(
                "id, title, summary, content_text, processing_status, ai_generated_at, processing_error, created_at, updated_at, embedding_id, file_size, filename"
            )
            .eq("id", paper_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Paper not found")

        paper = result.data[0]
        # Add content field for backward compatibility with frontend
        paper["content"] = paper.get("content_text")
        return paper
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch paper: {str(e)}")


@app.delete("/papers/{paper_id}", response_model=dict)
def delete_paper(paper_id: str):
    """Delete paper and its embeddings."""
    try:
        # First check if paper exists
        result = supabase.table("papers").select("id").eq("id", paper_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Paper not found")

        # Delete from Supabase
        supabase.table("papers").delete().eq("id", paper_id).execute()

        # Delete embeddings from Qdrant
        try:
            from workflow.db import qdrant
            from qdrant_client.http.models import Filter, FieldCondition, MatchValue

            # Delete by paper_id field in payload (embeddings use UUIDs as point IDs)
            try:
                qdrant.delete(
                    collection_name="litwise_collection",
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="paper_id",
                                match=MatchValue(value=paper_id)
                            )
                        ]
                    ),
                )
                print(f"✅ Deleted embeddings for paper: {paper_id}")
            except Exception as e:
                # If deletion fails, log but don't fail the whole operation
                print(f"Warning: Failed to delete embeddings for {paper_id}: {e}")
        except Exception as e:
            print(f"Warning: Failed to delete embeddings: {e}")

        return {"message": "Paper deleted successfully", "id": paper_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete paper: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
