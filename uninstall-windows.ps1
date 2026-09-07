param(
    [string]$InstallRoot = ""
)

$ErrorActionPreference = "Stop"

try {
    . "$PSScriptRoot\release-config.ps1"
    if (-not $InstallRoot) {
        $InstallRoot = $FsdInstallRoot
    }
    $launcherDir = Join-Path $InstallRoot "bin"

    $launcher = Join-Path $launcherDir "$FsdCommandName.cmd"
    Remove-Item -LiteralPath $launcher -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $InstallRoot -Recurse -Force -ErrorAction SilentlyContinue

    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    $parts = @($userPath -split ";" | Where-Object { $_ -and $_ -ne $launcherDir })
    [Environment]::SetEnvironmentVariable("PATH", ($parts -join ";"), "User")

    Write-Host "FSD Downloader was uninstalled." -ForegroundColor Green
    Write-Host "Downloaded media and logs were preserved." -ForegroundColor Cyan
} catch {
    Write-Host "FSD Downloader uninstall failed." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    exit 1
}
