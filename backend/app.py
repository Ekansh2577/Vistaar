from fastapi import FastAPI, UploadFile, BackgroundTasks, Request, File, Form
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from schemas import QuestionRequest, WebSearchRequest
from ingestion import extract_text
from background_tasks import process_document
from qa_service import answer_question
from rate_limiter import limiter
from web_search_service import search_web_and_synthesize
from image_service import analyze_image

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
templates = Jinja2Templates(directory="templates")


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/upload")
@limiter.limit("5/minute")
async def upload_document(request: Request, file: UploadFile, bg: BackgroundTasks):
    content = await file.read()
    text = extract_text(content, file.filename)

    if len(text.strip()) < 50:
        return {"message": "PDF text not readable. Try another file."}

    bg.add_task(process_document, text)
    return {"message": "Document uploaded. Processing started, wait a few seconds before asking."}


@app.post("/ask")
@limiter.limit("10/minute")
def ask(request: Request, req: QuestionRequest):
    answer = answer_question(req.question)
    return {"answer": answer}


@app.post("/search/web")
@limiter.limit("10/minute")
def search_web_endpoint(request: Request, req: WebSearchRequest):
    return search_web_and_synthesize(req.query)


@app.post("/ask-image")
@limiter.limit("10/minute")
async def ask_image_endpoint(
    request: Request,
    file: UploadFile = File(...),
    question: str = Form("What is this image about? Describe the key components and any visible text.")
):
    content = await file.read()
    return analyze_image(
        image_bytes=content,
        mime_type=file.content_type or "image/png",
        question=question,
        filename=file.filename or "uploaded_image"
    )
