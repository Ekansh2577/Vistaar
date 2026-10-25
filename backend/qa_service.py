import os
import time
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types, errors
from embeddings import model
from vector_store import search

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY not found. Check that .env is in the backend folder "
        "and contains a line like GEMINI_API_KEY=your_key"
    )

client = genai.Client(api_key=API_KEY)

GEMINI_MODELS = ["gemini-3-flash-preview", "gemini-flash-latest", "gemini-3.5-flash"]
MAX_RETRIES = 3

SYSTEM_PROMPT = (
    "You answer questions using ONLY the context provided. "
    "If the answer is not in the context, reply exactly: "
    "'I could not find this in the document.' "
    "Do not use outside knowledge and do not guess."
)


def ask_gemini(prompt):
    for model_name in GEMINI_MODELS:
        for attempt in range(MAX_RETRIES):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.0,
                    ),
                )
                if response.text:
                    return response.text
                break
            except errors.APIError as e:
                print(f"Gemini error ({model_name}, try {attempt + 1}):", e)
                if e.code in (429, 500, 503, 504):
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)
                    continue
                break
            except Exception as e:
                print("Unexpected error:", e)
                break
    return None


def answer_question(question):
    q_embedding = model.encode([question])[0]
    context_chunks = search(q_embedding, k=8)

    print("---- RETRIEVED CHUNKS ----")
    for i, c in enumerate(context_chunks):
        preview = c[:150].replace("\n", " ").encode("ascii", "ignore").decode()
        print(f"[{i}] {preview}")

    if not context_chunks:
        return "No relevant information found. Please upload a document first."

    context = "\n\n---\n\n".join(context_chunks)
    prompt = f"Context:\n{context}\n\nQuestion: {question}"

    answer = ask_gemini(prompt)
    if not answer:
        return "The AI service is busy right now. Please try again in a minute."
    return answer