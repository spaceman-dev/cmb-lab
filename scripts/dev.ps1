# Run cmb-lab on Windows.
#
#   .\scripts\dev.ps1 up          build if needed, start, wait, print the URL
#   .\scripts\dev.ps1 down | status | logs | doctor
#   .\scripts\dev.ps1 up -Backend wsl      use WSL instead of Docker
#
# healpy has no Windows build, so nothing runs natively here. Docker is the default;
# WSL is available with -Backend wsl. scripts/dev.py holds all the logic and is shared
# with macOS and Linux.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# Find any Python. dev.py uses only the standard library, so the version barely matters.
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $python) {
    $python = (Get-Command py -ErrorAction SilentlyContinue).Source
}

if ($python) {
    & $python (Join-Path $root "scripts\dev.py") @args
    exit $LASTEXITCODE
}

# No Python at all. Docker alone is enough to build and run everything, so do that
# directly rather than making the user install Python just to call docker twice.
Write-Host "No Python found; using Docker directly." -ForegroundColor Yellow
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Neither Python nor Docker found. Install Docker Desktop: https://docs.docker.com/desktop/install/windows-install/"
    exit 1
}

$command = if ($args.Count -gt 0) { $args[0] } else { "up" }
switch ($command) {
    "down"   { docker rm -f cmb-lab; exit $LASTEXITCODE }
    "logs"   { docker logs -f --tail 50 cmb-lab; exit $LASTEXITCODE }
    "status" { docker ps --filter "name=^cmb-lab$"; exit $LASTEXITCODE }
    default {
        Push-Location $root
        docker build -t cmb-lab .
        if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
        docker rm -f cmb-lab 2>$null | Out-Null
        docker run -d --name cmb-lab -p 7860:7860 -v cmb-lab-data:/app/data cmb-lab
        Pop-Location
        Write-Host "starting... then open http://localhost:7860" -ForegroundColor Green
        exit $LASTEXITCODE
    }
}
