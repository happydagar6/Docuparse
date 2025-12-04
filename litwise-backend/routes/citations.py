from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from typing import List
from models.citation import (
    CitationRequest, BatchCitationRequest, CitationResponse,
    CitationFormat, PaperMetadata
)
from services.citation_services import citation_service
from workflow.db import supabase

router = APIRouter(prefix="/api/citations", tags=["Citations"])

def extract_metadata(paper: dict) -> PaperMetadata:
    """Extract metadata from paper record"""
    # Extract authors from JSONB field
    authors = None
    authors_data = paper.get("authors", [])
    if authors_data and isinstance(authors_data, list):
        # authors is stored as [{"name": "John Doe", "affiliation": "..."}, ...]
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
    
    return PaperMetadata(
        id=paper.get("id", ""),
        title=paper.get("title", "Untitled"),
        authors=authors,
        year=year,
        doi=paper.get("doi"),
        url=paper.get("url"),
        journal=paper.get("journal_or_conference"),
    )

@router.post("/generate", response_model=CitationResponse)
async def generate_citation(request: CitationRequest):
    """Generate citation for a single paper"""
    result = supabase.table("papers").select("*").eq("id", request.paper_id).single().execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    metadata = extract_metadata(result.data)
    citation = citation_service.generate(metadata, request.format)
    
    return CitationResponse(
        paper_id=request.paper_id,
        format=request.format.value,
        citation=citation,
        raw_metadata=metadata
    )

@router.post("/batch")
async def batch_citations(request: BatchCitationRequest):
    """Generate citations for multiple papers"""
    if not request.paper_ids:
        raise HTTPException(status_code=400, detail="No paper IDs provided")
    
    result = supabase.table("papers").select("*").in_("id", request.paper_ids).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="No papers found")
    
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

@router.post("/export/bibtex", response_class=PlainTextResponse)
async def export_bibtex(request: BatchCitationRequest):
    """Export multiple papers as .bib file content"""
    result = supabase.table("papers").select("*").in_("id", request.paper_ids).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="No papers found")
    
    entries = []
    for paper in result.data:
        metadata = extract_metadata(paper)
        entry = citation_service.generate(metadata, CitationFormat.BIBTEX)
        entries.append(entry)
    
    return "\n\n".join(entries)