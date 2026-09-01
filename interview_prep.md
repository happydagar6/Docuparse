# DocuParse / Litwise AI: The Comprehensive Interview Masterclass

*This document is your ultimate, exhaustive guide to every single feature, architectural decision, and technical reason behind DocuParse (Litwise). It is written in simple, clear language but includes deep technical details designed to impress senior engineering interviewers.*

---

## 1. The High-Level Pitch (How to start the interview)

**"Walk me through your most recent project, DocuParse."**

"DocuParse (or Litwise) is a full-stack, AI-powered financial document analysis platform. Traditional AI struggles with financial documents because they only read raw text; they completely fail when they encounter complex financial tables or charts. 

To solve this, I built a custom **Multimodal RAG (Retrieval-Augmented Generation)** architecture. It intelligently rips PDFs apart, uses **Vision AI** to read charts, stitches broken tables back together, and prevents math hallucinations using a deterministic 'Calculation Gate.'

The backend is built in **FastAPI (Python)** for high-performance async processing, using **Qdrant** for Hybrid Vector Search, and **Redis** for L2 caching and task queues. The frontend is built in **Next.js (React 19)**, featuring a dual-pane PDF viewer, an infinite-scroll chat, a rich-text research editor, and modules for automated literature reviews and quizzes."

---

## 2. The "Why" Behind The Tech Stack

*   **Next.js (React 19):** Chosen for Server-Side Rendering (SSR) to ensure the app is fast and SEO-friendly. It handles complex routing (like quizzes and study plans) seamlessly.
*   **Tailwind CSS & Radix UI (shadcn/ui):** Radix gives me headless, fully accessible components (like modals and dropdowns). Tailwind lets me style them instantly without writing heavy CSS files.
*   **Zustand & React Query:** Redux requires too much boilerplate. Zustand handles global UI state efficiently, while React Query handles data fetching, caching, and loading states for my APIs.
*   **FastAPI (Python):** Python is the industry standard for AI. FastAPI was chosen because it natively supports `async/await`, which is critical when waiting for slow AI APIs or processing massive PDFs without blocking the server.
*   **Qdrant (Vector Database):** I chose Qdrant because it natively supports **Hybrid Search**. It allows me to search using dense vectors (for semantic meaning) AND sparse vectors (BM25 for exact keyword matches like 'Form 8-K').
*   **Redis:** Used heavily as an **L2 Cache** (to speed up chat history and save database queries) and as a **Task Queue** for background workers.
*   **Supabase:** Provides PostgreSQL (for relational data like users and chat logs), Auth, and Cloud Storage for the PDFs.

---

## 3. DEEP DIVE: The Text Splitter Problem & Solution

**Interviewer: "Why did you build a custom text splitter? What's wrong with the default ones?"**

**The Problem:** 
"When building RAG, most people use a standard `RecursiveCharacterTextSplitter`. This tool simply slices the document every 1,000 characters. **This is catastrophic for financial documents.** If you slice a document arbitrarily by character count, you will often chop a Balance Sheet table right in half. The top chunk gets the column headers, and the bottom chunk is just a grid of random numbers without context. When the AI reads the bottom chunk, it gets completely confused."

**The Solution (`MarkdownElementNodeParser`):**
"I wrote a custom chunking strategy inside `markdown_indexer.py`. Instead of splitting by character count, it splits by **structural elements**. 
1. It converts the PDF to Markdown.
2. It creates chunks based on semantic boundaries: sections, headers, paragraphs, and tables. 
3. If a table spans across three PDF pages, my `layout_aware_parser.py` detects the visual layout and stitches them back into one massive table.
4. If that stitched table is too large for the LLM context window (e.g., 200 rows), I chunk the table into blocks of 30 rows, but **I dynamically copy the exact column headers to the top of every single chunk.** The AI never loses context."

---

## 4. DEEP DIVE: Multimodal RAG (Images, Tables, and Text)

**Interviewer: "Explain your Multimodal RAG architecture. How do you handle charts and graphs?"**

"Traditional RAG only embeds text. My architecture treats Text, Images, and Tables as three independent data streams:"

1.  **Extraction (`multimodal_extractor.py`):** A background worker uses `PyMuPDF` to rip open the PDF. It extracts raw text, finds borders to extract tables, and rips out images. It uses MD5 hashing to deduplicate images (so we don't process the company logo 100 times).
2.  **Vision Processing (`vision_service.py`):** A vector database cannot natively 'search' a raw PNG file. So, I send the extracted base64 images to **GPT-4o-mini (Vision)**. It acts as an image-to-text pipeline, generating a highly detailed text caption describing the chart's trends, data points, and legends. We embed *that caption* into the vector database alongside the text.
3.  **Table Normalization (`table_normalizer.py`):** Financial tables are messy. A header might say 'In Millions' while the rows just say '1.5'. My normalizer code infers these multipliers and standardizes the math before it's embedded.
4.  **Retrieval (`financial_rag_pipeline.py`):** When a user asks a question, my system queries Qdrant using Hybrid Search. It pulls the most relevant text chunks, the normalized tables, and the image captions. Finally, it sends the text, tables, and the *actual raw base64 images* to the LLM to generate the final synthesized answer.

---

## 5. Advanced Backend Features & Services

**The Calculation Gate (`numeric_validator.py` & `financial_calculator.py`)**
"LLMs are terrible at math; they hallucinate numbers. If you ask it to sum up 20 rows of revenue, it will often guess. I built a 'Calculation Gate'. Instead of letting the LLM do the math, my Python backend extracts the raw numbers using precise `Decimal` types, runs strict, deterministic Python math, and feeds the mathematically proven result back to the LLM to format."

**Redis L2 Caching with Dual-Mode Resilience (`message_cache_service.py`)**
"To make the infinite-scroll chat lightning fast, I don't hit Postgres every time a user scrolls up. I cache the paginated chat history and session authentication tokens in Redis. I also built resilience into the service: it tries to connect to a high-speed native TCP socket, but if that fails, it gracefully falls back to an Upstash REST API so the application never goes down."

**Natural Language Query Parsing (`nl_query_parser.py`)**
"Users don't write perfect SQL or Vector search queries. I use an LLM layer to take a user's messy natural language question and extract precise metadata filters (e.g., extracting the year '2023', the metric 'EBITDA', or the specific document ID) before querying Qdrant."

**Automated Literature Review & APA Export (`literature_review_service.py` & `apa_export_service.py`)**
"The app can automatically synthesize multiple papers into a cohesive literature review. It tracks exactly which paper contributed which fact, and uses an APA Export service to automatically generate perfectly formatted academic citations for the user."

---

## 6. Advanced Frontend Features

**The Dual-Pane Reader & AI Citations (`components/reader/AdvancedPDFViewer.jsx`)**
"I built a side-by-side interface. On the left is the AI chat, and on the right is a custom PDF viewer using `pdf.js`. When the AI generates an answer, it includes clickable `CitationChips`. When a user clicks a chip, the PDF viewer automatically jumps to the exact page and highlights the source text."

**The TipTap Research Editor (`components/editor/ResearchEditor.jsx`)**
"Users need to save their findings. I integrated **TipTap** as a rich-text editor. As the user chats with the AI, they can easily port the AI's responses, tables, and charts directly into a 'Research Document' for export. TipTap allowed me to render markdown and complex tables beautifully."

**Infinite Scroll Chat (`hooks/useInifiniteMessages.js`)**
"Rendering thousands of chat messages will crash a browser. I built a custom hook that integrates with React Query and the backend Redis cache to allow seamless, virtualized infinite scrolling through chat history."

**Study Plans & Quizzes (`components/study-plan` & `components/quiz`)**
"To make the app more than just a chat bot, I built features where the AI analyzes a document and automatically generates flashcards, quizzes, and structured daily study plans based on the text."

---

## 7. The End-to-End Walkthrough (How Data Flows)

If the interviewer says, *"Walk me through the lifecycle of a PDF upload."*

1.  **Upload:** The user drags a PDF into the Next.js dropzone.
2.  **Queueing:** The FastAPI backend receives it, saves it to Supabase Cloud Storage, creates a 'Pending' database record, and drops a Job ID into the Redis Queue. It instantly tells the frontend "Processing".
3.  **Background Extraction:** A worker picks up the job. It uses PyMuPDF to extract text, tables, and base64 images.
4.  **AI Pipeline:** Images go to GPT-4o-mini to get text captions. Tables are stitched together and normalized.
5.  **Smart Chunking:** The `MarkdownElementNodeParser` splits the document perfectly, ensuring no tables are broken and headers are preserved.
6.  **Vector Storage:** The text, tables, and image captions are embedded into Qdrant using Hybrid Search (Dense Vectors + BM25).
7.  **User Query:** The user asks a question in the chat.
8.  **RAG:** Qdrant retrieves the best text chunks, tables, and image captions. The backend pulls the actual base64 images and sends everything to GPT-4o.
9.  **Streaming & Citations:** The LLM generates the answer, routing math through the Calculation Gate if necessary, and streams the markdown response back to the Next.js frontend, complete with clickable citations.
