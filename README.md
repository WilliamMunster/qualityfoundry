# QualityFoundry 🏗️

**A framework to make AI agents controllable, auditable, regressible, and cost-bounded.**

QualityFoundry 是一个 **Python-first** 的测试与质量闸门（Quality Gate）工具链。我们的核心哲学是 **Hybrid Quality**：确定性检查（assert）优先，辅以 AI 评测与 Trace 证据链。

> **最新版本**: `v0.16-sandbox-mcp-docs` — L3 容器沙箱 + MCP 写安全 + 文档收口
>
> **进度基线**: 详见 [docs/status/progress_baseline.md](docs/status/progress_baseline.md)

## 1. 核心哲学 (Core Philosophy)
- ⚖️ **Hybrid Quality**：针对确定性内容采用 assert 检查；不确定性内容使用评测/裁决（eval/judge）。
- 🔍 **Evidence-First**：关键链路必须具备 Trace 证据链（含日志、模型结果与版本信息）。
- 🔄 **Reproducibility**：模型参数、Prompt、工具版本及环境指纹化，确保失败可重放。
- 🛡️ **Least Privilege**：工具调用分级授权，环境隔离运行并配套全量审计。
- 📉 **Cost Governance**：预算与超时熔断，避免死循环导致的异常消耗。

## 2. 参考架构 (Architecture Layers)

| Layer | Name | Current Status |
|-------|------|----------------|
| **L1** | Policy (规则与门禁) | ✅ 完成 |
| **L2** | Orchestration (编排层) | ✅ 完成 (UUID runs 主路径) |
| **L3** | Execution (执行层) | ✅ 完成 (subprocess 默认 + container 可选; 不可用则拒绝审计) |
| **L4** | Protocol (MCP) | ✅ 完成 (read-only + write: run_pytest 仅受控写) |
| **L5** | Governance & Evals | ✅ 完成 (cost governance + golden regression) |

- **L1 规则与门禁层 (Policy)**：定义 `policy_config.yaml`、风险分级与发布门禁。
- **L2 编排层 (Orchestration)**：LangGraph 状态机执行，UUID runs 主路径：启动→查看→下载证据→审计链。
- **L3 执行层 (Execution)**：集成 Playwright、Pytest 等工具，支持 subprocess 默认沙箱与 L3 Container 强隔离沙箱。
- **L4 接口层 (Protocol)**：MCP Client 调用外部服务，MCP Server 支持只读工具 + 受控写工具（仅限 run_pytest），具备完整安全链（认证→权限→策略→沙箱）。
- **L5 治理与评测层 (Governance & Evals)**：Golden Datasets 回归、成本治理（timeout/budget）已落地；Dashboard 待 P1 演进。

> **⚠️ 存量声明 (Legacy Notice)**: 
> 原 `run_<TS>` 系列端点已 deprecated，转为只读。主入口请统一使用 `/api/v1/orchestrations/runs`。


---

## 当前状态 (main@HEAD)

### Completed Features (Verified)
- ✅ **需求/场景/用例管理**：支持从 NL 需求到场景、用例的全链路生成与审核，支持自动补全 `seq_id`
- ✅ **OrchestratorService (Phase 2.2)**：LangGraph 状态机执行，5 个节点支持动态路由扩展
- ✅ **全链路可复现性 (Phase 1.3)**：证据链自动记录 Git SHA、依赖指纹（Fingerprint）及运行时环境
- ✅ **回归评测体系 (Phase 5.2)**：支持 Golden Dataset 运行对比，一键产出 `diff_report.md`
- ✅ **多模型适配**：内置对接 OpenAI, DeepSeek, 智谱 AI 等主流提供商
- ✅ **质量门禁 (L1)**：基于 Policy 的自动决策（PASS/FAIL/NEED_HITL）
- ✅ **环境管理**：多环境配置，健康检查，变量管理
- ✅ **执行管理**：DSL/MCP Client 执行模式，实时状态追踪
- ✅ **测试报表**：仪表盘统计，执行历史记录
- ✅ **批量操作**：支持多选删除，确认弹窗
- ✅ **审计日志 (PR-C)**：完整的操作审计，记录工具执行与决策事件
- ✅ **Premium UI 前端**：AI 工作区前端重构，支持编排可视化与运行管理
- ✅ **L3 沙箱执行 (PR-B)**：进程隔离沙箱，policy 驱动的超时/路径/命令/环境变量控制
- ✅ **L4 MCP Write Security (Phase 1)**：`run_pytest` 写能力 + 安全链（auth→perm→policy→sandbox），25 项安全测试

### Partial / In Progress
- 🟡 **用户认证**：基于 token 的简单认证（非 JWT，待升级）
- 🟡 **角色权限**：UserRole 模型存在，RBAC 通过 MCP 安全链强制执行

### Not Started
- 🔴 **MCP Write Phase 2**：`run_playwright`、`run_shell` 等高危工具（需容器沙箱）
- 🔴 **L5 Dashboard**：趋势聚合与可视化

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- SQLite（内置）

### 后端启动

```powershell
# 1. 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 安装依赖
pip install -e .\backend

# 3. 初始化数据库
cd backend
alembic upgrade head
cd ..

# 4. 创建管理员账号
python seed_admin.py

# 5. 启动服务
uvicorn qualityfoundry.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```powershell
cd frontend
npm install
npm run dev
```

### 使用启动脚本（推荐）

```bash
# 一键启动全部（后台运行）
./scripts/start-all.sh

# 停止全部
./scripts/start-all.sh --stop

# 单独启动
./scripts/start-backend.sh --background
./scripts/start-frontend.sh --background
```

访问 http://localhost:5173，使用 `admin/admin` 登录。

---

## 项目结构

```
qualityfoundry/
├── backend/                    # 后端代码
│   ├── app/qualityfoundry/    # 主应用
│   │   ├── api/v1/            # API 路由
│   │   ├── database/          # 数据库模型
│   │   ├── services/          # 业务逻辑
│   │   └── main.py            # FastAPI 入口
│   ├── migrations/            # Alembic 迁移
│   └── tests/                 # 测试用例
├── frontend/                   # 前端代码
│   └── src/
│       ├── pages/             # 页面组件
│       └── layouts/           # 布局组件
├── scripts/                    # 启动脚本
└── pyproject.toml             # 项目配置
```

---

## API 文档

启动后端后访问：

- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

### 主要 API 端点

| 模块 | 端点                     | 说明                 |
| ---- | ------------------------ | -------------------- |
| 认证 | POST /api/v1/users/login | 用户登录             |
| 需求 | /api/v1/requirements     | 需求 CRUD            |
| 场景 | /api/v1/scenarios        | 场景 CRUD + AI 生成  |
| 用例 | /api/v1/testcases        | 用例 CRUD + AI 生成  |
| 环境 | /api/v1/environments     | 环境 CRUD + 健康检查 |
| 执行 | /api/v1/executions       | 执行管理             |
| 报表 | /api/v1/reports          | 仪表盘统计           |
| AI   | /api/v1/ai-configs       | AI 配置管理          |
| 用户 | /api/v1/users            | 用户管理             |

---

## 数据库模型

| 表名         | 说明     |
| ------------ | -------- |
| users        | 用户账号 |
| requirements | 需求文档 |
| scenarios    | 测试场景 |
| testcases    | 测试用例 |
| environments | 环境配置 |
| executions   | 执行记录 |
| approvals    | 审核记录 |
| reports      | 测试报告 |
| uploads      | 上传文件 |
| ai_configs   | AI 配置  |
| audit_logs   | 审计日志 |

---

## 开发指南

### 运行测试

```powershell
cd backend
pytest tests -v
```

### 代码检查

```powershell
ruff check backend
```

### 数据库迁移

```powershell
cd backend
alembic revision --autogenerate -m "描述"
alembic upgrade head
```

---

## CI/CD

GitHub Actions 配置：

- `ci.yml`：代码检查（ruff）+ 单元测试（pytest）
- `smoke`：核心执行链路冒烟测试（Required）
- `regression-smoke`：基于 Golden Dataset 的回归评测（非阻塞，输出 Diff）

---

## 许可证

MIT License

---

## 更新日志

### V0.14.1 (2026-01-25)

**L4 MCP Write Security Phase 1**

- ✅ **MCP 写能力**：`run_pytest` 作为首个受控写工具暴露给 MCP 客户端
- ✅ **安全链实现**：认证（token）→ 权限（RBAC）→ 策略（allowlist）→ 沙箱（enabled）四重校验
- ✅ **错误码体系**：`-32001 AUTH_REQUIRED`、`-32003 PERMISSION_DENIED`、`-32004 POLICY_BLOCKED`、`-32006 SANDBOX_VIOLATION`
- ✅ **审计事件**：`MCP_TOOL_CALL` 审计类型，记录 tool_name、args_hash、caller_user_id
- ✅ **安全测试**：25 项测试覆盖所有安全边界
- ✅ **设计文档**：`docs/designs/mcp-write-security.md` v0.1 frozen

**开发体验优化**

- ✅ **启动脚本**：`scripts/start-all.sh`、`start-frontend.sh`、`start-backend.sh` 避免 macOS TTY 挂起问题
- ✅ **E2E 测试**：`frontend/e2e/test_run_center.py` Run Center 主路径验收测试
- ✅ **验收文档**：`docs/walkthroughs/run-center-acceptance.md` API 契约与检查清单

### V0.9.6 (2026-01-23)

**Premium UI 与审计系统 (Frontend Revamp & Audit Foundation)**

- ✅ **Premium AI 工作区**：全面重构前端 UI，实现高端 AI 工作区设计，包含编排可视化、执行时间线、节点进度等组件
- ✅ **运行管理中心**：新增 `RunLaunchPage`（自然语言启动运行）、`RunListPage`（运行列表）、`RunDetailPage`（运行详情与时间线）
- ✅ **审计日志系统 (PR-C)**：实现完整的审计日志功能，包含 `AuditLog` ORM 模型、`AuditService` 服务、数据库迁移
- ✅ **审计事件类型**：支持 `tool_started`、`tool_finished`、`decision_made`、`policy_blocked`、`governance_short_circuit` 等事件
- ✅ **可追溯性增强**：审计日志自动记录 `policy_hash`、`git_sha`、`args_hash` 等元数据

**Antd 5.x 全局上下文修复 (UX & Reliability Foundation)**

- ✅ **全局消息注入**：实现 `AntdGlobal.tsx` 工具组件，配合 `App.tsx` 中的 `<App>` 包装，彻底解决 Antd 5.x 静态方法 (`message`, `modal`, `notification`) 在 Hooks 外部调用时不显示提示的问题
- ✅ **全站提示对齐**：批量替换全站 15+ 个页面的静态提示调用，确保操作反馈（成功/失败/加载中）在全浏览器环境下一致可见

**API 422 结构化修复 (Robust Web API)**

- ✅ **接口参数对齐 (422 修复)**：深度自查并修复了场景/用例审核接口、批量操作接口及执行启动接口中的数据结构不一致问题
- ✅ **稳定性增强**：修复了用例执行时偶尔因缺失环境 ID 导致的请求非法问题

### V0.9.5 (2026-01-21)

**回归基石：可复现性与回归体系 (Reliability & Evals Foundation)**

- ✅ **全链路元数据 (Phase 1.3)**：实现 `ReproMeta` 工具集，自动记录 Git SHA、分支、Dirty 状态及依赖指纹（SHA256），确保测试证据“可追溯、可对齐”。
- ✅ **Golden Dataset (Phase 5.2)**：建立 `governance/golden/dataset.yaml` 评测基准，包含 5 组针对不同决策逻辑（PASS/FAIL/HITL）的黄金案例。
- ✅ **回归 CLI**：实现 `python -m qualityfoundry.governance.evals`：
    - 快速运行评测集并计算 `Passed/Total` 成功率。
    - 支持基线对比（Generate Diff），自动指出决策漂移或回归项。
- ✅ **CI/CD 增强**：新增 `regression-smoke` 自动化评测流水线。

**多 AI 模型支持 (Multi-AI Support)**

- ✅ **多模型切换**：支持 OpenAI (GPT-4/3.5)、DeepSeek (Chat/Coder)、ZhipuAI (GLM-4)、Ollama 等多种模型动态切换
- ✅ **模型联动**：选择提供商后自动加载对应模型列表，支持自定义模型名称
- ✅ **连接测试**：新增配置连接测试功能，验证 API Key 和 Base URL 可用性
- ✅ **Prompt 优化**：针对不同模型优化了 JSON 生成的 Prompt 结构，提高成功率

**稳定性与体验 (Stability & UX)**

- ✅ **生成持久化**：修复 AI 生成内容（场景/用例）偶尔无法保存的问题
- ✅ **容错增强**：增强对 AI 返回 Markdown 代码块的解析能力 (` ```json ` wrapper)
- ✅ **事务安全**：优化 `seq_id` 生成逻辑，防止并发下的编号冲突
- ✅ **UI 优化**：配置中心界面重构，支持更直观的模型配置

### V0.9 (2026-01-16)

**质量闸门与流程控制 (Quality Gate & Workflow)**

- ✅ **流程强制约束**：实现“需求 -> 审核后场景 -> 审核后用例 -> 执行”的严谨链路
- ✅ **场景准入**：只有状态为 `approved` 的场景才允许调用 AI 生成测试用例
- ✅ **执行准入**：只有状态为 `approved` 的测试用例才允许驱动 MCP/DSL 执行任务
- ✅ **批量审核**：场景管理与用例管理页面新增“批量通过”和“批量拒绝”功能，大幅提升审核效率

**上帝视角修复 (Observer Optimization)**

- ✅ **API 稳定性**：优化 `AIService` 超时配置，解决 DeepSeek 等模型调用时出现的“Server disconnected”问题
- ✅ **提供商支持**：修复智谱 AI (ZhipuAI) 模型名匹配问题（更正为 `glm-4-plus`），确保分析结果稳定产出
- ✅ **诊断增强**：上帝视角分析接口稳定性提升，支持全链路一致性和覆盖度深度评估

**全球化与体验提升 (Globalization & UX)**

- ✅ **时区自动转换**：前端统一将后端返回的 UTC 时间转换为 **东八区 (UTC+8)** 本地时间显示
- ✅ **配置灵活更新**：修复并增强 AI 配置更新接口，支持动态修改 `model` 和 `provider` 字段
- ✅ **日志透明度**：完善 AI 调用日志记录，便于追踪和诊断复杂的 AI 交互过程

### V0.8 (2026-01-15)

**自动编号系统**

- ✅ 需求、场景、用例增加 `seq_id` 自动递增编号字段
- ✅ 支持按 `seq_id` 查询（如 REQ-1、SCN-1、TC-1）
- ✅ 前端列表页展示 seq_id 列，便于快速检索

**批量操作**

- ✅ 需求、场景、用例列表支持多选复选框
- ✅ 批量删除功能，带确认弹窗防误删
- ✅ 全选/取消全选快捷操作

**前端交互优化**

- ✅ 统一的加载状态提示（Spin + Toast）
- ✅ 删除/批量删除确认弹窗
- ✅ 表单验证增强

---

### V0.7 (2026-01-13)

**配置中心增强**

- ✅ AI 提示词配置页面：支持在线编辑场景生成、用例生成等步骤的提示词模板
- ✅ 提示词初始化功能：一键创建默认提示词
- ✅ 支持变量模板：`{requirement}`、`{scenario}` 等

**Bug 修复**

- ✅ 修复数据库表缺失问题（`ai_prompts`、`ai_configs` 表）
- ✅ 修复场景步骤序号重复显示问题（AI 返回带序号 + 前端 ol 列表重复）

### V0.6 (2026-01-10)

**执行引擎升级**

- ✅ 异步任务调度（可扩展架构，预留 Redis/Celery 接入）
- ✅ 实时进度查询 API
- ✅ 停止执行功能
- ✅ 执行日志聚合

**报告功能完善**

- ✅ 报告详情页：实时进度条、日志时间线、状态标签
- ✅ 报告仪表盘：真实执行记录加载
- ✅ 报告导出：JSON/CSV 导出 + 日期/状态筛选
- ✅ 报告趋势：每日统计 + 成功率 + 可视化图表

**前端交互优化**

- ✅ WebSocket 实时进度推送（`/ws/executions/{id}`）
- ✅ 表单验证增强（空选择禁用提交按钮）
- ✅ 分页功能完善（场景/用例列表）
- ✅ AI 生成加载提示优化

**AI 集成完善**

- ✅ 场景生成：真实 AI 调用（替换 Mock）
- ✅ 用例生成：真实 AI 调用（替换 Mock）
- ✅ 支持 Word 文档内容提取

**测试覆盖**

- ✅ 60 个测试用例通过
- ✅ 测试配置统一（conftest.py 修复）

### V0.5.1 (2026-01-10)

- ✅ 实现前端完整 CRUD 交互功能
- ✅ 需求管理：详情页、编辑页、查看/编辑/新建/删除按钮
- ✅ 场景管理：数据加载、AI 生成弹窗、审核、删除
- ✅ 用例管理：数据加载、AI 生成弹窗、执行、审核、删除
- ✅ 执行管理：数据加载、环境筛选、查看详情/日志、停止
- ✅ 修复异步通知处理（asyncio 兼容）
- ✅ 添加安全头中间件
- ✅ 创建数据播种脚本（`seed_data.py`）
- ✅ 修复数据库迁移（添加 result/completed_at 列）

### V0.5 (2026-01-10)

- ✅ 修复前端菜单顺序
- ✅ 修复仪表盘 Running 图标动画
- ✅ 添加登出功能
- ✅ 修复 CI lint 错误
- ✅ 修复 CI smoke 测试依赖
- ✅ 添加测试数据库统一配置

### V0.4 (2026-01-09)

- ✅ 完成阶段 1-3 核心功能
- ✅ 32 个管理 API 接口
- ✅ 完整的需求 → 场景 → 用例 → 执行链路

---

## 开发工具

### 数据播种

```powershell
cd backend/app
python seed_data.py
```

### 清理数据库

```powershell
Remove-Item qualityfoundry.db -Force
cd backend && alembic upgrade head
```
