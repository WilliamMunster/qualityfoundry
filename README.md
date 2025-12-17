# QualityFoundry 🏗️🧪

QualityFoundry 是一个 Python-first 的开源测试工具，目标是把「需求/规则」更规范地沉淀为**可评审、可复用的测试成果**，并把自然语言步骤“编译”为受控的 DSL 动作后再执行，最终产出截图/日志等证据，让回归测试更**可复现、可定位、可维护**。✨

---

## 我们要解决什么问题 🎯

在真实项目里，测试经常遇到这些痛点：

- 需求变化快：用例散落在文档/脑图/聊天记录里，难复用、难 Diff、难维护 😵
- 自然语言步骤“看懂不等于能跑”：执行时歧义大，脚本质量不稳定，偶现问题难定位 🧩
- 失败后缺少证据：没有截图/日志/trace，复现成本高，沟通成本大 📉

QualityFoundry 的思路是把测试流程收敛成一个更清晰的闭环：

**需求输入 → 结构化测试成果 → 步骤编译（DSL）→ 确定性执行 → 证据沉淀**

---

## 当前已完成（MVP）✅

### 1) 后端 API（FastAPI）
- Swagger 文档：`/docs`
- 健康检查：`/healthz`

### 2) 生成测试成果（Generate）
- `POST /api/v1/generate`
- 从「标题 + 需求描述」生成一个 `CaseBundle`：  
  **测试模块 → 测试目标 → 测试点 → 测试用例（含步骤）**
- 当前生成器是**确定性规则版**（无 LLM），用于先把链路跑通；后续可替换成 LLM/RAG。

### 3) 编译步骤为 DSL（Compile Bundle）
- `POST /api/v1/compile_bundle`
- 把用例步骤编译为受控 DSL actions（可 strict，可输出 warnings）
- 目标是：自然语言先“收敛成有限动作集合”，降低歧义与漂移。

### 4) 执行与证据（Execute / Execute Bundle）
- `POST /api/v1/execute`：执行 DSL actions（Playwright），产出 evidence（截图等）
- `POST /api/v1/execute_bundle`：对 bundle 做一键执行（更贴近日常回归使用方式）
- 产物输出在 `artifacts/` 下，每次执行一个独立目录 📁

### 5) 本地开发脚本（Windows / PowerShell）
- `scripts/dev.ps1`：自动激活 `.venv`、自动找可用端口（8000 → 8001…）、等待服务就绪，并写入：
  - `.qf_port`（记录最终端口）
  - `.server_pid`（记录服务 PID）
- `scripts/smoke*.ps1`：一键冒烟（健康检查 → 生成 → 编译 → 执行）

### 6) CI（GitHub Actions）
- Windows 环境 E2E 冒烟：启动服务 + Playwright + smoke + 上传 artifacts 🤖

---

## 项目结构与职责（脑图）🧠

> 后端主体位于：`backend/app/qualityfoundry/`

```mermaid
mindmap
  root((QualityFoundry))
    backend["backend/（后端工程）"]
      app["app/（应用入口）"]
        qualityfoundry["qualityfoundry/（核心包）"]
          main["main.py（FastAPI app 装配与启动）"]
          models["models/schemas.py（对外数据契约：请求/响应/枚举/错误模型）"]
          api["api/（路由层：薄控制器）"]
            v1["v1/（API v1 聚合与子路由）"]
              routes["routes.py（统一 include_router）"]
              routes_generation["routes_generation.py（/generate 接口）"]
              routes_compile_bundle["routes_compile_bundle.py（/compile_bundle 接口）"]
              routes_execution["routes_execution.py（/execute 接口）"]
              routes_execute_bundle["routes_execute_bundle.py（/execute_bundle 接口）"]
          services["services/（领域服务：核心业务逻辑）"]
            generation["generation/（生成 bundle：当前为确定性规则）"]
            compile["compile/（把步骤编译为 DSL actions）"]
            execution["execution/（执行编排：单条/整包执行）"]
          runners["runners/（执行器适配层）"]
            playwright["playwright/（DSL -> Playwright；截图/证据输出）"]
    scripts["scripts/（开发体验脚本）"]
      setup["setup.ps1（初始化环境/安装依赖/可选安装浏览器）"]
      dev["dev.ps1（启动服务：自动端口+就绪检测+写端口文件）"]
      smoke["smoke.ps1（基础冒烟：healthz + execute）"]
      smoke_bundle["smoke_bundle.ps1（冒烟：generate + compile_bundle + execute）"]
      smoke_exec_bundle["smoke_execute_bundle.ps1（冒烟：generate + execute_bundle）"]
    workflows[".github/workflows/（CI）"]
      ci["ci.yml（静态检查/单测等）"]
      e2e["e2e-smoke.yml（E2E 冒烟：起服务 + smoke + 上传产物）"]
    artifacts["artifacts/（执行产物：截图/证据/日志）"]
````

---

## 快速开始（本地开发）🚀

### 方式 A：Windows 一键脚本（推荐）

> PowerShell 建议先允许当前窗口执行脚本：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

1. 初始化（创建 .venv + 安装依赖，可选安装 Playwright 浏览器）

```powershell
.\scripts\setup.ps1
# 或者不安装浏览器（只调 API）
.\scripts\setup.ps1 -InstallPlaywright:$false
```

2. 启动服务（自动选择可用端口，并写入 .qf_port）

```powershell
.\scripts\dev.ps1
```

3. 冒烟验证

```powershell
.\scripts\smoke_execute_bundle.ps1 -TimeoutSec 180
.\scripts\smoke_bundle.ps1 -TimeoutSec 180
```

---

### 方式 B：手动安装（跨平台）

1. 创建虚拟环境 + 安装后端（editable）

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -e "backend"
```

2. 安装 Playwright 浏览器

```bash
python -m pip install playwright
python -m playwright install chromium
```

3. 启动 API

```bash
qf serve
# 打开：http://127.0.0.1:8000/docs
```

---

## API 列表（以 /docs 为准）🔌

* `GET /healthz`
* `POST /api/v1/generate`
* `POST /api/v1/compile`
* `POST /api/v1/compile_bundle`
* `POST /api/v1/execute`
* `POST /api/v1/execute_bundle`

---

## artifacts 产物说明 📁

执行后会在 `artifacts/` 下生成一次 run 的目录，常见内容包括：

* 每一步截图（step_000.png …）
* 执行结果（ok / error）
* 运行时间、动作列表、warnings 等

这些产物用于：

* 快速定位失败步骤
* 给开发/产品/QA 提供客观证据
* 复盘与回归留档

---

## 近期计划（Roadmap）🗺️

### 近期（先把工程打稳）

* [ ] 固化 `schemas.py`：对外接口契约版本化（v1 → v1.1）🧊
* [ ] 统一 artifacts 目录规范与输出字段（便于 CI 上传与消费）📦
* [ ] 编译规则分层：通用规则 / Web 常用规则 / 业务域规则 🧱
* [ ] 执行失败归因：定位器/网络/断言/环境（输出更可读的错误原因）🧠

### 中期（可规模化）

* [ ] Bundle 版本化与 Diff：需求变更 → 用例变更可追踪 🔍
* [ ] 编译策略可配置：strict / lenient / controlled-heal ⚙️
* [ ] 引入 RAG：规则库/组件库/历史缺陷库 📚

---

## 贡献指南 🤝

欢迎提交 Issue / PR。建议提交前本地跑：

```powershell
pytest -q
.\scripts\smoke_execute_bundle.ps1 -TimeoutSec 180
.\scripts\smoke_bundle.ps1 -TimeoutSec 180
```

---

## License 📄

Apache-2.0
