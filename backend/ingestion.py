import io
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Callable

from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)

MIN_TEXT_LAYER_CHARS = 40
OCR_RENDER_DPI = 240


class DocumentProcessingError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    extraction_method: str


@dataclass
class ExtractionResult:
    pages: list[ExtractedPage] = field(default_factory=list)
    scanned_pages: int = 0
    warnings: list[str] = field(default_factory=list)


def _readable_ocr_text(text):
    compact = "".join(character for character in text if not character.isspace())
    if len(compact) < 12:
        return False
    alphanumeric_count = sum(character.isalnum() for character in compact)
    return alphanumeric_count >= 8 and alphanumeric_count / len(compact) >= 0.45


def _render_pdf_page(document, page_index):
    import pymupdf

    scale = OCR_RENDER_DPI / 72
    pixmap = document.load_page(page_index).get_pixmap(
        matrix=pymupdf.Matrix(scale, scale),
        alpha=False,
    )
    return pixmap.tobytes("png")


def _vision_ocr(image_bytes):
    from qa_service import extract_page_text_from_image

    return extract_page_text_from_image(image_bytes)


def _tesseract_ocr(image_bytes):
    from PIL import Image
    import pytesseract

    configured_command = os.getenv("VISTAAR_TESSERACT_CMD")
    if configured_command:
        pytesseract.pytesseract.tesseract_cmd = configured_command
    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(
        image,
        timeout=int(os.getenv("VISTAAR_TESSERACT_TIMEOUT_SECONDS", "30")),
    )


def _ocr_page(image_bytes):
    failures = []
    if os.getenv("VISTAAR_OCR_VISION_ENABLED", "true").lower() not in {"0", "false", "no"}:
        try:
            text = _vision_ocr(image_bytes)
            if _readable_ocr_text(text or ""):
                return text.strip(), "gemini_vision", None
            failures.append("Gemini vision returned no readable text")
        except TimeoutError:
            failures.append("Gemini vision OCR timed out")
        except Exception as error:
            code = getattr(error, "code", None)
            if code == 429 or error.__class__.__name__ == "VisionOCRQuotaError":
                failures.append("Gemini vision OCR quota exceeded")
            elif error.__class__.__name__ in {"TimeoutException", "ReadTimeout", "ConnectTimeout"}:
                failures.append("Gemini vision OCR timed out")
            elif isinstance(error, RuntimeError) and "GEMINI_API_KEY" in str(error):
                failures.append("Gemini vision OCR is not configured")
            else:
                failures.append(f"Gemini vision OCR unavailable ({error.__class__.__name__})")
            logger.warning("Gemini vision OCR failed error_type=%s", error.__class__.__name__)

    fallback = os.getenv("VISTAAR_OCR_FALLBACK", "tesseract").strip().lower()
    if fallback == "tesseract":
        try:
            text = _tesseract_ocr(image_bytes)
            if _readable_ocr_text(text or ""):
                return text.strip(), "tesseract", None
            failures.append("Tesseract returned no readable text")
        except TimeoutError:
            failures.append("Tesseract OCR timed out")
        except Exception as error:
            if error.__class__.__name__ == "TesseractTimeoutError":
                failures.append("Tesseract OCR timed out")
            else:
                failures.append(f"Tesseract OCR unavailable ({error.__class__.__name__})")
            logger.warning("Tesseract OCR failed error_type=%s", error.__class__.__name__)
    elif fallback != "none":
        failures.append("VISTAAR_OCR_FALLBACK must be 'tesseract' or 'none'")

    return "", "unavailable", "; ".join(failures) or "No OCR provider is enabled"


def extract_pages(
    content: bytes,
    filename: str,
    on_progress: Callable[[str], None] | None = None,
) -> ExtractionResult:
    if not filename.lower().endswith(".pdf"):
        text = content.decode("utf-8", errors="ignore").strip()
        if not text:
            raise DocumentProcessingError("The uploaded text document is empty or unreadable.")
        return ExtractionResult(pages=[ExtractedPage(1, text, "text")])

    if on_progress:
        on_progress("Extracting text from PDF pages")
    try:
        reader = PdfReader(io.BytesIO(content), strict=False)
        document_text = []
        for page in reader.pages:
            try:
                document_text.append((page.extract_text() or "").strip())
            except Exception as error:
                logger.warning("PDF text extraction failed error_type=%s", error.__class__.__name__)
                document_text.append("")
    except Exception as error:
        raise DocumentProcessingError("This PDF is damaged or could not be opened.") from error

    result = ExtractionResult()
    scan_candidates = [
        index for index, text in enumerate(document_text)
        if len(re.sub(r"\s+", "", text)) < MIN_TEXT_LAYER_CHARS
    ]

    if scan_candidates:
        try:
            import pymupdf

            rendered_pdf = pymupdf.open(stream=content, filetype="pdf")
        except Exception as error:
            raise DocumentProcessingError(
                "The PDF has pages without readable text, and scanned-page rendering is unavailable."
            ) from error

        for page_index in scan_candidates:
            result.scanned_pages += 1
            if on_progress:
                on_progress(f"Processing scanned pages ({page_index + 1} of {len(document_text)})")
            try:
                image_bytes = _render_pdf_page(rendered_pdf, page_index)
            except Exception as error:
                failure = f"Page {page_index + 1}: scanned page rendering failed ({error.__class__.__name__})"
                result.warnings.append(failure)
                if document_text[page_index]:
                    result.pages.append(ExtractedPage(page_index + 1, document_text[page_index], "pdf_text_partial"))
                continue

            ocr_text, method, failure_reason = _ocr_page(image_bytes)
            if ocr_text:
                result.pages.append(ExtractedPage(page_index + 1, ocr_text, method))
            elif document_text[page_index] and _readable_ocr_text(document_text[page_index]):
                result.pages.append(ExtractedPage(page_index + 1, document_text[page_index], "pdf_text_partial"))
                result.warnings.append(
                    f"Page {page_index + 1}: OCR was unavailable; retained the partial PDF text layer."
                )
            else:
                result.warnings.append(
                    f"Page {page_index + 1}: no readable text could be extracted ({failure_reason})."
                )

        rendered_pdf.close()

    scanned_candidate_set = set(scan_candidates)
    for page_index, text in enumerate(document_text):
        if page_index not in scanned_candidate_set and text:
            result.pages.append(ExtractedPage(page_index + 1, text, "pdf_text"))

    result.pages.sort(key=lambda page: page.page_number)
    if not result.pages:
        warning_details = " ".join(result.warnings)
        raise DocumentProcessingError(
            "No readable text could be extracted from this PDF. "
            f"{warning_details or 'The PDF may contain blank, damaged, or unsupported pages.'}"
        )
    return result


def extract_text(content: bytes, filename: str) -> str:
    """Compatibility helper for callers that only need the extracted text."""
    result = extract_pages(content, filename)
    return "\n\n".join(page.text for page in result.pages)
