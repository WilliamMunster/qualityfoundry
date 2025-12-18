from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional, NoReturn
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import typer
from rich import print

from qualityfoundry.models.schemas import (
    Action,
    ActionType,
    ExecutionRequest,
    Locator,
    RequirementInput,
)
from qualityfoundry.services.execution.executor import execute
from qualityfoundry.services.generation.generator import generate_bundle

app = typer.Typer(add_completion=False, help="QualityFoundry CLI")


# ============================================================
# 路径约定（与 scripts/*.ps1 对齐）
# - .qf_port      : dev 启动后写入可用端口，smoke 默认读取
# - .server_pid   : dev 启动后写入 PID，stop 用于停服
# - .qf_dev.log   : dev 后台启动日志（默认）
# ============================================================


def _find_repo_root() -> Path:
    """
    从当前文件向上寻找 repo 根目录：
    - 优先：包含 backend 目录的父目录
    - 兜底：当前工作目录
    """
    p = Path(__file__).resolve()
    for _ in range(12):
        if (p / "backend").exists():
            return p
        p = p.parent
    return Path.cwd().resolve()


REPO_ROOT = _find_repo_root()
PORT_FILE = REPO_ROOT / ".qf_port"
PID_FILE = REPO_ROOT / ".server_pid"
LOG_FILE_DEFAULT = REPO_ROOT / ".qf_dev.log"


# ============================================================
# 小工具：日志
# ============================================================
def _info(msg: str) -> None:
    print(f"[cyan][QF][/cyan] {msg}")


def _ok(msg: str) -> None:
    print(f"[green][QF][OK][/green] {msg}")


def _fail(msg: str, code: int = 1) -> NoReturn:
    """
    统一失败出口：
    - 打印 FAIL 信息
    - 抛出 typer.Exit(code)
    - 额外在异常对象上附加 qf_message，便于 smoke 生成 summary.json / junit.xml
    """
    print(f"[red][QF][FAIL][/red] {msg}")
    e = typer.Exit(code)
    setattr(e, "qf_message", msg)
    raise e


# ============================================================
# 小工具：端口检测/挑选
# ============================================================
def _is_port_free(host: str, port: int) -> bool:
    """返回 True 表示可用（未被占用）。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def _pick_port(host: str, start_port: int, max_try: int) -> int:
    """从 start_port 开始递增，挑选可用端口。"""
    p = start_port
    for _ in range(max_try):
        if _is_port_free(host, p):
            return p
        p += 1
    _fail(f"从 {start_port} 起尝试 {max_try} 个端口仍不可用，请检查端口占用情况。")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


# ============================================================
# 小工具：HTTP（stdlib，避免额外依赖）
# ============================================================
def _http_json(
    method: str,
    url: str,
    payload: Optional[dict[str, Any]] = None,
    timeout_sec: int = 30,
) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url=url, data=data, method=method.upper(), headers=headers)
    try:
        with urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return None
            return json.loads(raw)
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = ""
        raise RuntimeError(f"HTTP {e.code} {e.reason} for {method} {url}; body={body}") from e
    except URLError as e:
        raise RuntimeError(f"Network error for {method} {url}: {e}") from e


def _utc_run_id(prefix: str) -> str:
    # e.g. smoke_20251218T040102Z
    return time.strftime(f"{prefix}_%Y%m%dT%H%M%SZ", time.gmtime())


def _write_json_file(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _wait_ready(base: str, timeout_sec: int = 45) -> None:
    """
    等待服务就绪（质量闸门语义）：
    - 优先探测 /health（你已新增）
    - 兼容探测 /healthz（旧约定）
    - 兜底探测 /openapi.json
    超时：exit code = 10
    """
    health_url = f"{base}/health"
    healthz_url = f"{base}/healthz"
    openapi_url = f"{base}/openapi.json"

    start = time.time()
    while True:
        # 1) /health
        try:
            _http_json("GET", health_url, None, timeout_sec=2)
            return
        except Exception:
            pass

        # 2) /healthz（兼容）
        try:
            _http_json("GET", healthz_url, None, timeout_sec=2)
            return
        except Exception:
            pass

        # 3) /openapi.json（兜底）
        try:
            _http_json("GET", openapi_url, None, timeout_sec=2)
            return
        except Exception:
            pass

        if time.time() - start > timeout_sec:
            _fail(
                f"服务未能在 {timeout_sec}s 内就绪：{health_url} / {healthz_url} / {openapi_url}",
                code=10,
            )
        time.sleep(1)


def _detect_api_prefix(base: str) -> str:
    """
    自动识别 API 前缀：
    - 如果 OpenAPI 里有 /api/v1/generate 则 prefix='/api/v1'
    - 如果有 /generate 则 prefix=''
    - 否则：保守默认 '/api/v1'
    """
    openapi = _http_json("GET", f"{base}/openapi.json", None, timeout_sec=10)
    paths = set((openapi or {}).get("paths", {}).keys())

    if "/api/v1/generate" in paths:
        return "/api/v1"
    if "/generate" in paths:
        return ""

    for candidate in ("/api/v1", "/v1", "/api"):
        if f"{candidate}/generate" in paths:
            return candidate

    return "/api/v1"


# ============================================================
# 小工具：JUnit XML（无第三方依赖）
# ============================================================
def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _write_junit_xml(
    path: Path,
    *,
    suite_name: str,
    case_name: str,
    ok: bool,
    duration_sec: float,
    failure_message: Optional[str] = None,
    system_out: Optional[str] = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tests = 1
    failures = 0 if ok else 1
    errors = 0
    time_attr = f"{duration_sec:.3f}"

    parts: list[str] = []
    parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    parts.append(
        f'<testsuite name="{_xml_escape(suite_name)}" tests="{tests}" failures="{failures}" errors="{errors}" time="{time_attr}">'
    )
    parts.append(
        f'  <testcase classname="{_xml_escape(suite_name)}" name="{_xml_escape(case_name)}" time="{time_attr}">'
    )
    if not ok:
        msg = _xml_escape(failure_message or "smoke failed")
        parts.append(f'    <failure message="{msg}">{msg}</failure>')
    if system_out:
        out = _xml_escape(system_out)
        parts.append(f"    <system-out>{out}</system-out>")
    parts.append("  </testcase>")
    parts.append("</testsuite>")

    path.write_text("\n".join(parts), encoding="utf-8")


# ============================================================
# 你原有命令：保持不变（serve / generate / run）
# ============================================================
@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000):
    """Run FastAPI server."""
    import uvicorn

    uvicorn.run("qualityfoundry.main:app", host=host, port=port, reload=True)


@app.command()
def generate(
    title: str = typer.Option(..., help="Requirement title"),
    text: str = typer.Option(..., help="Requirement text"),
    out: Path = typer.Option(Path("../../../bundle.json"), help="Output JSON file"),
):
    """Generate a structured case bundle (MVP deterministic generator)."""
    bundle = generate_bundle(RequirementInput(title=title, text=text))
    out.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    print(f"[green]Wrote[/green] {out}")


@app.command()
def run(
    url: str = typer.Option("https://example.com", help="Target URL"),
    headless: bool = typer.Option(True, help="Headless mode"),
):
    """Run a minimal example against a URL (DSL -> Playwright)."""
    req = ExecutionRequest(
        base_url=url,
        headless=headless,
        actions=[
            Action(type=ActionType.GOTO, url=url),
            Action(
                type=ActionType.ASSERT_VISIBLE,
                locator=Locator(strategy="text", value="Example Domain", exact=False),
            ),
        ],
    )
    result = execute(req)
    print(result.model_dump_json(indent=2))


# ============================================================
# 新增：dev / stop / smoke（统一入口）
# ============================================================
@app.command()
def dev(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host"),
    port: int = typer.Option(8000, "--port", help="Preferred port"),
    max_port_try: int = typer.Option(20, "--max-port-try", help="Max port scan attempts"),
    log_file: Path = typer.Option(LOG_FILE_DEFAULT, "--log-file", help="Uvicorn log file"),
):
    """
    本地开发启动（后台启动）：
    - 自动找端口（优先 --port）
    - 等待服务就绪（health/healthz/openapi）
    - 成功后写 .qf_port / .server_pid
    - 日志写入 --log-file
    """
    final_port = _pick_port(host, port, max_port_try)

    args = [
        sys.executable,
        "-m",
        "uvicorn",
        "qualityfoundry.main:app",
        "--host",
        host,
        "--port",
        str(final_port),
        "--reload",
    ]

    base = f"http://{host}:{final_port}"
    _info(f"Repo root: {REPO_ROOT}")
    _info(f"启动服务（后台）：{' '.join(args)}")
    _info(f"日志文件：{log_file}")

    log_file.parent.mkdir(parents=True, exist_ok=True)
    logf = open(log_file, "a", encoding="utf-8")

    try:
        proc = subprocess.Popen(
            args,
            cwd=str(REPO_ROOT),
            stdout=logf,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    except Exception as e:
        logf.close()
        _fail(f"启动 uvicorn 失败：{e}")

    _wait_ready(base, timeout_sec=45)

    _write_text(PORT_FILE, str(final_port))
    _write_text(PID_FILE, str(proc.pid))

    _ok(f"服务已就绪：PID={proc.pid}, base={base}")
    _info(f"Docs   : {base}/docs")
    _info(f"OpenAPI : {base}/openapi.json")
    _info("提示：后台进程不会随 Ctrl+C 自动停止；如需关闭请执行：qf stop")


@app.command()
def stop():
    """
    停止由 qf dev 启动的后台服务：
    - 读取 .server_pid
    - Windows 下用 taskkill /T /F 确保子进程一并退出
    - 清理 .server_pid / .qf_port
    """
    if not PID_FILE.exists():
        _fail("未找到 .server_pid；没有可停止的后台服务。")

    pid_str = _read_text(PID_FILE)
    if not pid_str.isdigit():
        _fail(f".server_pid 内容异常：{pid_str}")

    pid = int(pid_str)
    _info(f"Stopping PID={pid}")

    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F", "/T"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        else:
            os.kill(pid, 9)
    except Exception:
        pass

    try:
        PID_FILE.unlink(missing_ok=True)
        PORT_FILE.unlink(missing_ok=True)
    except Exception:
        pass

    _ok("已停止（若进程不存在也视为完成）")


@app.command()
def smoke(
    base: str = typer.Option("", "--base", help="Server base URL, e.g. http://127.0.0.1:8000"),
    url: str = typer.Option("https://example.com", "--url", help="Target URL"),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="Headless mode"),
    timeout_sec: int = typer.Option(180, "--timeout-sec", help="HTTP timeout"),
    wait_ready: int = typer.Option(45, "--wait-ready", help="Wait server ready seconds (0 to skip)"),
    json_out: Optional[Path] = typer.Option(None, "--json", help="Write smoke summary JSON to file"),
    junit_out: Optional[Path] = typer.Option(None, "--junit", help="Write JUnit XML report to file"),
    artifacts_dir: Optional[Path] = typer.Option(
        None,
        "--artifacts-dir",
        help="Write smoke artifacts under this directory (creates a timestamped run subdir)",
    ),
    mode: str = typer.Option("execute", "--mode", help="execute|bundle|both"),
    case_index: int = typer.Option(0, "--case-index", help="Which case to execute in bundle mode"),
):
    """
    冒烟：仅验证 executor 最小链路，不覆盖自然语言编译能力
    - execute: 只验证 /execute（最小链路，推荐默认）
    - bundle : 验证 /generate + /execute_bundle（当前编译器不支持 login 文本会失败）
    - both   : 先 execute 再 bundle（bundle 失败降级为 warning）
    """
    # 1) 解析 base：优先参数，其次 .qf_port
    if not base and PORT_FILE.exists():
        port_s = _read_text(PORT_FILE)
        if port_s.isdigit():
            base = f"http://127.0.0.1:{port_s}"

    if not base:
        _fail("未提供 --base，且未找到 .qf_port；请先 qf dev 或传入 --base。", code=2)

    started_at = time.time()

    # 2) 本次 smoke 运行目录（用于 request/response evidence）
    run_id = _utc_run_id("smoke")
    run_dir: Optional[Path] = None

    # 若用户只传了 --json，则默认把 artifacts 放在 summary.json 同目录下（更省心）
    if artifacts_dir is None and json_out is not None:
        artifacts_dir = json_out.parent

    if artifacts_dir is not None:
        run_dir = artifacts_dir / run_id
        (run_dir / "http").mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "ok": False,
        "base": base,
        "mode": (mode or "").strip().lower(),
        "api_prefix": None,
        "checks": [],
        "artifact_dir": None,       # normalized (/) for contract
        "artifact_dir_raw": None,   # raw value from server (Windows may contain '\')
        "smoke_artifacts_dir": (str(run_dir).replace("\\", "/") if run_dir else None),
        "exit_code": None,
        "error": None,
        "duration_ms": None,
    }

    def _write_summary() -> None:
        if json_out is None:
            return
        try:
            json_out.parent.mkdir(parents=True, exist_ok=True)
            json_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            _info(f"wrote summary json: {json_out}")
        except Exception as e:
            _info(f"[WARN] 写入 summary json 失败：{e}")

    def _write_junit() -> None:
        if junit_out is None:
            return
        try:
            duration_sec = max(0.0, time.time() - started_at)
            case_name = f"smoke:{summary.get('mode','execute')}"
            msg = None
            if not summary.get("ok"):
                err = summary.get("error") or {}
                msg = err.get("message") or "smoke failed"

            _write_junit_xml(
                junit_out,
                suite_name="qualityfoundry.smoke",
                case_name=case_name,
                ok=bool(summary.get("ok")),
                duration_sec=duration_sec,
                failure_message=msg,
                system_out=json.dumps(summary, ensure_ascii=False, indent=2),
            )
            _info(f"wrote junit xml: {junit_out}")
        except Exception as e:
            _info(f"[WARN] 写入 junit.xml 失败：{e}")

    def _dump_http(name: str, req_obj: Any, resp_obj: Any) -> None:
        if run_dir is None:
            return
        try:
            _write_json_file(run_dir / "http" / f"{name}.request.json", req_obj)
            _write_json_file(run_dir / "http" / f"{name}.response.json", resp_obj)
        except Exception as e:
            _info(f"[WARN] 写入 HTTP evidence 失败：{e}")

    try:
        _info(f"Base = {base}")

        if wait_ready > 0:
            _wait_ready(base, timeout_sec=wait_ready)

        _ok("server reachable")
        summary["checks"].append({"name": "server_reachable", "ok": True})

        prefix = _detect_api_prefix(base)
        summary["api_prefix"] = prefix
        _info(f"api prefix = '{prefix or '/'}'")

        mode_norm = summary["mode"]
        if mode_norm not in {"execute", "bundle", "both"}:
            _fail(f"--mode 仅支持 execute|bundle|both，当前={mode}", code=2)

        # ------------------------------------------------------------------
        # A) execute 最小链路：直接调用 /execute
        # ------------------------------------------------------------------
        def _smoke_execute() -> None:
            exec_url = f"{base}{prefix}/execute"
            _info(f"execute: POST {exec_url}")
            exec_req = {
                "base_url": url,
                "headless": headless,
                "actions": [
                    {"type": "goto", "url": url},
                    {
                        "type": "assert_text",
                        "locator": {"strategy": "text", "value": "Example Domain", "exact": False},
                        "value": "Example Domain",
                    },
                ],
            }
            exec_resp = _http_json("POST", exec_url, exec_req, timeout_sec=timeout_sec)

            # evidence：无论 ok/false 都落盘，便于定位
            _dump_http("execute", exec_req, exec_resp)

            if not (exec_resp or {}).get("ok"):
                _fail(
                    f"execute ok=false, resp={json.dumps(exec_resp, ensure_ascii=False)[:1200]}",
                    code=30,
                )

            raw = (exec_resp or {}).get("artifact_dir")
            summary["artifact_dir_raw"] = raw
            summary["artifact_dir"] = (raw or "").replace("\\", "/")
            summary["checks"].append({"name": "execute_ok", "ok": True})

            _ok(f"execute PASS. artifact_dir={raw}")

        # ------------------------------------------------------------------
        # B) bundle 链路：generate + execute_bundle（当前可能失败，both 下为 warning）
        # ------------------------------------------------------------------
        def _smoke_bundle(strict: bool) -> None:
            gen_url = f"{base}{prefix}/generate"
            gen_body = {"title": "Smoke", "text": f"Open {url} and verify basic availability."}
            _info(f"generate: POST {gen_url}")
            bundle = _http_json("POST", gen_url, gen_body, timeout_sec=timeout_sec)
            _dump_http("generate", gen_body, bundle)

            cases = (bundle or {}).get("cases") or []
            if not cases:
                msg = "generate 返回 cases=0（冒烟要求至少为 1）"
                if strict:
                    _fail(msg, code=20)
                _info(f"[WARN] {msg}")
                return

            if case_index < 0 or case_index >= len(cases):
                msg = f"case_index={case_index} 越界：cases={len(cases)}"
                if strict:
                    _fail(msg, code=20)
                _info(f"[WARN] {msg}")
                return

            _ok(f"generate ok, cases={len(cases)}, use case_index={case_index}")

            exec_bundle_url = f"{base}{prefix}/execute_bundle"
            _info(f"execute_bundle: POST {exec_bundle_url}")
            exec_bundle_req = {"bundle": bundle, "case_index": case_index, "headless": headless}
            exec_bundle_resp = _http_json("POST", exec_bundle_url, exec_bundle_req, timeout_sec=timeout_sec)
            _dump_http("execute_bundle", exec_bundle_req, exec_bundle_resp)

            if not (exec_bundle_resp or {}).get("ok"):
                msg = f"execute_bundle ok=false, resp={json.dumps(exec_bundle_resp, ensure_ascii=False)[:1200]}"
                if strict:
                    _fail(msg, code=30)
                _info(f"[WARN] {msg}")
                return

            raw = (exec_bundle_resp or {}).get("artifact_dir")
            summary["artifact_dir_raw"] = raw
            summary["artifact_dir"] = (raw or "").replace("\\", "/")
            summary["checks"].append({"name": "execute_bundle_ok", "ok": True})

            _ok(f"execute_bundle PASS. artifact_dir={raw}")

        # 执行模式
        if mode_norm == "execute":
            _smoke_execute()
        elif mode_norm == "bundle":
            _smoke_bundle(strict=True)
        else:
            _smoke_execute()
            _smoke_bundle(strict=False)

        summary["ok"] = True
        summary["exit_code"] = 0

    except typer.Exit as e:
        code = int(getattr(e, "exit_code", 1) or 1)
        summary["ok"] = False
        summary["exit_code"] = code
        summary["error"] = {
            "type": "typer.Exit",
            "message": getattr(e, "qf_message", "smoke failed"),
        }
        raise

    except Exception as e:
        summary["ok"] = False
        summary["exit_code"] = 1
        summary["error"] = {"type": type(e).__name__, "message": str(e)}
        _fail(f"unexpected error: {e}", code=1)

    finally:
        summary["duration_ms"] = int((time.time() - started_at) * 1000)
        if summary["exit_code"] is None:
            summary["exit_code"] = 0 if summary["ok"] else 1
        _write_summary()
        _write_junit()


if __name__ == "__main__":
    app()
