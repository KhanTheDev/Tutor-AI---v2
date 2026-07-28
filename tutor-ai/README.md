# Tutor AI Platform

A demo-ready MVP that lets students create courses, upload PDF/TXT materials, and ask questions answered **only** from those materials using Retrieval-Augmented Generation (RAG).

## Project Overview

Tutor AI Platform is a local Flask application for course-aware tutoring. Each course keeps its own documents, embeddings, and chat history. When a student asks a question, the system retrieves the most relevant chunks from that course's uploaded materials and sends them to OpenAI with strict grounding instructions.

## Main Features

- Create and manage courses
- Upload PDF and TXT course materials
- Extract, clean, and chunk document text
- Generate OpenAI embeddings and store them in ChromaDB
- Ask questions with AJAX chat (no page reload)
- Receive grounded answers with document and page citations
- View chat history per course
- Delete documents or entire courses safely

## Technology Stack

- Python 3
- Flask
- SQLite + SQLAlchemy
- OpenAI API (embeddings)
- Groq API (chat)
- ChromaDB (persistent vector storage)
- PyMuPDF (PDF text extraction)
- HTML, CSS, Vanilla JavaScript
- Bootstrap 5

## Architecture

```text
Student uploads a document
        ↓
Flask saves the document
        ↓
PyMuPDF extracts the text
        ↓
Text is cleaned and divided into chunks
        ↓
OpenAI creates embeddings
        ↓
ChromaDB stores chunks and metadata
        ↓
Student submits a question
        ↓
The question is embedded
        ↓
ChromaDB retrieves relevant course chunks
        ↓
Retrieved chunks are sent to the language model
        ↓
The model generates an answer using only those chunks
        ↓
The application displays the answer and sources
```

## RAG Workflow

1. **Ingestion** — PDF/TXT files are saved and parsed page by page.
2. **Chunking** — Text is split into ~1000-character chunks with ~200-character overlap.
3. **Embedding** — Each chunk is converted to a vector using `text-embedding-3-small`.
4. **Storage** — Chunks, metadata, and embeddings are stored in ChromaDB with course/document IDs.
5. **Retrieval** — The student's question is embedded and matched against chunks filtered by `course_id`.
6. **Generation** — Top chunks are included in the prompt with source labels; the model answers using only those materials.
7. **Citation** — Document name and page number metadata are shown under each answer.

## Folder Structure

```text
tutor-ai/
├── app.py
├── config.py
├── models.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── database/
│   └── tutor_ai.db
├── uploads/
├── chroma_data/
├── services/
│   ├── __init__.py
│   ├── document_processor.py
│   ├── embedding_service.py
│   ├── retrieval_service.py
│   └── tutor_service.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── course.html
│   └── error.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── app.js
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

Edit `.env`:

```env
OPENAI_API_KEY=your_key_here
SECRET_KEY=your_secret_key
```

### 4. Run the application

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

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

"Each course has its own SQLite records, uploaded files, ChromaDB metadata filter, and chat history. That prevents a Calculus document from appearing in a Data Structures answer."

### 3. Upload and processing

"When a student uploads a PDF or TXT file, Flask saves it with a UUID filename, creates a database record, extracts text, chunks it, embeds it, and stores everything in ChromaDB. The document status moves from processing to ready."

### 4. Chunking

"Long pages are split into chunks of about 1000 characters with overlap so context isn't lost at boundaries. Each chunk stores course ID, document ID, filename, page number, and chunk index."

### 5. Embeddings

"Embeddings turn text into numeric vectors that capture meaning. Similar questions and similar content end up close together in vector space, which makes semantic search possible."

### 6. Why ChromaDB

"ChromaDB gives persistent local vector storage with metadata filtering. For an MVP demo, it's lightweight, easy to run locally, and supports course-level isolation through metadata."

### 7. Retrieval

"When a student asks a question, the question is embedded and ChromaDB returns the top matching chunks for that course only. Duplicate or near-duplicate chunks are removed before prompting."

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
| Upload fails immediately | Unsupported file type | Use `.pdf` or `.txt` only |
| File too large | Exceeds 25 MB limit | Upload a smaller file |
| Document status `failed` | Empty PDF/text extraction issue | Try a different PDF or TXT with selectable text |
| Chat says no processed documents | No ready documents | Upload materials and wait for `ready` status |
| ChromaDB errors on first run | Missing folder permissions | Ensure `chroma_data/` exists and is writable |
| Module not found | Virtual env not activated | Activate venv and run `pip install -r requirements.txt` |

## License

Demo/educational MVP — use and modify freely for learning and interviews.
