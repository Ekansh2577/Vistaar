import os

path = r"C:\Users\ekans\OneDrive\New folder\vis\Vistaar-main\backend\qa_service.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

target = 'GEMINI_MODELS = ["gemini-3.5-flash", "gemini-2.5-flash"]'
replacement = 'GEMINI_MODELS = ["gemini-3-flash-preview", "gemini-flash-latest", "gemini-3.5-flash"]'

if target in text:
    text = text.replace(target, replacement)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("REPLACED SUCCESSFULLY")
else:
    print("TARGET NOT FOUND. Current lines:")
    for line in text.splitlines():
        if "GEMINI_MODELS" in line:
            print(line)
