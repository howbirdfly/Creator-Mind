$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
    Write-Host 'Created .env from .env.example'
}

if (-not (Test-Path -LiteralPath 'backend/.env')) {
    Copy-Item -LiteralPath 'backend/.env.example' -Destination 'backend/.env'
    Write-Host 'Created backend/.env from backend/.env.example'
}

if (-not (Test-Path -LiteralPath 'backend/.venv')) {
    py -m venv backend/.venv
}

& '.\backend\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\backend\.venv\Scripts\python.exe' -m pip install -e '.\backend[dev,agent]'

Push-Location frontend
try {
    npm install
} finally {
    Pop-Location
}

Write-Host ''
Write-Host 'CreatorMind dependencies are ready.'
Write-Host 'Start infrastructure: docker compose up -d postgres redis minio'
Write-Host 'Start API:            cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload'
Write-Host 'Start web:            cd frontend; npm run dev'