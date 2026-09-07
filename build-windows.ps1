$ErrorActionPreference = "Stop"

. .\release-config.ps1

function Find-Tool {
    param(
        [string]$Name,
        [string[]]$Roots
    )
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    foreach ($root in $Roots) {
        if (Test-Path -LiteralPath $root) {
            $found = Get-ChildItem -LiteralPath $root -Filter $Name -Recurse -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($found) {
                return $found.FullName
            }
        }
    }
    return $null
}

function Assert-File {
    param([string]$Path, [string]$Name)
    if (-not $Path -or -not (Test-Path -LiteralPath $Path)) {
        throw "$Name was not found. Run .\install-dev-windows.ps1 first or install $Name."
    }
}

if (-not (Test-Path -LiteralPath ".\.venv\Scripts\python.exe")) {
    .\install-dev-windows.ps1
}

$python = ".\.venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
& $python -m pip install pyinstaller

$wingetRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
$ffmpeg = Find-Tool "ffmpeg.exe" @($wingetRoot, "C:\Program Files", "C:\Program Files (x86)")
$ffprobe = Find-Tool "ffprobe.exe" @($wingetRoot, "C:\Program Files", "C:\Program Files (x86)")
$deno = Find-Tool "deno.exe" @($wingetRoot, "$env:USERPROFILE\.deno\bin", ".\.tools\deno")

Assert-File $ffmpeg "ffmpeg.exe"
Assert-File $ffprobe "ffprobe.exe"
Assert-File $deno "deno.exe"

Remove-Item -LiteralPath ".\build", ".\dist" -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path ".\release" | Out-Null

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --console `
    --name fsd `
    --collect-all yt_dlp `
    --collect-all yt_dlp_ejs `
    --add-binary "$ffmpeg;tools" `
    --add-binary "$ffprobe;tools" `
    --add-binary "$deno;tools" `
    .\fsd.py

$stageRoot = Join-Path ".\release" "fsd-downloader-v$FsdVersion-windows-x64"
$portableRoot = Join-Path $stageRoot "fsd-downloader"
Remove-Item -LiteralPath $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null
Copy-Item -LiteralPath ".\dist\fsd" -Destination $portableRoot -Recurse -Force

$zipPath = Join-Path ".\release" $FsdAssetName
Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -LiteralPath $portableRoot -DestinationPath $zipPath -Force

$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath
$checksumPath = Join-Path ".\release" "SHA256SUMS.txt"
"$($hash.Hash.ToLower())  $FsdAssetName" | Set-Content -LiteralPath $checksumPath

Write-Host "Built: $zipPath" -ForegroundColor Green
Write-Host "SHA256: $($hash.Hash.ToLower())" -ForegroundColor Green
