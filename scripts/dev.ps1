param(
  [string]$HostAddr = "127.0.0.1",
  [int]$Port = 8000,
  [switch]$AutoSetup = $false
)

# 统一输出编码，避免中文乱码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

function Info($msg) { Write-Host ("[开发] " + $msg) -ForegroundColor Cyan }
function Ok($msg)   { Write-Host ("[开发] " + $msg) -ForegroundColor Green }
function Warn($msg) { Write-Host ("[开发] " + $msg) -ForegroundColor Yellow }
function Fail($msg) { Write-Host ("[开发] " + $msg) -ForegroundColor Red; exit 1 }

try {
  # 进入仓库根目录（scripts 的上一级）
  $repoRoot = Split-Path -Parent $PSScriptRoot
  Set-Location $repoRoot

  # 1) 激活虚拟环境（如果存在）
  $activate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"
  if (Test-Path $activate) {
    Info "激活虚拟环境：$activate"
    . $activate
  } else {
    Warn "未检测到虚拟环境 .venv。"
    Warn "请先运行：.\scripts\setup.ps1（创建虚拟环境并安装依赖）"

    if ($AutoSetup) {
      Info "已开启 -AutoSetup，自动执行 setup.ps1..."
      & (Join-Path $repoRoot "scripts\setup.ps1") | Out-Host

      if (-not (Test-Path $activate)) {
        Fail "自动安装后仍未发现 .venv，请检查 setup 输出。"
      }
      . $activate
    } else {
      exit 1
    }
  }

  # 2) 启动服务（使用 python -m uvicorn，避免 PATH 问题）
  Info "启动服务：uvicorn qualityfoundry.main:app --reload --host $HostAddr --port $Port"
  Info "Swagger 地址：http://$HostAddr`:$Port/docs"

  python -m uvicorn qualityfoundry.main:app --reload --host $HostAddr --port $Port
}
catch {
  # 常见错误：依赖未安装（例如 uvicorn）
  if ($_.Exception.Message -match "No module named uvicorn") {
    Fail "未安装 uvicorn。请先执行：.\scripts\setup.ps1"
  }
  Fail $_.Exception.Message
}
