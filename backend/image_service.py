import io
from typing import Dict, Any
from google import genai
from google.genai import types

def get_gemini_client():
    from qa_service import client
    return client

ALLOWED_IMAGE_TYPES = {
    "image/png": "image/png",
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/webp": "image/webp",
    "image/gif": "image/gif",
}

SYSTEM_INSTRUCTION = (
    "You are an expert visual intelligence and OCR analyzer for VISTAAR. "
    "Analyze the provided image thoroughly to answer the user's question. "
    "Capabilities: "
    "- Describe the image and explain diagrams, architecture charts, or flowcharts. "
    "- Read and transcribe any handwritten or printed text, math equations, or code. "
    "- Identify specific visual components, data points, or entities. "
    "Always remain strictly grounded in what is visually depicted in the image. "
    "If any part of the image is blurry, unreadable, or missing, state that clearly rather than inventing details."
)

VISION_MODELS = ["gemini-3-flash-preview", "gemini-3.5-flash"]

def analyze_image(image_bytes: bytes, mime_type: str, question: str, filename: str = "image") -> Dict[str, Any]:
    if not image_bytes or len(image_bytes) == 0:
        return {
            "answer": "Uploaded image is empty or corrupt. Please upload a valid image file.",
            "source_type": "image",
            "filename": filename,
            "status": "error"
        }

    # Normalize mime type
    normalized_mime = ALLOWED_IMAGE_TYPES.get(mime_type.lower())
    if not normalized_mime:
        # Check by filename extension fallback
        lower_fn = filename.lower()
        if lower_fn.endswith(".png"):
            normalized_mime = "image/png"
        elif lower_fn.endswith((".jpg", ".jpeg")):
            normalized_mime = "image/jpeg"
        elif lower_fn.endswith(".webp"):
            normalized_mime = "image/webp"
        elif lower_fn.endswith(".gif"):
            normalized_mime = "image/gif"
        else:
            return {
                "answer": f"Unsupported image format: '{mime_type}'. Supported formats: PNG, JPG, JPEG, WEBP, GIF.",
                "source_type": "image",
                "filename": filename,
                "status": "error"
            }

    if len(image_bytes) > 20 * 1024 * 1024:
        return {
            "answer": "Image exceeds maximum allowed size of 20MB.",
            "source_type": "image",
            "filename": filename,
            "status": "error"
        }

    client = get_gemini_client()
    user_prompt = question.strip() if question and question.strip() else "What is this image about? Describe the key components and any visible text."

    for model_name in VISION_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=normalized_mime),
                    user_prompt
                ],
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.1,
                )
            )
            if response.text:
                return {
                    "answer": response.text.strip(),
                    "source_type": "image",
                    "filename": filename,
                    "status": "success"
                }
        except Exception as e:
            print(f"Vision analysis error ({model_name}): {e}")

    return {
        "answer": "The AI vision service is currently experiencing high demand. Please try again in a few moments.",
        "source_type": "image",
        "filename": filename,
        "status": "error"
    }
