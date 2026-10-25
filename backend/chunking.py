def chunk_text(text, size=1000, overlap=200):
    chunks = []
    for i in range(0, len(text), size - overlap):
        chunk = text[i:i + size]
        chunks.append(chunk)
    return chunks