param(
  [string]$Base = "http://127.0.0.1:8000",
  [int]$TimeoutSec = 30
)

$ErrorActionPreference = "Stop"

function Fail($msg) {
  Write-Host "[SMOKE][FAIL] $msg" -ForegroundColor Red
  exit 1
}

function Ok($msg) {
  Write-Host "[SMOKE][OK] $msg" -ForegroundColor Green
}

try {
  # 1) Health check
  $healthUrl = "$Base/healthz"
  $health = Invoke-RestMethod -Method GET -Uri $healthUrl -TimeoutSec $TimeoutSec
  Ok "Healthz reachable: $healthUrl"

  # 2) Execute a minimal scenario
  $execUrl = "$Base/api/v1/execute"
  $payload = @{
    base_url = "https://example.com"
    headless = $true
    actions  = @(
      @{ type = "goto"; url = "https://example.com" },
      @{
        type    = "assert_text"
        locator = @{ strategy = "text"; value = "Example Domain"; exact = $false }
        value   = "Example Domain"
      }
    )
  } | ConvertTo-Json -Depth 10

  $resp = Invoke-RestMethod -Method POST -Uri $execUrl -ContentType "application/json" -Body $payload -TimeoutSec $TimeoutSec

  if (-not $resp.ok) {
    Fail "Execute returned ok=false. artifact_dir=$($resp.artifact_dir)"
  }

  Ok "Execute ok=true"
  Write-Host ("artifact_dir: " + $resp.artifact_dir)

  # Optional: print first failing evidence if exists (defensive)
  $bad = $resp.evidence | Where-Object { $_.ok -ne $true } | Select-Object -First 1
  if ($null -ne $bad) {
    Write-Host ("first failure: step=" + $bad.index + " error=" + $bad.error)
  }

  exit 0
}
catch {
  Fail $_.Exception.Message
}
