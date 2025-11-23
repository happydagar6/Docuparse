from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import PaperUpload, PaperSummary, SearchQuery
from pipeline import workflow as graph_app
from workflow.utils import extract_text_from_pdf, store_embedding
from workflow.db import supabase
import os
import tempfile
import uuid
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload", response_model=dict)
async def upload_paper(file: UploadFile = File(...), title: str = "Untitled"):
    """Upload and process a PDF research paper."""
    # Generate unique ID for paper
    paper_id = str(uuid.uuid4())
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        text = extract_text_from_pdf(tmp_path)
    finally:
        os.unlink(tmp_path)  # Cleanup

    # Run LangGraph pipeline
    result = graph_app.invoke({"text": text, "summary": {}})

    # Store in Supabase papers table
    paper_data = {
        "id": paper_id,
        "title": title or file.filename or "Untitled",
        "filename": file.filename,
        "extracted_text": text,
        "summary": result.get("summary", {}),
        "file_size": len(content),
        "created_at": datetime.utcnow().isoformat(),
        "metadata": {
            "original_filename": file.filename,
            "content_type": file.content_type
        }
    }
    
    # Insert into Supabase
    supabase_result = supabase.table("papers").insert(paper_data).execute()

    # Store embedding for semantic search
    store_embedding(text, {
        "id": paper_id,
        "title": title or file.filename,
        "summary": result.get("summary", {}),
        "created_at": paper_data["created_at"]
    })

    return {
        "id": paper_id,
        "title": paper_data["title"],
        "summary": result.get("summary", {}),
        "message": "Paper uploaded and processed successfully"
    }

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
    """Get list of all uploaded papers."""
    try:
        result = supabase.table("papers").select("*").order("created_at", desc=True).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch papers: {str(e)}")

@app.get("/papers/{paper_id}", response_model=dict)
def get_paper(paper_id: str):
    """Get specific paper by ID."""
    try:
        result = supabase.table("papers").select("*").eq("id", paper_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        return result.data[0]
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