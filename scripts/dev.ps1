<#
QualityFoundry - 本地开发启动脚本（Windows / PowerShell）

目标：
1) 自动激活 .venv（如果存在）
2) 检查 uvicorn 是否可用（不可用给出明确中文指引）
3) 默认使用 8000；若端口被占用，自动递增寻找可用端口（8001, 8002...）
4) 启动服务并等待 /healthz 就绪
5) 就绪后写入 .\.qf_port（供 smoke 脚本复用），并写入 .\.server_pid（便于停服）
6) 输出 docs/healthz 地址

用法：
- .\scripts\dev.ps1
- .\scripts\dev.ps1 -Port 8000
- .\scripts\dev.ps1 -BindHost "127.0.0.1" -Port 8000 -AutoPort:$true
#>

param(
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8000,
  [switch]$AutoPort = $true,
  [int]$MaxPortTry = 20,
  [int]$ReadyWaitSec = 30
)

$ErrorActionPreference = "Stop"

function Info([string]$msg) { Write-Host ("[DEV] " + $msg) }
function Ok([string]$msg)   { Write-Host ("[DEV][OK] " + $msg) }
function Fail([string]$msg) { Write-Host ("[DEV][FAIL] " + $msg); exit 1 }

function Test-PortFree([string]$bindHost, [int]$port) {
  # 返回 $true 表示端口未被占用（可用）
  try {
    Get-NetTCPConnection -LocalAddress $bindHost -LocalPort $port -State Listen -ErrorAction Stop | Out-Null
    return $false
  } catch {
    return $true
  }
}

function Pick-Port([string]$bindHost, [int]$port, [int]$maxTry) {
  if (Test-PortFree $bindHost $port) { return $port }

  if (-not $AutoPort) {
    Fail ("端口被占用：{0}:{1}。你已关闭自动换端口（-AutoPort:$false）。" -f $bindHost, $port)
  }

  Info ("端口已占用：{0}:{1}，开始自动寻找可用端口..." -f $bindHost, $port)

  for ($i=1; $i -le $maxTry; $i++) {
    $p = $port + $i
    if (Test-PortFree $bindHost $p) { return $p }
  }

  Fail ("连续尝试 {0} 个端口仍不可用，请检查系统端口占用情况。" -f $maxTry)
}

try {
  # 1) 尝试激活虚拟环境（若存在）
  $venvActivate = Join-Path $PSScriptRoot "..\.venv\Scripts\Activate.ps1"
  if (Test-Path $venvActivate) {
    Info "检测到 .venv，正在激活虚拟环境..."
    . $venvActivate
    Ok "虚拟环境已激活"
  } else {
    Info "未检测到 .venv（将使用当前 Python 环境）。若是新机器建议先执行：python -m venv .venv; python -m pip install -e .\backend"
  }

  # 2) Python 命令（确保不为空）
  $py = "python"
  try { & $py -V | Out-Null } catch { Fail "未找到可用的 python 命令，请确认已安装 Python 并在 PATH 中可用。" }

  # 3) 检查 uvicorn 是否可用
  $uvicornOk = $false
  try {
    & $py -c "import uvicorn; print(uvicorn.__version__)" | Out-Null
    $uvicornOk = $true
  } catch {
    $uvicornOk = $false
  }
  if (-not $uvicornOk) {
    Fail "未安装 uvicorn。请先执行：python -m pip install -e .\backend"
  }

  # 4) 选择端口
  $finalPort = Pick-Port $BindHost $Port $MaxPortTry
  if ($finalPort -ne $Port) { Ok ("已选择可用端口：{0}" -f $finalPort) } else { Ok ("端口可用：{0}" -f $finalPort) }

  # 5) 启动 uvicorn（后台启动，便于探活）
  Info ("启动服务：uvicorn qualityfoundry.main:app --reload --host {0} --port {1}" -f $BindHost, $finalPort)

  $proc = Start-Process -FilePath $py -ArgumentList @(
    "-m","uvicorn","qualityfoundry.main:app",
    "--reload",
    "--host",$BindHost,
    "--port",$finalPort
  ) -PassThru

  # 6) 等待 healthz 就绪（成功后才写 .qf_port）
  $health = "http://$BindHost`:$finalPort/healthz"
  Info ("等待服务就绪（最多 {0}s）：{1}" -f $ReadyWaitSec, $health)

  $ready = $false
  for ($i=0; $i -lt $ReadyWaitSec; $i++) {
    try {
      Invoke-RestMethod -Method GET -Uri $health -TimeoutSec 2 | Out-Null
      $ready = $true
      break
    } catch {
      Start-Sleep -Seconds 1
    }
  }

  if (-not $ready) {
    Info ("服务未能就绪，尝试终止进程 PID=" + $proc.Id)
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Fail "服务未能在指定时间内启动成功。"
  }

  # 7) 服务就绪：写入端口和 PID 文件（供 smoke/停服使用）
  Set-Content -Path (Join-Path $PSScriptRoot "..\.qf_port") -Value $finalPort -Encoding ascii
  Set-Content -Path (Join-Path $PSScriptRoot "..\.server_pid") -Value $proc.Id -Encoding ascii
  Ok ("服务已就绪：PID={0}，端口={1}（已写入 .qf_port / .server_pid）" -f $proc.Id, $finalPort)

  Info ("Docs  : http://{0}:{1}/docs" -f $BindHost, $finalPort)
  Info ("Health: http://{0}:{1}/healthz" -f $BindHost, $finalPort)
  Info ("提示：按 Ctrl+C 不会自动停掉后台进程。如需关闭请执行：Stop-Process -Id {0} -Force" -f $proc.Id)

} catch {
  Fail ("启动失败：" + $_.Exception.Message)
}
