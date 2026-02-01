# QualityFoundry 进度基线

> **版本锚点**: `main@HEAD` (2026-02-01)
> **最后验证**: 2026-02-01 20:41
> **Git 标签**: `v0.24-tenant-api`
> **验证方式**: `ruff check` + `pytest -v --tb=short` + `npm run build`

本文档是项目进度的**唯一真实来源**。所有声明均可通过下文命令验证。

---

## 术语表 / Glossary

| 中文 | English | 说明 |
|------|---------|------|
| 沙箱 | Sandbox | 隔离执行环境 |
| 策略 | Policy | 治理规则配置 |
| 证据 | Evidence | 执行结果与审计数据 |
| 编排 | Orchestration | 工作流调度 |
| 网关 | Gate | 决策点 |
| 审计 | Audit | 操作记录 |

---

## L1–L5 架构状态矩阵

| 层级 | 组件 | 状态 | 缺口 | 验证 |
|:----:|------|:----:|------|------|
| **L1** | 策略配置 + 网关规则 | ✅ | — | `policy_loader.py`, `gate.py` |
| **L1** | 工具白名单 | ✅ | — | `PolicyConfig.tools.allowlist` |
| **L1** | 成本治理 | ✅ | — | `CostGovernance` + `_enforce_budget()` |
| **L1** | 沙箱策略 | ✅ | — | `SandboxPolicy` + `sandbox.mode` + `ContainerPolicy` |
| **L2** | LangGraph 状态机 | ✅ | — | `build_orchestration_graph()` |
| **L2** | 节点契约 (5 节点) | ✅ | — | `orchestrator_service.py` |
| **L2** | 重试/短路 | ✅ | — | `GovernanceBudget` + 条件边 |
| **L3** | 工具契约 + 注册表 | ✅ | — | `tools/contracts.py`, `tools/registry.py` |
| **L3** | 沙箱 (subprocess) | ✅ | — | `execution/sandbox.py` (319 行) |
| **L3** | 容器沙箱 (run_pytest/playwright) | ✅ | — | `execution/container_sandbox.py` (265 行) |
| **L3** | Playwright 强制容器化 | ✅ | — | `playwright_tool.py` 安全门禁通过 |
| **L3** | 产物熔断 (Count/Size) | ✅ | — | `ToolExecutionContext` 熔断验证 |
| **L3** | 策略驱动沙箱 | ✅ | — | 15+ 集成测试通过 (含网络隔离设计) |
| **L4** | MCP 客户端 | ✅ | — | `protocol/mcp/client.py` |
| **L4** | MCP 服务端 (write: run_pytest) | ✅ | — | `server.py` + `errors.py` + 25 测试 |
| **L4** | MCP 速率限制 (Phase 2A) | ✅ | — | `rate_limiter.py` + 13 测试 (-32008/-32009) |
| **L5** | 黄金数据集 | ✅ | — | `governance/golden/dataset.yaml` (5 用例) |
| **L5** | 回归 CLI | ✅ | — | `python -m qualityfoundry.governance.evals` |
| **L5** | 证据聚合 | ✅ | — | `evidence.json` 含 policy/repro/governance |
| **L5** | Dashboard P3 (Real-time) | ✅ | — | SSE streaming + RunEvent model (`4d080a35a5a2`) |
| **L5** | Dashboard P2 | ✅ | — | timeseries + filters + policy diff + risk card + csv + anomaly + contract guards |

---

## 核心理念对齐

| 原则 | 状态 | 实现 |
|------|:----:|------|
| **证据优先** | ✅ | `evidence.json`、构件索引、审计日志 |
| **可复现性** | ✅ | `ReproMeta`: git_sha, branch, dirty, deps_fingerprint |
| **最小权限** | ✅ | RBAC + 白名单 + MCP write 安全链 (auth→perm→rate_limit→policy→sandbox) |
| **成本治理** | ✅ | timeout + max_retries + 预算短路 + evidence.governance |
| **混合质量** | ✅ | 确定性检查 + AI 评审 (多模型评估、Policy 集成、Gate/Evidence 链) |

---

## MVP 闭环状态

```
NL → Plan → (HITL) → Execute → Evidence → Judgment
 ✅    ✅      ✅        ✅         ✅          ✅
```

**闭环完成**: 证据优先 + 可复现性 + 最小权限 + 成本治理，均带审计追踪。

---

## 启动保证

> **自动初始化**: 后端启动时，若 `environments` 表为空则自动初始化 `Local` 环境。
>
> **策略 API**: `GET /api/v1/policies/current` 始终返回当前策略元数据。

### Run 体系唯一入口（P2 统一后）

> **Run Center 数据源**：
> - 列表：`GET /api/v1/orchestrations/runs`
> - 详情：`GET /api/v1/orchestrations/runs/{id}`
>
> **Legacy 端点**（deprecated，Sunset: 2026-02-23）：
> - `GET /api/v1/runs*`：只读、deprecated、不可写
> - 前端代码禁止引用 `qf.ts`（使用 `api/orchestrations.ts`）

---

## 关键缺口 (待办优先级)

### P1 — 能力跃迁

| 项目 | 描述 | 状态 |
|------|------|------|
| **L4 MCP Write Phase 2B** | `run_playwright` (Container-only) | ✅ v0.20 已发布 |
| **L4 MCP Write Phase 3** | `run_shell` (高危工具硬拦截) | 🔴 设计已锁定，HARD BLOCK |

| 项目 | 描述 | 工作量 |
|------|------|--------|
| **L5 Dashboard P3** | 实时推送 / webhook 通知 / 多租户 | 2-3d |

### P2 — 长期演进

| 项目 | 描述 | 状态 |
|------|------|:----:|
| **Auth JWT 升级** | opaque→JWT 标准化认证 | ✅ v0.22 |
| **L3 Multi-tenant Phase 1-2** | Tenant 模型 + TenantContext + API | ✅ v0.24 |
| **L3 Multi-tenant Phase 3-4** | 沙箱增强 + Migration 自动化 | 🔴 待研究 |
| **混合质量 (AI 评审)** | 多模型评审 + Policy/Gate/Evidence 集成 | ✅ v0.21 |

---

## 关键文件参考

| 功能 | 文件路径 |
|------|----------|
| 编排服务 | `backend/app/qualityfoundry/services/orchestrator_service.py` |
| 网关决策 | `backend/app/qualityfoundry/governance/gate.py` |
| 策略加载器 | `backend/app/qualityfoundry/governance/policy_loader.py` |
| 沙箱执行 | `backend/app/qualityfoundry/execution/sandbox.py` |
| 容器沙箱 | `backend/app/qualityfoundry/execution/container_sandbox.py` |
| 复现元数据 | `backend/app/qualityfoundry/governance/repro.py` |
| 证据收集器 | `backend/app/qualityfoundry/governance/tracing/collector.py` |
| 黄金数据集 | `backend/app/qualityfoundry/governance/golden/dataset.yaml` |
| MCP 服务端 | `backend/app/qualityfoundry/protocol/mcp/server.py` |
| MCP 工具 (读+写) | `backend/app/qualityfoundry/protocol/mcp/tools.py` |
| MCP 错误码 | `backend/app/qualityfoundry/protocol/mcp/errors.py` |
| MCP 速率限制 | `backend/app/qualityfoundry/protocol/mcp/rate_limiter.py` |
| MCP 安全测试 | `backend/tests/test_mcp_write_security.py` (11 测试) |
| AI 评审引擎 | `backend/app/qualityfoundry/governance/ai_review/` |
| AI 评审预研 | `docs/designs/ai-review-research.md` |
| MCP 速率测试 | `backend/tests/test_mcp_rate_limiter.py` (13 测试) |
| Phase 2B 设计 | `docs/designs/mcp-write-phase2b.md` v0.2 |

---

## 验证命令

```bash
# 检查 L1 策略
cat backend/app/qualityfoundry/governance/policy_config.yaml

# 检查 L2 LangGraph
grep -n "StateGraph\|build_orchestration_graph" backend/app/qualityfoundry/services/orchestrator_service.py

# 检查 L3 沙箱
wc -l backend/app/qualityfoundry/execution/sandbox.py  # 应为 ~319 行

# 检查 L4 MCP Write 安全 (25 测试)
cd backend && python -m pytest tests/test_mcp_write_security.py tests/test_mcp_server_smoke.py -v

# 检查 L4 MCP 服务端
ls backend/app/qualityfoundry/protocol/mcp/

# 检查 L5 黄金数据集
cat backend/app/qualityfoundry/governance/golden/dataset.yaml

# 运行测试
cd backend && python -m pytest -q --tb=short
```

---
 
## CI Gate Definition (Required Checks)
 
| Job Name | Command | Description |
|----------|---------|-------------|
| `unit-tests` | `ruff check .` && `pytest -q --tb=short` | 静态检查与稳定单元测试 |
| `smoke-fast` | `pytest -m smoke_fast` | 核心流程快速验证 |
| `mcp-security` | `pytest tests/test_mcp_write_security.py ...` | L4 写能力安全门禁 |
| `dashboard-contracts` | `pytest tests/test_api_contract_dashboard_summary.py` | L5 Dashboard 数据准确性护栏 |
 
> [!NOTE]
> `E2E Smoke` (Playwright) 暂不纳入合并门禁，仅作为 `workflow_dispatch` 手动触发或 nightly 运行，避免因环境不稳定阻断开发。
 
---
 
## 文档历史

| 2026-02-01 | Claude (Antigravity) + Kimi | v0.24: **Multi-tenant Phase 2** — TenantService CRUD + API + 成员管理 (5 任务/26 测试/~800 行) |
| 2026-02-01 | Claude (Antigravity) + Kimi | v0.23: **Multi-tenant Phase 1a** — Tenant/Membership 模型 + JWT 扩展 + TenantContext 中间件 (6 任务/14 测试/~640 行) |
| 2026-02-01 | Claude (Antigravity) + Kimi | v0.22: **JWT Auth 升级** — opaque→JWT 标准化认证，双模式兼容，17 测试通过 (6 任务/~400 行) |
| 2026-01-31 | Claude (Antigravity) + Kimi | v0.21: **AI 评审系统完整交付** — 多模型 PoC + Policy + Gate + Evidence + API (8 任务/61 测试/1100 行) |
| 2026-01-29 | Claude (Antigravity) | v0.20 正式版收官：CI 回归修复（Table Registration/Schema Sync/Token Test/Audit Order）完成，全量 453+ 测试通过。 |
| 2026-01-27 | Claude (Antigravity) | 审计标准化 (Option 1) 完成：一致性口径、Playback 跳过诊断映射；Linux CI 容器门禁 (Option 2) 已建立。 |
| 2026-01-27 | Claude (Antigravity) | Artifact audit 已通用化：pytest + playwright 均覆盖；payload bounded & sanitized (rel_path / samples<=10 / boundary) |
| 2026-01-26 | Claude (Antigravity) | MCP Phase 2A 速率限制 + Phase 2B 设计文档 v0.2 |
| 2026-01-26 | Claude (Antigravity) | v0.18: L5 Dashboard P2 完成 (P2-2/3/4) |
| 2026-01-25 | Claude (Antigravity) | 文档中文化 |
| 2026-01-25 | Claude (Antigravity) | v0.15: L3 容器沙箱完成 (PR#56/#57) |
| 2026-01-25 | Claude (Antigravity) | L4 MCP Write Security Phase 1 完成 (25 测试) |
| 2026-01-25 | Claude (Antigravity) | 状态矩阵 + ChatGPT 路线图对齐 |
| 2026-01-24 | Claude + ChatGPT Audit | Run 统一 P2 更新 |
| 2026-01-22 | Claude + ChatGPT Audit | 初始基线与验证 |
