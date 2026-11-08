$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "Starting ComplianceCrew..." -ForegroundColor Green
Write-Host "  API     -> http://localhost:8000  (Swagger at /docs)"
Write-Host "  Console -> http://localhost:3000"

Start-Process powershell -ArgumentList "-NoExit", "-File", (Join-Path $root "scripts\run_api.ps1")
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-File", (Join-Path $root "scripts\run_web.ps1")

Write-Host "`nBoth processes launched in separate windows. Open http://localhost:3000" -ForegroundColor Cyan
