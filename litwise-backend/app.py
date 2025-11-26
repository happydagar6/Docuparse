from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import PaperUpload, PaperSummary, SearchQuery, ProcessingRequest, ProcessingResponse
from pipeline import workflow as graph_app
from workflow.utils import extract_text_from_pdf, store_embedding
from workflow.db import supabase
from async_pipeline import get_async_pipeline
import os
import tempfile
import uuid
import asyncio
import json
from datetime import datetime

# Import chat routes
from routes.chat import router as chat_router


app = FastAPI(title="Litwise API", version="1.0.0")

@app.get("/health")
def health_check():
    """Health check endpoint to verify the server is running."""
    return {"status": "healthy", "message": "Litwise API is running"}

#Include chat router
app.include_router(chat_router)

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
        "https://localhost:3000", # HTTPS variant
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.post("/upload", response_model=dict)
async def upload_paper(file: UploadFile = File(...), title: str = None):
    """Upload and extract text from PDF (without AI processing)."""
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
            text, page_info = extract_text_from_pdf(tmp_path)
            if not text or len(text.strip()) < 10:
                raise HTTPException(status_code=400, detail="Could not extract meaningful text from PDF")
        finally:
            os.unlink(tmp_path)  # Cleanup

        # Extract clean filename without extension
        clean_filename = None
        if file.filename:
            clean_filename = os.path.splitext(file.filename)[0]
        
        # Store in Supabase papers table (without AI summary)
        paper_data = {
            "id": paper_id,
            "title": title or clean_filename or "Untitled Document",
            "content_text": text,
            "page_info": json.dumps(page_info),  # Store page info as JSON
            "embedding_id": paper_id,
            "user_id": None,
            "file_size": file_size,
            "filename": file.filename,
            "processing_status": "uploaded",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Insert into Supabase
        try:
            supabase_result = supabase.table("papers").insert(paper_data).execute()
            print(f"Successfully uploaded paper: {paper_id}")
        except Exception as e:
            print(f"Database insertion error: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        # Note: Embeddings will be generated during processing stage for efficiency
        
        return {
            "id": paper_id,
            "title": paper_data["title"],
            "status": "uploaded",
            "message": "Paper uploaded successfully! You can start chatting now. AI summary generation is optional for enhanced features."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/papers/{paper_id}/process", response_model=ProcessingResponse)
async def process_paper_ai(paper_id: str):
    """Generate AI summary for an uploaded paper."""
    try:
        # Get paper from database
        result = supabase.table("papers").select(
            "id, title, content_text, page_info, processing_status"
        ).eq("id", paper_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        paper = result.data[0]
        
        # Check if paper is already processed
        if paper["processing_status"] == "completed":
            return ProcessingResponse(
                id=paper_id,
                status="completed", 
                message="Paper already processed"
            )
        
        if paper["processing_status"] == "processing":
            raise HTTPException(status_code=409, detail="Paper is currently being processed")
        
        # Update status to processing
        supabase.table("papers").update({
            "processing_status": "processing",
            "processing_error": None
        }).eq("id", paper_id).execute()
        
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
            pipeline_result = await async_pipeline.process_with_timeout(text, timeout_seconds=300)
            
            if pipeline_result["status"] != "completed":
                # Handle timeout or error
                error_msg = pipeline_result.get("error", "Processing failed")
                raise HTTPException(status_code=500, detail=f"AI processing failed: {error_msg}")
            
            result = pipeline_result["result"]
            
            # Clean and structure the summary (reuse existing logic)
            summary_data = result.get("summary", {})
            
            if isinstance(summary_data, dict):
                if "summary" in summary_data and isinstance(summary_data["summary"], dict):
                    summary_data = summary_data["summary"]
                    
                if not any(key in summary_data for key in ["key_points", "citations", "related_works"]):
                    for value in summary_data.values():
                        if isinstance(value, dict) and any(key in value for key in ["key_points", "citations", "related_works"]):
                            summary_data = value
                            break
            
            clean_summary = {
                "key_points": [],
                "citations": [], 
                "related_works": []
            }
            
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
                        clean_summary["related_works"] = [str(item) for item in rw if item]
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
                    "error": "JSON serialization failed"
                }
            
            # Update paper with AI summary
            supabase.table("papers").update({
                "summary": final_summary,
                "processing_status": "completed",
                "ai_generated_at": datetime.utcnow().isoformat()
            }).eq("id", paper_id).execute()
            
            # Generate enhanced embeddings with AI insights
            try:
                print(f"Enhancing embeddings with AI insights for paper: {paper_id}")
                
                # Create AI-enhanced content for superior retrieval
                enhanced_text = f"{text}\n\n=== AI SUMMARY ===\n"
                enhanced_text += f"Key Points: {'. '.join(final_summary.get('key_points', []))}\n"
                enhanced_text += f"Citations: {'. '.join(final_summary.get('citations', []))}\n"
                enhanced_text += f"Related Works: {'. '.join(final_summary.get('related_works', []))}"
                
                # Enhanced metadata with AI insights
                enhanced_metadata = {
                    "id": paper_id,
                    "title": paper["title"],
                    "summary": final_summary,
                    "status": "completed",
                    "has_ai_summary": True,
                    "processing_date": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat()
                }
                
                # Store enhanced embeddings for optimal chat functionality
                store_embedding(enhanced_text, enhanced_metadata, paper_id=paper_id, embedding_type="enhanced", page_info=page_info)
                print(f"Successfully enhanced embeddings with AI insights for paper: {paper_id}")
                
            except Exception as e:
                print(f"Embedding enhancement error: {e}")
                # Don't fail processing if embedding generation fails
                print(f"WARNING: AI processing completed but embedding enhancement failed for {paper_id}")
            
            return ProcessingResponse(
                id=paper_id,
                status="completed",
                message="AI processing completed successfully",
                summary=final_summary
            )
            
        except Exception as e:
            # Update status to failed
            supabase.table("papers").update({
                "processing_status": "failed",
                "processing_error": str(e)
            }).eq("id", paper_id).execute()
            
            print(f"AI processing failed for {paper_id}: {e}")
            raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/search")
def search_papers(query: SearchQuery):
    from workflow.db import qdrant
    from workflow.utils import generate_embeddings
    from fastapi import HTTPException
    from qdrant_client.http import models as rest_models

    collection = "litwise_collection"
    vector = generate_embeddings(query.query)

    # Try several client methods for compatibility across qdrant-client versions.
    # For each call we try both possible argument names ('vector' and 'query_vector'),
    # and continue to the next option on any exception until one succeeds.
    raw_hits = None
    last_exc = None

    def try_call(func, /, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return e

    # 1) qdrant.search
    if hasattr(qdrant, "search"):
        for kw in ("vector", "query_vector"):
            res = try_call(getattr(qdrant, "search"), collection_name=collection, **{kw: vector}, limit=query.limit, with_payload=True)
            if not isinstance(res, Exception):
                raw_hits = res
                break
            last_exc = res

    # 2) qdrant.query_points
    if raw_hits is None and hasattr(qdrant, "query_points"):
        for kw in ("vector", "query_vector"):
            res = try_call(getattr(qdrant, "query_points"), collection_name=collection, **{kw: vector}, limit=query.limit)
            if not isinstance(res, Exception):
                raw_hits = res
                break
            last_exc = res

    # 3) qdrant.search_points
    if raw_hits is None and hasattr(qdrant, "search_points"):
        for kw in ("vector", "query_vector"):
            # some clients accept 'vector' positional arg
            try:
                if kw == "vector":
                    res = try_call(getattr(qdrant, "search_points"), collection_name=collection, vector=vector, limit=query.limit)
                else:
                    res = try_call(getattr(qdrant, "search_points"), collection_name=collection, query_vector=vector, limit=query.limit)
            except Exception as e:
                res = e
            if not isinstance(res, Exception):
                raw_hits = res
                break
            last_exc = res

    # 4) HTTP API fallback
    if raw_hits is None and hasattr(qdrant, "http") and hasattr(qdrant.http, "points_api"):
        api = qdrant.http.points_api
        # find any method name containing 'search' and try calling it
        search_methods = [name for name in dir(api) if "search" in name]
        if search_methods:
            for name in search_methods:
                func = getattr(api, name)
                try:
                    # Try calling with (collection_name=..., body=SearchPoints(...))
                    resp = func(collection_name=collection, body=rest_models.SearchPoints(vector=vector, limit=query.limit)).result
                    raw_hits = resp
                    break
                except TypeError:
                    # Try alternative positional call
                    try:
                        resp = func(collection, rest_models.SearchPoints(vector=vector, limit=query.limit)).result
                        raw_hits = resp
                        break
                    except Exception as e:
                        last_exc = e
                        continue
                except Exception as e:
                    last_exc = e
                    continue
        else:
            # As a last resort, call Qdrant HTTP REST API directly using requests.
            # This covers environments where the generated points_api client doesn't expose a search helper.
            try:
                import requests
                QDRANT_URL = os.getenv("QDRANT_URL")
                QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
                if not QDRANT_URL:
                    raise RuntimeError("QDRANT_URL not configured in environment")

                url = QDRANT_URL.rstrip("/") + f"/collections/{collection}/points/search"
                headers = {"Content-Type": "application/json"}
                # Qdrant cloud uses 'api-key' header; try both common headers
                if QDRANT_API_KEY:
                    headers.update({"api-key": QDRANT_API_KEY, "x-api-key": QDRANT_API_KEY})

                body = {"vector": vector, "top": query.limit, "with_payload": True}
                resp = requests.post(url, json=body, headers=headers, timeout=15)
                if resp.status_code >= 400:
                    last_exc = RuntimeError(f"Qdrant REST search failed: {resp.status_code} {resp.text}")
                else:
                    parsed = resp.json()
                    # The REST response typically contains 'result' or 'points'
                    candidates = parsed.get("result") or parsed.get("points") or parsed.get("hits") or []
                    raw_hits = candidates
            except Exception as e:
                last_exc = e

    if raw_hits is None:
        # If debug requested, return diagnostics instead of raising immediately
        if getattr(query, "debug", False):
            diag = {}
            try:
                diag = qdrant_diagnostics()
            except Exception as e:
                diag = {"diagnostics_error": str(e)}
            return {"results": [], "error": str(last_exc), "diagnostics": diag}
        raise HTTPException(status_code=500, detail=f"Qdrant search failed: {last_exc}")

    results = []
    # Normalize different hit formats
    try:
        for hit in raw_hits:
            title = None
            score = None
            # object with payload and score attributes
            if hasattr(hit, "payload"):
                payload = hit.payload
                if isinstance(payload, dict):
                    title = payload.get("title")
                score = getattr(hit, "score", None)
            # dict-like response
            elif isinstance(hit, dict):
                payload = hit.get("payload") or hit.get("result") or hit
                if isinstance(payload, dict):
                    title = payload.get("title")
                score = hit.get("score") or (hit.get("result") and hit.get("result").get("score"))
            # fallback: try nested structures (e.g., http response object)
            else:
                try:
                    # Example: resp.points -> list of point objects
                    pts = getattr(raw_hits, "points", None) or getattr(raw_hits, "result", None)
                    if pts:
                        for ph in pts:
                            pld = getattr(ph, "payload", None) or (isinstance(ph, dict) and ph.get("payload"))
                            t = None
                            if isinstance(pld, dict):
                                t = pld.get("title")
                            s = getattr(ph, "score", None) or (isinstance(ph, dict) and ph.get("score"))
                            results.append({"title": t, "score": s})
                        continue
                except Exception:
                    pass
            results.append({"title": title, "score": score})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse qdrant hits: {e}")

    # If no results and debug requested, include diagnostics
    if not results and getattr(query, "debug", False):
        try:
            diag = qdrant_diagnostics()
        except Exception as e:
            diag = {"diagnostics_error": str(e)}
        return {"results": results, "diagnostics": diag}

    return results


@app.get("/qdrant/diagnostics", response_model=dict)
def qdrant_diagnostics():
    """Return basic Qdrant collection diagnostics to help debug empty search results."""
    from workflow.db import qdrant

    collection = "litwise_collection"
    info = {"collection": collection, "exists": None, "count": None, "sample_points": [], "errors": []}

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
        result = supabase.table("papers").select(
            "id, title, summary, processing_status, ai_generated_at, created_at, updated_at, embedding_id, file_size, filename"
        ).order("created_at", desc=True).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch papers: {str(e)}")

@app.get("/papers/{paper_id}", response_model=dict)
def get_paper(paper_id: str):
    """Get specific paper by ID with processing status."""
    try:
        result = supabase.table("papers").select(
            "id, title, summary, content_text, processing_status, ai_generated_at, processing_error, created_at, updated_at, embedding_id, file_size, filename"
        ).eq("id", paper_id).execute()
        
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
            # Try to delete by point ID (if using paper_id as point ID)
            try:
                qdrant.delete(
                    collection_name="litwise_collection",
                    points_selector={"ids": [paper_id]}
                )
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