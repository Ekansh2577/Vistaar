@echo off
echo Starting VISTAAR Backend from workspace...
set "BACKEND_DIR=%~dp0backend"
if exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
  set "BACKEND_PYTHON=%BACKEND_DIR%\venv\Scripts\python.exe"
) else (
  set "BACKEND_PYTHON=python"
)
cd /d "%BACKEND_DIR%"
"%BACKEND_PYTHON%" -m uvicorn app:app --host 127.0.0.1 --port 8000
