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
- Background document ingestion
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

---

## Retrieval Process

- Documents are divided into approximately 500-character chunks with overlap
- Each chunk is converted into a dense vector embedding
- User queries are embedded into the same vector space
- Similarity search retrieves the most relevant chunks
- The language model generates answers using retrieved context only

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