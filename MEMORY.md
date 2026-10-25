# Litwise — Project Progress Memory Log (MEMORY.md)

This document records the complete chronological development history, engineering decisions, security remediations, and milestones achieved from the project's inception to the present day.

---

## 🏛️ Phase 0: Project Inception & The Rebuild Decision

### 1. The Core Problem
The initial Litwise backend was developed using rapid generative AI scaffolding, resulting in:
* Over 900 lines of entangled, legacy code (`workflow/enhanced_search.py`, `workflow/financial_rag_pipeline.py`, `pipelines/chat_pipeline.py`).
* Domain-inappropriate bloat (hardcoded financial balance sheet boosts, income statement parsers, ticker queries) inside an academic research assistant.
* Lack of modularity, making it nearly impossible for the engineer to explain the system architecture, mathematical formulas, or retrieval nuances in technical interviews.

### 2. The Architectural Pivot
We decided to completely rebuild the core RAG (Retrieval-Augmented Generation) engine from the ground up under a clean, modular namespace:
`litwise-backend/services/rag/`
* **Rule 1**: Zero unnecessary dependencies or financial bloat.
* **Rule 2**: Every single line, loop, formula, and class must be fully understood and interview-ready.
* **Rule 3**: Zero breaking changes to the Next.js frontend (`POST /upload` response shape and `POST /api/chat/stream` SSE tokens).

---

## 🔒 Phase 1: Security Audit & Git History Purge

### Remediation Details:
1. **Secret Exposure Identification**: Discovered active and expired API keys (OpenAI, xAI, Upstash Redis, LangSmith, Resend) committed into `DEPLOYMENT_GUIDE.md` and scattered throughout 107 Git commits.
2. **Local Key Cleanup**: Deleted residual key artifacts (`k-proj`) and sanitized documentation templates with environment variable placeholders (`your_openai_api_key_here`).
3. **Git History Rewrite**:
   * Executed `git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch DEPLOYMENT_GUIDE.md' --prune-empty --tag-name-filter cat -- --all`.
   * Force-pushed clean Git tree across all branches and tags to GitHub (`happydagar6/Litwise-AI`).
   * Executed `git for-each-ref --format="delete %(refname)" refs/original | git update-ref --stdin` and `git gc --prune=now` to permanently purge local dangling blobs.
4. **Credential Rotation**: User generated a fresh, secure OpenAI API key and updated `litwise-backend/.env`.

---

## 🏗️ Phase 2: Core RAG Pipeline Implementation & Verification

### Step 1.1: Document Ingestion & Page Mapping (`services/rag/ingestion.py`)
* **Created**: [`services/rag/ingestion.py`](file:///c:/Users/harsh/OneDrive/Desktop/Litwise%20Project/litwise-backend/services/rag/ingestion.py)
* **Implemented**:
  * `DocumentChunk` dataclass encapsulating `chunk_id`, `paper_id`, `content`, `page_number`, `chunk_index`, and `metadata`.
  * `clean_text()` sanitizing invisible poison characters (null bytes `\x00` and ASCII control chars) that crash PostgreSQL and Qdrant.
  * `chunk_document()` utilizing LangChain's `RecursiveCharacterTextSplitter` (chunk size: 1000, overlap: 150) paired with custom `_find_page_number()` to map start/end character offsets directly to physical PDF page numbers.
* **Bug Fixes**:
  * Fixed `NameError: name 'logger' is not defined` (corrected `logging = logging.getLogger(...)`).
  * Fixed typo `"paper_number"` to `"page_number"` in `DocumentChunk.to_dict()`.
  * Removed circular self-import at the bottom of the file.

---

### Step 1.2: Qdrant Vector Store Service (`services/rag/vector_store.py`)
* **Created**: [`services/rag/vector_store.py`](file:///c:/Users/harsh/OneDrive/Desktop/Litwise%20Project/litwise-backend/services/rag/vector_store.py)
* **Implemented**:
  * `VectorStoreService` targeting active collection `litwise_collection`.
  * Configured OpenAI `text-embedding-3-small` (1,536 dimensions, Cosine distance).
  * Implemented `ensure_collection_exists()` to verify collection existence and create indexed payload fields (`paper_id` as Keyword, `page_number` as Integer).
  * Built non-blocking batch upserting (`upsert_chunks()`) with `batch_size=50` using `asyncio.to_thread`.
  * Implemented scoped vector search with `paper_filter`:
    ```python
    paper_filter = Filter(must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))])
    ```
* **Bug Fixes & Modern Client Upgrades**:
  * Modernized from deprecated `client.search` to `client.query_points(query=query_vector, ...)` for `qdrant-client` 1.16.0.
  * Fixed tuple iteration bug by iterating over `search_results.points` instead of the raw `QueryResponse`.
  * Resolved 401 OpenAI Authentication error by updating `.env` with a fresh API key.
* **Live Test Verification**: Created [`services/rag/test_vector_rag.py`](file:///c:/Users/harsh/OneDrive/Desktop/Litwise%20Project/litwise-backend/services/rag/test_vector_rag.py) and successfully verified live embedding generation, upsertion to Qdrant Cloud, and isolated retrieval returning Cosine Similarity `0.3704` with Page 1 attribution.

---

### Step 1.3: The Hybrid Retriever & Re-Ranker (`services/rag/retriever.py`)
* **Created**: [`services/rag/retriever.py`](file:///c:/Users/harsh/OneDrive/Desktop/Litwise%20Project/litwise-backend/services/rag/retriever.py)
* **Implemented**:
  * **Text Preprocessing**: Lowercasing, regex punctuation stripping (`re.sub(r"[^\w\s]", " ", ...)`), split tokenization, and NLTK English stopword removal (`_init_nltk()`).
  * **In-Memory BM25 Indexing**: `index_paper()` creates a `BM25Okapi` index per paper stored in `self.bm25_indices[paper_id]`.
  * **Lexical Keyword Search**: `bm25_search()` retrieves top matches with keyword score filtering (`score > 0.0`) and descending sort using `key=lambda x: x[1]`.
  * **Min-Max Score Normalization**:
    $$\text{Normalized Score} = \frac{\text{Score} - \text{Min Score}}{\text{Max Score} - \text{Min Score}}$$
    Safeguarded against division by zero with `if max_score == min_score: return [(doc, 1.0) ...]`.
  * **Weighted Alpha Fusion**:
    $$\text{Combined Score} = (\alpha \times \text{Vector Score}) + ((1 - \alpha) \times \text{BM25 Score})$$
    (Default $\alpha = 0.7$, prioritizing 70% semantic understanding and 30% exact keyword precision).
  * **Heuristic Re-ranking Layer (`rerank()`)**:
    * Verbatim match boost (+0.35 if $\ge 2$ query words found literally, +0.25 if $1$ word found).
    * Token overlap bonus (ratio of common tokens multiplied by 0.35).
    * Deduplication by first 100-character prefix hash (`hash(content[:100])`).
* **Bug Fixes & Typing Contract Alignment**:
  * Fixed `AttributeError: VectorStoreService has no attribute vector_search` by pointing to `vector_store.search()`.
  * Fixed typing warning on line 87 by wrapping `content = str(doc.get("content", "") or "")`.
  * Converted raw dictionary outputs from vector search into `(doc, score)` tuples, harmonizing input contracts for `combine_search_results` and `rerank`.
* **Live Test Verification**:
  * Executed `python -m services.rag.test_vector_rag` in `litwise-backend`.
  * Pure Vector search scored `0.5342`.
  * Hybrid search + Re-ranking scored **`1.1342`**, verifying that exact matches for `"GLUE benchmark"` and `"accuracy"` triggered the verbatim boost and pushed the chunk to Rank #1 with 100% confidence.

### Step 1.4: The LLM Generator (`services/rag/generator.py`)
* **Created**: [`services/rag/generator.py`](file:///c:/Users/harsh/OneDrive/Desktop/Litwise%20Project/litwise-backend/services/rag/generator.py)
* **Implemented**:
  * `ResponseGenerator` class configuring OpenAI's `gpt-6-luna` with `reasoning_effort="medium"`.
  * Strict academic anti-hallucination system prompt enforcing source grounding and page citations (`[Page X]`).
  * Structured context block compiler (`_build_context_block()`) tagging passages with their respective page numbers.
  * Conversational memory formatting (`_format_messages()`) including recent conversation history turns.
  * Real-time Server-Sent Events (SSE) generator (`chat_stream()`) emitting:
    - Token chunks: `data: {"type": "token", "content": "..."}\n\n`
    - Verified source citations: `data: {"type": "sources", "sources": [...]}\n\n`
    - Completion signal: `data: {"type": "complete"}\n\n`
* **Bug Fixes & Typing Alignment**:
  * Fixed `ChatCompletionMessageParam` typing mismatch in message list.
  * Fixed `AsyncStream[ChatCompletionChunk]` async iteration type warning with `cast()`.
  * Discovered and remediated `gpt-6-luna` API constraint: removed incompatible `temperature=0.2` which causes HTTP 400 when `reasoning_effort` is set.
* **Live Test Verification**:
  * Executed `python -m services.rag.test_vector_rag`.
  * `gpt-6-luna` successfully streamed the answer: `"The model achieved a final accuracy score of **94.6%** on the GLUE benchmark [Page 1]."`
  * Emitted citation sources with score `1.1342` and fired `[SSE COMPLETE EVENT RECEIVED]` cleanly.

---

## 📍 Current Status Summary
* **Step 1.1 (Ingestion)**: ✅ Complete & Live-Verified.
* **Step 1.2 (Vector Store)**: ✅ Complete & Live-Verified.
* **Step 1.3 (Hybrid Retriever)**: ✅ Complete & Live-Verified.
* **Step 1.4 (LLM Generator)**: ✅ Complete & Live-Verified with `gpt-6-luna`.
* **Documentation Core (PRD, ARCHITECTURE, MEMORY, DESIGN, TRACKER)**: ✅ Built & Up to Date.
* **Next Active Target**: Phase 2 — Wire `services/rag/` into `routes/chat.py` & `app.py`, replacing legacy pipelines.
