$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path -LiteralPath 'backend/.venv/Scripts/python.exe')) {
    throw 'Backend virtual environment is missing. Run .\scripts\setup.ps1 first.'
}

if (-not (Test-Path -LiteralPath 'frontend/node_modules')) {
    throw 'Frontend dependencies are missing. Run .\scripts\setup.ps1 first.'
}

Push-Location backend
try {
    & '.\.venv\Scripts\python.exe' -m ruff check .
    & '.\.venv\Scripts\python.exe' -m pytest
} finally {
    Pop-Location
}

Push-Location frontend
try {
    npm run typecheck
    npm test
    npm run build
} finally {
    Pop-Location
}

Write-Host 'All checks passed.'