import hashlib
import logging
import time
from threading import RLock
from uuid import uuid4

from fastapi import FastAPI, UploadFile, Request, File, Form, Depends, BackgroundTasks, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from schemas import QuestionRequest, WebSearchRequest
from ingestion import DocumentProcessingError, extract_pages
from background_tasks import process_document
from qa_service import answer_question_with_sources
from rate_limiter import limiter
from web_search_service import search_web_and_synthesize
from image_service import analyze_image
from auth import allowed_frontend_origins, get_current_user, router as auth_router
from vector_store import document_chunk_count, has_indexed_document, set_document_status

logger = logging.getLogger(__name__)
_upload_jobs = {}
_upload_jobs_lock = RLock()

app = FastAPI()
allowed_origins = allowed_frontend_origins()
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
templates = Jinja2Templates(directory="templates")
app.include_router(auth_router)


def _set_upload_job(job_key, **values):
    with _upload_jobs_lock:
        _upload_jobs[job_key].update(values)


def _process_upload_job(job_key, content, user_id, source_filename, document_id):
    stage = "Extracting text"
    set_document_status(
        document_id,
        source_filename,
        "processing",
        user_id=user_id,
    )
    try:
        if has_indexed_document(document_id, user_id=user_id):
            set_document_status(
                document_id,
                source_filename,
                "ready",
                user_id=user_id,
                indexed_chunks=document_chunk_count(document_id, user_id=user_id),
            )
            _set_upload_job(
                job_key,
                status="ready",
                stage="Ready",
                indexed_chunks=document_chunk_count(document_id, user_id=user_id),
                duplicate=True,
                message="This document was already indexed and is ready for questions.",
                warnings=[],
            )
            return

        extraction = extract_pages(
            content,
            source_filename,
            on_progress=lambda message: _set_upload_job(job_key, stage=message),
        )
        stage = "Indexing"
        indexed = process_document(
            extraction.pages,
            user_id,
            source_filename,
            document_id=document_id,
            on_progress=lambda message: _set_upload_job(job_key, stage=message),
        )
        set_document_status(
            document_id,
            source_filename,
            "ready",
            user_id=user_id,
            indexed_chunks=indexed["indexed_chunks"],
            pages=len(extraction.pages),
            scanned_pages=extraction.scanned_pages,
            warnings=extraction.warnings,
        )
        _set_upload_job(
            job_key,
            status="ready",
            stage="Ready",
            indexed_chunks=indexed["indexed_chunks"],
            pages=len(extraction.pages),
            scanned_pages=extraction.scanned_pages,
            warnings=extraction.warnings,
            duplicate=indexed["duplicate"],
            message="Document indexed and ready for questions.",
        )
    except DocumentProcessingError as error:
        set_document_status(
            document_id,
            source_filename,
            "failed",
            user_id=user_id,
            error=str(error),
        )
        _set_upload_job(job_key, status="failed", stage="Failed", error=str(error))
    except Exception as error:
        logger.error(
            "Document processing failed job_id=%s stage=%s error_type=%s",
            job_key[1],
            stage,
            error.__class__.__name__,
        )
        if stage == "Indexing":
            detail = f"Document indexing failed ({error.__class__.__name__}). Check the embedding model and backend configuration."
        else:
            detail = f"Document extraction failed ({error.__class__.__name__}). Check that the PDF is valid and OCR is configured."
        set_document_status(
            document_id,
            source_filename,
            "failed",
            user_id=user_id,
            error=detail,
        )
        _set_upload_job(job_key, status="failed", stage="Failed", error=detail)


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/upload", status_code=202)
@limiter.limit("5/minute")
async def upload_document(
    request: Request,
    file: UploadFile,
    bg: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    source_filename = file.filename or "uploaded document"
    extension = source_filename.lower().rsplit(".", 1)[-1] if "." in source_filename else ""
    if extension not in {"pdf", "txt", "md", "json", "csv"}:
        raise HTTPException(status_code=415, detail="Unsupported file type. Upload a PDF or UTF-8 text document.")

    content = await file.read()
    user_id = str(user["id"])
    document_id = hashlib.sha256(
        user_id.encode("utf-8") + b"\0" + source_filename.encode("utf-8") + b"\0" + content
    ).hexdigest()
    job_id = uuid4().hex
    job_key = (user_id, job_id)
    with _upload_jobs_lock:
        now = time.monotonic()
        expired_jobs = [
            key for key, value in _upload_jobs.items()
            if value.get("status") != "processing"
            and now - value.get("_created_at", now) > 30 * 60
        ]
        for expired_key in expired_jobs:
            _upload_jobs.pop(expired_key, None)
        _upload_jobs[job_key] = {
            "status": "processing",
            "stage": "Extracting text",
            "filename": source_filename,
            "document_id": document_id,
            "_created_at": now,
        }
    bg.add_task(
        _process_upload_job,
        job_key,
        content,
        user_id,
        source_filename,
        document_id,
    )
    return {"job_id": job_id, "status": "processing", "message": "Document processing started."}


@app.get("/upload/{job_id}")
def upload_status(job_id: str, user: dict = Depends(get_current_user)):
    job_key = (str(user["id"]), job_id)
    with _upload_jobs_lock:
        job = _upload_jobs.get(job_key)
        if job is None:
            raise HTTPException(status_code=404, detail="Upload job not found or expired.")
        public_fields = {
            "status",
            "stage",
            "filename",
            "error",
            "indexed_chunks",
            "pages",
            "scanned_pages",
            "warnings",
            "duplicate",
            "message",
        }
        return {key: value for key, value in job.items() if key in public_fields}


@app.post("/ask")
@limiter.limit("10/minute")
def ask(request: Request, req: QuestionRequest, user: dict = Depends(get_current_user)):
    return answer_question_with_sources(req.question, str(user["id"]))


@app.post("/search/web")
@limiter.limit("10/minute")
def search_web_endpoint(request: Request, req: WebSearchRequest, user: dict = Depends(get_current_user)):
    return search_web_and_synthesize(req.query)


@app.post("/ask-image")
@limiter.limit("10/minute")
async def ask_image_endpoint(
    request: Request,
    file: UploadFile = File(...),
    question: str = Form("What is this image about? Describe the key components and any visible text."),
    user: dict = Depends(get_current_user),
):
    content = await file.read()
    return analyze_image(
        image_bytes=content,
        mime_type=file.content_type or "image/png",
        question=question,
        filename=file.filename or "uploaded_image"
    )
