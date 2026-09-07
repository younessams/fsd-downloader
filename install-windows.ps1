param(
    [string]$BundlePath = "",
    [string]$ChecksumPath = "",
    [string]$InstallRoot = ""
)

$ErrorActionPreference = "Stop"

try {
    $FsdAppName = "FSD Downloader"
    $FsdCommandName = "fsd"
    $FsdOwner = "younessams"
    $FsdRepo = "fsd-downloader"
    $FsdVersion = "1.0.0"
    $FsdTag = "v$FsdVersion"
    $FsdAssetName = "fsd-downloader-v$FsdVersion-windows-x64.zip"
    $FsdChecksumAssetName = "SHA256SUMS.txt"
    $FsdReleaseBaseUrl = "https://github.com/$FsdOwner/$FsdRepo/releases/download/$FsdTag"
    $FsdAssetUrl = "$FsdReleaseBaseUrl/$FsdAssetName"
    $FsdChecksumUrl = "$FsdReleaseBaseUrl/$FsdChecksumAssetName"
    $FsdInstallRoot = Join-Path $env:LOCALAPPDATA "Programs\FSD Downloader"

    if ($PSScriptRoot) {
        $configPath = Join-Path $PSScriptRoot "release-config.ps1"
        if (Test-Path -LiteralPath $configPath) {
            . $configPath
        }
    }
    if (-not $InstallRoot) {
        $InstallRoot = $FsdInstallRoot
    }
    $launcherDir = Join-Path $InstallRoot "bin"

    if (-not [Environment]::Is64BitOperatingSystem) {
        throw "FSD Downloader currently supports Windows x64 only."
    }

    $tempRoot = Join-Path $env:TEMP "fsd-downloader-install"
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null

    if (-not $BundlePath) {
        if (-not $FsdReleaseBaseUrl) {
            throw "Release URL is not configured yet. Provide -BundlePath for local installation tests."
        }
        $BundlePath = Join-Path $tempRoot $FsdAssetName
        Invoke-WebRequest -Uri $FsdAssetUrl -OutFile $BundlePath
        if (-not $ChecksumPath) {
            $ChecksumPath = Join-Path $tempRoot $FsdChecksumAssetName
            Invoke-WebRequest -Uri $FsdChecksumUrl -OutFile $ChecksumPath
        }
    }

    if (-not (Test-Path -LiteralPath $BundlePath)) {
        throw "Bundle not found: $BundlePath"
    }

    if ($ChecksumPath -and (Test-Path -LiteralPath $ChecksumPath)) {
        $line = Get-Content -LiteralPath $ChecksumPath | Where-Object { $_ -match [regex]::Escape((Split-Path -Leaf $BundlePath)) } | Select-Object -First 1
        if ($line) {
            $expected = ($line -split "\s+")[0].ToLower()
            $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $BundlePath).Hash.ToLower()
            if ($expected -ne $actual) {
                throw "Checksum verification failed."
            }
            Write-Host "Checksum verified." -ForegroundColor Green
        }
    }

    $extractRoot = Join-Path $tempRoot "extract"
    Expand-Archive -LiteralPath $BundlePath -DestinationPath $extractRoot -Force
    $sourceApp = Join-Path $extractRoot "fsd-downloader"
    if (-not (Test-Path -LiteralPath (Join-Path $sourceApp "fsd.exe"))) {
        throw "Invalid FSD Downloader bundle."
    }

    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
    Copy-Item -Path (Join-Path $sourceApp "*") -Destination $InstallRoot -Recurse -Force

    New-Item -ItemType Directory -Force -Path $launcherDir | Out-Null
    $launcher = Join-Path $launcherDir "$FsdCommandName.cmd"
    "@echo off`r`n`"$InstallRoot\fsd.exe`" %*" | Set-Content -LiteralPath $launcher -Encoding ASCII

    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if (-not (($userPath -split ";") -contains $launcherDir)) {
        $newPath = @($userPath, $launcherDir) | Where-Object { $_ }
        [Environment]::SetEnvironmentVariable("PATH", ($newPath -join ";"), "User")
    }

    Write-Host "FSD Downloader installed successfully." -ForegroundColor Green
    Write-Host "Open a new PowerShell or CMD and run: fsd" -ForegroundColor Cyan
} catch {
    Write-Host "FSD Downloader installation failed." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    exit 1
}
