import logging
from dataclasses import dataclass
from threading import RLock
from uuid import uuid4

import faiss
import numpy as np

logger = logging.getLogger(__name__)

dimension = 384
indices = {}
stored_chunks_by_user = {}
indexed_document_ids_by_user = {}
document_status_by_user = {}
_index_lock = RLock()


@dataclass(frozen=True)
class IndexedChunk:
    chunk_id: str
    document_id: str
    source_filename: str
    page_number: int | None
    extraction_method: str
    text: str


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    source_filename: str
    page_number: int | None
    extraction_method: str
    text: str
    l2_distance: float


def add_to_index(
    embeddings,
    chunks,
    user_id="default",
    source_filename="uploaded document",
    document_id=None,
    chunk_metadata=None,
):
    embeddings = np.asarray(embeddings, dtype="float32")
    if embeddings.ndim != 2 or embeddings.shape[1] != dimension:
        raise ValueError(f"Expected a 2D embedding array with dimension {dimension}.")
    if embeddings.shape[0] != len(chunks):
        raise ValueError("The number of embeddings must match the number of chunks.")
    if not np.isfinite(embeddings).all():
        raise ValueError("Embeddings must contain only finite values.")

    document_id = document_id or uuid4().hex
    metadata = chunk_metadata or [{} for _ in chunks]
    if len(metadata) != len(chunks):
        raise ValueError("The number of metadata entries must match the number of chunks.")

    with _index_lock:
        indexed_ids = indexed_document_ids_by_user.setdefault(user_id, set())
        if document_id in indexed_ids:
            logger.info("FAISS skipped duplicate document_id=%s source=%s", document_id, source_filename)
            return False

        index = indices.setdefault(user_id, faiss.IndexFlatL2(dimension))
        if index.d != embeddings.shape[1]:
            raise ValueError(f"Embedding dimension {embeddings.shape[1]} does not match FAISS index dimension {index.d}.")

        index.add(embeddings)
        stored_chunks_by_user.setdefault(user_id, []).extend(
            IndexedChunk(
                chunk_id=f"{document_id}:chunk-{offset + 1:04d}",
                document_id=document_id,
                source_filename=source_filename,
                page_number=chunk_metadata_item.get("page_number"),
                extraction_method=chunk_metadata_item.get("extraction_method", "text"),
                text=chunk,
            )
            for offset, (chunk, chunk_metadata_item) in enumerate(zip(chunks, metadata))
        )
        indexed_ids.add(document_id)
        logger.info(
            "FAISS indexed chunks=%d source=%s document_id=%s index_chunks=%d embedding_dimension=%d",
            len(chunks),
            source_filename,
            document_id,
            index.ntotal,
            embeddings.shape[1],
        )
        return True


def has_indexed_document(document_id, user_id="default"):
    with _index_lock:
        return document_id in indexed_document_ids_by_user.get(user_id, set())


def document_chunk_count(document_id, user_id="default"):
    with _index_lock:
        return sum(
            chunk.document_id == document_id
            for chunk in stored_chunks_by_user.get(user_id, [])
        )


def set_document_status(document_id, source_filename, status, user_id="default", **details):
    with _index_lock:
        user_statuses = document_status_by_user.setdefault(user_id, {})
        user_statuses[document_id] = {
            "document_id": document_id,
            "source_filename": source_filename,
            "status": status,
            **details,
        }


def get_document_statuses(user_id="default"):
    with _index_lock:
        return [dict(status) for status in document_status_by_user.get(user_id, {}).values()]


def index_size(user_id="default"):
    with _index_lock:
        index = indices.get(user_id)
        return index.ntotal if index is not None else 0


def retrieve(query_embedding, k=3, user_id="default"):
    with _index_lock:
        index = indices.get(user_id)
        if index is None or index.ntotal == 0:
            return []

        query_embedding = np.asarray(query_embedding, dtype="float32").reshape(1, -1)
        if query_embedding.shape[1] != index.d:
            raise ValueError(f"Query embedding dimension {query_embedding.shape[1]} does not match FAISS index dimension {index.d}.")
        if k <= 0:
            return []

        distances, positions = index.search(query_embedding, min(k, index.ntotal))
        chunks = stored_chunks_by_user.get(user_id, [])
        results = []
        for distance, position in zip(distances[0], positions[0]):
            if 0 <= position < len(chunks):
                chunk = chunks[position]
                results.append(
                    RetrievedChunk(
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        source_filename=chunk.source_filename,
                        page_number=chunk.page_number,
                        extraction_method=chunk.extraction_method,
                        text=chunk.text,
                        l2_distance=float(distance),
                    )
                )
        return results


def search(query_embedding, k=3, user_id="default"):
    return [chunk.text for chunk in retrieve(query_embedding, k=k, user_id=user_id)]
