from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from models import (
    ProcessingResponse,
)
from pipelines import graph_app, get_async_pipeline
from workflow.utils import store_embedding, extract_multimodal_from_pdf, store_multimodal_embeddings
from workflow.db import supabase
from typing import Optional, List, Dict, Any, cast
import os
import tempfile
import uuid
import json
from datetime import datetime, timezone
import logging

# Import authentication middleware and rate limiting middleware
from middleware import get_current_user, AuthUser
from middleware.rate_limit_middleware import RateLimitMiddleware

# Import cache service to verify initialization
from services.message_cache_service import message_cache_service

# Import all the routes here
from routes.chat import router as chat_router
from routes.study_plan import router as study_plan_router
from routes.citations import router as citations_router
from routes.literature_review import router as literature_review_router
from routes.ai_citations import router as ai_citations_router
from routes.export import router as export_router
from routes.media import router as media_router
from routes.notes import router as notes_router
from routes.quiz import router as quiz_router
from routes.search import router as search_router

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Sentry for error tracking
def init_sentry():
    """
    Initialize Sentry error tracking.

    Sentry captures and reports all errors in production.
    - Development: Disabled if SENTRY_DSN not set
    - Production: Enabled with SENTRY_DSN environment variable

    Tracks:
    - Unhandled exceptions
    - HTTP errors (4xx, 5xx)
    - Performance metrics
    - User feedback
    """
    sentry_dsn = os.getenv("SENTRY_DSN", "")
    environment = os.getenv("ENVIRONMENT", "development")

    if not sentry_dsn:
        logger.info("[WARNING]   Sentry: NOT CONFIGURED (no SENTRY_DSN)")
        logger.info("   - Error tracking disabled")
        logger.info("   - Production errors will go unseen")
        return

    try:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                FastApiIntegration(),
                StarletteIntegration(),
            ],
            # Sample 10% of transactions (performance monitoring)
            traces_sample_rate=0.1,
            # Sample 100% of errors (all errors are captured)
            sample_rate=1.0,
            environment=environment,
            # Release info (optional, helps track deployments)
            release=os.getenv("APP_VERSION", "1.0.0"),
            # Enable sending server name for debugging
            server_name=os.getenv("SERVER_NAME", "litwise-api"),
        )
        logger.info("[OK] Sentry: Connected and monitoring errors")
        logger.info(f"   - Environment: {environment}")
        logger.info(f"   - Capturing 100% of errors")
        logger.info(f"   - Performance sampling: 10%")
    except Exception as e:
        logger.error(f" Sentry initialization failed: {e}")

# Initialize Sentry before creating the app
init_sentry()

# CORS configuration - support both local development and production
def get_allowed_origins():
    """
    This sets up Cross-Origin Resource Sharing (CORS).
    It ensures our frontend (Vercel) is allowed to make requests to our backend (Render/Railway).
    If the backend crashes and doesn't return these headers, the browser throws a CORS error.

    Environment variable: ALLOWED_ORIGINS (comma-separated list)
    Default for development: http://localhost:3000, http://127.0.0.1:3000, https://localhost:3000

    Examples:
    - Development (default): ALLOWED_ORIGINS not set
    - Production: ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
    """
    env_origins = os.getenv("ALLOWED_ORIGINS", "")

    if env_origins:
        # Production: split by comma and strip whitespace
        origins = [origin.strip() for origin in env_origins.split(",") if origin.strip()]
        logger.info(f"[OK] CORS Origins (from environment): {origins}")
        return origins
    else:
        # Development: default localhost origins
        default_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://localhost:3000",
        ]
        logger.info(f"ℹ️ï¸  CORS Origins (default development): {default_origins}")
        return default_origins

async def startup_event():
    """Initialize and verify Redis cache on startup."""
    logger.info("=" * 60)
    logger.info("[START] Litwise API Starting Up")
    logger.info("=" * 60)

    # Check Redis cache status
    if message_cache_service.redis_client:
        logger.info("[OK] Redis Cache: Connected and ready")
        logger.info(f"   - Cache TTL: 24 hours")
        logger.info(f"   - Max messages per session: 5000")
    else:
        logger.warning("[WARNING]   Redis Cache: NOT CONNECTED - Cache disabled!")
        logger.warning("   - Database will be queried on every request (no caching)")
        logger.warning("   - Check REDIS_URL environment variable")

    # Check Sentry error monitoring
    if sentry_sdk.Hub.current.client:
        logger.info("[OK] Error Monitoring: Sentry is active")
        logger.info(f"   - All exceptions will be tracked")
        logger.info(f"   - Dashboard: https://sentry.io")
    else:
        logger.warning("[WARNING]   Error Monitoring: Sentry is disabled")
        logger.warning("   - Production errors will NOT be captured")
        logger.warning("   - Set SENTRY_DSN environment variable")

    logger.info("[OK] Response Compression: Enabled (GZIP)")
    logger.info("   - Reduces response size by 60-70%")
    logger.info("   - Minimum compression size: 1 KB")

    logger.info("=" * 60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    await startup_event()
    yield
    # Shutdown (if needed in future)

app = FastAPI(
    title="Litwise API", 
    version="1.0.0",
    # Increase max request body size to 40MB (to handle 35MB PDFs with multipart overhead)
    max_request_size=40 * 1024 * 1024,
    lifespan=lifespan
)

# CORS configuration - MUST be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Add GZIP compression middleware - compresses responses to reduce network transfer time
# Minimum 1000 bytes to avoid overhead on very small responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

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

# Include AI citations router (new hybrid DOI + AI generator)
app.include_router(ai_citations_router)

# Include literature review router
app.include_router(literature_review_router)

# Include export router
app.include_router(export_router)

# Include media router (figure uploads)
app.include_router(media_router)

# Include notes router (research notes)
app.include_router(notes_router)

# Include quiz router (quiz generation)
app.include_router(quiz_router)

# Include search router (hybrid search & vector diagnostics)
app.include_router(search_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the DocuParse API"}

@app.get("/stats/research-materials")
async def get_research_materials_stats(current_user: AuthUser = Depends(get_current_user)):
    """
    Get count of research materials created by the user.

    Returns:
        - literature_reviews: Count of literature reviews created
        - study_plans: Count of study plans created
        - quizzes: Count of quizzes created (if table exists)
        - total: Total research materials created
    """
    try:
        # Convert user_id to string for consistency with database
        user_id_str = current_user.id

        # Count literature reviews (user_id is stored as text)
        lit_reviews = supabase.table("literature_reviews").select("id", count=cast(Any, "exact")).eq("user_id", user_id_str).execute()
        lit_reviews_count = lit_reviews.count if hasattr(lit_reviews, 'count') and lit_reviews.count is not None else len(lit_reviews.data or [])

        # Count study plans (need to join through papers table since study_plans doesn't have user_id directly)
        paper_ids = []
        try:
            # Get all user's papers
            user_papers = supabase.table("papers").select("id").eq("user_id", current_user.id).execute()
            paper_ids = [p["id"] for p in (user_papers.data or []) if isinstance(p, dict)]

            if paper_ids:
                # Count study plans for these papers
                study_plans = supabase.table("study_plans").select("id", count=cast(Any, "exact")).in_("paper_id", paper_ids).execute()
                study_plans_count = study_plans.count if hasattr(study_plans, 'count') and study_plans.count is not None else len(study_plans.data or [])
            else:
                study_plans_count = 0
        except Exception as e:
            print(f"Error counting study plans: {e}")
            study_plans_count = 0

        # Count quizzes using the same paper_ids approach
        try:
            if paper_ids:
                quizzes = supabase.table("quizzes").select("id", count=cast(Any, "exact")).in_("paper_id", paper_ids).execute()
                quizzes_count = quizzes.count if hasattr(quizzes, 'count') and quizzes.count is not None else len(quizzes.data or [])
            else:
                quizzes_count = 0
        except Exception as e:
            print(f"Error counting quizzes: {e}")
            quizzes_count = 0

        total = lit_reviews_count + study_plans_count + quizzes_count

        return {
            "literature_reviews": lit_reviews_count,
            "study_plans": study_plans_count,
            "quizzes": quizzes_count,
            "total": total
        }
    except Exception as e:
        print(f"Error fetching research materials stats: {e}")
        import traceback
        traceback.print_exc()
        # Return zeros if there's an error
        return {
            "literature_reviews": 0,
            "study_plans": 0,
            "quizzes": 0,
            "total": 0
        }

# Handle CORS preflight requests explicitly
@app.options("/{full_path:path}")
def options_handler():
    """Handle CORS preflight requests."""
    return {"message": "OK"}

@app.post("/upload", response_model=dict)
async def upload_paper(
    file: UploadFile = File(...), 
    title: Optional[str] = None,
    current_user: AuthUser = Depends(get_current_user)
):
    """Upload and extract text/metadata from various document formats. Requires authentication."""
    from workflow.document_processors.factory import process_document, ProcessorRegistry

    try:
        # Generate unique ID for paper
        paper_id = str(uuid.uuid4())

        # Extract file extension and MIME type
        file_extension = os.path.splitext(file.filename)[1] if file.filename else ""
        mime_type = file.content_type or ""

        # Validate file type using registry
        if not ProcessorRegistry.get_processor(file_extension, mime_type):
            supported = ProcessorRegistry.get_supported_extensions()
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type '{file_extension}'. Supported: {', '.join(supported)}"
            )

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Process document using appropriate processor
            print(f"[START] Processing {file_extension} file: {file.filename}")
            # ✅ Run CPU-heavy processing in thread pool to avoid blocking the event loop
            import asyncio
            loop = asyncio.get_event_loop()
            processed_doc = await loop.run_in_executor(
                None,  # Use default ThreadPoolExecutor
                process_document, tmp_path, file_extension, mime_type
            )


            # Validate extraction
            if not processed_doc.full_text or len(processed_doc.full_text.strip()) < 10:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Could not extract meaningful text from {file_extension} file"
                )

            print(f"✅  Extraction complete: {len(processed_doc.full_text)} chars")
            print(f"   File type: {processed_doc.file_type}")
            print(f"   Sections/Pages: {len(processed_doc.page_info)}")
            if processed_doc.processing_notes:
                for note in processed_doc.processing_notes:
                    print(f"   [WARNING]   {note}")

            # Extract variables from processed document
            text = processed_doc.full_text
            page_info = processed_doc.page_info
            multimodal_content = processed_doc.multimodal_content
            paper_metadata = processed_doc.metadata or {}

        finally:
            os.unlink(tmp_path)  # Cleanup

        # Extract clean filename without extension
        clean_filename = None
        if file.filename:
            clean_filename = os.path.splitext(file.filename)[0]

        # Determine final title
        final_title = (
            title
            or clean_filename
            or paper_metadata.get("title")
            or paper_metadata.get("extracted_title")
            or "Untitled Document"
        )

        # Store PDF file in Supabase Storage (PRIVATE with Signed URL)
        pdf_url = None
        try:
            storage_path = f"users/{current_user.id}/pdfs/{paper_id}.pdf"
            supabase.storage.from_("papers").upload(storage_path, content)
            # Generate signed URL valid for 7 days (604800 seconds)
            signed_url_response = supabase.storage.from_("papers").create_signed_url(
                storage_path,
                expires_in=604800
            )
            print(f"DEBUG: signed_url_response type: {type(signed_url_response)}, value: {signed_url_response}")

            # Extract the signedURL from the response
            if isinstance(signed_url_response, dict) and 'signedURL' in signed_url_response:
                pdf_url = signed_url_response['signedURL']
                print(f"DEBUG: Extracted signedURL from dict: {pdf_url}")
            else:
                pdf_url = signed_url_response  # Fallback if response structure is different
                print(f"DEBUG: Using signed_url_response directly: {pdf_url}")
            print(f"PDF stored securely (signed URL): {storage_path}")
        except Exception as e:
            print(f"Could not store PDF: {e}")
            print(f"Continuing without PDF URL - markdown content will be used as fallback")

        # Store in Supabase papers table
        paper_data = {
            "id": paper_id,
            "title": final_title,
            "content_text": text,
            "markdown_content": multimodal_content.get('markdown_full', ''),  # Store markdown with tables/images
            "page_info": json.dumps(page_info),
            "embedding_id": paper_id,
            "user_id": current_user.id,  # Set authenticated user ID
            "file_size": file_size,
            "filename": file.filename,
            "file_type": file_extension.lstrip('.') if file_extension else 'unknown',  # NEW: Store file type
            "pdf_url": pdf_url,
            "processing_status": "uploaded",
            "created_at": datetime.now(timezone.utc).isoformat(),
            # Add extracted metadata (authors as JSONB, not string!)
            "authors": paper_metadata.get("authors", []),  # Store as JSONB array
            "publication_year": paper_metadata.get("publication_year"),
            "doi": paper_metadata.get("doi"),
            "keywords": paper_metadata.get("keywords", []),
            "journal_or_conference": paper_metadata.get("journal") or paper_metadata.get("journal_or_conference"),
            "abstract": paper_metadata.get("abstract"),
            # Content type flags for filtering
            "has_images": len(multimodal_content.get("images", [])) > 0,
            "has_tables": len(multimodal_content.get("tables", [])) > 0,
            "has_equations": multimodal_content.get("has_equations", False),
        }

        # Insert into Supabase
        try:
            supabase_result = supabase.table("papers").insert(paper_data).execute()
            print(f"✅  Successfully uploaded paper: {paper_id}")
            print(
                f"📊  Metadata: {len(paper_metadata.get('authors', []))} authors, year: {paper_metadata.get('publication_year')}"
            )
        except Exception as e:
            print(f" Database insertion error: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        # ✅ PRODUCTION-GRADE: Use HYBRID indexing strategy (Markdown + Multi-modal)
        paper_metadata_for_embedding: Dict[str, Any] = {
            "id": paper_id,
            "title": final_title,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "authors": paper_metadata.get("authors", []),
            "publication_year": paper_metadata.get("publication_year"),
        }
        try:
            print(f"🚀 Storing embeddings for paper: {paper_id}")

            # ✅ UNIFIED MULTI-MODAL INDEXING STRATEGY
            # ------------------------------------------------------------------------------
            # This approach creates embeddings ONCE for all content types:
            #   • Text chunks: Recursive chunking for semantic search
            #   • Images: Vision API captions embedded for visual content retrieval  
            #   • Tables: PyMuPDF + pymupdf4llm extraction (smart chunking for large tables)
            #
            # Previous HYBRID approach created DUPLICATE embeddings:
            #   - Markdown parser extracted tables → 18 embeddings
            #   - Multimodal also extracted tables → 54 embeddings  
            #   - Total waste: ~100 duplicate embeddings per document
            #
            # Current unified approach eliminates ALL duplication while preserving quality.
            # ------------------------------------------------------------------------------
            print(f"✅ Using UNIFIED multi-modal indexing (Text + Images + Tables)")
            from workflow.utils import store_multimodal_embeddings

            store_multimodal_embeddings_fn = store_multimodal_embeddings
            await loop.run_in_executor(
                None,
                lambda: store_multimodal_embeddings_fn(
                    text=text,
                    multimodal_content=multimodal_content,
                    metadata=paper_metadata_for_embedding,
                    paper_id=paper_id,
                    page_info=page_info
                )
            )

            print(f"✅ Multi-modal embeddings stored successfully")
            print(f"   📝 Text chunks: processed")
            print(f"   🖼️  Images: {len(multimodal_content.get('images', []))}")
            print(f"   📊 Tables: {len(multimodal_content.get('tables', []))}")

        except Exception as e:
            print(f"[WARNING] Primary embedding storage failed: {e}")
            print(f"   Falling back to text-only embeddings...")
            # Fallback to text-only if everything else fails
            try:
                store_embedding(text, paper_metadata_for_embedding, paper_id, "basic", page_info)
                print(f"✅ Fallback: Text-only embeddings stored")
            except Exception as fallback_e:
                print(f"❌ Even text-only embedding failed: {fallback_e}")
                # Don't fail the upload if embeddings fail - user can retry processing

        # AUTO-EXTRACT CITATIONS (Enhanced Citation Manager Feature)
        citations_extracted = 0
        try:
            from services.citation_extraction_service import citation_extraction_service

            print(f"📚  Auto-extracting citations from paper...")

            # Extract bibliography section
            bib_text = citation_extraction_service.extract_bibliography_section(text)
            if bib_text:
                raw_citations = citation_extraction_service.parse_bibliography_entries(bib_text)
                print(f"   Found {len(raw_citations)} citations in bibliography")

                # Store basic citations (no AI enrichment on upload for speed)
                for raw_cit in raw_citations[:50]:  # Limit to 50 citations to avoid timeout
                    metadata = citation_extraction_service.extract_metadata_from_citation(raw_cit['raw_text'])

                    try:
                        supabase.table("paper_citations").insert({
                            "paper_id": paper_id,
                            "citation_text": raw_cit['raw_text'][:2000],  # Truncate if too long
                            "in_text_refs": raw_cit.get('in_text_refs', []),
                            "title": metadata.get('title'),
                            "authors": metadata.get('authors', []),
                            "year": metadata.get('year'),
                            "doi": metadata.get('doi'),
                            "venue": metadata.get('venue'),
                            "extraction_method": "auto"
                        }).execute()
                        citations_extracted += 1
                    except Exception as insert_error:
                        # Skip duplicates or invalid citations
                        pass

                print(f"✅  Auto-extracted {citations_extracted} citations")
            else:
                print(f"   No bibliography section found")
        except Exception as e:
            print(f"[WARNING]   Citation auto-extraction failed: {e}")
            # Don't fail upload if citation extraction fails

        return {
            "id": paper_id,
            "title": paper_data["title"],
            "status": "uploaded",
            "file_type": file_extension.lstrip('.') if file_extension else 'unknown',
            "message": f"{(file_extension or '').upper()} file uploaded successfully! You can start chatting now.",
            "metadata": {
                "authors": paper_metadata.get("authors", []),
                "year": paper_metadata.get("publication_year"),
                "doi": paper_metadata.get("doi"),
                "keywords": paper_metadata.get("keywords", []),
            },
            "citations_extracted": citations_extracted,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f" Upload error: {e}")
        import traceback  # What is traceback used for? It provides detailed error stack traces for debugging.

        traceback.print_exc()  # Print the full traceback to the console for debugging.
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/papers/{paper_id}/process", response_model=ProcessingResponse)
async def process_paper_ai(paper_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Generate AI summary for an uploaded paper. User must own the paper."""
    try:
        # Get paper from database and verify ownership
        result = (
            supabase.table("papers")
            .select("id, title, content_text, page_info, processing_status")
            .eq("id", paper_id)
            .eq("user_id", current_user.id)
            .execute()
        )

        papers_data = cast(List[Dict[str, Any]], result.data or [])
        if not papers_data:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")

        paper = papers_data[0]

        # Check if paper is already processed
        if paper.get("processing_status") == "completed":
            return ProcessingResponse(
                id=paper_id, status="completed", message="Paper already processed"
            )

        if paper.get("processing_status") == "processing":
            raise HTTPException(
                status_code=409, detail="Paper is currently being processed"
            )

        # Update status to processing
        supabase.table("papers").update(
            {"processing_status": "processing", "processing_error": None}
        ).eq("id", paper_id).execute()

        try:
            # Start AI processing and embedding enhancement in parallel
            text = str(paper.get("content_text") or "")

            # Parse page_info from stored JSON
            stored_page_info = paper.get("page_info")
            page_info = None
            if isinstance(stored_page_info, str) and stored_page_info:
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
                    "ai_generated_at": datetime.now(timezone.utc).isoformat(),
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
                    "title": str(paper.get("title") or ""),
                    "summary": final_summary,
                    "status": "completed",
                    "has_ai_summary": True,
                    "processing_date": datetime.now(timezone.utc).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }

                # SKIP embedding re-storage - multimodal embeddings already stored during upload
                # Re-storing would DELETE multimodal content (images/tables)
                print(f"✅  Skipping embedding re-storage (multimodal content preserved)")
                print(f"Successfully enhanced paper metadata with AI insights for: {paper_id}")

            except Exception as e:
                print(f"AI insight metadata error: {e}")
                # Don't fail processing if metadata update fails
                print(
                    f"WARNING: AI processing completed but metadata update failed for {paper_id}"
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
        raise HTTPException(
            status_code=500, detail=f"Processing failed: {str(e)}"
        )


@app.get("/papers", response_model=list)
def get_papers(current_user: AuthUser = Depends(get_current_user)):
    """Get list of all uploaded papers with processing status for the authenticated user."""
    try:
        result = (
            supabase.table("papers")
            .select(
                "id, title, summary, processing_status, ai_generated_at, created_at, updated_at, embedding_id, file_size, filename"
            )
            .eq("user_id", current_user.id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch papers: {str(e)}")

@app.get("/papers/{paper_id}", response_model=dict)
def get_paper(paper_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Get specific paper by ID with processing status. User must own the paper."""
    try:
        result = (
            supabase.table("papers")
            .select(
                "id, title, summary, content_text, markdown_content, page_info, processing_status, ai_generated_at, processing_error, created_at, updated_at, embedding_id, file_size, filename, pdf_url"
            )
            .eq("id", paper_id)
            .eq("user_id", current_user.id)
            .execute()
        )

        papers_list = cast(List[Dict[str, Any]], result.data or [])
        if not papers_list:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")

        paper = papers_list[0]
        # Add content field for backward compatibility with frontend
        paper["content"] = paper.get("content_text")
        return paper
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch paper: {str(e)}")

@app.get("/papers/{paper_id}/multimodal")
async def get_paper_multimodal_content(paper_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Get multi-modal content (images, tables) for a paper. User must own the paper."""
    try:
        # Verify paper ownership
        paper_check = supabase.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
        if not paper_check.data:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")

        print(f"📊  Fetching multimodal content for paper: {paper_id}")

        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        from workflow.db import qdrant

        # Retrieve all chunks for this paper
        results = qdrant.scroll(
            collection_name="litwise_collection",
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="paper_id", match=MatchValue(value=paper_id))
                ]
            ),
            limit=1000,  # Adjust if needed
            with_payload=True
        )

        chunks = results[0]
        print(f"   Total chunks retrieved: {len(chunks)}")

        # Separate by type
        images = []
        tables = []

        for chunk in (chunks or []):
            payload = getattr(chunk, "payload", {}) or {}
            if not isinstance(payload, dict):
                continue
            chunk_type = payload.get('type', 'text')

            if chunk_type == 'image':
                images.append({
                    'page': payload.get('page'),
                    'caption': payload.get('content'),
                    'width': payload.get('image_width'),
                    'height': payload.get('image_height'),
                    'format': payload.get('image_format'),
                    'image_base64': payload.get('image_base64')  # Truncated
                })
            elif chunk_type == 'table':
                tables.append({
                    'page': payload.get('page'),
                    'headers': payload.get('table_headers', []),
                    'rows': payload.get('table_rows_data', []),
                    'row_count': payload.get('table_rows'),
                    'col_count': payload.get('table_cols')
                })

        print(f"   Images found: {len(images)}")
        print(f"   Tables found: {len(tables)}")

        response = {
            "paper_id": paper_id,
            "images": images,
            "tables": tables,
            "total_images": len(images),
            "total_tables": len(tables)
        }

        print(f"✅  Returning multimodal response: {response}")
        return response

    except Exception as e:
        print(f" Error fetching multimodal content: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve multi-modal content: {str(e)}")

@app.delete("/papers/{paper_id}", response_model=dict)
def delete_paper(paper_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Delete paper and its embeddings. User must own the paper."""
    try:
        # Check if paper exists and user owns it
        result = supabase.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")

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
                print(f"✅  Deleted embeddings for paper: {paper_id}")
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

@app.post("/papers/regenerate-pdf-urls")
async def regenerate_pdf_urls(current_user: AuthUser = Depends(get_current_user)):
    """
    Regenerate signed URLs for all existing papers.
    This is a utility endpoint to fix missing or expired PDF URLs.
    """
    try:
        # Get all papers for the user
        papers = supabase.table("papers").select("id, filename").eq("user_id", current_user.id).execute()

        updated_count = 0
        failed_count = 0
        not_found_count = 0

        papers_data = cast(List[Dict[str, Any]], papers.data or [])
        for paper in papers_data:
            paper_id = None
            try:
                paper_id = str(paper.get("id", ""))
                if not paper_id:
                    continue
                storage_path = f"users/{current_user.id}/pdfs/{paper_id}.pdf"

                # Check if PDF exists in storage first
                try:
                    supabase.storage.from_("papers").list(f"users/{current_user.id}/pdfs")
                except:
                    # Storage path doesn't exist, skip
                    not_found_count += 1
                    print(f"[WARNING] PDF file not found in storage for paper: {paper_id}")
                    continue

                # Try to generate signed URL
                try:
                    signed_url_response = supabase.storage.from_("papers").create_signed_url(
                        storage_path,
                        expires_in=604800  # 7 days
                    )

                    # Extract the signed URL from response
                    if isinstance(signed_url_response, dict) and 'signedURL' in signed_url_response:
                        pdf_url = signed_url_response['signedURL']
                    else:
                        pdf_url = signed_url_response

                    # Update the paper with the new signed URL
                    supabase.table("papers").update({"pdf_url": pdf_url}).eq("id", paper_id).execute()
                    updated_count += 1
                    print(f"✅ Regenerated PDF URL for paper: {paper_id}")
                except Exception as url_error:
                    failed_count += 1
                    print(f"❌ Failed to create signed URL for paper {paper_id}: {url_error}")

            except Exception as e:
                failed_count += 1
                print(f"❌ Error processing paper {paper_id}: {e}")

        return {
            "message": "PDF URL regeneration completed",
            "updated_count": updated_count,
            "failed_count": failed_count,
            "not_found_count": not_found_count,
            "total_count": len(papers_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate PDF URLs: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
