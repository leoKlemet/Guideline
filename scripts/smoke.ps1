$ErrorActionPreference = "Stop"

Write-Host "--- Guideline Smoke Test ---" -ForegroundColor Cyan

# 1. Backend Verification
Write-Host "`n[1/5] Backend Setup..." -ForegroundColor Yellow
Set-Location apps/api

if (Test-Path .venv) { Remove-Item .venv -Recurse -Force }
if (Test-Path data/guideline.db) { Remove-Item data/guideline.db -Force }

Write-Host "Creating venv..."
python -m venv .venv

# Try Windows activation first
if (Test-Path .venv\Scripts\Activate.ps1) {
    . .venv\Scripts\Activate.ps1
} elseif (Test-Path .venv/bin/activate) {
    . .venv/bin/activate
} else {
    Write-Warning "Could not find activate script. Assuming venv is active or python is global."
}

Write-Host "Installing requirements..."
python -m pip install -q -r requirements.txt

Write-Host "Seeding DB..."
python -m app.seed

if (-not (Test-Path data/guideline.db)) {
    Write-Error "DB file not found after seeding!"
}

# Start Server in Background
Write-Host "Starting API server..."
$apiProcess = Start-Process -FilePath "python" -ArgumentList "-m uvicorn app.main:app --port 8000" -PassThru -NoNewWindow
Start-Sleep -Seconds 5

try {
    # Smoke Endpoints
    Write-Host "`n[2/5] Testing Endpoints..." -ForegroundColor Yellow
    
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health"
    if (-not $health.ok) { throw "/health failed" }
    Write-Host "  /health OK" -ForegroundColor Green

    $docs = Invoke-RestMethod -Uri "http://localhost:8000/docs"
    if ($docs.Count -eq 0) { throw "/docs returned empty" }
    Write-Host "  /docs OK ($($docs.Count) docs)" -ForegroundColor Green

    $schedule = Invoke-RestMethod -Uri "http://localhost:8000/schedule"
    if (-not $schedule.timezone) { throw "/schedule failed" }
    Write-Host "  /schedule OK" -ForegroundColor Green
    
    # Test Chat
    $chat = Invoke-RestMethod -Uri "http://localhost:8000/chat/ask" -Method Post -Body (@{
        userId = "smoke_test"
        role = "internal"
        question = "What's the meals limit?"
    } | ConvertTo-Json) -ContentType "application/json"
    
    if ($chat.lowConfidence -eq $true) { throw "Basic chat question failed (Low Confidence)" }
    Write-Host "  /chat/ask OK" -ForegroundColor Green

    # Run Pytest
    Write-Host "`n[3/5] Running Tests (pytest)..." -ForegroundColor Yellow
    python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Pytest failed" }
    Write-Host "  Pytest Passed" -ForegroundColor Green

} finally {
    Stop-Process -Id $apiProcess.Id -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped API server."
}

Set-Location ../..

# 2. Frontend Verification
Write-Host "`n[4/5] Frontend Setup..." -ForegroundColor Yellow
Set-Location apps/web

if (Test-Path node_modules) { Remove-Item node_modules -Recurse -Force }

Write-Host "Installing dependencies..."
& "C:\Program Files\nodejs\npm.cmd" install --silent

Write-Host "Checking for line-clamp plugin..."
$twConfig = Get-Content tailwind.config.cjs -Raw
if ($twConfig -notmatch "@tailwindcss/line-clamp") {
    Write-Error "Tailwind config missing line-clamp plugin!"
}
Write-Host "  Tailwind config OK" -ForegroundColor Green

Write-Host "`n[5/5] Smoke Test Complete!" -ForegroundColor Cyan
Set-Location ../..
