# Litwise — Product Requirements Document (PRD)

---

## 1. Executive Summary & Vision

**Litwise** is an AI-powered academic and scientific research companion designed to transform how students, researchers, and professionals read, comprehend, synthesize, and extract knowledge from dense research papers and scientific literature.

Unlike generic chat-with-PDF tools that hallucinate, lose context over long documents, or return ungrounded responses, Litwise couples **Hybrid Semantic & Lexical Retrieval (Qdrant + BM25)** with **page-level citation tracking**, rich interactive learning modules (Study Plans, Interactive Quizzes, Multi-paper Literature Reviews), and a distraction-free split-pane research workstation.

---

## 2. Target Audience & Personas

| Persona | Needs & Goals | Core Litwise Workflows |
| :--- | :--- | :--- |
| **Graduate & PhD Students** | Digest 20+ papers a week, synthesize literature reviews, extract methodology differences, verify citations. | Literature Review Generator, AI Chat with exact page citations, AI Study Plans. |
| **Scientific & Clinical Researchers** | Find specific numbers, dosages, sample sizes, and equations without false claims. | Exact verbatim search via BM25, citation verification, split-screen PDF highlighting. |
| **Undergraduate Students** | Understand complex academic jargon, test comprehension before exams. | Concept simplifier, AI-generated multiple choice quizzes, note-taking in TipTap. |
| **Industry Analysts & Engineers** | Extract state-of-the-art benchmarks, architecture diagrams, and takeaways from arXiv preprints. | Benchmark extraction, summarization, export to Markdown/PDF. |

---

## 3. Core Features & Capabilities

### 3.1 Grounded Academic Chat (RAG Engine)
* **Zero-Hallucination Retrieval**: Combines Dense Vector Search (OpenAI `text-embedding-3-small` in Qdrant Cloud) with Sparse Lexical Search (in-memory BM25Okapi) and heuristic re-ranking.
* **Exact Page-Level Citations**: Every claim in the AI response maps to a verifiable PDF page number (e.g., `[Page 4]`). Clicking the citation scrolls the PDF reader directly to that page.
* **Real-time SSE Streaming**: Answers stream word-by-word with ultra-low latency using Server-Sent Events (`POST /api/chat/stream`), followed by structured citation metadata.
* **Session Memory & Context Awareness**: Multi-turn conversational memory with Redis L2 caching and cursor pagination.

### 3.2 Document Upload & Multi-Modal Ingestion
* **PDF Upload & Text Sanitization**: Extracts raw text, scrubs poison characters (null bytes `\x00`), and computes dynamic character offsets to guarantee accurate page boundaries.
* **Automated Background Summarization**: Uses a LangGraph multi-agent workflow to generate executive summaries, key contributions, and methodology breakdowns upon upload.
* **Data Isolation**: Strict multi-tenant isolation where each paper's chunks are indexed with unique `paper_id` filters in Qdrant and foreign keys in Supabase.

### 3.3 Interactive Learning & Comprehension Tools
* **AI Study Plan Generator (`routes/study_plan.py`)**: Generates structured, day-by-day learning roadmaps broken into milestones, key concepts, reading assignments, and review checkpoints based on the uploaded paper.
* **Adaptive AI Quizzes (`routes/quiz.py`)**: Automatically creates 5-10 multiple-choice or short-answer questions testing comprehension of methodology, findings, and formulas, with instant grading and explanations.
* **Multi-Paper Literature Review (`routes/literature_review.py`)**: Synthesizes multiple uploaded papers into a comparative matrix highlighting consensus, contradictions, and open questions.
* **Inline AI Citation Verification (`routes/ai_citations.py` & `routes/citations.py`)**: Exports formatted bibliographies in APA, MLA, Chicago, Harvard, and BibTeX formats.

### 3.4 Research Workstation UI
* **Split-Screen Layout**: Synchronized PDF reader on the left and interactive AI assistant/editor on the right.
* **Rich Text Note Editor**: TipTap editor with typography extensions, markdown shortcuts, mention tags, and export capabilities.
* **Audio Summaries & Podcasts (`routes/media.py`)**: Text-to-speech audio overviews of papers for listening on the go.

---

## 4. Non-Functional & Technical Requirements

### 4.1 Performance & Latency
* **Initial Token Latency (TTFT)**: `< 1.2s` for streaming chat responses.
* **Hybrid Retrieval Speed**: `< 250ms` across dense vector querying + in-memory BM25 scoring + re-ranking.
* **PDF Processing**: Upload and chunking completed in `< 5s` for a typical 25-page paper.

### 4.2 Reliability & Security
* **Authentication**: Supabase JWT authentication verified at the FastAPI middleware layer (`middleware/auth.py`).
* **Rate Limiting**: Sliding-window rate limiter via Upstash Redis (`services/rate_limiter_service.py`) preventing API abuse.
* **Error Monitoring**: Production error tracking and transaction profiling via Sentry (`sentry_sdk`).
* **Data Integrity**: Preserves exact character offsets across PDF extractions to eliminate phantom citations.

---

## 5. Success Metrics (KPIs)
* **Citation Accuracy**: 100% of generated claims backed by verified page numbers.
* **Retrieval Precision@5**: $\ge 90\%$ of relevant passages retrieved in the top 5 candidates.
* **User Engagement**: Average session length $> 15\text{ minutes}$ across chat, quiz, and study plan features.
* **Zero Crashes**: Sub-0.1% unhandled API 500 error rate in production.
