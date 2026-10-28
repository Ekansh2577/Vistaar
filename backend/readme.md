# RAG-Based Document Question Answering System

A full-stack Retrieval-Augmented Generation (RAG) application that allows users to upload documents and ask natural language questions. The system retrieves relevant content using vector similarity search and generates accurate answers using a language model.

## Live Demo



## Overview

Traditional language models rely only on pretrained knowledge. This project improves response accuracy by retrieving relevant information directly from uploaded documents before generating answers.

The system workflow:

1. Accept user-uploaded documents
2. Extract and process text
3. Generate vector embeddings
4. Store embeddings in a FAISS vector index
5. Retrieve relevant document chunks
6. Generate answers grounded in retrieved context

This enables context-aware and document-specific question answering.


## Features

- Support for PDF and TXT document uploads
- Intelligent document chunking with overlap
- Embedding generation using SentenceTransformers
- Fast similarity search using FAISS
- Answer generation using:
  - Local Transformer models
  - OpenAI API
- Interactive web interface
- Document indexing completes before an upload is reported as ready
- Modular backend architecture



## System Architecture

### Pipeline

```text
User Document
      ↓
Text Extraction
      ↓
Chunking
      ↓
Embeddings
      ↓
FAISS Index
      ↓
Query Processing
      ↓
Relevant Retrieval
      ↓
Language Model
      ↓
Generated Answer
```


## Tech Stack

| Component | Technology |
|---|---|
| Backend API | FastAPI |
| Embeddings | SentenceTransformers |
| Vector Database | FAISS |
| Language Model | Hugging Face Transformers / OpenAI API |
| Frontend | HTML, JavaScript |
| Deployment | Hugging Face Spaces, Cloud, Containers |


## Project Structure

```text
app.py                # FastAPI application entry point
background_tasks.py   # Background document ingestion
ingestion.py          # File text extraction
chunking.py           # Document chunking logic
embeddings.py         # Embedding model wrapper
vector_store.py       # FAISS index management
qa_service.py         # Retrieval and answer generation
templates/index.html  # Frontend interface
```


## Installation

```bash

cd backend

python -m venv venv

# Windows
venv\Scripts\activate


pip install -r requirements.txt

uvicorn app:app --reload
```

Open the application at:

```text
http://127.0.0.1:8000
```

## Authentication

The FastAPI service provides persistent account and session storage in SQLite through SQLAlchemy 2. The database is created at first startup; by default it is `backend/vistaar_auth.sqlite3` and is excluded from Git. Set `VISTAAR_AUTH_DB` in `backend/.env` to choose another absolute or backend-relative path. Passwords are hashed with Argon2id through `pwdlib`; sessions use random opaque tokens stored only as SHA-256 hashes in SQLite and are sent to the browser in HttpOnly cookies.

The `users` table contains `id`, `full_name`, unique normalized `email`, `password_hash`, and `created_at`. SQLAlchemy's `create_all` initializes missing tables idempotently and retains existing rows in the same SQLite file.

Copy `.env.example` to `.env` and configure:

- `VISTAAR_AUTH_DB`: SQLite file path.
- `VISTAAR_ENV=production` or `VISTAAR_COOKIE_SECURE=true` when serving over HTTPS. The cookie defaults to Secure in production and non-Secure for local HTTP development.
- `VISTAAR_COOKIE_SAMESITE=lax` for the Vite proxy/same-site deployment. For a truly cross-site frontend, configure HTTPS, `VISTAAR_COOKIE_SECURE=true`, and `VISTAAR_COOKIE_SAMESITE=none`.
- `VISTAAR_CORS_ORIGINS`: comma-separated exact frontend origins when the frontend calls a separate API origin; configure this explicitly in production. Development automatically trusts only `http://localhost:5173` and `http://127.0.0.1:5173` for the Vite proxy. Browser requests use credentials.
- `VISTAAR_FRONTEND_URL`, `VISTAAR_SMTP_HOST`, `VISTAAR_SMTP_PORT`, `VISTAAR_SMTP_USERNAME`, `VISTAAR_SMTP_PASSWORD`, and `VISTAAR_SMTP_FROM` to enable email-based password recovery. Recovery returns an explicit configuration error until SMTP is set up.

Available endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/auth/register` | Register and start a session |
| `POST` | `/auth/login` | Validate credentials and start a session |
| `GET` | `/auth/me` | Get the current session user |
| `POST` | `/auth/logout` | Revoke the current session |
| `POST` | `/auth/forgot-password` | Send a one-time recovery link (SMTP required) |
| `POST` | `/auth/reset-password` | Set a new password with a valid recovery token |
| `GET` | `/upload/{job_id}` | Get authenticated extraction/OCR/indexing status |

Registration/login bodies use `email` and `password`; registration also requires `full_name`. Passwords must be 8–128 characters. The `/upload`, `/ask`, `/search/web`, and `/ask-image` endpoints require a valid session cookie. FAISS indices are isolated by user in memory. Frontend uploaded-item lists and chat history use per-user browser storage keys; passwords and session tokens are never stored there.

Backend auth tests: install test dependencies with `python -m pip install -r requirements-dev.txt`, then run `python -m pytest tests` from `backend/`.

---

## Retrieval Process

- Documents are divided into 1000-character chunks with 200-character overlap
- Each chunk is converted into a 384-dimensional `all-MiniLM-L6-v2` embedding
- User queries use the same loaded embedding model and vector dimensions
- FAISS `IndexFlatL2` returns nearest chunks in ascending L2 distance (lower is closer)
- Retrieval logs include index and result counts, chunk IDs, distances, source filenames, and short redacted previews
- The language model receives labeled document evidence and is instructed to cite filenames (and page numbers when available)
- The upload dialog polls job status and only marks a document ready after extraction, chunking, embeddings, and indexing finish

FAISS indices and chunk metadata are isolated by authenticated user but kept in process memory; they are cleared when the backend process restarts.

### Scanned and handwritten PDFs

The PDF extractor first reads each page's existing text layer. Pages with fewer than 40 non-whitespace characters are treated as possible scans, rendered at 240 DPI with PyMuPDF, and passed to Gemini vision OCR. OCR text is quality-checked and indexed as independent page-level chunks; FAISS metadata retains the filename, stable document ID, page number, and extraction method.

Gemini OCR uses the existing `GEMINI_API_KEY` from `backend/.env`; the key is never sent to or stored in the frontend. By default, OCR tries the existing Gemini model fallback list. Set `VISTAAR_OCR_VISION_MODEL` to pin a model, `VISTAAR_OCR_VISION_ENABLED=false` to disable vision, or `VISTAAR_OCR_FALLBACK=none` to disable local fallback. The default local fallback is Tesseract. Install the Tesseract executable separately and set `VISTAAR_TESSERACT_CMD` if it is not on `PATH`; `VISTAAR_TESSERACT_TIMEOUT_SECONDS` defaults to 30. Gemini request timeouts are controlled by `VISTAAR_GEMINI_TIMEOUT_SECONDS` (default 45).

Install the Python dependencies with:

```powershell
cd backend
python -m pip install -r requirements.txt
```

Tesseract is optional when Gemini vision is available. If desired, install it with `winget install UB-Mannheim.TesseractOCR` and configure `VISTAAR_TESSERACT_CMD` in `backend/.env` if needed. If all OCR providers fail, the upload job reports the affected page numbers and OCR limitation instead of indexing empty or unreadable text. If only some pages are readable, those pages are indexed and the upload status includes warnings for the others.

Each upload receives a stable per-user ID derived from its filename and content; retrying the same upload does not add duplicate FAISS vectors.

### Benefits

- Improved factual accuracy
- Better contextual grounding
- Domain-specific adaptability
- Reduced hallucinations



## Performance Considerations

- Background processing avoids blocking the user interface
- FAISS enables efficient large-scale vector similarity search
- Initial latency mainly comes from model loading
- Architecture designed for scalable document-based AI systems


## Deployment Options

This project can be deployed using:

- Hugging Face Spaces
- Cloud virtual machines
- Containerized FastAPI services
- Render
- Railway


## Use Cases

- Research paper question answering
- Legal and policy document analysis
- Internal company knowledge bases
- Educational assistants
- Resume and report analysis
