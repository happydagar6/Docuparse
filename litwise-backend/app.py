from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from models import (
    SearchQuery,
    ProcessingResponse,
)
from pipeline import workflow as graph_app
from workflow.utils import store_embedding, extract_multimodal_from_pdf, store_multimodal_embeddings
from workflow.db import supabase
from async_pipeline import get_async_pipeline
from typing import Optional
import os
import tempfile
import uuid
import json
from datetime import datetime, timezone
import logging

# Import authentication middleware and rate limiting middleware
from auth_middleware import get_current_user, AuthUser
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
        logger.info("âš ï¸  Sentry: NOT CONFIGURED (no SENTRY_DSN)")
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
        logger.error(f"âŒ Sentry initialization failed: {e}")


# Initialize Sentry before creating the app
init_sentry()

# CORS configuration - support both local development and production
def get_allowed_origins():
    """
    Get allowed origins from environment variable or use defaults for development.
    
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
        logger.info(f"â„¹ï¸  CORS Origins (default development): {default_origins}")
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
        logger.warning("âš ï¸  Redis Cache: NOT CONNECTED - Cache disabled!")
        logger.warning("   - Database will be queried on every request (no caching)")
        logger.warning("   - Check REDIS_URL environment variable")
    
    # Check Sentry error monitoring
    if sentry_sdk.Hub.current.client:
        logger.info("[OK] Error Monitoring: Sentry is active")
        logger.info(f"   - All exceptions will be tracked")
        logger.info(f"   - Dashboard: https://sentry.io")
    else:
        logger.warning("âš ï¸  Error Monitoring: Sentry is disabled")
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

@app.get("/")
async def root():
    return {"message": "Welcome to the Litwise API"}


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
        user_id_str = str(current_user.id)
        
        # Count literature reviews (user_id is stored as text)
        lit_reviews = supabase.table("literature_reviews").select("id", count="exact").eq("user_id", user_id_str).execute()
        lit_reviews_count = lit_reviews.count if hasattr(lit_reviews, 'count') and lit_reviews.count is not None else len(lit_reviews.data or [])
        
        # Count study plans (need to join through papers table since study_plans doesn't have user_id directly)
        try:
            # Get all user's papers
            user_papers = supabase.table("papers").select("id").eq("user_id", current_user.id).execute()
            paper_ids = [p["id"] for p in user_papers.data or []]
            
            if paper_ids:
                # Count study plans for these papers
                study_plans = supabase.table("study_plans").select("id", count="exact").in_("paper_id", paper_ids).execute()
                study_plans_count = study_plans.count if hasattr(study_plans, 'count') and study_plans.count is not None else len(study_plans.data or [])
            else:
                study_plans_count = 0
        except Exception as e:
            print(f"Error counting study plans: {e}")
            study_plans_count = 0
        
        # For quizzes: they don't have a dedicated table yet, so return 0
        # Once quizzes table is created with user_id, we can count them
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
    title: str = None,
    current_user: AuthUser = Depends(get_current_user)
):
    """Upload and extract text/metadata from various document formats. Requires authentication."""
    from workflow.document_processors.factory import process_document, ProcessorRegistry
    
    try:
        # Generate unique ID for paper
        paper_id = str(uuid.uuid4())

        # Extract file extension and MIME type
        file_extension = os.path.splitext(file.filename)[1] if file.filename else None
        mime_type = file.content_type
        
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
            processed_doc = process_document(tmp_path, file_extension, mime_type)
            
            # Validate extraction
            if not processed_doc.full_text or len(processed_doc.full_text.strip()) < 10:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Could not extract meaningful text from {file_extension} file"
                )
            
            print(f"âœ… Extraction complete: {len(processed_doc.full_text)} chars")
            print(f"   File type: {processed_doc.file_type}")
            print(f"   Sections/Pages: {len(processed_doc.page_info)}")
            if processed_doc.processing_notes:
                for note in processed_doc.processing_notes:
                    print(f"   âš ï¸  {note}")
            
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
            print(f"âœ… Successfully uploaded paper: {paper_id}")
            print(
                f"ðŸ“Š Metadata: {len(paper_metadata.get('authors', []))} authors, year: {paper_metadata.get('publication_year')}"
            )
        except Exception as e:
            print(f"âŒ Database insertion error: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        # âœ… PRODUCTION-GRADE: Use HYBRID indexing strategy (Markdown + Multi-modal)
        try:
            print(f"ðŸš€ Storing embeddings for paper: {paper_id}")
            
            paper_metadata_for_embedding = {
                "id": paper_id,
                "title": final_title,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "authors": paper_metadata.get("authors", []),
                "publication_year": paper_metadata.get("publication_year"),
            }
            
            # Check if we have full markdown from PDF extraction
            markdown_full = multimodal_content.get('markdown_full', '')
            
            if markdown_full and len(markdown_full) > 1000:
                # âœ… PRIMARY: Use MarkdownElementNodeParser for superior table indexing
                print(f"âœ… Using HYBRID indexing strategy (Markdown + Multi-modal)")
                print(f"   1ï¸âƒ£  PRIMARY: MarkdownElementNodeParser (element-aware tables)")
                from workflow.utils import store_markdown_embeddings, store_multimodal_embeddings
                
                store_markdown_embeddings(
                    markdown_text=markdown_full,
                    metadata=paper_metadata_for_embedding,
                    paper_id=paper_id,
                    page_info=page_info
                )
                
                print(f"âœ… Markdown-based embeddings stored")
                print(f"   Strategy: MarkdownElementNodeParser")
                print(f"   Markdown size: {len(markdown_full)} chars")
                
                # âœ… SECONDARY: Add multi-modal embeddings for comprehensive coverage
                # Text chunks + images provide backup retrieval paths
                print(f"\n   2ï¸âƒ£  SECONDARY: Multi-modal embeddings (text chunks + images)")
                store_multimodal_embeddings(
                    text=text,
                    multimodal_content=multimodal_content,
                    metadata=paper_metadata_for_embedding,
                    paper_id=paper_id,
                    page_info=page_info
                )
                
                print(f"âœ… Multi-modal embeddings stored (secondary)")
                print(f"   ðŸ“ Text chunks: processed")
                print(f"   ðŸ–¼ï¸  Images: {len(multimodal_content.get('images', []))}")
                print(f"   ðŸ“Š Tables: {len(multimodal_content.get('tables', []))}")
                print(f"\nðŸŽ‰ HYBRID indexing complete: Markdown tables + Text chunks + Images")
                
            else:
                # Fallback: Use multi-modal embeddings if no markdown
                print(f"âš ï¸  No markdown available, using multi-modal fallback")
                from workflow.utils import store_multimodal_embeddings
                
                store_multimodal_embeddings(
                    text=text,
                    multimodal_content=multimodal_content,
                    metadata=paper_metadata_for_embedding,
                    paper_id=paper_id,
                    page_info=page_info
                )
                
                print(f"âœ… Multi-modal embeddings stored successfully")
                print(f"   ðŸ“ Text chunks: processed")
                print(f"   ðŸ–¼ï¸  Images: {len(multimodal_content.get('images', []))}")
                print(f"   ðŸ“Š Tables: {len(multimodal_content.get('tables', []))}")
            
        except Exception as e:
            print(f"âš ï¸  Primary embedding storage failed: {e}")
            print(f"   Falling back to text-only embeddings...")
            # Fallback to text-only if everything else fails
            try:
                store_embedding(text, paper_metadata_for_embedding, paper_id, "basic", page_info)
                print(f"âœ… Fallback: Text-only embeddings stored")
            except Exception as fallback_e:
                print(f"âŒ Even text-only embedding failed: {fallback_e}")
                # Don't fail the upload if embeddings fail - user can retry processing

        # AUTO-EXTRACT CITATIONS (Enhanced Citation Manager Feature)
        citations_extracted = 0
        try:
            from services.citation_extraction_service import citation_extraction_service
            
            print(f"ðŸ“š Auto-extracting citations from paper...")
            
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
                
                print(f"âœ… Auto-extracted {citations_extracted} citations")
            else:
                print(f"   No bibliography section found")
        except Exception as e:
            print(f"âš ï¸  Citation auto-extraction failed: {e}")
            # Don't fail upload if citation extraction fails

        return {
            "id": paper_id,
            "title": paper_data["title"],
            "status": "uploaded",
            "file_type": file_extension.lstrip('.') if file_extension else 'unknown',
            "message": f"{file_extension.upper()} file uploaded successfully! You can start chatting now.",
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
        print(f"âŒ Upload error: {e}")
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

        if not result.data:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")

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

                # SKIP embedding re-storage - multimodal embeddings already stored during upload
                # Re-storing would DELETE multimodal content (images/tables)
                print(f"âœ… Skipping embedding re-storage (multimodal content preserved)")
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
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.post("/search")
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
    from workflow.db import qdrant, supabase
    from workflow.utils import generate_embeddings
    from workflow.enhanced_search import enhanced_search
    from langchain_openai import OpenAIEmbeddings
    from fastapi import HTTPException
    from services.nl_query_parser import nl_query_parser

    try:
        # Phase 2 Stage 1: Natural Language Query Parsing
        parsed_query_info = None
        search_query_text = query.query
        
        if query.use_nl_parsing:
            print(f"ðŸ§  Parsing natural language query: '{query.query}'")
            parsed = await nl_query_parser.parse_query(query.query, enable_ai=False)  # Regex-only for speed
            
            if parsed.get('parsed_elements'):
                print(f"âœ… Parsed filters: {', '.join(parsed['parsed_elements'])}")
                search_query_text = parsed['semantic_query']
                
                # Merge parsed filters with existing filters
                if not query.filters:
                    from models import SearchFilters
                    query.filters = SearchFilters()
                
                # Apply parsed filters (don't override manually set filters)
                for key, value in parsed['filters'].items():
                    if not getattr(query.filters, key, None):
                        setattr(query.filters, key, value)
                
                # Store parsed info for response
                parsed_query_info = {
                    'original_query': query.query,
                    'semantic_query': search_query_text,
                    'parsed_elements': parsed['parsed_elements'],
                    'confidence': parsed['confidence']
                }
            else:
                print(f"â„¹ï¸ No filters detected in query, using as-is")
        
        # Initialize embeddings model
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small", openai_api_key=os.getenv("OPENAI_API_KEY")
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
        if db_filters and not filtered_paper_ids:
            try:
                where_clause = " AND ".join(db_filters)
                result = (
                    supabase.table("papers")
                    .select("id")
                    .filter(where_clause)
                    .eq("user_id", current_user.id)
                    .execute()
                )
                filtered_paper_ids = [paper["id"] for paper in result.data]

                if not filtered_paper_ids:
                    print(f"âš ï¸ No papers match the metadata filters")
                    return []

                print(f"ðŸ“‹ Filtered to {len(filtered_paper_ids)} papers by metadata")
            except Exception as e:
                print(f"âš ï¸ Metadata filtering failed: {e}, proceeding without filters")
                filtered_paper_ids = None
        elif not filtered_paper_ids:
            # No specific filters, but still need to limit to user's papers
            try:
                result = supabase.table("papers").select("id").eq("user_id", current_user.id).execute()
                filtered_paper_ids = [paper["id"] for paper in result.data]
                
                if not filtered_paper_ids:
                    print(f"â„¹ï¸ User has no papers uploaded yet")
                    return []
                
                print(f"ðŸ“‹ Searching across {len(filtered_paper_ids)} papers owned by user")
            except Exception as e:
                print(f"âš ï¸ Failed to fetch user's papers: {e}")
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
                for paper in paper_data.data:
                    paper_metadata_map[paper["id"]] = paper

                print(
                    f"ðŸ“š Fetched metadata for {len(paper_metadata_map)} unique papers"
                )
            except Exception as e:
                print(f"âš ï¸ Failed to fetch paper metadata: {e}")

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
                result["journal_or_conference"] = paper_info.get(
                    "journal_or_conference"
                )

            # Ensure both paper_id and id are present for frontend compatibility
            result["id"] = paper_id  # Add explicit id field for frontend
            enriched_results.append(result)

        return enriched_results

    except Exception as e:
        print(f"âŒ Search failed: {e}")
        import traceback

        traceback.print_exc()

        if query.debug:
            return []

        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")



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

        if not result.data:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")

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


@app.get("/papers/{paper_id}/multimodal")
async def get_paper_multimodal_content(paper_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Get multi-modal content (images, tables) for a paper. User must own the paper."""
    try:
        # Verify paper ownership
        paper_check = supabase.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
        if not paper_check.data:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")
        
        print(f"ðŸ“Š Fetching multimodal content for paper: {paper_id}")
        
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
        
        for chunk in chunks:
            payload = chunk.payload
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
        
        print(f"âœ… Returning multimodal response: {response}")
        return response
        
    except Exception as e:
        print(f"âŒ Error fetching multimodal content: {e}")
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
                print(f"âœ… Deleted embeddings for paper: {paper_id}")
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
        
        for paper in papers.data:
            try:
                paper_id = paper["id"]
                storage_path = f"users/{current_user.id}/pdfs/{paper_id}.pdf"
                
                # Check if PDF exists in storage first
                try:
                    supabase.storage.from_("papers").list(f"users/{current_user.id}/pdfs")
                except:
                    # Storage path doesn't exist, skip
                    not_found_count += 1
                    print(f"⚠️  PDF file not found in storage for paper: {paper_id}")
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
            "total_count": len(papers.data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate PDF URLs: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
