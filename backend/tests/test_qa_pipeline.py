import logging
import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
import pymupdf
from PIL import Image, ImageDraw


@pytest.fixture
def qa_client(monkeypatch, tmp_path):
    monkeypatch.setenv("VISTAAR_AUTH_DB", str(tmp_path / "qa-accounts.sqlite3"))
    monkeypatch.setenv("VISTAAR_ENV", "development")
    monkeypatch.setenv("VISTAAR_CORS_ORIGINS", "")
    monkeypatch.setenv("VISTAAR_COOKIE_SECURE", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "pipeline-test-key")

    from app import app
    import qa_service
    from rate_limiter import limiter
    from vector_store import (
        document_status_by_user,
        indexed_document_ids_by_user,
        indices,
        stored_chunks_by_user,
    )

    monkeypatch.setattr(limiter, "enabled", False, raising=False)
    indices.clear()
    stored_chunks_by_user.clear()
    indexed_document_ids_by_user.clear()
    document_status_by_user.clear()

    with TestClient(app) as client:
        yield client, qa_service

    indices.clear()
    stored_chunks_by_user.clear()
    indexed_document_ids_by_user.clear()
    document_status_by_user.clear()


def test_upload_is_indexed_before_grounded_question(qa_client, monkeypatch, caplog):
    client, qa_service = qa_client
    answer_text = "The VISTAAR field support code is VST-2048."
    captured_prompts = []

    def generate_from_evidence(prompt):
        captured_prompts.append(prompt)
        assert answer_text in prompt
        assert "Source: support-guide.txt" in prompt
        return f"{answer_text} (support-guide.txt)"

    monkeypatch.setattr(qa_service, "ask_gemini", generate_from_evidence)
    account = client.post("/auth/register", json={
        "full_name": "Pipeline Reader",
        "email": "pipeline-reader@example.com",
        "password": "safe-password-123",
    })
    assert account.status_code == 201

    document = (
        "VISTAAR field support reference. "
        f"{answer_text} "
        "Customers should provide this code when contacting the field support team. "
        "Contact: private-reader@example.test. API key=unit-test-secret."
    )
    with caplog.at_level(logging.INFO):
        uploaded = client.post(
            "/upload",
            files={"file": ("support-guide.txt", document.encode("utf-8"), "text/plain")},
        )
        assert uploaded.status_code == 202
        upload_status = client.get(f"/upload/{uploaded.json()['job_id']}").json()
        assert upload_status["status"] == "ready"
        assert upload_status["indexed_chunks"] == 1

        response = client.post("/ask", json={"question": "What is the field support code?"})

    assert response.status_code == 200
    assert response.json()["answer"] == f"{answer_text} (support-guide.txt)"
    assert response.json()["sources"][0]["filename"] == "support-guide.txt"
    assert response.json()["sources"][0]["chunk_id"].endswith(":chunk-0001")
    assert response.json()["sources"][0]["page"] == 1
    assert response.json()["sources"][0]["extraction_method"] == "text"
    assert captured_prompts
    assert "FAISS indexed chunks=1" in caplog.text
    assert "FAISS retrieval index_chunks=1 retrieved_chunks=1" in caplog.text
    assert "l2_distance=" in caplog.text
    assert "support-guide.txt" in caplog.text
    assert "preview=" in caplog.text
    assert "private-reader@example.test" not in caplog.text
    assert "unit-test-secret" not in caplog.text


def test_scanned_pdf_upload_retrieves_ocr_evidence_with_page_citation(qa_client, monkeypatch):
    client, qa_service = qa_client
    import ingestion

    image = Image.new("RGB", (1200, 1600), "white")
    ImageDraw.Draw(image).text((80, 100), "Association Rule Mining Apriori", fill="black")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    pdf = pymupdf.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_image(page.rect, stream=image_bytes.getvalue())

    monkeypatch.setattr(
        ingestion,
        "_vision_ocr",
        lambda _image: "Apriori is used for association rule mining to discover frequent itemsets.",
    )
    monkeypatch.setattr(
        qa_service,
        "ask_gemini",
        lambda prompt: (
            "Apriori discovers frequent itemsets for association rule mining "
            "(unit-4-scan.pdf, page 1)."
            if "page 1" in prompt and "frequent itemsets" in prompt
            else pytest.fail("The page OCR evidence was not included in the Gemini prompt.")
        ),
    )
    assert client.post("/auth/register", json={
        "full_name": "PDF Reader",
        "email": "pdf-reader@example.com",
        "password": "safe-password-123",
    }).status_code == 201

    pdf_content = pdf.tobytes()
    uploaded = client.post(
        "/upload",
        files={"file": ("unit-4-scan.pdf", pdf_content, "application/pdf")},
    )
    assert uploaded.status_code == 202
    status = client.get(f"/upload/{uploaded.json()['job_id']}").json()
    assert status["status"] == "ready"
    assert status["scanned_pages"] == 1
    assert status["indexed_chunks"] == 1

    response = client.post("/ask", json={"question": "What is Apriori used for?"})

    assert response.status_code == 200
    assert "frequent itemsets" in response.json()["answer"]
    assert response.json()["sources"][0]["filename"] == "unit-4-scan.pdf"
    assert response.json()["sources"][0]["page"] == 1
    assert response.json()["sources"][0]["extraction_method"] == "gemini_vision"

    retry = client.post(
        "/upload",
        files={"file": ("unit-4-scan.pdf", pdf_content, "application/pdf")},
    )
    retry_status = client.get(f"/upload/{retry.json()['job_id']}").json()
    assert retry_status["duplicate"] is True
    assert retry_status["indexed_chunks"] == 1


def test_failed_scanned_pdf_reports_ocr_limitation_to_questioner(qa_client, monkeypatch):
    client, _qa_service = qa_client
    import ingestion

    image = Image.new("RGB", (1200, 1600), "white")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    pdf = pymupdf.open()
    page = pdf.new_page(width=612, height=792)
    page.insert_image(page.rect, stream=image_bytes.getvalue())

    monkeypatch.setenv("VISTAAR_OCR_VISION_ENABLED", "false")
    monkeypatch.setattr(ingestion, "_tesseract_ocr", lambda _image: "### ???")
    assert client.post("/auth/register", json={
        "full_name": "OCR Failure Reader",
        "email": "ocr-failure@example.com",
        "password": "safe-password-123",
    }).status_code == 201

    uploaded = client.post(
        "/upload",
        files={"file": ("unreadable-scan.pdf", pdf.tobytes(), "application/pdf")},
    )
    assert uploaded.status_code == 202
    status = client.get(f"/upload/{uploaded.json()['job_id']}").json()
    assert status["status"] == "failed"
    assert "Page 1" in status["error"]
    assert "no readable text" in status["error"]

    response = client.post("/ask", json={"question": "What does this document say?"})

    assert response.status_code == 200
    assert "unreadable-scan.pdf" in response.json()["answer"]
    assert "Page 1" in response.json()["answer"]
    assert response.json()["needs_web_fallback"] is True


def test_retrieval_orders_matches_by_increasing_l2_distance():
    from vector_store import add_to_index, retrieve

    indices = np.zeros((2, 384), dtype="float32")
    indices[1, 0] = 3.0
    add_to_index(indices, ["nearest passage", "farther passage"], user_id="distance-test")

    results = retrieve(np.zeros(384, dtype="float32"), k=2, user_id="distance-test")

    assert [result.text for result in results] == ["nearest passage", "farther passage"]
    assert results[0].l2_distance < results[1].l2_distance


def test_query_dimension_must_match_index_dimension():
    from vector_store import add_to_index, retrieve

    add_to_index(np.zeros((1, 384), dtype="float32"), ["passage"], user_id="dimension-test")

    with pytest.raises(ValueError, match="Query embedding dimension"):
        retrieve(np.zeros(383, dtype="float32"), user_id="dimension-test")
