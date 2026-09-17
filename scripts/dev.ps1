# Thin wrapper around scripts/dev.py for Windows PowerShell.
#
#   .\scripts\dev.ps1 setup
#   .\scripts\dev.ps1 up | down | restart | status | logs | build | doctor
#
# scripts/dev.py holds the actual logic and is shared with macOS and Linux.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $python) {
    Write-Error "No Python found. Install 3.12, then run: python scripts\dev.py setup"
    exit 1
}

& $python (Join-Path $root "scripts\dev.py") @args
exit $LASTEXITCODE
