# QualityFoundry 进度基线

> **版本锚点**: `main@0938806` (2026-01-26)
> **最后验证**: 2026-01-26
> **Git 标签**: `v0.16-sandbox-mcp-docs`
> **验证方式**: `ruff check` + `pytest -m smoke_fast` (Playwright 环境缺失导致 skip / 非门禁)

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
| **L3** | 容器沙箱 (run_pytest) | ✅ | — | `execution/container_sandbox.py` (265 行) |
| **L3** | 策略驱动沙箱 | ✅ | — | 12+ 集成测试通过 |
| **L4** | MCP 客户端 | ✅ | — | `protocol/mcp/client.py` |
| **L4** | MCP 服务端 (write: run_pytest) | ✅ | — | `server.py` + `errors.py` + 25 测试 |
| **L5** | 黄金数据集 | ✅ | — | `governance/golden/dataset.yaml` (5 用例) |
| **L5** | 回归 CLI | ✅ | — | `python -m qualityfoundry.governance.evals` |
| **L5** | 证据聚合 | ✅ | — | `evidence.json` 含 policy/repro/governance |

---

## 核心理念对齐

| 原则 | 状态 | 实现 |
|------|:----:|------|
| **证据优先** | ✅ | `evidence.json`、构件索引、审计日志 |
| **可复现性** | ✅ | `ReproMeta`: git_sha, branch, dirty, deps_fingerprint |
| **最小权限** | ✅ | RBAC + 白名单 + MCP write 安全链 (auth→perm→policy→sandbox) |
| **成本治理** | ✅ | timeout + max_retries + 预算短路 + evidence.governance |
| **混合质量** | 🟡 | 确定性检查强；AI 评审/多模型评估待定 |

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

### P0 — 收口项（本周可完成）

| 项目 | 描述 | 状态 |
|------|------|------|
| **L4 MCP Write 安全 Phase 1** | `run_pytest` 写能力 + 安全链 (auth→perm→policy→sandbox) | ✅ 25 测试 |
| **前端 Run Center 验收** | UUID orchestration runs 主路径：启动→查看→下载证据→审计链 | 1-2d |

### P1 — 能力跃迁

| 项目 | 描述 | 工作量 |
|------|------|--------|
| **L5 Dashboard/趋势** | 消费 `evidence.governance` / `repro` / `policy_meta` 做趋势图 | 2-3d |

### P2 — 长期演进

| 项目 | 描述 |
|------|------|
| **L3 强隔离深化** | 多租户支持与禁网策略动态下发 |
| **混合质量 (AI 评审)** | 多模型评审资产、主观评估体系 |

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
| MCP 安全测试 | `backend/tests/test_mcp_write_security.py` (11 测试) |

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

## 文档历史

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-01-25 | Claude (Antigravity) | 文档中文化 |
| 2026-01-25 | Claude (Antigravity) | v0.15: L3 容器沙箱完成 (PR#56/#57) |
| 2026-01-25 | Claude (Antigravity) | L4 MCP Write Security Phase 1 完成 (25 测试) |
| 2026-01-25 | Claude (Antigravity) | 状态矩阵 + ChatGPT 路线图对齐 |
| 2026-01-24 | Claude + ChatGPT Audit | Run 统一 P2 更新 |
| 2026-01-22 | Claude + ChatGPT Audit | 初始基线与验证 |
