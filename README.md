# QualityFoundry 🏗️🧪

QualityFoundry 是一个 **Python-first** 的测试与质量闸门（Quality Gate）工具链，目标是把“**最小可验证链路**”做成可本地复用、可 CI 消费、可持续演进的工程能力。

当前阶段聚焦两件事：
- **最小门禁（smoke）**：服务可达 + `/execute` 最小链路可执行，并输出 CI 友好的 `summary.json / junit.xml`。
- **证据产物（artifacts）**：把每次执行的关键证据（截图、HTTP 请求/响应等）结构化落盘，便于回溯与审计。

> 本 README 已按仓库当前实现的**真实可运行能力**对齐：哪些已稳定可用（MVP ✅），哪些仍属实验（🧪），哪些在规划中（🗺️）。

---

## 能力分层一览 🧭（MVP / 实验 / 规划）

| 能力域 | MVP ✅（已稳定可用） | 实验 🧪（可跑但不稳定/覆盖不全） | 规划 🗺️（Roadmap） |
|---|---|---|---|
| CLI 工具（qf） | `serve / dev / stop / smoke` 可用；`smoke --mode execute` 已验证通过；**默认生成** `artifacts/smoke/summary.json` 与 `artifacts/smoke/junit.xml`，并归档 `smoke_<TS>/http` 证据；支持 `--wait-ready/--json/--junit/--artifacts-dir` 覆盖输出 | `smoke --mode bundle/both` 依赖编译覆盖度 | CLI 自检与能力输出、报告导出、并发与隔离策略 |
| 服务管理 | `qf dev` 后台启动、自动端口、写 `.qf_port/.server_pid`；`qf stop` 可停服；readiness 探测 `/health → /healthz → /openapi.json` | 多实例/多环境同时运行 | 跨平台脚本统一、守护进程化 |
| 后端 API | `/docs`、`/openapi.json` 可用；`/api/v1/execute` 可用 | `/api/v1/generate` 可生成 bundle，但可能超出编译器覆盖范围 | 版本化 API、鉴权、多租户等 |
| 执行器（executor） | `goto` + `assert_text` 已可执行并产出截图证据 📸 | schema 可描述更多动作，但 executor 覆盖未完全（例如 `assert_visible` 当前未支持） | 完整动作集、容错与重试、并发执行、隔离与回放 |
| 生成（generate） | 可生成多个 case 的 bundle（用于演进） | 登录类自然语言步骤当前不可稳定编译 | 受控生成：按 executor/编译器能力生成“可编译步骤” |
| 编译（compile / execute_bundle） | — | 自然语言步骤 → DSL 映射覆盖不足（登录类步骤易失败） | 规则/模板/LLM 混合编译；可扩展 mapping registry ⚙️ |
| 证据产物（artifacts） | `/execute` 生成 `artifacts/run_<TS>/`（含 step 截图）；`smoke` 生成 `summary/junit` 与 HTTP 证据归档 | bundle 失败时返回结构化 error（用于诊断） | JUnit/Allure/HTML 报告增强、差异对比与归档策略 🔍 |
| CI 门禁 | 推荐用 `qf smoke --mode execute` 作为最小门禁 ✅（退出码可做 Gate 条件） | bundle/编译链路暂不建议做硬门禁 | 多层门禁：smoke / regression / nightly |

---

## 变更记录 📝

- ✅ `qf smoke --mode execute` 默认生成 `artifacts/smoke/summary.json`、`artifacts/smoke/junit.xml` 与 `smoke_<TS>/http` 证据归档（无需额外参数）。
- 🛡️ main 分支 Ruleset 启用了 Required checks，并对齐到 Actions job 名 `smoke`，避免出现 “Expected — Waiting for status to be reported”。
- 🧪 E2E（bundle/compile/execute_bundle）链路当前属于实验能力，建议仅保留为手动触发（`workflow_dispatch`），避免阻断 PR 合并。
- ℹ️ README 全文保留 emoji 字符（不使用短码），并要求代码块围栏成对闭合，避免渲染异常。

---

## 项目结构与职责（概览）🧠

- `backend/app/qualityfoundry/`
  - `main.py`：FastAPI 入口
  - `cli.py`：QualityFoundry CLI（qf）
  - `api/`：API 路由
  - `services/`：核心服务层（generate / execute / compile 等）
  - `services/execution/executor.py`：执行器（Playwright）与产物落盘

- `scripts/`
  - `setup.ps1`：一键环境初始化
  - `dev.ps1`：一键后台启动（自动端口、写 `.qf_port/.server_pid`）
  - `stop.ps1`：一键停服

- `.github/workflows/`
  - `quality-gate.yml`：PR 门禁（Required check：`smoke`）
  - `e2e-smoke.yml`：实验性 E2E（手动触发）

---

## 快速开始（本地开发）🚀

### 方式 A：Windows 一键脚本（推荐）

1) 初始化环境（可选安装 Playwright 浏览器）

```powershell
.\scripts\setup.ps1
# 或者不安装浏览器（只调 API）
.\scripts\setup.ps1 -InstallPlaywright:$false
```

2) 启动服务（自动选择可用端口，并写入 `.qf_port/.server_pid`）

```powershell
.\scripts\dev.ps1
```

3) 停止服务

```powershell
.\scripts\stop.ps1
```

---

## CLI 使用说明 🧰

### `qf serve`（前台启动）

```powershell
qf serve --port 8000
```

### `qf dev`（后台启动，自动端口）

```powershell
qf dev
```

### `qf stop`（停止后台服务）

```powershell
qf stop
```

---

## 执行与证据（Execute / Artifacts）📁

### 执行单条用例：`/api/v1/execute`

执行成功会返回 `artifact_dir`，并在对应目录下输出步骤证据：

- 目录示例：`artifacts/run_YYYYMMDDTHHMMSSZ/`
- 常见文件：
  - `step_000.png / step_001.png ...`（按步骤截图 📸）

> 说明：`run_<TS>` 是“执行侧证据”；`smoke` 目录是“门禁侧报告与归档”。

---

## Smoke 质量闸门（最小门禁）🚦（稳定可用 ✅）

`qf smoke` 用于快速验证“服务可达 + `/execute` 最小链路”，并输出适合 CI 消费的门禁产物。

### 推荐命令（本地/CI 通用）

最简（推荐）：默认生成门禁产物（`summary.json / junit.xml / smoke_<TS>/http`）

```powershell
qf smoke --mode execute --base http://127.0.0.1:8000 --wait-ready 45
```

可选：显式指定输出位置（用于自定义 CI 目录结构或多任务并行）

```powershell
qf smoke --mode execute --base http://127.0.0.1:8000 --wait-ready 45 `
  --json .\artifacts\smoke\summary.json `
  --junit .\artifacts\smoke\junit.xml `
  --artifacts-dir .\artifacts\smoke
```

### 产物结构（`artifacts/smoke`）

- `artifacts/smoke/summary.json`：门禁主契约（Contract，机读）
- `artifacts/smoke/junit.xml`：JUnit 报告（便于 CI 展示）
- `artifacts/smoke/smoke_YYYYMMDDTHHMMSSZ/http/*.json`：HTTP 证据（request/response）
  - `execute.request.json`
  - `execute.response.json`

### `summary.json` 关键字段

- `ok`：是否通过
- `exit_code`：退出码（见下）
- `api_prefix`：自动探测到的 API 前缀（如 `/api/v1`）
- `artifact_dir`：本次 `/execute` 返回的产物目录（标准化为 `/`）
- `artifact_dir_raw`：服务端返回的原始产物目录（Windows 可能包含 `\`）
- `smoke_artifacts_dir`：本次 smoke 的证据目录（标准化为 `/`）

### 退出码约定

- `0`：PASS
- `1`：FAIL（服务不可达 / execute 失败 / 内部异常等）
- `2`：参数错误（例如未提供 `--base` 且未找到 `.qf_port`）

---

## CI（GitHub Actions）🤖（建议）

### Required checks 配置建议

- Required checks 请选择：`smoke`（GitHub Actions 的 job 名）
- 建议只把 smoke 作为硬门禁：bundle/compile 先保持实验能力（手动触发），避免阻断合并

---

## 常见问题（FAQ）🧩

### Q1：为什么 `qf smoke` 显示 PASS，但我之前看到 `summary/junit` 没有更新？
A：已修复。现在 `qf smoke --mode execute` 即使不带参数，也会默认写入 `artifacts/smoke/summary.json` 与 `artifacts/smoke/junit.xml`，并归档 `smoke_<TS>/http` 证据。

### Q2：bundle 模式为什么容易失败？
A：当前自然语言步骤 → DSL 的映射覆盖度不足，尤其是登录类步骤；属于实验能力，建议仅手动触发验证。

---

## License

MIT