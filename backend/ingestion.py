import io
from PyPDF2 import PdfReader

def extract_text(content: bytes, filename: str) -> str:
    text = ""

    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    else:
        text = content.decode("utf-8", errors="ignore")

    return text.strip()