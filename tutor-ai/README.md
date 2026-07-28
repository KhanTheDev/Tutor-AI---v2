# Tutor AI Platform

A demo-ready MVP that lets students create courses, upload PDF/TXT materials, and ask questions answered **only** from those materials using Retrieval-Augmented Generation (RAG).

## Project Overview

Tutor AI Platform is a course-aware tutoring app deployed as a single Vercel project with two parts living side by side:

- **`app.py` + `api/`** — a Flask JSON API. No server-rendered HTML — every route under `/api/*` returns JSON.
- **`index.html`, `course.html`, `static/`** — a static HTML/CSS/vanilla-JS frontend, served directly by Vercel and calling the API via same-origin `fetch()` (see `static/js/config.js`).

`vercel.json` routes `/api/*` to the Python function and lets Vercel serve everything else as static files, so there's no CORS to manage — frontend and backend share one domain. Each course keeps its own documents, embeddings, and chat history. When a student asks a question, the API retrieves the most relevant chunks from that course's uploaded materials and sends them to the language model with strict grounding instructions.

## Main Features

- Create and manage courses (manual form or one-click default subjects)
- Upload PDF, TXT, and image (JPG/PNG) course materials
- Extract, clean, and chunk document text
- Generate OpenAI embeddings and store them in Postgres (pgvector)
- Ask questions via a JSON API, called from the static frontend with `fetch()`
- Receive grounded answers with document and page citations
- View chat history per course
- Delete documents or entire courses safely

## Technology Stack

**Backend (`app.py`, `api/`, `services/`):**
- Python 3, Flask (JSON API only — no server-rendered HTML)
- Postgres + pgvector, via SQLAlchemy (e.g. a free [Neon](https://neon.tech) database)
- Flask-CORS (harmless same-origin default; useful if you ever split the frontend out again)
- OpenAI API (embeddings), Groq API (chat)
- PyMuPDF (PDF text extraction)

**Frontend (`index.html`, `course.html`, `static/`):**
- Static HTML + CSS, vanilla JavaScript (no build step, no framework)
- Talks to the backend via `fetch()` against `window.API_BASE` (empty string = same origin)

## Architecture

```text
Student uploads a document
        ↓
The file is read into memory (never written to disk)
        ↓
PyMuPDF extracts the text
        ↓
Text is cleaned and divided into chunks
        ↓
OpenAI creates embeddings
        ↓
Chunks + embeddings are stored in Postgres (pgvector)
        ↓
Student submits a question
        ↓
The question is embedded
        ↓
pgvector retrieves the closest course chunks (cosine distance)
        ↓
Retrieved chunks are sent to the language model
        ↓
The model generates an answer using only those chunks
        ↓
The application displays the answer and sources
```

## RAG Workflow

1. **Ingestion** — PDF/TXT/image files are parsed page by page, entirely in memory.
2. **Chunking** — Text is split into ~1000-character chunks with ~200-character overlap.
3. **Embedding** — Each chunk is converted to a vector using `text-embedding-3-small`.
4. **Storage** — Chunks, metadata, and embeddings are stored as rows in a Postgres `chunks` table (pgvector).
5. **Retrieval** — The student's question is embedded and matched against chunks filtered by `course_id`, ordered by cosine distance.
6. **Generation** — Top chunks are included in the prompt with source labels; the model answers using only those materials.
7. **Citation** — Document name and page number metadata are shown under each answer.

## Deployment (Vercel — frontend + backend together)

Everything deploys as one Vercel project. `vercel.json` routes `/api/*` to the Python function (`api/index.py`) and serves `index.html`, `course.html`, and `static/` directly as static files — same origin, no CORS needed.

1. Create a free Postgres database (e.g. [Neon](https://neon.tech)) and copy its connection string.
2. New Vercel project → set the project's root directory to `tutor-ai`.
3. Set environment variables: `OPENAI_API_KEY`, `GROQ_API_KEY`, `SECRET_KEY`, `DATABASE_URL`.
4. Deploy. On first boot the app runs `CREATE EXTENSION IF NOT EXISTS vector` and creates its tables automatically.

`static/js/config.js` sets `window.API_BASE = ""` — leave it empty for this same-origin setup. Only change it if you ever split the frontend out to a different host again.

Note: Vercel's Hobby plan limits request body size and function duration, so very large uploads or slow embedding calls may need a higher plan.

## Folder Structure

```text
Updated Tutor AI/
└── tutor-ai/                    # Vercel project root
    ├── api/
    │   └── index.py             # Vercel entrypoint (imports app.py's Flask app)
    ├── app.py                   # JSON API routes
    ├── config.py
    ├── models.py
    ├── vercel.json              # /api/* -> function, everything else -> static
    ├── requirements.txt
    ├── .env.example
    ├── dev_server.py            # local-only: serves frontend + API together
    ├── index.html
    ├── course.html
    ├── services/
    │   ├── __init__.py
    │   ├── document_processor.py
    │   ├── embedding_service.py
    │   ├── retrieval_service.py
    │   └── tutor_service.py
    └── static/
        ├── css/templatemo-621-luminary-style.css
        ├── js/config.js         # set window.API_BASE here
        ├── js/utils.js
        ├── js/dashboard.js      # index.html logic
        ├── js/course.js         # course.html logic
        └── img/hero-notes.jpg
```

## Setup Instructions

### 1. Create a virtual environment

```bash
python -m venv venv
```

Mac or Linux:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example file and add your keys:

```bash
cp .env.example .env
```

Edit `.env` with your OpenAI/Groq keys, a secret key, and a Postgres connection
string with pgvector available (a free [Neon](https://neon.tech) database
works for local dev too — there's no SQLite fallback, since the app is meant
to run the same way locally and in production):

```env
OPENAI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

### 4. Run it locally

```bash
python dev_server.py
```

This serves the frontend (`/`, `/course.html`, `/static/*`) *and* the API (`/api/*`) together on `http://127.0.0.1:5000`, the same way Vercel serves them together in production. `dev_server.py` is dev-only — it's not what runs on Vercel (that's `api/index.py`), so nothing here needs to change before deploying.

If you ever want to run just the bare API (no frontend), `python app.py` does that on its own.

## Example Usage

1. Create a course named **Data Structures**.
2. Upload:
   - One textbook chapter PDF
   - One lecture PDF
   - One TXT notes file
3. Wait for document status to become **ready**.
4. Ask questions such as:
   - What is the difference between BFS and DFS?
   - How does a queue work in breadth-first search?
   - What is the time complexity of binary search?
   - Explain recursion using the uploaded lecture notes.
   - What topics should I review before the exam?
5. If the answer is not in the materials, the tutor returns the fallback message.

## Testing Data Suggestions

Use short PDFs or TXT files for faster demo processing. Good test content includes definitions, algorithm explanations, and page-specific examples so citations are visible during the demo.

## Known Limitations

- Document processing runs synchronously during upload (fine for MVP demos).
- No user authentication or multi-student accounts.
- No background job queue for large files.
- Retrieval quality depends on chunking and uploaded content quality.
- Only PDF and TXT files are supported.

## Future Improvements

- Async/background document processing
- User authentication and roles
- Support for DOCX and web page imports
- Re-ranking retrieved chunks
- Streaming chat responses
- Better duplicate detection across pages
- Admin dashboard and usage analytics

## Interview Demo Script

Use this script when presenting the project in an interview. It reflects only features that exist in this MVP.

### 1. Problem

"Students often have scattered course materials — textbooks, slides, and notes — and need fast, trustworthy answers tied to their specific class content. Generic AI tools can hallucinate or mix subjects together."

### 2. Why courses are separated

"Each course has its own Postgres records, chunk rows, and chat history, all filtered by `course_id`. That prevents a Calculus document from appearing in a Data Structures answer."

### 3. Upload and processing

"When a student uploads a PDF, TXT, or image file, Flask reads it into memory, creates a database record, extracts text, chunks it, embeds it, and stores the chunks and embeddings as rows in Postgres. Nothing is written to disk. The document status moves from processing to ready."

### 4. Chunking

"Long pages are split into chunks of about 1000 characters with overlap so context isn't lost at boundaries. Each chunk stores course ID, document ID, filename, page number, and chunk index."

### 5. Embeddings

"Embeddings turn text into numeric vectors that capture meaning. Similar questions and similar content end up close together in vector space, which makes semantic search possible."

### 6. Why Postgres + pgvector

"Since the app runs on Vercel's serverless functions, there's no writable local disk to persist a vector database on — everything has to live in an external, always-on store. Postgres with the pgvector extension covers both the relational data and the vector search in one database, so there's only one connection string to manage."

### 7. Retrieval

"When a student asks a question, the question is embedded and pgvector returns the top matching chunks for that course only, ordered by cosine distance. Duplicate or near-duplicate chunks are removed before prompting."

### 8. Reducing hallucinations

"The system prompt tells the model to use only provided sources, avoid outside knowledge, and explicitly say when the answer isn't found. Sources are passed in labeled blocks with document name and page number."

### 9. Citations

"Citations come from chunk metadata, not from model imagination. The UI shows badges like `Lecture 7.pdf — Page 4` under each tutor response."

### 10. Technical challenges

"Balancing chunk size and overlap, handling empty PDF text extraction, keeping course isolation in vector search, and providing useful fallback behavior when retrieval finds nothing."

### 11. Next improvements

"I'd add background processing for large uploads, streaming responses, better re-ranking, and authentication if this moved beyond a local demo."

## Common Errors and Fixes

| Error | Likely Cause | Fix |
|------|--------------|-----|
| `OPENAI_API_KEY is not configured` | Missing `.env` value | Add your API key to `.env` and restart |
| `DATABASE_URL is not configured` | Missing/empty `.env` value | Add a Postgres connection string to `.env` |
| Upload fails immediately | Unsupported file type | Use `.pdf`, `.txt`, `.jpg`, or `.png` only |
| File too large | Exceeds 4 MB limit (kept under Vercel's request body limit) | Upload a smaller file |
| Document status `failed` | Empty PDF/text extraction issue | Try a different PDF or TXT with selectable text |
| Chat says no processed documents | No ready documents | Upload materials and wait for `ready` status |
| `extension "vector" is not available` | Postgres provider doesn't have pgvector installed | Use a provider that supports it (Neon does) |
| Module not found | Virtual env not activated | Activate venv and run `pip install -r requirements.txt` |
| Frontend shows "Couldn't load courses" | `API_BASE` wrong, or API not running/deployed | Check `static/js/config.js` — should be `""` for same-origin |

## License

Demo/educational MVP — use and modify freely for learning and interviews.
