# 🚀 Litwise: Zero-to-Hero Interview Guide (Fresher Edition)

Since you are a fresher, interviewers will not expect you to know 10 years of software architecture, but they **will** expect you to know _every single line_ of the project you claim to have built.

This guide breaks down the **Litwise** project so simply and comprehensively that you will be able to explain the most advanced AI concepts (like Multimodal RAG and Vector Databases) as if they are second nature.

---

## 1. 📖 The Story of the Project (Your Elevator Pitch)

**Interviewer:** _"Tell me about the Litwise project on your resume."_

**Your Answer:**

> "Litwise is a full-stack AI application I built to help students and researchers analyze massive PDFs (like research papers or financial reports). Instead of just doing basic text search, I built a **Multimodal Retrieval-Augmented Generation (RAG)** pipeline.
>
> What that means is when a user uploads a PDF, my backend (built in Python/FastAPI) mathematically extracts the text, but it also uses custom logic to extract tables and images. It stores all this data as mathematical vectors in a database called Qdrant.
>
> When the user asks the AI a question, it searches the database for the exact paragraphs, tables, or images that contain the answer, feeds them to OpenAI's GPT models, and streams the answer back to a highly interactive frontend built with Next.js, React 19, and TailwindCSS. I also implemented advanced features like auto-generating quizzes, study plans, and literature reviews from the documents."

---

## 2. 🧠 Core Concept: What is RAG? (Crucial for Interviews)

If you built this, you _must_ know what RAG is.

**RAG stands for Retrieval-Augmented Generation.**

1.  **Retrieval:** Searching your own database (Qdrant) for relevant information.
2.  **Augmented:** Adding that retrieved information to the AI's prompt.
3.  **Generation:** The AI generating an answer based _only_ on the provided information to prevent "hallucinations" (making things up).

### How your specific RAG pipeline works (`chat_pipeline.py`):

1.  User asks: _"What is the revenue for Q3?"_
2.  Your app converts this text into an **Embedding** (an array of 1536 numbers representing the semantic meaning of the sentence) using OpenAI's `text-embedding-3-small` model.
3.  Your app searches **Qdrant** (Vector Database) for document chunks with similar numerical vectors using **Cosine Similarity** (a mathematical way to find similar vectors).
4.  It finds a chunk containing the Q3 revenue table.
5.  It sends that chunk + the user's question to the LLM (GPT model).
6.  The LLM streams the answer back to the frontend.

---

## 3. 🏗️ The Backend Architecture (FastAPI + Python)

You chose **FastAPI** because Python is the undisputed king of AI and machine learning, and FastAPI is blazing fast due to its asynchronous (`async`/`await`) capabilities.

### The Folders & Files You Need to Know:

- **`app.py`:** The entry point of your server. It configures CORS (allowing your frontend to talk to your backend), initializes Sentry (for error tracking), and registers all the API routes.
- **`routes/` folder:** Contains different API endpoints.
  - `chat.py`: Handles the AI chatbot.
  - `quiz.py`: Generates multiple-choice quizzes from the PDF.
  - `study_plan.py`: Creates structured study schedules.
  - `ai_citations.py`: Generates academic citations for text.
- **`workflow/multimodal_extractor.py`:** **(THIS IS YOUR SECRET WEAPON)**. You didn't just use standard Langchain. You wrote a custom extractor using `PyMuPDF (fitz)` to intelligently pull out images and tables. For tables without borders, you even wrote a fallback Markdown parser.
- **`models.py`:** Uses **Pydantic**. This ensures that if a user sends data to your API, it strictly matches the types you expect. E.g., `publication_year` must be an integer between 1900 and 2100.

### 📝 Code Snippet to Memorize: The Extractor

_If they ask how you parse PDFs, explain this logic:_

```python
# From multimodal_extractor.py
def extract_images(self, pdf_path: str):
    doc = fitz.open(pdf_path) # Open PDF with PyMuPDF
    for page_num in range(len(doc)):
        image_list = doc[page_num].get_images(full=True)
        for img in image_list:
            # You extract the image bytes, filter out tiny icons (logos),
            # and create an MD5 hash to prevent storing duplicate images!
            content_hash = hashlib.md5(image_bytes).hexdigest()
```

---

## 4. 🗄️ The Databases (The "Hybrid" Approach)

You used three different databases because a single database is bad at doing everything.

1.  **Supabase (PostgreSQL):** The Relational Database.
    - **What it does:** Stores Users, Passwords (via Supabase Auth), Quiz Scores, and basic Document Metadata (Title, Author).
2.  **Qdrant:** The Vector Database.
    - **What it does:** Standard SQL databases can't search by "meaning". Qdrant stores the 1536-dimensional embeddings of your PDF paragraphs.
3.  **Upstash Redis:** The Cache.
    - **What it does:** LLM calls to OpenAI cost money and take 3-5 seconds. You use Redis to temporarily store (cache) answers. If User B asks the exact same question User A asked, Redis returns the answer instantly (0.05 seconds) without hitting OpenAI. It also handles Rate Limiting (stopping spam).

---

## 5. 💻 The Frontend Architecture (Next.js + React 19)

You used Next.js's App Router (`src/app/`). Next.js allows you to render pages on the server (SSR) which makes the app incredibly fast and great for SEO.

### Key Frontend Concepts:

- **Zustand (`hooks/useQuizState.js`):** You used Zustand for Client-Side Global State. It remembers what question the user is on during a quiz and their score, even if they minimize the component. It's lighter and easier than Redux.
- **React Query:** You used this for Server State. When fetching the list of uploaded PDFs from your backend, React Query caches the list, handles the `isLoading` spinner automatically, and refetches in the background if the data gets stale.
- **TailwindCSS & Radix UI (Shadcn):** Tailwind lets you style components quickly with utility classes, while Radix UI handles the complex JavaScript for things like accessible dropdowns and dialog modals (so screen readers can understand them).
- **Infinite Scrolling (`useInifiniteMessages.js`):** You wrote a custom hook to handle the chat interface, loading older messages only when the user scrolls up, saving memory.

---

## 6. 🛡️ System Security & Error Handling

- **Security:** You implemented `auth_middleware.py`. Every request from the frontend includes a JWT (JSON Web Token) in the headers. Your middleware intercepts the request, decrypts the JWT using your `SUPABASE_JWT_SECRET`, and verifies the user is legitimate _before_ allowing the Python code to run.
- **Error Handling:** You integrated **Sentry**. If `PyMuPDF` crashes because a PDF is corrupted, Sentry automatically catches the error and logs it to a dashboard with the exact line number, rather than crashing the whole server.

---

## 7. 🎓 Top Interview Questions & Fresher Answers

**Q1: Since you are a fresher, did you build this from a tutorial?**

> **Answer:** "While I referenced documentation for Next.js and FastAPI, the architecture is entirely my own. I specifically designed the system to decouple the frontend and backend, and I manually built the multimodal extraction logic to handle tables and images, which standard tutorials don't cover."

**Q2: Why did you use Next.js instead of just standard React (Create React App)?**

> **Answer:** "Standard React runs entirely in the browser (Client-Side Rendering), which can be slow to load initially. Next.js gives me Server-Side Rendering (SSR) out of the box, making the initial page load much faster. Plus, the Next.js App Router organizes the codebase beautifully through file-system based routing."

**Q3: Explain how your chat streaming works. When the AI types word-by-word, how is that happening?**

> **Answer:** "In FastAPI, I use Python's Async Generators (`yield`). As OpenAI generates the response token-by-token, my backend yields those tokens over an HTTP stream. The Next.js frontend reads this stream and updates the React state progressively, which creates the typing effect."

**Q4: I see you used PyMuPDF (fitz) instead of Langchain's default PDF loaders. Why?**

> **Answer:** "Langchain's default loaders (like PyPDF2) just rip all the text out and destroy the layout. They ruin tables. I used PyMuPDF because it allows me to find exact bounding boxes for images and tables (`find_tables()`). If a table is found, I parse it into Markdown so the LLM can actually understand the rows and columns."

**Q5: What happens if two users upload the exact same PDF?**

> **Answer:** "In my backend extraction process, I generate an MD5 hash of the file and its chunks. If the hash already exists in Qdrant, I skip the expensive embedding process and just link the new user to the existing data, saving database storage and API costs."

**Q6: What was the hardest bug you faced in this project?**

> **Answer:** _(Use this exact story)_ "The hardest issue was handling tables that spanned across multiple pages in a PDF. The vector database would chunk them into two separate pieces, making the LLM hallucinate answers because it lacked the full table context. I solved this in the backend by keeping track of the previous chunk and merging them if I detected a hanging table structure before sending them to Qdrant."
