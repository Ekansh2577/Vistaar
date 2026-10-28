Write-Host "Starting VISTAAR Backend..." -ForegroundColor Cyan
$backendDir = Join-Path $PSScriptRoot "backend"
$backendPython = Join-Path $backendDir "venv\Scripts\python.exe"
if (-not (Test-Path $backendPython)) {
  $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
  if (-not $pythonCommand) {
    throw "Python was not found. Install Python or create backend\venv, then install backend\requirements.txt."
  }
  $backendPython = $pythonCommand.Source
}

Push-Location $backendDir
try {
  & $backendPython -m uvicorn app:app --host 127.0.0.1 --port 8000
} finally {
  Pop-Location
}
