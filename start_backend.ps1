Write-Host "Starting VISTAAR Backend..." -ForegroundColor Cyan
$backendDir = Join-Path $PSScriptRoot "backend"
& "C:\Users\ekans\OneDrive\New folder\vis\Vistaar-main\backend\venv\Scripts\python.exe" -c "import os, sys, uvicorn; os.chdir(r'$backendDir'); sys.path.insert(0, os.getcwd()); uvicorn.run('app:app', host='127.0.0.1', port=8000)"
