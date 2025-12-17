param(
  # 可不传：会优先读取项目根目录 .qf_port；读不到则默认 8000
  [string]$Base = "",
  [int]$TimeoutSec = 180
)

$ErrorActionPreference = "Stop"

function Fail([string]$msg) { Write-Host ("[SMOKE_EXEC_BUNDLE][FAIL] " + $msg); exit 1 }
function Ok([string]$msg)   { Write-Host ("[SMOKE_EXEC_BUNDLE][OK] " + $msg) }
function Info([string]$msg) { Write-Host ("[SMOKE_EXEC_BUNDLE] " + $msg) }

function Resolve-Base([string]$BaseIn) {
  if ($BaseIn -and $BaseIn.Trim().Length -gt 0) { return $BaseIn.Trim() }

  $portFile = Join-Path $PSScriptRoot "..\.qf_port"
  if (Test-Path $portFile) {
    $p = (Get-Content $portFile | Select-Object -First 1).Trim()
    if ($p -match '^\d+$') { return "http://127.0.0.1:$p" }
  }
  return "http://127.0.0.1:8000"
}

function Read-HttpBodyFromException($err) {
  $detail = $null
  try { $detail = $err.ErrorDetails.Message } catch { }
  if (-not $detail -and $err.Exception -and $err.Exception.Response) {
    try {
      $sr = New-Object System.IO.StreamReader($err.Exception.Response.GetResponseStream())
      $detail = $sr.ReadToEnd()
      $sr.Close()
    } catch { }
  }
  return $detail
}

function Invoke-Json([string]$method, [string]$url, $obj = $null) {
  try {
    if ($null -ne $obj) {
      $json = $obj | ConvertTo-Json -Depth 60
      return Invoke-RestMethod -Method $method -Uri $url -ContentType "application/json" -Body $json -TimeoutSec $TimeoutSec
    } else {
      return Invoke-RestMethod -Method $method -Uri $url -TimeoutSec $TimeoutSec
    }
  } catch {
    $body = Read-HttpBodyFromException $_
    if ($body) {
      Fail ("请求失败：{0} {1}`n服务端返回：{2}" -f $method, $url, $body)
    } else {
      Fail ("请求失败：{0} {1}`n异常：{2}" -f $method, $url, $_.Exception.Message)
    }
  }
}

function Detect-ApiPrefix([string]$base) {
  $paths = (Invoke-Json "GET" "$base/openapi.json").paths.PSObject.Properties.Name
  if ($paths -contains "/api/v1/generate") { return "/api/v1" }
  if ($paths -contains "/generate") { return "" }
  Fail ("无法识别 API 路由前缀：openapi 中未找到 /api/v1/generate 或 /generate。实际 paths: " + ($paths -join ", "))
}

# ----------------------------
# 0) Base / Prefix
# ----------------------------
$Base = Resolve-Base $Base
Info ("Base = " + $Base)

# 1) healthz
$healthUrl = "$Base/healthz"
Info ("healthz: " + $healthUrl)
Invoke-Json "GET" $healthUrl | Out-Null
Ok "healthz reachable"

# 2) prefix by openapi
$prefix = Detect-ApiPrefix $Base
Info ("api prefix = '" + $prefix + "'")

# 3) generate（冒烟：Example Domain）
$genUrl = "$Base$prefix/generate"
Info ("generate: POST " + $genUrl)

$genBody = @{
  title = "Example Domain"
  text  = "Open https://example.com and see Example Domain."
}

$bundle = Invoke-Json "POST" $genUrl $genBody

if (-not $bundle) { Fail "generate returned empty" }
if (-not $bundle.cases -or $bundle.cases.Count -lt 1) { Fail "generate returned no cases" }
Ok ("generate ok, cases=" + $bundle.cases.Count)

# 防呆：确保是冒烟用例（避免 generator 被改回 Login 模板）
if ($bundle.cases.Count -ne 1 -or $bundle.cases[0].title -notmatch "Open\s+https?://") {
  Fail ("generate 结果不是冒烟用例（当前 cases=" + $bundle.cases.Count + "），请检查 generator 或入参")
}

# 4) execute_bundle（先尝试新契约：compile_options/run；失败再兜底旧 options）
$execBundleUrl = "$Base$prefix/execute_bundle"
Info ("execute_bundle: POST " + $execBundleUrl)

$newReq = @{
  bundle      = $bundle
  case_index  = 0
  compile_options = @{
    target = "playwright_dsl_v1"
    strict = $true
    default_timeout_ms = 15000
  }
  run = @{
    base_url = "https://example.com"
    headless = $true
  }
}

try {
  $resp = Invoke-RestMethod -Method POST -Uri $execBundleUrl -ContentType "application/json" -Body ($newReq | ConvertTo-Json -Depth 60) -TimeoutSec $TimeoutSec
} catch {
  Info "execute_bundle 新契约失败，尝试旧 options 兼容格式..."
  $oldReq = @{
    bundle  = $bundle
    options = @{
      strict = $true
      default_timeout_ms = 15000
      headless = $true
    }
  }
  try {
    $resp = Invoke-RestMethod -Method POST -Uri $execBundleUrl -ContentType "application/json" -Body ($oldReq | ConvertTo-Json -Depth 60) -TimeoutSec $TimeoutSec
  } catch {
    $body = Read-HttpBodyFromException $_
    if ($body) { Fail ("请求失败：POST $execBundleUrl`n服务端返回：$body") }
    Fail ("请求失败：POST $execBundleUrl`n异常：" + $_.Exception.Message)
  }
}

if (-not $resp.ok) { Fail "execute_bundle ok=false" }

$artifact = $resp.artifact_dir
Ok ("ALL PASS. artifact_dir=" + $artifact)

# 5) 写 GitHub Actions step output（可选）
if ($env:GITHUB_OUTPUT -and $artifact) {
  $dir_norm = ($artifact -replace "\\", "/")
  "artifact_dir=$dir_norm" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
  Info ("已写出 step output: artifact_dir=" + $dir_norm)
}
