import io

import pymupdf
import pytest
from PIL import Image, ImageDraw

import ingestion
from background_tasks import process_document
from vector_store import (
    document_chunk_count,
    document_status_by_user,
    has_indexed_document,
    indexed_document_ids_by_user,
    indices,
    retrieve,
    stored_chunks_by_user,
)


@pytest.fixture(autouse=True)
def clear_vector_state():
    indices.clear()
    stored_chunks_by_user.clear()
    indexed_document_ids_by_user.clear()
    document_status_by_user.clear()
    yield
    indices.clear()
    stored_chunks_by_user.clear()
    indexed_document_ids_by_user.clear()
    document_status_by_user.clear()


def _printed_scan_pdf():
    image = Image.new("RGB", (1200, 1600), "white")
    draw = ImageDraw.Draw(image)
    draw.text((80, 100), "Association Rule Mining Apriori", fill="black")
    image_buffer = io.BytesIO()
    image.save(image_buffer, format="PNG")

    pdf = pymupdf.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_image(page.rect, stream=image_buffer.getvalue())
    return pdf.tobytes()


def _mixed_pdf():
    pdf = pymupdf.open()
    native_page = pdf.new_page()
    native_page.insert_textbox(
        pymupdf.Rect(50, 50, 550, 240),
        (
            "This page contains a readable digital text layer with sufficient content. "
            "Association Rule Mining is a method for discovering relationships between items."
        ),
    )
    scanned_page = pdf.new_page(width=612, height=792)
    scanned_page.insert_image(scanned_page.rect, stream=_printed_scan_pdf_image())
    return pdf.tobytes()


def _printed_scan_pdf_image():
    image = Image.new("RGB", (1200, 1600), "white")
    ImageDraw.Draw(image).text((80, 100), "Apriori frequent itemsets", fill="black")
    image_buffer = io.BytesIO()
    image.save(image_buffer, format="PNG")
    return image_buffer.getvalue()


def test_ordinary_text_pdf_uses_existing_text_layer(monkeypatch):
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_textbox(
        pymupdf.Rect(50, 50, 550, 240),
        (
            "Association Rule Mining discovers useful relationships among items. "
            "The Apriori algorithm finds frequent itemsets before generating rules."
        ),
    )
    monkeypatch.setattr(ingestion, "_vision_ocr", lambda _image: pytest.fail("OCR should not run"))

    result = ingestion.extract_pages(pdf.tobytes(), "unit-4.pdf")

    assert len(result.pages) == 1
    assert result.pages[0].page_number == 1
    assert result.pages[0].extraction_method == "pdf_text"
    assert "Apriori" in result.pages[0].text
    assert result.scanned_pages == 0


def test_scanned_printed_pdf_uses_vision_ocr_and_preserves_page_metadata(monkeypatch):
    from PIL import Image

    def assert_high_resolution_render(image_bytes):
        rendered = Image.open(io.BytesIO(image_bytes))
        assert rendered.width >= 2000
        assert rendered.height >= 2500
        return "Association Rule Mining uses Apriori to find frequent itemsets."

    monkeypatch.setattr(
        ingestion,
        "_vision_ocr",
        assert_high_resolution_render,
    )
    monkeypatch.setattr(ingestion, "_tesseract_ocr", lambda _image: pytest.fail("Vision OCR succeeded"))

    result = ingestion.extract_pages(_printed_scan_pdf(), "printed-scan.pdf")

    assert result.scanned_pages == 1
    assert result.pages == [
        ingestion.ExtractedPage(
            1,
            "Association Rule Mining uses Apriori to find frequent itemsets.",
            "gemini_vision",
        )
    ]


def test_handwritten_pdf_uses_mocked_vision_transcription(monkeypatch):
    monkeypatch.setattr(
        ingestion,
        "_vision_ocr",
        lambda _image: "K-means clustering partitions data into k clusters using centroid updates.",
    )

    result = ingestion.extract_pages(_printed_scan_pdf(), "handwritten-notes.pdf")

    assert result.pages[0].extraction_method == "gemini_vision"
    assert "K-means clustering" in result.pages[0].text


def test_mixed_pdf_keeps_text_and_scanned_page_boundaries(monkeypatch):
    monkeypatch.setattr(
        ingestion,
        "_vision_ocr",
        lambda _image: "Apriori identifies frequent itemsets on the scanned page.",
    )

    result = ingestion.extract_pages(_mixed_pdf(), "mixed.pdf")

    assert [(page.page_number, page.extraction_method) for page in result.pages] == [
        (1, "pdf_text"),
        (2, "gemini_vision"),
    ]
    assert "Association Rule Mining" in result.pages[0].text
    assert "Apriori" in result.pages[1].text


def test_image_only_pdf_pages_can_be_transcribed(monkeypatch):
    monkeypatch.setattr(
        ingestion,
        "_vision_ocr",
        lambda _image: "The handwritten note describes K-means clustering and centroids.",
    )

    result = ingestion.extract_pages(_printed_scan_pdf(), "image-only.pdf")

    assert result.pages[0].page_number == 1
    assert "centroids" in result.pages[0].text


def test_unreadable_scan_fails_with_ocr_limitation(monkeypatch):
    monkeypatch.setenv("VISTAAR_OCR_VISION_ENABLED", "false")
    monkeypatch.setenv("VISTAAR_OCR_FALLBACK", "tesseract")
    monkeypatch.setattr(ingestion, "_tesseract_ocr", lambda _image: "### ???")

    with pytest.raises(ingestion.DocumentProcessingError, match="No readable text"):
        ingestion.extract_pages(_printed_scan_pdf(), "unreadable.pdf")


def test_tesseract_fallback_runs_after_vision_quota_error(monkeypatch):
    class VisionOCRQuotaError(RuntimeError):
        pass

    monkeypatch.setenv("VISTAAR_OCR_VISION_ENABLED", "true")
    monkeypatch.setenv("VISTAAR_OCR_FALLBACK", "tesseract")
    monkeypatch.setattr(ingestion, "_vision_ocr", lambda _image: (_ for _ in ()).throw(VisionOCRQuotaError()))
    monkeypatch.setattr(
        ingestion,
        "_tesseract_ocr",
        lambda _image: "Apriori finds frequent itemsets in transaction records.",
    )

    text, method, failure = ingestion._ocr_page(b"fake rendered page")

    assert "Apriori" in text
    assert method == "tesseract"
    assert failure is None


def test_ocr_chunks_keep_page_and_extraction_metadata_and_retry_is_idempotent():
    pages = [
        ingestion.ExtractedPage(
            page_number=4,
            text="Association Rule Mining Apriori finds frequent itemsets in transaction data.",
            extraction_method="gemini_vision",
        ),
        ingestion.ExtractedPage(
            page_number=12,
            text="K-means clustering repeatedly updates centroids to group observations.",
            extraction_method="tesseract",
        ),
    ]
    document_id = "stable-test-document"
    result = process_document(
        pages,
        user_id="pdf-test-user",
        source_filename="notes.pdf",
        document_id=document_id,
    )

    assert result == {"indexed_chunks": 2, "duplicate": False}
    assert has_indexed_document(document_id, user_id="pdf-test-user")
    assert document_chunk_count(document_id, user_id="pdf-test-user") == 2
    chunks = stored_chunks_by_user["pdf-test-user"]
    assert [(chunk.page_number, chunk.extraction_method) for chunk in chunks] == [
        (4, "gemini_vision"),
        (12, "tesseract"),
    ]
    retry = process_document(
        pages,
        user_id="pdf-test-user",
        source_filename="notes.pdf",
        document_id=document_id,
    )
    assert retry == {"indexed_chunks": 2, "duplicate": True}
    assert indices["pdf-test-user"].ntotal == 2

    from embeddings import model

    apriori_result = retrieve(
        model.encode(["What is the Apriori algorithm used for?"])[0],
        k=2,
        user_id="pdf-test-user",
    )
    kmeans_result = retrieve(
        model.encode(["How does K-means clustering update its centroids?"])[0],
        k=2,
        user_id="pdf-test-user",
    )
    assert apriori_result[0].page_number == 4
    assert apriori_result[0].extraction_method == "gemini_vision"
    assert "frequent itemsets" in apriori_result[0].text
    assert kmeans_result[0].page_number == 12
    assert "K-means clustering" in kmeans_result[0].text
