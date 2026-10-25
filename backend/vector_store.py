import faiss
import numpy as np

dimension = 384
index = faiss.IndexFlatL2(dimension)
stored_chunks = []

def add_to_index(embeddings, chunks):
    global stored_chunks
    embeddings = np.array(embeddings).astype("float32")
    index.add(embeddings)
    stored_chunks.extend(chunks)

def search(query_embedding, k=3):
    if index.ntotal == 0:
        return []

    query_embedding = np.array([query_embedding]).astype("float32")
    D, I = index.search(query_embedding, k)

    results = []
    for idx in I[0]:
        if 0 <= idx < len(stored_chunks):
            results.append(stored_chunks[idx])

    return results