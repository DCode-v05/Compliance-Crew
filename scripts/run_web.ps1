# Launch the ComplianceCrew Next.js frontend (Regulatory Intelligence console).
# Usage:  .\scripts\run_web.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$web = Join-Path $root "frontend"
Set-Location $web

if (-not (Test-Path (Join-Path $web "node_modules"))) {
  Write-Host "Installing frontend dependencies (first run)..." -ForegroundColor Cyan
  npm install --no-audit --no-fund
}

Write-Host "ComplianceCrew Console  ->  http://localhost:3000" -ForegroundColor Green
npm run dev
