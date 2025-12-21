from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from typing import List
from models.citation import (
    CitationRequest, BatchCitationRequest, CitationResponse,
    CitationFormat, PaperMetadata
)
from services.citation_services import citation_service
from workflow.db import supabase
from auth_middleware import get_current_user, AuthUser

router = APIRouter(prefix="/api/citations", tags=["Citations"])

def extract_metadata(paper: dict) -> PaperMetadata:
    """Extract complete metadata from paper record for citations"""
    # Extract authors from JSONB field
    authors = None
    authors_data = paper.get("authors", [])
    if authors_data and isinstance(authors_data, list):
        # authors is stored as [{"name": "LastName, I.", "affiliation": "..."}, ...]
        authors = []
        for author in authors_data:
            if isinstance(author, dict) and author.get("name"):
                authors.append(author["name"])
            elif isinstance(author, str):
                authors.append(author)
        if not authors:
            authors = None
    
    # Get publication year from dedicated field, fallback to created_at
    year = paper.get("publication_year")
    if not year:
        created_at = paper.get("created_at", "")
        if created_at:
            try:
                year = int(created_at[:4])
            except:
                pass
    
    # Extract additional metadata from summary JSONB if available
    summary_data = paper.get("summary", {})
    volume = None
    issue = None
    pages = None
    publisher = None
    
    if isinstance(summary_data, dict):
        volume = summary_data.get("volume")
        issue = summary_data.get("issue")
        pages = summary_data.get("pages")
        publisher = summary_data.get("publisher")
    
    # Get URL - use DOI link if DOI exists, otherwise use stored URL
    url = paper.get("url")
    doi = paper.get("doi")
    if doi and not url:
        url = f"https://doi.org/{doi}"
    
    return PaperMetadata(
        id=paper.get("id", ""),
        title=paper.get("title", "Untitled"),
        authors=authors,
        year=year,
        doi=doi,
        url=url,
        journal=paper.get("journal_or_conference"),
        volume=volume,
        issue=issue,
        pages=pages,
        publisher=publisher,
    )

@router.post("/generate", response_model=CitationResponse)
async def generate_citation(request: CitationRequest, current_user: AuthUser = Depends(get_current_user)):
    """Generate citation for a single paper. User must own the paper."""
    result = supabase.table("papers").select("*").eq("id", request.paper_id).eq("user_id", current_user.id).single().execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Paper not found or access denied")
    
    # Debug: Print paper data
    print(f"\n🔍 [CITATION DEBUG] Paper ID: {request.paper_id}")
    print(f"   Title: {result.data.get('title', 'N/A')}")
    print(f"   Authors (raw from DB): {result.data.get('authors', 'N/A')}")
    print(f"   Year: {result.data.get('publication_year', 'N/A')}")
    print(f"   DOI: {result.data.get('doi', 'N/A')}")
    
    metadata = extract_metadata(result.data)
    
    print(f"   Extracted metadata authors: {metadata.authors}")
    print(f"   Extracted metadata year: {metadata.year}")
    
    citation = citation_service.generate(metadata, request.format)
    
    print(f"   Generated citation: {citation}\n")
    
    return CitationResponse(
        paper_id=request.paper_id,
        format=request.format.value,
        citation=citation,
        raw_metadata=metadata
    )

@router.post("/batch")
async def batch_citations(request: BatchCitationRequest, current_user: AuthUser = Depends(get_current_user)):
    """Generate citations for multiple papers. User must own all papers."""
    if not request.paper_ids:
        raise HTTPException(status_code=400, detail="No paper IDs provided")
    
    result = supabase.table("papers").select("*").eq("user_id", current_user.id).in_("id", request.paper_ids).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="No papers found or access denied")
    
    citations = []
    for paper in result.data:
        metadata = extract_metadata(paper)
        citation = citation_service.generate(metadata, request.format)
        citations.append({
            "paper_id": paper["id"],
            "title": paper["title"],
            "citation": citation
        })
    
    return {"citations": citations, "format": request.format.value}

@router.get("/formats")
async def get_formats():
    """Get available citation formats"""
    return {
        "formats": [
            {"value": "apa", "label": "APA 7th Edition", "description": "American Psychological Association"},
            {"value": "ieee", "label": "IEEE", "description": "Institute of Electrical and Electronics Engineers"},
            {"value": "bibtex", "label": "BibTeX", "description": "For LaTeX documents"},
            {"value": "vancouver", "label": "Vancouver", "description": "Medical/scientific journals"},
            {"value": "mla", "label": "MLA 9th Edition", "description": "Modern Language Association"},
        ]
    }

@router.post("/export/formatted")
async def export_formatted_citations(request: BatchCitationRequest, current_user: AuthUser = Depends(get_current_user)):
    """Export extracted citations (from bibliography) in any format. User must own all papers."""
    
    # Verify user owns all papers first
    papers_check = supabase.table("papers").select("id").eq("user_id", current_user.id).in_("id", request.paper_ids).execute()
    if not papers_check.data or len(papers_check.data) != len(request.paper_ids):
        raise HTTPException(status_code=404, detail="One or more papers not found or access denied")
    
    # Get all extracted citations for the papers
    result = supabase.table("paper_citations").select("*").in_("paper_id", request.paper_ids).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="No citations found for export")
    
    citations = result.data
    formatted_citations = []
    
    # Generate formatted citation for each extracted citation
    for cit in citations:
        try:
            # Create metadata from citation data
            metadata = PaperMetadata(
                id=cit.get("id", "unknown"),
                title=cit.get("title") or cit.get("citation_text", "Untitled")[:200],
                authors=cit.get("authors") or [],
                year=cit.get("year"),
                journal=cit.get("venue"),
                doi=cit.get("doi"),
                url=None,  # URLs typically not in extracted citations
                volume=None,
                issue=None,
                pages=None,
                publisher=None
            )
            
            # Generate formatted citation
            formatted = citation_service.generate(metadata, request.format)
            formatted_citations.append({
                "citation_id": cit.get("id"),
                "title": metadata.title,
                "citation": formatted
            })
        except Exception as e:
            print(f"⚠️ Failed to format citation {cit.get('id')}: {e}")
            continue
    
    if not formatted_citations:
        raise HTTPException(status_code=500, detail="Failed to generate formatted citations")
    
    return {
        "citations": formatted_citations,
        "format": request.format.value,
        "count": len(formatted_citations)
    }

@router.post("/export/bibtex", response_class=PlainTextResponse)
async def export_bibtex(request: BatchCitationRequest, current_user: AuthUser = Depends(get_current_user)):
    """Export extracted citations as BibTeX format (.bib file content). User must own all papers."""
    
    # Verify user owns all papers first
    papers_check = supabase.table("papers").select("id").eq("user_id", current_user.id).in_("id", request.paper_ids).execute()
    if not papers_check.data or len(papers_check.data) != len(request.paper_ids):
        raise HTTPException(status_code=404, detail="One or more papers not found or access denied")
    
    # Get all extracted citations for the papers
    result = supabase.table("paper_citations").select("*").in_("paper_id", request.paper_ids).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="No citations found for export")
    
    citations = result.data
    entries = []
    
    # Generate BibTeX entry for each citation
    for cit in citations:
        try:
            # Create metadata from citation data
            metadata = PaperMetadata(
                id=cit.get("id", "unknown"),
                title=cit.get("title", cit.get("citation_text", "Untitled")),
                authors=cit.get("authors", []),
                year=cit.get("year"),
                journal=cit.get("venue"),
                doi=cit.get("doi")
            )
            
            # Generate BibTeX entry
            entry = citation_service.generate(metadata, CitationFormat.BIBTEX)
            entries.append(entry)
        except Exception as e:
            print(f"⚠️ Failed to generate BibTeX for citation {cit.get('id')}: {e}")
            continue
    
    if not entries:
        raise HTTPException(status_code=500, detail="Failed to generate BibTeX entries")
    
    return "\n\n".join(entries)



from models.citation import ExtractCitationsRequest, ExtractCitationsResponse, ExtractedCitation, CitationStatsResponse
from services.citation_extraction_service import citation_extraction_service
import time

@router.post("/extract", response_model=ExtractCitationsResponse)
async def extract_citations_from_paper(request: ExtractCitationsRequest, current_user: AuthUser = Depends(get_current_user)):
    """Auto-extract citations from paper text. User must own the paper."""
    start_time = time.time()
    
    # Get paper and verify ownership
    result = supabase.table("papers").select("*").eq("id", request.paper_id).eq("user_id", current_user.id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Paper not found or access denied")
    
    paper = result.data
    full_text = paper.get("content_text", "")
    
    # Delete existing citations for this paper to avoid duplicate key violations
    # This ensures a fresh extraction when user clicks "AI Enrich" again
    try:
        supabase.table("paper_citations").delete().eq("paper_id", request.paper_id).execute()
        print(f"✅ Cleared existing citations for paper: {request.paper_id}")
    except Exception as e:
        print(f"⚠️ Warning: Could not clear existing citations: {e}")
    
    if not full_text:
        raise HTTPException(status_code=400, detail="Paper has no full text available for extraction")
    
    # Extract bibliographic sections
    bib_text = citation_extraction_service.extract_bibliography_section(full_text)
    if not bib_text:
        return ExtractCitationsResponse(
            paper_id=request.paper_id,
            citations_extracted=0,
            citations=[],
            extraction_time=time.time() - start_time
        )
        
    # Parse bibliography entries
    raw_citations = citation_extraction_service.parse_bibliography_entries(bib_text)
    
    # Detect and merge duplicate citations (same paper cited multiple times with slight variations)
    duplicates = citation_extraction_service.detect_duplicate_citations(raw_citations, similarity_threshold=0.85)
    if duplicates:
        print(f"⚠️ Found {len(duplicates)} duplicate citation(s), merging...")
        raw_citations = citation_extraction_service.merge_duplicate_citations(raw_citations, duplicates)
        print(f"✅ After deduplication: {len(raw_citations)} unique citations")
    
    # Find in-text contexts (increased limit from 3 to 10 for better context)
    citation_contexts = citation_extraction_service.find_in_text_citations(full_text, raw_citations)
    
    # Process each citation with enhanced regex metadata extraction
    extracted_citations = []
    
    for idx, raw_cit in enumerate(raw_citations):
        # Extract metadata using enhanced regex patterns (no AI calls)
        metadata = citation_extraction_service.extract_metadata_from_citation(raw_cit['raw_text'])
        
        # Calculate importance (increase context limit from 3 to 10)
        contexts = citation_contexts.get(raw_cit.get("ref_number", ""), [])[:10]
        importance = await citation_extraction_service.calculate_importance_score(raw_cit, contexts)
        
        # Create citation object
        citation = ExtractedCitation(
            paper_id=request.paper_id,
            citation_text=raw_cit['raw_text'],
            in_text_refs=raw_cit.get('in_text_refs', []),
            title=metadata.get('title'),
            authors=metadata.get('authors', []),
            year=metadata.get('year'),
            doi=metadata.get('doi'),
            venue=metadata.get('venue'),
            relevance_summary=metadata.get('relevance_summary'),
            citation_context=contexts,
            mention_count=len(contexts),
            importance_score=importance,
            citation_type=metadata.get('citation_type'),
            verified=False
        )
        
        extracted_citations.append(citation)
        
        # Store in database (duplicates won't occur now since we cleared old citations)
        try:
            # Truncate long fields to prevent index size errors (PostgreSQL limit: 8191 bytes)
            # GIN index on title field causes "index row requires X bytes, maximum size is 8191" error
            truncated_title = citation.title[:500] if citation.title else None
            truncated_relevance = citation.relevance_summary[:1000] if citation.relevance_summary else None
            truncated_contexts = [ctx[:500] for ctx in citation.citation_context[:10]] if citation.citation_context else []
            
            supabase.table("paper_citations").insert({
                "paper_id": request.paper_id,
                "citation_text": citation.citation_text[:2000],  # Truncate raw citation text
                "in_text_refs": citation.in_text_refs[:20],  # Limit array size
                "title": truncated_title,
                "authors": citation.authors[:10] if citation.authors else [],  # Limit author array
                "year": citation.year,
                "doi": citation.doi[:200] if citation.doi else None,
                "venue": citation.venue[:300] if citation.venue else None,
                "relevance_summary": truncated_relevance,
                "citation_context": truncated_contexts,
                "mention_count": citation.mention_count,
                "importance_score": citation.importance_score,
                "citation_type": citation.citation_type[:50] if citation.citation_type else None,
                "extraction_method": "regex"  # Using enhanced regex extraction
            }).execute()
        except Exception as e:
            print(f"❌ Failed to store citation: {e}")
            # Continue processing other citations even if one fails
        
    return ExtractCitationsResponse(
        paper_id=request.paper_id,
        citations_extracted=len(extracted_citations),
        citations=extracted_citations,
        extraction_time=time.time() - start_time
    )
    
    
@router.get("/paper/{paper_id}", response_model=List[ExtractedCitation])
async def get_paper_citations(paper_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Get all extracted citations for a paper. User must own the paper."""
    # Verify paper ownership
    paper_check = supabase.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
    if not paper_check.data:
        raise HTTPException(status_code=404, detail="Paper not found or access denied")
    
    result = supabase.table("paper_citations").select("*").eq("paper_id", paper_id).order("importance_score", desc=True).execute()
    
    if not result.data:
        return []
    
    # Process citations to ensure proper data types
    citations = []
    for cit in result.data:
        # Ensure arrays are not None
        if cit.get('in_text_refs') is None:
            cit['in_text_refs'] = []
        if cit.get('citation_context') is None:
            cit['citation_context'] = []
        if cit.get('authors') is None:
            cit['authors'] = []
        
        try:
            citations.append(ExtractedCitation(**cit))
        except Exception as e:
            print(f"Failed to parse citation: {e}")
            print(f"Citation data: {cit}")
            continue
    
    return citations


@router.get("/stats/{paper_id}", response_model=CitationStatsResponse)
async def get_citation_stats(paper_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Get citation statistics for a paper. User must own the paper."""
    # Verify paper ownership
    paper_check = supabase.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
    if not paper_check.data:
        raise HTTPException(status_code=404, detail="Paper not found or access denied")
    
    result = supabase.table("paper_citations").select("*").eq("paper_id", paper_id).execute()
    
    if not result.data:
        return CitationStatsResponse(
            paper_id=paper_id,
            total_citations=0,
            citations_by_type={},
            top_cited_works=[],
            average_citation_year=None
        )
        
    citations = result.data
    
    # Calculate stats
    citations_by_type = {}
    years = []
    top_works = []
    
    for cit in citations:
        cit_type = cit.get("citation_type") or "unknown"  # Ensure never None
        citations_by_type[cit_type] = citations_by_type.get(cit_type, 0) + 1
        
        if cit.get("year"):
            years.append(cit["year"])
            
        if cit.get('importance_score', 0) > 0.5:
            top_works.append({
                'title': cit.get('title'),
                'authors': cit.get('authors'),
                'year': cit.get('year'),
                'importance_score': cit.get('importance_score')
            })
    
    top_works.sort(key=lambda x: x['importance_score'], reverse=True)
    return CitationStatsResponse(
        paper_id=paper_id,
        total_citations=len(citations),
        citations_by_type=citations_by_type,
        top_cited_works=top_works[:10],
        average_citation_year=sum(years) / len(years) if years else None
    )
    

@router.delete("/paper/{paper_id}/citations")
async def delete_paper_citations(paper_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Delete all extracted citations for a paper. User must own the paper."""
    # Verify paper ownership
    paper_check = supabase.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
    if not paper_check.data:
        raise HTTPException(status_code=404, detail="Paper not found or access denied")
    
    supabase.table("paper_citations").delete().eq("paper_id", paper_id).execute()
    return {"success": True, "message": f"Deleted citations for paper {paper_id}"}


@router.patch("/{citation_id}/verify")
async def verify_citation(citation_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Mark a citation as verified/trusted. User must own the associated paper."""
    try:
        # Get citation and verify paper ownership
        citation = supabase.table("paper_citations").select("paper_id").eq("id", citation_id).single().execute()
        if not citation.data:
            raise HTTPException(status_code=404, detail="Citation not found")
        
        paper_check = supabase.table("papers").select("id").eq("id", citation.data["paper_id"]).eq("user_id", current_user.id).execute()
        if not paper_check.data:
            raise HTTPException(status_code=404, detail="Citation not found or access denied")
        
        result = supabase.table("paper_citations").update({
            "verified": True
        }).eq("id", citation_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Citation not found")
        
        return {"success": True, "message": "Citation marked as verified"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify citation: {str(e)}")


@router.patch("/{citation_id}/unverify")
async def unverify_citation(citation_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Unmark a citation as verified. User must own the associated paper."""
    try:
        # Get citation and verify paper ownership
        citation = supabase.table("paper_citations").select("paper_id").eq("id", citation_id).single().execute()
        if not citation.data:
            raise HTTPException(status_code=404, detail="Citation not found")
        
        paper_check = supabase.table("papers").select("id").eq("id", citation.data["paper_id"]).eq("user_id", current_user.id).execute()
        if not paper_check.data:
            raise HTTPException(status_code=404, detail="Citation not found or access denied")
        
        result = supabase.table("paper_citations").update({
            "verified": False
        }).eq("id", citation_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Citation not found")
        
        return {"success": True, "message": "Citation unmarked as verified"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unverify citation: {str(e)}")


@router.get("/verified/{paper_id}")
async def get_verified_citations(paper_id: str, current_user: AuthUser = Depends(get_current_user)):
    """Get only verified citations for a paper. User must own the paper."""
    try:
        # Verify paper ownership
        paper_check = supabase.table("papers").select("id").eq("id", paper_id).eq("user_id", current_user.id).execute()
        if not paper_check.data:
            raise HTTPException(status_code=404, detail="Paper not found or access denied")
        
        result = supabase.table("paper_citations").select("*").eq("paper_id", paper_id).eq("verified", True).order("importance_score", desc=True).execute()
        
        if not result.data:
            return []
        
        citations = []
        for cit in result.data:
            if cit.get('in_text_refs') is None:
                cit['in_text_refs'] = []
            if cit.get('citation_context') is None:
                cit['citation_context'] = []
            if cit.get('authors') is None:
                cit['authors'] = []
            
            try:
                citations.append(ExtractedCitation(**cit))
            except Exception as e:
                print(f"Failed to parse citation: {e}")
                continue
        
        return citations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch verified citations: {str(e)}")