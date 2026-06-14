# Launch the ComplianceCrew FastAPI backend (Groq Llama 3.3 70B, free tier).
# Usage:  .\scripts\run_api.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
  Write-Host "Virtual env not found at .venv — create it and 'pip install -r requirements.txt' first." -ForegroundColor Yellow
  exit 1
}

Write-Host "ComplianceCrew API  ->  http://localhost:8000   (docs at /docs)" -ForegroundColor Green
& $venvPy -m uvicorn api.main:app --reload --port 8000
