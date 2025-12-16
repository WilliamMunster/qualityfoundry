$ErrorActionPreference = "SilentlyContinue"

function Info([string]$msg) { Write-Host ("[STOP] " + $msg) }
function Ok([string]$msg)   { Write-Host ("[STOP][OK] " + $msg) }
function Fail([string]$msg) { Write-Host ("[STOP][FAIL] " + $msg); exit 1 }

$root = Join-Path $PSScriptRoot ".."
$pidFile = Join-Path $root ".server_pid"
$portFile = Join-Path $root ".qf_port"

$stopped = $false

# 1) 优先按 .server_pid 停止
if (Test-Path $pidFile) {
  $pidText = (Get-Content $pidFile | Select-Object -First 1).Trim()
  if ($pidText -match "^\d+$") {
    $pid = [int]$pidText
    $p = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($p) {
      Info ("停止进程 PID={0}（{1}）" -f $pid, $p.ProcessName)
      Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
      Start-Sleep -Milliseconds 300
      $stopped = $true
      Ok ("已停止 PID={0}" -f $pid)
    } else {
      Info ("PID 文件存在，但进程已不存在：PID={0}" -f $pid)
    }
  } else {
    Info ".server_pid 内容不是有效 PID，跳过按 PID 停止。"
  }
}

# 2) 若按 PID 未停掉，再按 .qf_port 查端口监听进程
if (-not $stopped -and (Test-Path $portFile)) {
  $portText = (Get-Content $portFile | Select-Object -First 1).Trim()
  if ($portText -match "^\d+$") {
    $port = [int]$portText
    $conn = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
      $own = $conn.OwningProcess
      Info ("按端口停止：127.0.0.1:{0} OwningProcess={1}" -f $port, $own)
      Stop-Process -Id $own -Force -ErrorAction SilentlyContinue
      Start-Sleep -Milliseconds 300
      $stopped = $true
      Ok ("已停止端口 {0} 的监听进程 PID={1}" -f $port, $own)
    } else {
      Info ("未发现端口 {0} 的监听进程" -f $port)
    }
  } else {
    Info ".qf_port 内容不是有效端口，跳过按端口停止。"
  }
}

# 3) 清理 .server_pid（避免下次误杀）
if (Test-Path $pidFile) {
  Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
  Info "已清理 .server_pid"
}

if (-not $stopped) {
  Fail "未找到可停止的服务进程（可能已退出）。"
}
