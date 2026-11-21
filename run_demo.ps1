# ChangeRadar Demo Launcher Script
param(
    [ValidateSet("frontend", "backend", "worker", "all", "test")]
    [string]$Mode = "frontend"
)

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "             ChangeRadar Demo Launcher                   " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Use native SQLite by default for hassle-free local demo without Docker/WSL
if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "sqlite:///./changeradar.db"
}

if ($Mode -eq "frontend") {
    Write-Host "Starting ChangeRadar React Frontend (Demo Mode)..." -ForegroundColor Green
    Write-Host "URL: http://localhost:5173" -ForegroundColor Yellow
    Set-Location "$RootDir\frontend"
    npm run dev
}
elseif ($Mode -eq "backend") {
    Write-Host "Starting ChangeRadar FastAPI Backend (Native SQLite)..." -ForegroundColor Green
    Write-Host "API: http://localhost:8000" -ForegroundColor Yellow
    Write-Host "Docs: http://localhost:8000/docs" -ForegroundColor Yellow
    Set-Location "$RootDir\backend"
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}
elseif ($Mode -eq "worker") {
    Write-Host "Starting ChangeRadar Background Research Worker..." -ForegroundColor Green
    Set-Location "$RootDir\backend"
    python -m app.worker.runner
}
elseif ($Mode -eq "test") {
    Write-Host "Running End-to-End Pipeline Verification Test (Tavily + Bifrost)..." -ForegroundColor Green
    python "C:\Users\Win10\.gemini\antigravity\brain\b6c9f582-bc07-4df7-9a4a-e017500b05aa\scratch\test_live_pipeline_e2e.py"
}
elseif ($Mode -eq "all") {
    Write-Host "Launching complete stack in separate terminal windows..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$RootDir\frontend'; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:DATABASE_URL='sqlite:///./changeradar.db'; cd '$RootDir\backend'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:DATABASE_URL='sqlite:///./changeradar.db'; cd '$RootDir\backend'; python -m app.worker.runner"
    Write-Host "Services launched! Access the UI at: http://localhost:5173" -ForegroundColor Cyan
}
