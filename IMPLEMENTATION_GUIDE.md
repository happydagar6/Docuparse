# Enhanced Semantic Search Implementation Guide

## Overview
This implementation adds powerful hybrid search capabilities to Litwise with:
- **Hybrid Search**: Vector similarity (70%) + BM25 keyword matching (30%)
- **Query Expansion**: Automatic acronym and synonym expansion
- **Metadata Filtering**: Filter by author, publication year, keywords
- **Cross-Paper Search**: Search across all uploaded papers
- **Automatic Metadata Extraction**: Extract authors, year, DOI from PDFs

---

## Implementation Steps

### Step 1: Database Migration

**File**: `database_metadata_migration.sql`

Run this SQL migration to add metadata columns to your Supabase database:

```sql
-- Run in Supabase SQL Editor
\i database_metadata_migration.sql
```

**What it does**:
- Adds `authors`, `publication_year`, `doi`, `keywords`, `journal_or_conference`, `abstract` columns
- Creates GIN indexes for efficient JSON and array filtering
- Sets up default values for existing records

---

### Step 2: Install Python Dependencies

The metadata extractor requires PyMuPDF (fitz):

```bash
cd litwise-backend
pip install PyMuPDF
```

Or add to `requirements.txt`:
```
PyMuPDF>=1.23.0
```

---

### Step 3: Test the Implementation

#### 3.1 Test Database Migration

```bash
# Check if migration succeeded in Supabase SQL Editor
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'papers' 
AND column_name IN ('authors', 'publication_year', 'doi', 'keywords');
```

#### 3.2 Test Metadata Extraction

Upload a new PDF through the UI - it should automatically extract metadata.

Check backend logs for:
```
✅ Extracted metadata: X authors, year: 2024, DOI: 10.xxxx/yyyy
```

#### 3.3 Test Enhanced Search

1. **Basic Search** (no filters):
   ```
   Search query: "machine learning transformer"
   Expected: Results from all papers, expanded query with synonyms
   ```

2. **Search with Filters**:
   ```
   Query: "deep learning"
   Filters:
     - Author: "Smith"
     - Year From: 2020
     - Year To: 2024
   Expected: Only papers matching filters
   ```

3. **Acronym Expansion**:
   ```
   Query: "NLP with BERT"
   Expected: Expands to "natural language processing with bidirectional encoder representations"
   Check backend logs for: "🔍 Query expanded: 'NLP with BERT' → '...'"
   ```

---

## Architecture Overview

### Backend Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Upload Flow                          │
├─────────────────────────────────────────────────────────────┤
│  1. PDF Upload → 2. Text Extraction → 3. Metadata Extract  │
│  4. Store in Supabase → 5. Generate Embeddings             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                        Search Flow                          │
├─────────────────────────────────────────────────────────────┤
│  1. Query Expansion (acronyms/synonyms)                    │
│  2. Metadata Filtering (DB-level)                          │
│  3. Hybrid Search:                                          │
│     • Vector Search (Qdrant)                                │
│     • BM25 Search (if available)                            │
│  4. Result Fusion (70% vector + 30% BM25)                  │
│  5. Re-ranking (query term overlap)                         │
│  6. Diversity Scoring (prefer different papers)            │
│  7. Metadata Enrichment (add author, year, DOI)           │
└─────────────────────────────────────────────────────────────┘
```

### Component Structure

```
litwise-backend/
├── models.py                          # ✅ Updated with SearchFilters, PaperMetadata
├── app.py                             # ✅ Updated /upload and /search endpoints
├── workflow/
│   ├── enhanced_search.py            # ✅ Updated with query expansion, cross-paper search
│   ├── metadata_extractor.py         # ✅ NEW: PDF metadata extraction
│   └── utils.py                       # Existing embedding utilities
└── database_metadata_migration.sql    # ✅ NEW: Database schema updates

litwise-frontend/
├── src/
│   ├── components/forms/
│   │   └── SearchForm.js              # ✅ Updated with filter state and UI
│   └── lib/
│       ├── api.js                     # ✅ Updated searchPapers with filters
│       └── react-query.js             # ✅ Updated mutation to pass filters
```

---

## Key Features Implemented

### 1. Query Expansion

**Location**: `enhanced_search.py` → `expand_query()`

**Acronyms Supported**:
- ML → machine learning
- NLP → natural language processing
- CNN → convolutional neural network
- BERT → bidirectional encoder representations from transformers
- LLM → large language model
- ... (40+ acronyms)

**Synonym Groups**:
- method, approach, technique, methodology
- model, architecture, framework, system
- improve, enhance, optimize, boost
- ... (9 synonym groups)

**How it works**:
```python
query = "ML model"
# Expands to: "ML model machine learning ML architecture framework system"
```

### 2. Metadata Extraction

**Location**: `metadata_extractor.py` → `MetadataExtractor`

**Extraction Methods**:
1. **PDF Metadata Fields**: Author, title, keywords from PDF properties
2. **Text Pattern Matching**: Regex patterns for DOI, year, abstract, authors
3. **Heuristic Analysis**: Author block detection, affiliation extraction

**Example Output**:
```json
{
  "authors": [
    {"name": "John Smith", "affiliation": "MIT", "email": "john@mit.edu"}
  ],
  "publication_year": 2024,
  "doi": "10.1234/example",
  "keywords": ["machine learning", "transformers"],
  "abstract": "This paper presents..."
}
```

### 3. Hybrid Search

**Location**: `enhanced_search.py` → `hybrid_search()`

**Algorithm**:
1. Generate embeddings for query
2. **Vector Search**: Semantic similarity via Qdrant
3. **BM25 Search**: Keyword matching (if index available)
4. **Score Fusion**: `combined_score = 0.7 * vector_score + 0.3 * bm25_score`
5. **Re-ranking**: Add bonus for query term overlap
6. **Diversity**: Penalize multiple results from same paper

**Performance**:
- Retrieves 50 candidates
- Re-ranks to top 15 results
- Cross-paper search includes diversity scoring

### 4. Advanced Filters

**Location**: `SearchForm.js` + `app.py /search`

**Supported Filters**:
- **Author**: Partial name matching in JSONB array
- **Year Range**: Filter by publication year (from/to)
- **Keywords**: Match any specified keyword
- **Paper IDs**: Limit search to specific papers

**Implementation**:
```javascript
// Frontend
filters = {
  author: "Smith",
  year_from: 2020,
  year_to: 2024
}

// Backend SQL
WHERE authors @> '[{"name": "Smith"}]'::jsonb
  AND publication_year >= 2020
  AND publication_year <= 2024
```

---

## Error Handling

### Robust Fallbacks

1. **Metadata Extraction Fails**:
   - Falls back to empty arrays/null values
   - Upload continues successfully
   - Log warning but don't block

2. **BM25 Index Missing**:
   - Falls back to vector-only search
   - Logs: "⚠️ BM25 index not found for paper X"
   - Still returns quality results

3. **Filter SQL Errors**:
   - Catches SQL exceptions
   - Proceeds without filters
   - Logs: "⚠️ Metadata filtering failed, proceeding without filters"

4. **Query Expansion Errors**:
   - Returns original query if expansion fails
   - Doesn't break search flow

### Validation

**Backend** (`models.py`):
- Year validation: 1900-2100
- Year range validation: from ≤ to
- Field length limits
- Type checking with Pydantic

**Frontend** (`SearchForm.js`):
- Client-side year range validation
- Empty query prevention
- Numeric input constraints (min/max)

---

## Performance Optimizations

1. **Parallel Operations**:
   ```python
   # Vector and BM25 search run in parallel
   vector_task = self.vector_search(...)
   bm25_task = asyncio.to_thread(self.bm25_search, ...)
   results = await asyncio.gather(vector_task, bm25_task)
   ```

2. **Database Indexes**:
   - GIN index on `authors` JSONB
   - B-tree index on `publication_year`
   - Full-text index on `abstract`

3. **Result Limiting**:
   - Fetch 50 candidates
   - Re-rank to top 15
   - Prevents over-retrieval

4. **Caching** (via React Query):
   - Search results cached
   - Automatic invalidation
   - Optimistic updates

---

## Testing Checklist

### Backend Tests

- [ ] Database migration runs without errors
- [ ] Metadata extraction works for sample PDF
- [ ] Query expansion logs show expanded terms
- [ ] Hybrid search returns results
- [ ] Filters correctly limit results
- [ ] Error handling doesn't crash server

### Frontend Tests

- [ ] Search form renders correctly
- [ ] Advanced filters expand/collapse
- [ ] Author input updates state
- [ ] Year range validation works
- [ ] Filter indicator shows when applied
- [ ] Clear filters button works
- [ ] Results display metadata (author, year)

### Integration Tests

- [ ] Upload PDF → Metadata appears in database
- [ ] Search with "ML" → Query expansion happens
- [ ] Search with filters → Results match criteria
- [ ] Cross-paper search → Multiple papers in results
- [ ] Acronym search → Finds relevant papers

---

## Monitoring & Debugging

### Backend Logs to Watch

```bash
# Successful metadata extraction
✅ Extracted metadata: 3 authors, year: 2024, DOI: 10.1234/example

# Query expansion
🔍 Query expanded: 'ML' → 'ML machine learning ML'

# Hybrid search progress
📊 Vector search: 45 results
📊 BM25 search: 38 results
🔗 Combined: 67 unique results
✅ Hybrid search complete: 15 final results

# Diversity scoring
🎯 Applied diversity scoring: 5 unique papers in results
```

### Common Issues & Solutions

**Issue**: Metadata not extracted
```bash
Solution: Check PyMuPDF installation
pip install --upgrade PyMuPDF
```

**Issue**: Filters not working
```bash
Solution: Verify database migration
SELECT * FROM papers LIMIT 1; -- Check for new columns
```

**Issue**: Search returns no results
```bash
Solution: Check Qdrant connection and embeddings
# Visit /qdrant/diagnostics endpoint
```

---

## Future Enhancements

### Potential Improvements

1. **Citation Network Analysis**:
   - Extract citations from PDFs
   - Build citation graph
   - Recommend related papers

2. **Advanced Metadata**:
   - Extract figures and tables
   - Parse equations with LaTeX
   - Identify methodology sections

3. **Multi-Modal Search**:
   - Search by figure similarity
   - Search by equation patterns
   - Search by code snippets

4. **Collaborative Filtering**:
   - Track user search patterns
   - Recommend papers based on behavior
   - Popular search terms dashboard

5. **Export & Integration**:
   - Export to Zotero/Mendeley
   - BibTeX generation
   - PDF annotation sync

---

## Maintenance

### Regular Tasks

1. **Monitor Index Size**:
   ```sql
   SELECT pg_size_pretty(pg_total_relation_size('papers'));
   ```

2. **Update Synonym Mappings**:
   - Edit `QUERY_EXPANSIONS` in `enhanced_search.py`
   - Add domain-specific acronyms

3. **Optimize Queries**:
   - Analyze slow searches
   - Adjust result limits
   - Tune fusion weights (alpha parameter)

### Backup Strategy

1. **Database**: Use Supabase automatic backups
2. **Qdrant**: Regular snapshots of vector collections
3. **PDFs**: Store originals in object storage (Supabase Storage)

---

## Support & Resources

### Documentation
- Qdrant: https://qdrant.tech/documentation/
- PyMuPDF: https://pymupdf.readthedocs.io/
- LangChain: https://python.langchain.com/docs/

### Troubleshooting
- Check backend logs for detailed error messages
- Use `debug=true` in search requests
- Visit `/qdrant/diagnostics` for collection status

---

## Conclusion

This implementation provides a production-ready semantic search system with:
✅ Hybrid search (vector + keyword)
✅ Query expansion for better recall
✅ Metadata filtering for precision
✅ Automatic metadata extraction
✅ Robust error handling
✅ Performance optimizations
✅ Clean, maintainable architecture

The system is scalable, extensible, and follows best practices for both backend and frontend development.
