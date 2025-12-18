# QualityFoundry 🏗️🧪

QualityFoundry 是一个 Python-first 的测试工具原型，目标是把「需求/规则」更规范地沉淀为**可评审、可执行、可追踪**的测试资产，并在执行过程中产出截图/日志等证据，让回归测试更**可复现、可定位、可维护**。✨

> 本 README 已按仓库当前实现的**真实可运行能力**对齐：哪些已稳定可用（MVP ✅），哪些仍属实验（🧪），哪些属于规划（🗺️）。

---

## 我们要解决什么问题 🎯

在真实项目里，测试经常遇到这些痛点：

- 需求变化快：用例散落在文档/脑图/聊天记录里，难复用、难 Diff、难维护 😵
- 自然语言步骤“看懂不等于能跑”：执行时歧义大，脚本质量不稳定，偶现问题难定位 🧩
- 失败后缺少证据：没有截图/日志/trace，复现成本高，沟通成本大 📉

QualityFoundry 的思路是把测试流程收敛成一个更清晰的闭环：

**需求文本 → Bundle（结构化测试资产）→ DSL（受控动作）→ 执行（Playwright）→ Evidence（证据产物）**

---

## 能力分层一览 🧭（MVP / 实验 / 规划）

| 能力域 | MVP ✅（已稳定可用） | 实验 🧪（可跑但不稳定/覆盖不全） | 规划 🗺️（Roadmap） |
|---|---|---|---|
| CLI 工具（qf） | `serve / dev / stop / smoke` 已可用；`smoke --mode execute` 已验证通过；支持 `--wait-ready/--json/--junit/--artifacts-dir` | `smoke --mode bundle/both` 依赖编译覆盖度 | CLI 增强：capabilities、自检输出、报告导出等 |
| 服务管理 | `qf dev` 后台启动、自动端口、写 `.qf_port/.server_pid`；`qf stop` 可靠停服；readiness 探测 `/health → /healthz → /openapi.json` | 多实例/多环境管理 | 跨平台脚本统一、守护进程化 |
| 后端 API | `/docs`、`/openapi.json` 可用；`/api/v1/execute` 可用 | `/api/v1/generate` 可生成 bundle，但可能超出编译器覆盖范围 | 版本化 API、鉴权、多租户等 |
| 执行器（executor） | `goto` + `assert_text` 已验证可执行并产出 evidence 📁 | schema 允许更多动作，但 executor 覆盖未完全（例如 `assert_visible` 当前未支持） | 完整动作集、容错策略、并发执行、隔离与重试 |
| 生成（generate） | 可生成多个 case 的 bundle（用于演进） | 生成的登录类自然语言步骤当前不可稳定编译 | 受控生成：按 executor/编译器能力生成“可编译步骤” |
| 编译（compile / execute_bundle） | - | 自然语言步骤 → DSL 映射覆盖不足（登录类步骤易失败） | 规则/模板/LLM 混合编译策略；可扩展 mapping registry ⚙️ |
| 证据产物（artifacts/evidence） | `/execute` 可生成 `artifact_dir` + 步骤截图；`smoke` 可落盘 HTTP request/response 证据；输出 `summary.json`/`junit.xml` | bundle 失败时返回结构化 error（用于诊断） | JUnit/Allure/HTML 报告输出增强、归档与对比 🔍 |
| CI 门禁 | 推荐用 `qf smoke --mode execute` 作为最小门禁 ✅（支持退出码 + summary/junit + evidence 上传） | bundle/编译链路暂不建议做硬 gate | 多层级门禁：smoke / regression / nightly |

> 关键结论：当前推荐把 `smoke --mode execute` 作为**稳定最小门禁**。bundle/编译链路仍在演进阶段，不建议作为强制 gate。

---

## 当前已完成（MVP）✅

### 1) CLI 工具（qf）🧰

QualityFoundry 提供统一 CLI 入口 `qf`，用于本地开发、服务管理与冒烟验证。

当前命令：

- `qf serve`：前台启动 FastAPI 服务（reload）
- `qf dev`：后台启动服务（自动端口、写 `.qf_port/.server_pid`，日志写 `.qf_dev.log`）
- `qf stop`：停止 `qf dev` 启动的服务
- `qf smoke`：冒烟测试（推荐 `--mode execute`，支持输出门禁产物）
- `qf generate`：生成 bundle（实验性）
- `qf run`：本地最小示例执行（本地执行器路径）

> Windows 如遇 `WinError 32: qf.exe 被占用`，请先执行 `qf stop` 或结束占用进程后再安装/升级。

---

### 2) 后端 API（FastAPI）🔌

- `GET /docs`：Swagger UI
- `GET /openapi.json`：OpenAPI 文档
- `GET /health`：readiness（若存在则优先）
- `POST /api/v1/execute`：执行受控 DSL actions（**已验证可用**）
- `POST /api/v1/generate`：生成 bundle（实验性）
- `POST /api/v1/compile_bundle` / `POST /api/v1/execute_bundle`：bundle 编译/执行（实验性）

---

### 3) 生成测试成果（Generate）🧠（实验性）

`POST /api/v1/generate`

- 输入：需求 title/text
- 输出：结构化 Bundle（可能包含多个 case）
- 现状：生成侧会产出更“业务化”的自然语言步骤（例如登录流程），但是否能编译为可执行 DSL 取决于编译器覆盖度（当前覆盖不足）。

---

### 4) 编译步骤为 DSL（Compile Bundle）⚙️（实验性）

`POST /api/v1/compile_bundle`

- 目标：把 Bundle 里的步骤编译成 `playwright_dsl_v1` actions
- 现状：常见自然语言步骤（如登录/表单输入）尚未稳定映射，可能出现 “无法编译步骤 …” 的报错

---

### 5) 执行与证据（Execute / Execute Bundle）📎

#### `POST /api/v1/execute`（稳定可用 ✅）

用于执行受控 DSL actions，并产出证据：

- 返回字段通常包含：`ok / artifact_dir / evidence[]`
- 每个 step 可产出截图：`step_000.png / step_001.png ...` 📁

当前已验证可用的最小动作链路（推荐作为门禁基线）：

- `goto`
- `assert_text`

> 注意：接口 schema 允许的动作类型不等于 executor 已实现的动作类型。以 executor 当前覆盖为准（例如 `assert_visible` 当前未支持）。

#### `POST /api/v1/execute_bundle`（实验性 🧪）

更贴近“一键执行生成结果”的路径，但当前受限于编译覆盖度，登录类用例容易失败，暂不建议作为硬门禁。

---

### 6) Smoke 质量闸门（最小门禁）🚦（稳定可用 ✅）

`qf smoke` 用于快速验证“服务可达 + /execute 最小链路”，并输出适合 CI 消费的门禁产物。

#### 推荐命令（本地/CI 通用）

```powershell
qf smoke --mode execute --base http://127.0.0.1:8000 --wait-ready 45 --json .\artifacts\smoke\summary.json --junit .\artifacts\smoke\junit.xml --artifacts-dir .\artifacts\smoke
````

* readiness 探测顺序：`/health` → `/healthz` → `/openapi.json`
* 默认验证：`POST /api/v1/execute`（最小动作链路：`goto + assert_text`）

#### Smoke 产物结构（artifacts/smoke）

运行后会生成：

* `artifacts/smoke/summary.json`：门禁主契约（Contract，机读）
* `artifacts/smoke/junit.xml`：JUnit 报告（便于 CI 展示）
* `artifacts/smoke/smoke_YYYYMMDDTHHMMSSZ/http/*.json`：HTTP 证据（request/response）

  * `execute.request.json`
  * `execute.response.json`

`summary.json` 关键字段：

* `ok`：是否通过
* `exit_code`：退出码（见下）
* `api_prefix`：自动探测到的 API 前缀（如 `/api/v1`）
* `artifact_dir`：服务端执行产物目录（路径标准化为 `/`）
* `artifact_dir_raw`：服务端原始路径（Windows 可能为 `\`）
* `smoke_artifacts_dir`：本次 smoke 的证据目录（标准化为 `/`）
* `duration_ms`：耗时（毫秒）

#### 退出码约定（Exit codes）

* `0`：PASS
* `10`：服务未在 `--wait-ready` 时间内就绪（readiness 超时/不可达）
* `20`：bundle 模式输入不合法（例如 cases=0、case_index 越界）
* `30`：执行失败（`execute` / `execute_bundle` 返回 ok=false）

> 推荐：把 `smoke --mode execute` 作为强制 gate；bundle/编译链路先作为非阻断性检查，待覆盖稳定再升级。

---

### 7) 本地开发脚本（Windows / PowerShell）🛠️

仓库提供了脚本以降低本地启动成本（与 CLI 行为对齐）：

* `.\scripts\setup.ps1`：初始化环境（可选安装 Playwright 浏览器）
* `.\scripts\dev.ps1`：启动服务（自动端口，并写入 `.qf_port`）
* `.\scripts\smoke_*.ps1`：实验性的 bundle 冒烟脚本（依赖编译覆盖度）

> 推荐：即使使用脚本启动服务，冒烟仍建议使用 `qf smoke --mode execute` 作为稳定门禁。

---

### 8) CI（GitHub Actions）🤖（建议）

当前推荐 CI 门禁用最小可执行链路：

* 起服务（dev/uvicorn）
* 跑 `qf smoke --mode execute`（生成 `summary.json / junit.xml / http evidence`）
* 上传 artifacts（便于失败定位）
* 关服务（可选）

分支保护建议（Rulesets / Branch protection）：

* 对 `main` 启用 `Require status checks to pass`
* Required checks 选择：`quality-gate / smoke`（以你的工作流/Job 命名为准）
* 建议启用 `Require a pull request before merging`

bundle/编译链路建议先作为非阻断性检查，待编译覆盖稳定后再升级为 gate。

---

## 项目结构与职责（脑图）🧠

> 用于帮助理解职责边界，具体以仓库为准。

* `backend/app/qualityfoundry/`

  * `main.py`：FastAPI 入口
  * `cli.py`：CLI 入口（qf）
  * `models/schemas.py`：请求/响应与动作 schema
  * `services/generation/`：生成（bundle）
  * `services/execution/`：执行器（Playwright）
* `scripts/`：Windows / PowerShell 工具脚本

---

## 快速开始（本地开发）🚀

### 方式 A：Windows 一键脚本（推荐）

1. 初始化环境（可选安装 Playwright 浏览器）

```powershell
.\scripts\setup.ps1
# 或者不安装浏览器（只调 API）
.\scripts\setup.ps1 -InstallPlaywright:$false
```

2. 启动服务（自动选择可用端口，并写入 `.qf_port`）

```powershell
.\scripts\dev.ps1
```

3. 冒烟验证（推荐：稳定最小门禁 ✅）

```powershell
qf smoke --mode execute
```

4. 停止服务（若服务由 qf dev 启动）

```powershell
qf stop
```

> 说明：若你是用脚本启动的服务，请按脚本的方式停服；`qf stop` 仅负责停止 `qf dev` 启动的进程。

---

### 方式 B：手动安装（跨平台）

1. 创建虚拟环境 + 安装后端（editable）

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -e backend --no-cache-dir
```

> 若你使用仓库根目录 `pyproject.toml` 进行打包安装，也可执行：
> `python -m pip install -e .`

2. 启动服务（后台推荐）

```bash
qf dev
```

3. 打开接口文档

* 打开：`http://127.0.0.1:8000/docs`（若端口变化，以 `.qf_port` 为准）

4. 冒烟验证

```bash
qf smoke --mode execute
```

---

## API 列表（以 /docs 为准）🔌

* Swagger：`http://127.0.0.1:8000/docs`
* OpenAPI：`http://127.0.0.1:8000/openapi.json`

若 `qf dev` 或脚本自动换端口，以 `.qf_port` 内容为准。

---

## artifacts 产物说明 📁

执行成功或失败，服务通常会返回：

* `artifact_dir`：产物目录（如 `artifacts\run_YYYYMMDDTHHMMSSZ`）
* `evidence[]`：步骤级证据，包括 action、结果、截图路径、错误信息等

示例信息常见字段：

* `ok`：整体通过/失败
* `artifact_dir`：产物目录
* `evidence[]`：每步执行结果与截图路径

---

## 近期计划（Roadmap）🗺️

### 近期（先把工程打稳）

* [ ] 统一 artifacts 目录规范与输出字段（便于 CI 上传与消费）📦
* [ ] executor 支持集与文档对齐（显式输出支持的 action 列表）🧾
* [ ] 执行失败归因：定位器/网络/断言/环境（输出更可读的错误原因）🧠

### 中期（可规模化）

* [ ] 自然语言步骤 → DSL 编译覆盖：登录/表单/列表等常见模式 ⚙️
* [ ] Bundle 版本化与 Diff：需求变更 → 用例变更可追踪 🔍
* [ ] 编译策略可配置：strict / lenient / controlled-heal ⚙️

---

## 贡献指南 🤝

欢迎提交 Issue / PR。建议提交前本地跑（按当前能力分层选择）：

**稳定门禁：**

```powershell
qf smoke --mode execute
```

**实验链路（可能失败）：**

```powershell
qf smoke --mode bundle --case-index 0
qf smoke --mode both --case-index 0
```

---

## License 📄

Apache-2.0
