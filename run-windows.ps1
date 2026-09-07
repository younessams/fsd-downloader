$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Virtual environment not found. Run .\install-dev-windows.ps1 first." -ForegroundColor Red
    exit 1
}

if (Test-Path ".\.fsd-env.ps1") {
    . .\.fsd-env.ps1
}

.\.venv\Scripts\python.exe -m app.main @args
