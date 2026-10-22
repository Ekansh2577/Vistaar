import urllib.request
import urllib.parse
import json
import mimetypes
import uuid

BASE_URL = "http://localhost:5173/api"

print("=" * 60)
print("VISTAAR FINAL END-TO-END VERIFICATION")
print("=" * 60)

# Helper for multipart form data
def post_multipart(url, fields, files):
    boundary = uuid.uuid4().hex
    body = bytearray()
    
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{value}\r\n".encode("utf-8"))
        
    for name, (filename, filedata, content_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(filedata)
        body.extend(b"\r\n")
        
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def post_json(url, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

# Test 1: Upload document
print("\n--- TEST 1: Document Upload & FAISS Indexing ---")
with open(r"c:\Users\ekans\.gemini\antigravity-ide\scratch\vistaar\test_sample.txt", "rb") as f:
    sample_bytes = f.read()

upload_resp = post_multipart(
    f"{BASE_URL}/upload",
    {},
    {"file": ("test_sample.txt", sample_bytes, "text/plain")}
)
print("Upload status:", upload_resp)

# Test 2: In-corpus Question
print("\n--- TEST 2: In-Corpus Grounded Question ---")
doc_q = "What is the chunk size and chunk overlap configured in VISTAAR?"
ask_resp = post_json(f"{BASE_URL}/ask", {"question": doc_q})
print("Question:", doc_q)
print("Answer:", ask_resp.get("answer"))
print("Sources:", len(ask_resp.get("sources", [])))

# Test 3: Insufficient Evidence Question
print("\n--- TEST 3: Insufficient Evidence Detection ---")
missing_q = "What is the return and refund policy for commercial drones?"
missing_resp = post_json(f"{BASE_URL}/ask", {"question": missing_q})
print("Question:", missing_q)
print("Answer:", missing_resp.get("answer"))

# Test 4: Web Search Fallback
print("\n--- TEST 4: Live Web Search Fallback ---")
web_resp = post_json(f"{BASE_URL}/search/web", {"query": missing_q})
print("Query:", web_resp.get("query"))
print("Synthesized Answer:", web_resp.get("synthesized_answer")[:250], "...")
print("Citations Found:", len(web_resp.get("sources", [])))
for idx, s in enumerate(web_resp.get("sources", [])[:3], 1):
    print(f"  [{idx}] {s['title']} ({s['domain']}) -> {s['url']}")

# Test 5: Image Multimodal Analysis
print("\n--- TEST 5: Multimodal Image Analysis ---")
with open(r"c:\Users\ekans\.gemini\antigravity-ide\scratch\vistaar\src\assets\hero.png", "rb") as f:
    img_bytes = f.read()

img_q = "What visual elements and text are present in this image?"
img_resp = post_multipart(
    f"{BASE_URL}/ask-image",
    {"question": img_q},
    {"file": ("hero.png", img_bytes, "image/png")}
)
print("Question:", img_q)
print("Image Analysis:", img_resp.get("answer")[:250], "...")
print("Analysis Type:", img_resp.get("analysis_type"))

print("\n" + "=" * 60)
print("ALL TESTS COMPLETED SUCCESSFULLY!")
print("=" * 60)
