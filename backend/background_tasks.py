from chunking import chunk_text
from embeddings import get_embeddings
from vector_store import add_to_index

def process_document(text):
    print("Processing document...")

    chunks = chunk_text(text)
    print(f"Created {len(chunks)} chunks")

    embeddings = get_embeddings(chunks)
    print("Embeddings created")

    add_to_index(embeddings, chunks)
    print("Stored in FAISS")