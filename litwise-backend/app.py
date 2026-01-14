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
    SynthesisRequest,
    SynthesisResponse,  # Phase 1: Synthesis models
    SaveSynthesisRequest,
    UpdateSynthesisTagsRequest,
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


# Import synthesis service (Phase 1)
from workflow.synthesis_service import synthesis_service

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
        logger.info("⚠️  Sentry: NOT CONFIGURED (no SENTRY_DSN)")
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
        logger.info("✅ Sentry: Connected and monitoring errors")
        logger.info(f"   - Environment: {environment}")
        logger.info(f"   - Capturing 100% of errors")
        logger.info(f"   - Performance sampling: 10%")
    except Exception as e:
        logger.error(f"❌ Sentry initialization failed: {e}")


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
        logger.info(f"✅ CORS Origins (from environment): {origins}")
        return origins
    else:
        # Development: default localhost origins
        default_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://localhost:3000",
        ]
        logger.info(f"ℹ️  CORS Origins (default development): {default_origins}")
        return default_origins


async def startup_event():
    """Initialize and verify Redis cache on startup."""
    logger.info("=" * 60)
    logger.info("🚀 Litwise API Starting Up")
    logger.info("=" * 60)
    
    # Check Redis cache status
    if message_cache_service.redis_client:
        logger.info("✅ Redis Cache: Connected and ready")
        logger.info(f"   - Cache TTL: 24 hours")
        logger.info(f"   - Max messages per session: 5000")
    else:
        logger.warning("⚠️  Redis Cache: NOT CONNECTED - Cache disabled!")
        logger.warning("   - Database will be queried on every request (no caching)")
        logger.warning("   - Check REDIS_URL environment variable")
    
    # Check Sentry error monitoring
    if sentry_sdk.Hub.current.client:
        logger.info("✅ Error Monitoring: Sentry is active")
        logger.info(f"   - All exceptions will be tracked")
        logger.info(f"   - Dashboard: https://sentry.io")
    else:
        logger.warning("⚠️  Error Monitoring: Sentry is disabled")
        logger.warning("   - Production errors will NOT be captured")
        logger.warning("   - Set SENTRY_DSN environment variable")
    
    logger.info("✅ Response Compression: Enabled (GZIP)")
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
            print(f"🚀 Processing {file_extension} file: {file.filename}")
            processed_doc = process_document(tmp_path, file_extension, mime_type)
            
            # Validate extraction
            if not processed_doc.full_text or len(processed_doc.full_text.strip()) < 10:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Could not extract meaningful text from {file_extension} file"
                )
            
            print(f"✅ Extraction complete: {len(processed_doc.full_text)} chars")
            print(f"   File type: {processed_doc.file_type}")
            print(f"   Sections/Pages: {len(processed_doc.page_info)}")
            if processed_doc.processing_notes:
                for note in processed_doc.processing_notes:
                    print(f"   ⚠️  {note}")
            
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

        # Store in Supabase papers table
        paper_data = {
            "id": paper_id,
            "title": final_title,
            "content_text": text,
            "page_info": json.dumps(page_info),
            "embedding_id": paper_id,
            "user_id": current_user.id,  # Set authenticated user ID
            "file_size": file_size,
            "filename": file.filename,
            "file_type": file_extension.lstrip('.') if file_extension else 'unknown',  # NEW: Store file type
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
            print(f"✅ Successfully uploaded paper: {paper_id}")
            print(
                f"📊 Metadata: {len(paper_metadata.get('authors', []))} authors, year: {paper_metadata.get('publication_year')}"
            )
        except Exception as e:
            print(f"❌ Database insertion error: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        # ✅ PRODUCTION-GRADE: Use HYBRID indexing strategy (Markdown + Multi-modal)
        try:
            print(f"🚀 Storing embeddings for paper: {paper_id}")
            
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
                # ✅ PRIMARY: Use MarkdownElementNodeParser for superior table indexing
                print(f"✅ Using HYBRID indexing strategy (Markdown + Multi-modal)")
                print(f"   1️⃣  PRIMARY: MarkdownElementNodeParser (element-aware tables)")
                from workflow.utils import store_markdown_embeddings, store_multimodal_embeddings
                
                store_markdown_embeddings(
                    markdown_text=markdown_full,
                    metadata=paper_metadata_for_embedding,
                    paper_id=paper_id,
                    page_info=page_info
                )
                
                print(f"✅ Markdown-based embeddings stored")
                print(f"   Strategy: MarkdownElementNodeParser")
                print(f"   Markdown size: {len(markdown_full)} chars")
                
                # ✅ SECONDARY: Add multi-modal embeddings for comprehensive coverage
                # Text chunks + images provide backup retrieval paths
                print(f"\n   2️⃣  SECONDARY: Multi-modal embeddings (text chunks + images)")
                store_multimodal_embeddings(
                    text=text,
                    multimodal_content=multimodal_content,
                    metadata=paper_metadata_for_embedding,
                    paper_id=paper_id,
                    page_info=page_info
                )
                
                print(f"✅ Multi-modal embeddings stored (secondary)")
                print(f"   📝 Text chunks: processed")
                print(f"   🖼️  Images: {len(multimodal_content.get('images', []))}")
                print(f"   📊 Tables: {len(multimodal_content.get('tables', []))}")
                print(f"\n🎉 HYBRID indexing complete: Markdown tables + Text chunks + Images")
                
            else:
                # Fallback: Use multi-modal embeddings if no markdown
                print(f"⚠️  No markdown available, using multi-modal fallback")
                from workflow.utils import store_multimodal_embeddings
                
                store_multimodal_embeddings(
                    text=text,
                    multimodal_content=multimodal_content,
                    metadata=paper_metadata_for_embedding,
                    paper_id=paper_id,
                    page_info=page_info
                )
                
                print(f"✅ Multi-modal embeddings stored successfully")
                print(f"   📝 Text chunks: processed")
                print(f"   🖼️  Images: {len(multimodal_content.get('images', []))}")
                print(f"   📊 Tables: {len(multimodal_content.get('tables', []))}")
            
        except Exception as e:
            print(f"⚠️  Primary embedding storage failed: {e}")
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
            
            print(f"📚 Auto-extracting citations from paper...")
            
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
                
                print(f"✅ Auto-extracted {citations_extracted} citations")
            else:
                print(f"   No bibliography section found")
        except Exception as e:
            print(f"⚠️  Citation auto-extraction failed: {e}")
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
        print(f"❌ Upload error: {e}")
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
                print(f"✅ Skipping embedding re-storage (multimodal content preserved)")
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
            print(f"🧠 Parsing natural language query: '{query.query}'")
            parsed = await nl_query_parser.parse_query(query.query, enable_ai=False)  # Regex-only for speed
            
            if parsed.get('parsed_elements'):
                print(f"✅ Parsed filters: {', '.join(parsed['parsed_elements'])}")
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
                print(f"ℹ️ No filters detected in query, using as-is")
        
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
                    print(f"⚠️ No papers match the metadata filters")
                    return []

                print(f"📋 Filtered to {len(filtered_paper_ids)} papers by metadata")
            except Exception as e:
                print(f"⚠️ Metadata filtering failed: {e}, proceeding without filters")
                filtered_paper_ids = None
        elif not filtered_paper_ids:
            # No specific filters, but still need to limit to user's papers
            try:
                result = supabase.table("papers").select("id").eq("user_id", current_user.id).execute()
                filtered_paper_ids = [paper["id"] for paper in result.data]
                
                if not filtered_paper_ids:
                    print(f"ℹ️ User has no papers uploaded yet")
                    return []
                
                print(f"📋 Searching across {len(filtered_paper_ids)} papers owned by user")
            except Exception as e:
                print(f"⚠️ Failed to fetch user's papers: {e}")
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
        
        # Return results with optional parsed query info
        if parsed_query_info:
            return {
                "results": enriched_results,
                "parsed_query": parsed_query_info
            }
        return enriched_results

    except Exception as e:
        print(f"❌ Search failed: {e}")
        import traceback

        traceback.print_exc()

        if query.debug:
            return {"results": [], "error": str(e), "traceback": traceback.format_exc()}

        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/search/synthesize", response_model=SynthesisResponse)
async def synthesize_search_results(request: SynthesisRequest, current_user: AuthUser = Depends(get_current_user)):
    """
    Generate AI-powered research synthesis from search results. Requires authentication.

    This endpoint:
    1. Takes search results from the /search endpoint
    2. Analyzes papers using LLM (GPT-4)
    3. Identifies themes, key findings, research gaps
    4. Analyzes publication trends over time
    5. Returns structured synthesis data

    Args:
        request: SynthesisRequest with query and search_results
        current_user: Authenticated user (automatically injected)

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
        
        # DEBUG: Check what types we actually have
        print(f"🔍 DEBUG - Type validation:")
        print(f"   - key_findings type: {type(synthesis.get('key_findings', []))}")
        if synthesis.get('key_findings'):
            print(f"   - First finding type: {type(synthesis['key_findings'][0])}")
            print(f"   - First finding: {synthesis['key_findings'][0][:100] if isinstance(synthesis['key_findings'][0], str) else synthesis['key_findings'][0]}")
        
        print(f"   - research_gaps type: {type(synthesis.get('research_gaps', []))}")
        if synthesis.get('research_gaps'):
            print(f"   - First gap type: {type(synthesis['research_gaps'][0])}")
        
        print(f"   - themes type: {type(synthesis.get('themes', []))}")
        if synthesis.get('themes'):
            print(f"   - First theme type: {type(synthesis['themes'][0])}")
            print(f"   - First theme: {synthesis['themes'][0]}")

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
async def save_synthesis(request: SaveSynthesisRequest, current_user: AuthUser = Depends(get_current_user)):
    """
    Save a synthesis to history for future reference. Requires authentication.
    
    This endpoint stores the complete synthesis result including:
    - Query and settings used
    - All synthesis data (themes, findings, gaps, trends)
    - Original search results for reproducibility
    - Optional tags for organization
    
    Args:
        request: SaveSynthesisRequest with synthesis data
        current_user: Authenticated user (automatically injected)
        
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
            "tags": request.tags,
            "user_id": current_user.id  # Set authenticated user ID
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
    current_user: AuthUser = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
    tag: Optional[str] = None
):
    """
    Get list of saved syntheses from history for the authenticated user.
    
    Returns lightweight list items with essential information.
    Use GET /synthesis/history/{id} to get full synthesis details.
    
    Args:
        current_user: Authenticated user (automatically injected)
        limit: Maximum number of items to return (default: 20)
        offset: Number of items to skip (for pagination, default: 0)
        tag: Optional tag filter (returns only syntheses with this tag)
        
    Returns:
        List of synthesis history items with counts
        
    Example:
        GET /synthesis/history?limit=10&tag=literature-review
    """
    try:
        # Build query for user's synthesis history
        query = supabase.table("synthesis_history").select(
            "id, query, paper_count, themes, tags, created_at"
        ).eq("user_id", current_user.id)
        
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
async def get_synthesis_by_id(synthesis_id: str, current_user: AuthUser = Depends(get_current_user)):
    """
    Get full details of a specific saved synthesis. User must own the synthesis.
    
    Returns complete synthesis data including all themes, findings, gaps, and trends.
    
    Args:
        synthesis_id: UUID of the saved synthesis
        current_user: Authenticated user (automatically injected)
        
    Returns:
        Complete synthesis object
        
    Example:
        GET /synthesis/history/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        result = supabase.table("synthesis_history").select("*").eq("id", synthesis_id).eq("user_id", current_user.id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail=f"Synthesis not found or access denied")
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Get synthesis by ID failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to retrieve synthesis: {str(e)}")


@app.patch("/synthesis/history/{synthesis_id}/tags")
async def update_synthesis_tags(synthesis_id: str, request: UpdateSynthesisTagsRequest, current_user: AuthUser = Depends(get_current_user)):
    """
    Update tags on a saved synthesis.
    
    Allows users to organize their saved syntheses with custom tags.
    Only the owner can update tags.
    
    Args:
        synthesis_id: UUID of the saved synthesis
        request: UpdateSynthesisTagsRequest with new tags
        current_user: Authenticated user (from JWT)
        
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
        
        # Check if synthesis exists and user owns it
        check_result = supabase.table("synthesis_history").select("id").eq("id", synthesis_id).eq("user_id", current_user.id).execute()
        if not check_result.data:
            raise HTTPException(status_code=404, detail="Synthesis not found or access denied")
        
        # Update tags
        result = supabase.table("synthesis_history").update(
            {"tags": request.tags}
        ).eq("id", synthesis_id).eq("user_id", current_user.id).execute()
        
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
async def delete_synthesis(synthesis_id: str, current_user: AuthUser = Depends(get_current_user)):
    """
    Delete a saved synthesis from history.
    
    Only the owner of the synthesis can delete it.
    
    Args:
        synthesis_id: UUID of the synthesis to delete
        current_user: Authenticated user (from JWT)
        
    Returns:
        Success message
        
    Example:
        DELETE /synthesis/history/123e4567-e89b-12d3-a456-426614174000
    """
    try:
        # Check if synthesis exists and user owns it
        check_result = supabase.table("synthesis_history").select("id").eq("id", synthesis_id).eq("user_id", current_user.id).execute()
        if not check_result.data:
            raise HTTPException(status_code=404, detail="Synthesis not found or access denied")
        
        # Delete from database
        supabase.table("synthesis_history").delete().eq("id", synthesis_id).eq("user_id", current_user.id).execute()
        
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
                "id, title, summary, content_text, processing_status, ai_generated_at, processing_error, created_at, updated_at, embedding_id, file_size, filename"
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
        
        return {
            "paper_id": paper_id,
            "images": images,
            "tables": tables,
            "total_images": len(images),
            "total_tables": len(tables)
        }
        
    except Exception as e:
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
