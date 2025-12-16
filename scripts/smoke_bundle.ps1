param(
  # 可不传：会优先读取项目根目录 .qf_port；读不到则默认 8000
  [string]$Base = "",
  [int]$TimeoutSec = 60
)

$ErrorActionPreference = "Stop"

function Fail([string]$msg) { Write-Host ("[SMOKE_EXEC_BUNDLE][FAIL] " + $msg); exit 1 }
function Ok([string]$msg)   { Write-Host ("[SMOKE_EXEC_BUNDLE][OK] " + $msg) }
function Info([string]$msg) { Write-Host ("[SMOKE_EXEC_BUNDLE] " + $msg) }

# 0) Base 推导（优先读取 .qf_port，避免 dev.ps1 自动换端口后脚本仍打 8000）
if (-not $Base) {
  $portFile = Join-Path $PSScriptRoot "..\.qf_port"
  if (Test-Path $portFile) {
    $p = (Get-Content $portFile | Select-Object -First 1).Trim()
    if ($p) {
      $Base = "http://127.0.0.1:$p"
    }
  }
}
if (-not $Base) { $Base = "http://127.0.0.1:8000" }
Info ("Base = " + $Base)

# 通用：请求失败时尽量把服务端返回体打印出来（FastAPI 500/422 都能看清楚 detail）
function Invoke-Json([string]$method, [string]$url, [string]$jsonBody = "") {
  try {
    if ($jsonBody) {
      return Invoke-RestMethod -Method $method -Uri $url -ContentType "application/json" -Body $jsonBody -TimeoutSec $TimeoutSec
    } else {
      return Invoke-RestMethod -Method $method -Uri $url -TimeoutSec $TimeoutSec
    }
  } catch {
    $ex = $_.Exception
    $detail = $_.ErrorDetails.Message

    # 有些情况下 ErrorDetails 为空，尝试从 WebException 的响应流读取
    if (-not $detail -and $ex.Response) {
      try {
        $reader = New-Object System.IO.StreamReader($ex.Response.GetResponseStream())
        $detail = $reader.ReadToEnd()
      } catch { }
    }

    if ($detail) {
      Fail ("请求失败：{0} {1}`n服务端返回：{2}" -f $method, $url, $detail)
    } else {
      Fail ("请求失败：{0} {1}`n异常：{2}" -f $method, $url, $ex.Message)
    }
  }
}

# 1) healthz
$healthUrl = "$Base/healthz"
Info "healthz: $healthUrl"
Invoke-Json "GET" $healthUrl | Out-Null
Ok "healthz reachable"

# 2) generate（冒烟：Example Domain）
$genUrl = "$Base/api/v1/generate"
Info "generate: POST $genUrl"

$genBody = @{
  title = "Example Domain"
  text  = "Open https://example.com and see Example Domain."
} | ConvertTo-Json -Depth 10

$bundle = Invoke-Json "POST" $genUrl $genBody

if (-not $bundle) { Fail "generate returned empty" }
if (-not $bundle.cases -or $bundle.cases.Count -lt 1) { Fail "generate returned no cases" }
Ok ("generate ok, cases=" + $bundle.cases.Count)

# 3) execute_bundle
$execBundleUrl = "$Base/api/v1/execute_bundle"
Info "execute_bundle: POST $execBundleUrl"

$req = @{
  bundle  = $bundle
  options = @{ strict=$true; default_timeout_ms=15000; headless=$true }
} | ConvertTo-Json -Depth 30

$resp = Invoke-Json "POST" $execBundleUrl $req

if (-not $resp.ok) { Fail ("execute_bundle ok=false, artifact_dir=" + $resp.artifact_dir) }
Ok ("ALL PASS. artifact_dir=" + $resp.artifact_dir)
