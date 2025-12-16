param(
  [switch]$InstallPlaywright = $true
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

function Info($msg) { Write-Host ("[安装] " + $msg) -ForegroundColor Cyan }
function Ok($msg)   { Write-Host ("[完成] " + $msg) -ForegroundColor Green }
function Fail($msg) { Write-Host ("[失败] " + $msg) -ForegroundColor Red; exit 1 }

try {
  # 进入仓库根目录（scripts 的上一级）
  $repoRoot = Split-Path -Parent $PSScriptRoot
  Set-Location $repoRoot
  Info "当前仓库目录：$repoRoot"

  # 1) 创建虚拟环境
  $venvDir = Join-Path $repoRoot ".venv"
  if (-not (Test-Path $venvDir)) {
    Info "未检测到 .venv，开始创建虚拟环境（Python 3.11）..."
    py -3.11 -m venv .venv
    Ok "虚拟环境已创建：$venvDir"
  } else {
    Info "已检测到 .venv，跳过创建。"
  }

  # 2) 激活虚拟环境
  $activate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"
  if (-not (Test-Path $activate)) {
    Fail "未找到虚拟环境激活脚本：$activate（请确认 .venv 创建成功）"
  }
  Info "激活虚拟环境：$activate"
  . $activate

  # 3) 升级基础工具
  Info "升级 pip / setuptools / wheel..."
  python -m pip install -U pip setuptools wheel

  # 4) 安装 backend（editable）
  $backendPath = Join-Path $repoRoot "backend"
  if (-not (Test-Path $backendPath)) {
    Fail "未找到 backend 目录：$backendPath（请确认仓库结构正确）"
  }
  Info "安装后端依赖（editable）：python -m pip install -e .\backend"
  python -m pip install -e .\backend
  Ok "后端依赖安装完成"
  # 4.1) 安装开发依赖（ruff/pytest），用于本地与 CI 的一致性
  $devReq = Join-Path $repoRoot "backend\requirements-dev.txt"
  if (Test-Path $devReq) {
    Info "安装开发依赖（ruff/pytest）..."
    python -m pip install -r $devReq
    Ok "开发依赖安装完成"
  } else {
    Info "未发现 backend\requirements-dev.txt，跳过开发依赖安装"
  }

  # 5) 可选：安装 Playwright 浏览器
  if ($InstallPlaywright) {
    Info "安装 Playwright 浏览器（首次会下载浏览器组件）..."
    python -m playwright install
    Ok "Playwright 浏览器安装完成"
  } else {
    Info "已跳过 Playwright 浏览器安装（如需 UI 自动化请手动运行：python -m playwright install）"
  }

  # 6) 验收：检查 uvicorn 是否可导入（只打印版本号，避免引号/编码坑）
  Info "验收：检查 uvicorn 是否可导入..."
  python -c "import uvicorn; print(uvicorn.__version__)"
  Ok "uvicorn 已就绪"

  Ok "环境初始化完成。下一步："
  Write-Host "  1) 启动服务：.\scripts\dev.ps1" -ForegroundColor Yellow
  Write-Host "  2) 冒烟自检：.\scripts\smoke.ps1" -ForegroundColor Yellow
}
catch {
  Fail $_.Exception.Message
}
