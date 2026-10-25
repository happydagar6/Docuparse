# Litwise — Active Work & Feature Tracker (TRACKER.md)

> **Note**: This tracker monitors current and upcoming engineering tasks starting from this moment forward. Past historical milestones are recorded in `MEMORY.md`.

---

## 🎯 Active Feature: Phase 2 — Wiring the RAG Pipeline into the Web Application

### Goal:
Connect our clean, modular `services/rag/` pipeline directly into the active FastAPI routes (`routes/chat.py` and `app.py`), replacing the legacy bloated pipelines without breaking any frontend contracts.

### 📋 Work-in-Progress Checklist for Phase 2:

- [ ] **1. Chat Route Adapter (`routes/chat.py`)**:
  - Update `POST /api/chat/stream` in `routes/chat.py` to invoke `rag_generator.chat_stream()`.
  - Ensure Upstash Redis L2 message caching and Supabase message persistence continue to save the streamed message and citation sources.

- [ ] **2. Document Upload Wiring (`app.py`)**:
  - Wire `POST /upload` in `app.py` to use `document_ingestion_service.chunk_document()` and `vector_store_service.upsert_chunks()`.
  - Ensure in-memory BM25 index is built for the uploaded paper via `hybrid_retriever.index_paper()`.

- [ ] **3. Full Backend Test Suite**:
  - Run `$env:PYTHONIOENCODING="utf-8"; .\myenv\Scripts\python.exe -m pytest tests/` to verify all 48 existing backend tests pass.

- [ ] **4. Live End-to-End Browser Test**:
  - Launch Next.js frontend, upload a fresh research PDF, ask a question in chat, and verify live streaming tokens and clickable page citations in the browser.

---

## 🗺️ Milestones Overview

| Milestone | Target Component | Description | Status |
| :--- | :--- | :--- | :--- |
| **Step 1.1** | `services/rag/ingestion.py` | Document chunking with dynamic character-offset page mapping | **COMPLETE** ✅ |
| **Step 1.2** | `services/rag/vector_store.py` | Qdrant Cloud vector store with 1536-dim OpenAI embeddings | **COMPLETE** ✅ |
| **Step 1.3** | `services/rag/retriever.py` | In-memory BM25 + Weighted Alpha Fusion + Heuristic Re-ranker | **COMPLETE** ✅ |
| **Step 1.4** | `services/rag/generator.py` | `gpt-6-luna` LLM generator with real-time SSE streaming & page citations | **COMPLETE** ✅ |
| **Phase 2** | `routes/chat.py` & `app.py` | Connect clean RAG engine to active FastAPI endpoints & run full test suite | **IN PROGRESS** 🟡 |
| **Phase 3** | Code Cleanup & Cheatsheet | Retire obsolete legacy files (`financial_rag_pipeline.py`) & build interview guide | PENDING ⚪ |
| **Step 2.0** | `routes/chat.py` & Adapter | Connect `services/rag/` to the FastAPI chat router, deprecating legacy `chat_pipeline.py` | PENDING ⚪ |
| **Step 3.0** | `app.py` (`POST /upload`) | Connect upload route to use `ingestion.py` and `vector_store.py` directly | PENDING ⚪ |
| **Step 4.0** | Full Backend Test Suite | Execute `$env:PYTHONIOENCODING="utf-8"; .\myenv\Scripts\python.exe -m pytest tests/` to confirm all 48 tests pass | PENDING ⚪ |
| **Step 5.0** | Frontend Integration Test | Run `litwise-frontend` locally, upload a fresh PDF, and verify live streaming chat & citation highlighting in the browser | PENDING ⚪ |
| **Step 6.0** | Codebase Cleanup & Interview Mastery | Delete obsolete bloated files (`financial_rag_pipeline.py`, etc.) and finalize technical interview cheatsheet | PENDING ⚪ |

---

## ⚠️ Current Blockers & Technical Risks
* **None**: All retrieval components (Steps 1.1, 1.2, 1.3) are live-verified and passing. Qdrant Cloud and OpenAI API credentials are authenticated and operational.
