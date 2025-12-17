param(
  [string]$Base,
  [int]$TimeoutSec = 180
)

$ErrorActionPreference = "Stop"

function Fail([string]$msg) { Write-Host ("[SMOKE_EXEC_BUNDLE][FAIL] " + $msg); exit 1 }
function Ok([string]$msg)   { Write-Host ("[SMOKE_EXEC_BUNDLE][OK] " + $msg) }
function Info([string]$msg) { Write-Host ("[SMOKE_EXEC_BUNDLE] " + $msg) }

# 0) 自动确定 Base：优先使用入参，其次读取 .qf_port，最后回退到 8000
if (-not $Base -or $Base.Trim().Length -eq 0) {
  $portFile = Join-Path $PSScriptRoot "..\.qf_port"
  if (Test-Path $portFile) {
    $p = (Get-Content $portFile | Select-Object -First 1).Trim()
    if ($p -match '^\d+$') {
      $Base = "http://127.0.0.1:$p"
    }
  }
}
if (-not $Base -or $Base.Trim().Length -eq 0) {
  $Base = "http://127.0.0.1:8000"
}

Info ("Base = " + $Base)

# 1) healthz
$healthUrl = "$Base/healthz"
Info "healthz: $healthUrl"
try {
  Invoke-RestMethod -Method GET -Uri $healthUrl -TimeoutSec $TimeoutSec | Out-Null
} catch {
  Fail ("无法访问 healthz：" + $_.Exception.Message)
}
Ok "healthz reachable"

# 2) generate（冒烟：Example Domain）
$genUrl = "$Base/api/v1/generate"
Info "generate: POST $genUrl"

$genBodyObj = @{
  title = "Example Domain"
  text  = "Open https://example.com and see Example Domain."
}
$genBody = $genBodyObj | ConvertTo-Json -Depth 10

try {
  $bundle = Invoke-RestMethod -Method POST -Uri $genUrl -ContentType "application/json" -Body $genBody -TimeoutSec $TimeoutSec
} catch {
  Fail ("请求失败：POST $genUrl`n" + $_.Exception.Message)
}

if (-not $bundle) { Fail "generate returned empty" }
if (-not $bundle.cases -or $bundle.cases.Count -lt 1) { Fail "generate returned no cases" }
Ok ("generate ok, cases=" + $bundle.cases.Count)

# 防呆：确保是冒烟用例（避免 generator 被改回 Login 模板）
if ($bundle.cases.Count -ne 1 -or $bundle.cases[0].title -notmatch "Open\s+https?://") {
  Fail ("generate 结果不是冒烟用例（当前 cases=" + $bundle.cases.Count + "），请检查 generator 或入参")
}

# 3) execute_bundle
$execBundleUrl = "$Base/api/v1/execute_bundle"
Info "execute_bundle: POST $execBundleUrl"

# 关键：ExecuteBundleRequest 需要 "bundle" 包裹（不要把 bundle 拍平）
$execReqObj = @{
  bundle = $bundle
  case_index = 0
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

$execReqJson = $execReqObj | ConvertTo-Json -Depth 50

try {
  $resp = Invoke-RestMethod -Method POST -Uri $execBundleUrl -ContentType "application/json" -Body $execReqJson -TimeoutSec $TimeoutSec
} catch {
  # 关键：把 HTTP 响应体读出来（422/500 的 JSON 都在这里）
  $bodyText = ""
  try {
    $r = $_.Exception.Response
    if ($r -and $r.GetResponseStream()) {
      $sr = New-Object System.IO.StreamReader($r.GetResponseStream())
      $bodyText = $sr.ReadToEnd()
      $sr.Close()
    }
  } catch { }

  if (-not $bodyText) {
    # 兜底：至少把异常信息打印出来
    $bodyText = ($_.Exception.Message | Out-String)
  }

  Fail ("请求失败：POST $execBundleUrl`n服务端返回：$bodyText")
}

if (-not $resp.ok) { Fail ("execute_bundle ok=false") }
Ok ("ALL PASS. artifact_dir=" + $resp.artifact_dir)


# 4) 写 GitHub Actions step output（可选）
if ($env:GITHUB_OUTPUT -and $resp.artifact_dir) {
  $dir_norm = ($resp.artifact_dir -replace "\\", "/")
  "artifact_dir=$dir_norm" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
  Info ("已写出 step output: artifact_dir=" + $dir_norm)
}
