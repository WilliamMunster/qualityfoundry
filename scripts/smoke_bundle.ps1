param(
  [string]$Base = "http://127.0.0.1:8000",
  [int]$TimeoutSec = 60
)

$ErrorActionPreference = "Stop"

function Fail([string]$msg) { Write-Host ("[SMOKE_BUNDLE][FAIL] " + $msg); exit 1 }
function Ok([string]$msg)   { Write-Host ("[SMOKE_BUNDLE][OK] " + $msg) }
function Info([string]$msg) { Write-Host ("[SMOKE_BUNDLE] " + $msg) }

# 0) healthz
$healthUrl = "$Base/healthz"
Info "healthz: $healthUrl"
Invoke-RestMethod -Method GET -Uri $healthUrl -TimeoutSec $TimeoutSec | Out-Null
Ok "healthz reachable"

# 1) generate
$genUrl = "$Base/api/v1/generate"
Info "generate: POST $genUrl"

$genBody = @{
  title="Example Domain";
  text="Open https://example.com and see Example Domain."
} | ConvertTo-Json -Depth 10
$bundle = Invoke-RestMethod -Method POST -Uri $genUrl -ContentType "application/json" -Body $genBody -TimeoutSec $TimeoutSec

if (-not $bundle) { Fail "generate returned empty" }
if (-not $bundle.cases -or $bundle.cases.Count -lt 1) { Fail "generate returned no cases" }
Ok ("generate ok, cases=" + $bundle.cases.Count)

# 2) compile_bundle
$compileUrl = "$Base/api/v1/compile_bundle"
Info "compile_bundle: POST $compileUrl"

$compileReq = @{
  requirement = $bundle.requirement
  modules     = $bundle.modules
  objectives  = $bundle.objectives
  test_points = $bundle.test_points
  cases       = $bundle.cases
  options     = @{ target="playwright_dsl_v1"; strict=$true; default_timeout_ms=15000 }
} | ConvertTo-Json -Depth 30

$compiledResp = Invoke-RestMethod -Method POST -Uri $compileUrl -ContentType "application/json" -Body $compileReq -TimeoutSec $TimeoutSec

if (-not $compiledResp.ok) { Fail "compile_bundle ok=false" }
if (-not $compiledResp.compiled -or $compiledResp.compiled.Count -lt 1) { Fail "compile_bundle returned empty compiled list" }

$first = $compiledResp.compiled[0]
$w = ""
if ($first.warnings) { $w = ($first.warnings -join "; ") }

if (-not $first.actions -or $first.actions.Count -lt 1) {
  Fail ("compile_bundle no actions; warnings=" + $w)
}

Ok ("compile_bundle ok, compiled=" + $compiledResp.compiled.Count + ", first_actions=" + $first.actions.Count)

# 3) execute
$execUrl = "$Base/api/v1/execute"
Info "execute: POST $execUrl"

$actions = @($first.actions)

$hasGoto = $false
foreach ($a in $actions) { if ($a.type -eq "goto") { $hasGoto = $true; break } }
if (-not $hasGoto) { $actions = @(@{ type="goto"; url="https://example.com"; timeout_ms=15000 }) + $actions }

$execReq = @{
  base_url = "https://example.com"
  headless = $true
  actions  = $actions
} | ConvertTo-Json -Depth 30

$execResp = Invoke-RestMethod -Method POST -Uri $execUrl -ContentType "application/json" -Body $execReq -TimeoutSec $TimeoutSec

if (-not $execResp.ok) { Fail ("execute ok=false, artifact_dir=" + $execResp.artifact_dir) }

Ok ("ALL PASS. artifact_dir=" + $execResp.artifact_dir)
# ---- 将 artifact_dir 写入 GitHub Actions step output，方便后续精确上传本次产物 ----
# 说明：
# - $env:GITHUB_OUTPUT 在 GitHub Actions 环境中自动存在
# - Windows 路径建议转成 /，避免后续 YAML 引用时兼容性问题
if ($env:GITHUB_OUTPUT) {
  $dir = $execResp.artifact_dir
  $dir_norm = $dir -replace "\\", "/"
  "artifact_dir=$dir_norm" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
  Info ("已写出 step output: artifact_dir=" + $dir_norm)
}
