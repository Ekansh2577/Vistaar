import logging

from chunking import chunk_text
from embeddings import get_embeddings
from ingestion import DocumentProcessingError, ExtractedPage
from vector_store import add_to_index, document_chunk_count, has_indexed_document

logger = logging.getLogger(__name__)


def process_document(
    pages,
    user_id="default",
    source_filename="uploaded document",
    document_id=None,
    on_progress=None,
):
    if isinstance(pages, str):
        pages = [ExtractedPage(page_number=1, text=pages, extraction_method="text")]
    if not pages:
        raise DocumentProcessingError("No readable page text is available for indexing.")

    if has_indexed_document(document_id, user_id=user_id):
        return {
            "indexed_chunks": document_chunk_count(document_id, user_id=user_id),
            "duplicate": True,
        }

    logger.info("Starting document indexing source=%s", source_filename)
    chunks = []
    chunk_metadata = []
    for page in pages:
        page_chunks = chunk_text(page.text)
        chunks.extend(page_chunks)
        chunk_metadata.extend(
            {
                "page_number": page.page_number,
                "extraction_method": page.extraction_method,
            }
            for _ in page_chunks
        )

    if not chunks:
        raise DocumentProcessingError("No readable text chunks were created from the document.")
    if on_progress:
        on_progress("Indexing document pages")

    embeddings = get_embeddings(chunks)
    inserted = add_to_index(
        embeddings,
        chunks,
        user_id=user_id,
        source_filename=source_filename,
        document_id=document_id,
        chunk_metadata=chunk_metadata,
    )
    return {
        "indexed_chunks": len(chunks) if inserted else document_chunk_count(document_id, user_id=user_id),
        "duplicate": not inserted,
    }
