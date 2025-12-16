param(
  [string]$Base = "http://127.0.0.1:8000",
  [int]$TimeoutSec = 30
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

function Fail($msg) { Write-Host ("[冒烟][失败] " + $msg) -ForegroundColor Red; exit 1 }
function Ok($msg)   { Write-Host ("[冒烟][成功] " + $msg) -ForegroundColor Green }
function Info($msg) { Write-Host ("[冒烟] " + $msg) -ForegroundColor Cyan }

try {
  # 1) 健康检查
  $healthUrl = "$Base/healthz"
  Info "检查服务健康状态：$healthUrl"
  $null = Invoke-RestMethod -Method GET -Uri $healthUrl -TimeoutSec $TimeoutSec
  Ok "服务可访问（healthz 通过）"

  # 2) 执行最小用例：打开 example.com 并断言文本
  $execUrl = "$Base/api/v1/execute"
  Info "执行最小用例：POST $execUrl"

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
    Fail "执行返回 ok=false。产物目录：$($resp.artifact_dir)"
  }

  Ok "执行返回 ok=true"
  Write-Host ("[冒烟] 产物目录：" + $resp.artifact_dir)
  exit 0
}
catch {
  if ($_.Exception.Message -match "无法连接到远程服务器") {
    Fail "无法连接到服务：$Base。请先运行：.\scripts\dev.ps1（或确认端口是否正确）"
  }
  Fail $_.Exception.Message
}
