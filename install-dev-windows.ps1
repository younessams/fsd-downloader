$ErrorActionPreference = "Stop"

Write-Host "Installing FSD Downloader for Windows..." -ForegroundColor Cyan

function Find-Python {
    $commands = @("python", "py")
    foreach ($command in $commands) {
        $candidate = Get-Command $command -ErrorAction SilentlyContinue
        if ($candidate) {
            $oldErrorActionPreference = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            $version = & $candidate.Source --version 2>&1
            $exitCode = $LASTEXITCODE
            $ErrorActionPreference = $oldErrorActionPreference
            if ($exitCode -eq 0 -and "$version" -match "Python 3") {
                return $candidate.Source
            }
        }
    }

    $installed = Get-ChildItem -LiteralPath "$env:LOCALAPPDATA\Programs\Python" -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        Select-Object -First 1
    if ($installed) {
        return $installed.FullName
    }

    return $null
}

function Find-FFmpeg {
    $candidate = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($candidate) {
        return $candidate.Source
    }

    $roots = @(
        "$env:LOCALAPPDATA\Microsoft\WinGet\Packages",
        "C:\Program Files",
        "C:\Program Files (x86)"
    )
    foreach ($root in $roots) {
        if (Test-Path -LiteralPath $root) {
            $installed = Get-ChildItem -LiteralPath $root -Filter ffmpeg.exe -Recurse -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($installed) {
                return $installed.FullName
            }
        }
    }

    return $null
}

function Find-Deno {
    $candidate = Get-Command deno -ErrorAction SilentlyContinue
    if ($candidate) {
        return $candidate.Source
    }

    $localDeno = ".\.tools\deno\deno.exe"
    if (Test-Path -LiteralPath $localDeno) {
        return (Resolve-Path -LiteralPath $localDeno).Path
    }

    $roots = @(
        "$env:LOCALAPPDATA\Microsoft\WinGet\Packages",
        "$env:USERPROFILE\.deno\bin"
    )
    foreach ($root in $roots) {
        if (Test-Path -LiteralPath $root) {
            $installed = Get-ChildItem -LiteralPath $root -Filter deno.exe -Recurse -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($installed) {
                return $installed.FullName
            }
        }
    }

    return $null
}

function Install-LocalDeno {
    $toolsDir = ".\.tools\deno"
    $zipPath = ".\.tools\deno.zip"
    New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null
    New-Item -ItemType Directory -Force -Path ".\.tools" | Out-Null
    Write-Host "Deno was not found. Installing project-local Deno runtime..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip" -OutFile $zipPath
    Expand-Archive -LiteralPath $zipPath -DestinationPath $toolsDir -Force
    Remove-Item -LiteralPath $zipPath -Force
    return (Resolve-Path -LiteralPath "$toolsDir\deno.exe").Path
}

$pythonExe = Find-Python
if (-not $pythonExe) {
    Write-Host "Python 3 was not found." -ForegroundColor Red
    Write-Host "Install Python 3 from https://www.python.org/downloads/ and enable 'Add Python to PATH'." -ForegroundColor Red
    exit 1
}

$ffmpegExe = Find-FFmpeg
if (-not $ffmpegExe) {
    Write-Host "FFmpeg was not found on PATH." -ForegroundColor Yellow
    Write-Host "Install it with one of these commands, then reopen PowerShell:" -ForegroundColor Yellow
    Write-Host "  winget install Gyan.FFmpeg" -ForegroundColor White
    Write-Host "  choco install ffmpeg" -ForegroundColor White
} else {
    $ffmpegDir = Split-Path -Parent $ffmpegExe
    Write-Host "Using FFmpeg: $ffmpegExe" -ForegroundColor Green
}

$denoExe = Find-Deno
if (-not $denoExe) {
    $denoExe = Install-LocalDeno
}
$denoDir = Split-Path -Parent $denoExe
Write-Host "Using Deno: $denoExe" -ForegroundColor Green

$envLines = @()
if ($ffmpegExe) {
    $envLines += "`$env:PATH = '$ffmpegDir;' + `$env:PATH"
}
$envLines += "`$env:PATH = '$denoDir;' + `$env:PATH"
$envLines += "`$env:FSD_DENO_PATH = '$denoExe'"
Set-Content -LiteralPath ".\.fsd-env.ps1" -Value $envLines

Write-Host "Using Python: $pythonExe" -ForegroundColor Green
& $pythonExe -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host ""
Write-Host "Ready. Run with:" -ForegroundColor Green
Write-Host "  .\run-windows.ps1" -ForegroundColor White
Write-Host "  .\run-windows.ps1 'https://example.com/video' -q 720" -ForegroundColor White
