param(
  [string]$HostAddr = "127.0.0.1",
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

function Info($msg) {
  Write-Host "[DEV] $msg"
}

# Go to repo root (script parent is scripts/)
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# Activate venv if present
$activate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $activate) {
  Info "Activating venv: $activate"
  . $activate
} else {
  Info "No .venv found at $repoRoot\.venv (skip activation)."
  Info "If first time on this machine, run: python -m venv .venv; python -m pip install -e .\backend"
}

# Start server
Info "Starting server: uvicorn qualityfoundry.main:app --reload --host $HostAddr --port $Port"
python -m uvicorn qualityfoundry.main:app --reload --host $HostAddr --port $Port
