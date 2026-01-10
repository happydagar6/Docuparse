"""
Diagnostic tool to analyze what's actually being extracted and indexed from uploaded documents
"""

import os
import sys
from workflow.db import supabase, qdrant
from workflow.utils import extract_text_from_pdf, extract_multimodal_from_pdf
import json

def analyze_indexed_content(paper_id: str):
    """
    Analyze what's actually indexed in Qdrant for a specific paper
    """
    print(f"\n{'='*80}")
    print(f"🔍 ANALYZING INDEXED CONTENT FOR PAPER: {paper_id}")
    print(f"{'='*80}\n")
    
    try:
        # Query Qdrant for this paper's content
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
        
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="paper_id",
                    match=MatchValue(value=paper_id)
                )
            ]
        )
        
        # Get all points for this paper
        results = qdrant.scroll(
            collection_name="litwise_collection",
            scroll_filter=query_filter,
            limit=1000  # Get up to 1000 chunks
        )
        
        points, next_offset = results
        
        print(f"✅ Found {len(points)} indexed chunks for this paper\n")
        
        # Analyze content by page
        pages = {}
        content_types = {"text": 0, "table": 0, "image": 0}
        
        for i, point in enumerate(points):
            payload = point.payload
            page = payload.get('page', 'unknown')
            content_type = payload.get('type', 'unknown')
            content = payload.get('content', '')[:100]  # First 100 chars
            
            if page not in pages:
                pages[page] = []
            
            pages[page].append({
                'type': content_type,
                'content_preview': content,
                'relevance_score': payload.get('relevance_score', 'N/A'),
                'chunk_id': payload.get('chunk_id', 'N/A')
            })
            
            if content_type in content_types:
                content_types[content_type] += 1
        
        # Print analysis by page
        print("📊 INDEXED CONTENT BREAKDOWN BY PAGE:")
        print("-" * 80)
        for page in sorted(pages.keys(), key=lambda x: int(x) if isinstance(x, int) or (isinstance(x, str) and x.isdigit()) else 0):
            chunks = pages[page]
            print(f"\n📄 Page {page}: {len(chunks)} chunks")
            for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks per page
                print(f"   [{i+1}] Type: {chunk['type']}")
                print(f"       Content: {chunk['content_preview']}...")
            if len(chunks) > 3:
                print(f"   ... and {len(chunks) - 3} more chunks")
        
        print(f"\n\n📈 CONTENT TYPE SUMMARY:")
        print("-" * 80)
        for ctype, count in content_types.items():
            print(f"  {ctype.upper()}: {count} chunks")
        
        # Search for specific keywords
        print(f"\n\n🔎 SEARCHING FOR SPECIFIC KEYWORDS:")
        print("-" * 80)
        
        keywords = [
            "Unit cost of processing",
            "unit cost",
            "processing cost",
            "Financial Performance",
            "Net surplus",
            "deficit"
        ]
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            found_chunks = []
            
            for point in points:
                content = point.payload.get('content', '').lower()
                if keyword_lower in content:
                    found_chunks.append({
                        'page': point.payload.get('page', '?'),
                        'type': point.payload.get('type', '?'),
                        'preview': point.payload.get('content', '')[:80]
                    })
            
            if found_chunks:
                print(f"\n✅ '{keyword}': Found in {len(found_chunks)} chunks")
                for chunk in found_chunks[:2]:
                    print(f"   📄 Page {chunk['page']} ({chunk['type']}): {chunk['preview']}...")
            else:
                print(f"\n❌ '{keyword}': NOT FOUND in any chunks")
        
    except Exception as e:
        print(f"❌ Error analyzing indexed content: {e}")
        import traceback
        traceback.print_exc()


def analyze_extraction(pdf_path: str):
    """
    Analyze what's being extracted from the PDF
    """
    print(f"\n{'='*80}")
    print(f"🔍 ANALYZING PDF EXTRACTION: {pdf_path}")
    print(f"{'='*80}\n")
    
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return
    
    try:
        # Extract basic text
        from workflow.utils import extract_text_from_pdf
        full_text, page_info = extract_text_from_pdf(pdf_path)
        
        print(f"📄 TEXT EXTRACTION:")
        print("-" * 80)
        print(f"  Total pages: {len(page_info)}")
        print(f"  Total characters: {len(full_text)}")
        
        # Search for keywords in extracted text
        keywords = [
            "Unit cost of processing",
            "unit cost",
            "Financial Performance",
            "Net surplus/deficit"
        ]
        
        print(f"\n🔎 KEYWORD SEARCH IN EXTRACTED TEXT:")
        print("-" * 80)
        for keyword in keywords:
            if keyword.lower() in full_text.lower():
                # Find context around keyword
                idx = full_text.lower().find(keyword.lower())
                context_start = max(0, idx - 100)
                context_end = min(len(full_text), idx + len(keyword) + 100)
                context = full_text[context_start:context_end]
                
                print(f"\n✅ FOUND: '{keyword}'")
                print(f"   Context: ...{context}...")
            else:
                print(f"\n❌ NOT FOUND: '{keyword}'")
        
        # Extract multimodal content
        print(f"\n\n📊 MULTIMODAL EXTRACTION:")
        print("-" * 80)
        try:
            full_text_mm, page_info_mm, multimodal = extract_multimodal_from_pdf(pdf_path)
            
            print(f"  Images: {len(multimodal['images'])}")
            print(f"  Tables: {len(multimodal['tables'])}")
            
            # Show table details
            if multimodal['tables']:
                print(f"\n  📋 TABLE DETAILS:")
                for i, table in enumerate(multimodal['tables'][:3]):
                    print(f"\n    Table {i+1} (Page {table.get('page', '?')}):")
                    print(f"      Rows: {table.get('row_count', 0)}")
                    print(f"      Cols: {table.get('col_count', 0)}")
                    print(f"      Headers: {table.get('headers', [])[:5]}...")
                    
                    # Check if this table contains relevant keywords
                    text_repr = table.get('text_representation', '')
                    if 'unit cost' in text_repr.lower():
                        print(f"      ✅ Contains 'unit cost'!")
                        print(f"         Preview: {text_repr[:150]}...")
        
        except Exception as e:
            print(f"  ⚠️  Multimodal extraction issue: {e}")
        
    except Exception as e:
        print(f"❌ Error analyzing extraction: {e}")
        import traceback
        traceback.print_exc()


def diagnose_search_quality(paper_id: str, query: str):
    """
    Test the search quality for a specific query
    """
    print(f"\n{'='*80}")
    print(f"🔍 TESTING SEARCH QUALITY")
    print(f"{'='*80}\n")
    
    print(f"Paper ID: {paper_id}")
    print(f"Query: {query}\n")
    
    try:
        from workflow.enhanced_search import enhanced_search
        from langchain_openai import OpenAIEmbeddings
        import asyncio
        
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        async def test_search():
            results = await enhanced_search.hybrid_search(
                qdrant_client=qdrant,
                embeddings_model=embeddings,
                paper_id=paper_id,
                query=query,
                top_k=35
            )
            return results
        
        results = asyncio.run(test_search())
        
        print(f"Found {len(results)} results\n")
        
        print("📋 TOP 10 RESULTS:")
        print("-" * 80)
        for i, result in enumerate(results[:10]):
            print(f"\n[{i+1}] Page {result.get('page', '?')} | Score: {result.get('relevance_score', 0):.4f}")
            print(f"    Type: {result.get('type', 'unknown')}")
            content_preview = result.get('content', '')[:80]
            print(f"    Content: {content_preview}...")
        
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Usage examples
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "indexed" and len(sys.argv) > 2:
            analyze_indexed_content(sys.argv[2])
        
        elif command == "extract" and len(sys.argv) > 2:
            analyze_extraction(sys.argv[2])
        
        elif command == "search" and len(sys.argv) > 3:
            diagnose_search_quality(sys.argv[2], " ".join(sys.argv[3:]))
        
        else:
            print("""
Usage:
  python diagnostic_document_analysis.py indexed <paper_id>
    Analyze what's indexed in Qdrant for a paper
  
  python diagnostic_document_analysis.py extract <pdf_path>
    Analyze PDF extraction (text and multimodal)
  
  python diagnostic_document_analysis.py search <paper_id> <query>
    Test search quality for a specific query
""")
    else:
        print("Run with --help or see code for usage examples")
