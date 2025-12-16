param(
  [string]$Base = "",
  [int]$TimeoutSec = 60
)

# 若未传入 Base，则优先读取根目录 .qf_port
if (-not $Base) {
  $portFile = Join-Path $PSScriptRoot "..\.qf_port"
  if (Test-Path $portFile) {
    $p = (Get-Content $portFile | Select-Object -First 1).Trim()
    if ($p) { $Base = "http://127.0.0.1:$p" }
  }
}
# 兜底：仍为空则回退到 8000
if (-not $Base) { $Base = "http://127.0.0.1:8000" }

$ErrorActionPreference = "Stop"

function Fail([string]$msg) { Write-Host ("[SMOKE_EXEC_BUNDLE][FAIL] " + $msg); exit 1 }
function Ok([string]$msg)   { Write-Host ("[SMOKE_EXEC_BUNDLE][OK] " + $msg) }
function Info([string]$msg) { Write-Host ("[SMOKE_EXEC_BUNDLE] " + $msg) }

# 0) healthz
$healthUrl = "$Base/healthz"
Info "healthz: $healthUrl"
Invoke-RestMethod -Method GET -Uri $healthUrl -TimeoutSec $TimeoutSec | Out-Null
Ok "healthz reachable"

# 1) generate
$genUrl = "$Base/api/v1/generate"
Info "generate: POST $genUrl"

$genBodyObj = @{
  title = "Example Domain"
  text  = "Open https://example.com and see Example Domain."
}
$genBody = $genBodyObj | ConvertTo-Json -Depth 10

$bundle = Invoke-RestMethod -Method POST -Uri $genUrl -ContentType "application/json" -Body $genBody -TimeoutSec $TimeoutSec
if (-not $bundle -or -not $bundle.cases -or $bundle.cases.Count -lt 1) { Fail "generate returned no cases" }

Ok ("generate ok, cases=" + $bundle.cases.Count)

# 2) execute_bundle
$execBundleUrl = "$Base/api/v1/execute_bundle"
Info "execute_bundle: POST $execBundleUrl"

$reqObj = @{
  bundle = $bundle
  case_index = 0
  compile_options = @{ target="playwright_dsl_v1"; strict=$true; default_timeout_ms=15000 }
  run = @{ base_url="https://example.com"; headless=$true }
}
$reqJson = $reqObj | ConvertTo-Json -Depth 40

$resp = Invoke-RestMethod -Method POST -Uri $execBundleUrl -ContentType "application/json" -Body $reqJson -TimeoutSec $TimeoutSec

if (-not $resp.ok) { Fail ("execute_bundle ok=false, error=" + $resp.error) }

Ok ("ALL PASS. artifact_dir=" + $resp.execution.artifact_dir)