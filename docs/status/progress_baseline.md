# QualityFoundry Progress Baseline

> **Release Anchor**: `main@HEAD` (2026-01-25)
> **Last Verified**: 2026-01-25
> **Git Tag**: `v0.15-container-sandbox`
> **Verification Method**: Code grep + pytest (container sandbox: 23 tests)

This document serves as the **single source of truth** for project progress. All claims are verifiable via the commands provided.

---

## L1–L5 Architecture Status Matrix

| Layer | Component | Status | Gap | Verification |
|:-----:|-----------|:------:|-----|--------------|
| **L1** | PolicyConfig + Gate Rules | ✅ | — | `policy_loader.py`, `gate.py` |
| **L1** | Tools Allowlist | ✅ | — | `PolicyConfig.tools.allowlist` |
| **L1** | Cost Governance | ✅ | — | `CostGovernance` + `_enforce_budget()` |
| **L1** | SandboxPolicy | ✅ | — | `SandboxPolicy` + `sandbox.mode` + `ContainerPolicy` |
| **L2** | LangGraph State Machine | ✅ | — | `build_orchestration_graph()` |
| **L2** | Node Contracts (5 nodes) | ✅ | — | `orchestrator_service.py` |
| **L2** | Retry/Short-circuit | ✅ | — | `GovernanceBudget` + conditional edges |
| **L3** | Tool Contracts + Registry | ✅ | — | `tools/contracts.py`, `tools/registry.py` |
| **L3** | Sandbox (subprocess) | ✅ | — | `execution/sandbox.py` (319 lines) |
| **L3** | Container Sandbox (run_pytest) | ✅ | 🟡 仅 run_pytest | `execution/container_sandbox.py` (265 lines) |
| **L3** | Policy-driven Sandbox | ✅ | — | 12 integration tests passed |
| **L4** | MCP Client | ✅ | — | `protocol/mcp/client.py` |
| **L4** | MCP Server (write: run_pytest) | ✅ | 🟡 Phase 2: playwright/shell | `server.py` + `errors.py` + 25 tests |
| **L5** | Golden Dataset | ✅ | — | `governance/golden/dataset.yaml` (5 cases) |
| **L5** | Regression CLI | ✅ | — | `python -m qualityfoundry.governance.evals` |
| **L5** | Evidence Aggregation | ✅ | — | `evidence.json` with policy/repro/governance |

---

## Core Philosophy Alignment

| Principle | Status | Implementation |
|-----------|:------:|----------------|
| **Evidence-First** | ✅ | `evidence.json`, artifact index, audit log |
| **Reproducibility** | ✅ | `ReproMeta`: git_sha, branch, dirty, deps_fingerprint |
| **Least Privilege** | ✅ | RBAC + allowlist + MCP write security chain (auth→perm→policy→sandbox) |
| **Cost Governance** | ✅ | timeout + max_retries + budget short-circuit + evidence.governance |
| **Hybrid Quality** | 🟡 | Deterministic checks strong; AI Judge/multi-model eval TBD |

---

## MVP Loop Status

```
NL → Plan → (HITL) → Execute → Evidence → Judgment
 ✅    ✅      ✅        ✅         ✅          ✅
```

**Closed Loop**: Evidence-First + Reproducibility + Least Privilege + Cost Governance all engineered with audit trail.

---

## Bootstrap Guarantees

> **Auto-seed**: Backend startup auto-seeds `Local` environment if `environments` table is empty.
>
> **Policy API**: `GET /api/v1/policies/current` always returns current policy metadata.

### Run 体系唯一入口（P2 统一后）

> **Run Center 数据源**：
> - 列表：`GET /api/v1/orchestrations/runs`
> - 详情：`GET /api/v1/orchestrations/runs/{id}`
>
> **Legacy 端点**（deprecated，Sunset: 2026-02-23）：
> - `GET /api/v1/runs*`：只读、deprecated、不可写
> - 前端代码禁止引用 `qf.ts`（使用 `api/orchestrations.ts`）

---

## Key Gaps (Next Priorities)

### P0 — 收口项（本周可完成）

| Item | Description | Status |
|------|-------------|--------|
| **L4 MCP Write Safety Phase 1** | `run_pytest` 写能力 + 安全链 (auth→perm→policy→sandbox) | ✅ 25 tests |
| **Frontend Run Center 验收** | UUID orchestration runs 主路径：启动→查看→下载证据→审计链 | 1-2d |

### P1 — 能力跃迁

| Item | Description | Effort |
|------|-------------|--------|
| **L3 Container Sandbox** | ✅ `run_pytest` 容器化完成：scope 仅 run_pytest; default subprocess; container 不可用拒绝+审计; 安全特性：禁网/只读/资源限制/超时kill | ✅ Done |
| **L5 Dashboard/趋势** | 消费 `evidence.governance` / `repro` / `policy_meta` 做趋势图 | 2-3d |

### P2 — 长期演进

| Item | Description |
|------|-------------|
| **Hybrid Quality (AI Judge)** | 多模型评审资产、主观评估体系 |
| **Multi-tenant + Quotas** | 开放给更多人/agent 使用时再做 |

---

## Key Files Reference

| Function | File Path |
|----------|-----------|
| Orchestrator Service | `backend/app/qualityfoundry/services/orchestrator_service.py` |
| Gate Decision | `backend/app/qualityfoundry/governance/gate.py` |
| Policy Loader | `backend/app/qualityfoundry/governance/policy_loader.py` |
| Sandbox Execution | `backend/app/qualityfoundry/execution/sandbox.py` |
| Container Sandbox | `backend/app/qualityfoundry/execution/container_sandbox.py` |
| ReproMeta | `backend/app/qualityfoundry/governance/repro.py` |
| Evidence Collector | `backend/app/qualityfoundry/governance/tracing/collector.py` |
| Golden Dataset | `backend/app/qualityfoundry/governance/golden/dataset.yaml` |
| MCP Server | `backend/app/qualityfoundry/protocol/mcp/server.py` |
| MCP Tools (read + write) | `backend/app/qualityfoundry/protocol/mcp/tools.py` |
| MCP Errors | `backend/app/qualityfoundry/protocol/mcp/errors.py` |
| MCP Security Tests | `backend/tests/test_mcp_write_security.py` (11 tests) |

---

## Verification Commands

```bash
# Check L1 Policy
cat backend/app/qualityfoundry/governance/policy_config.yaml

# Check L2 LangGraph
grep -n "StateGraph\|build_orchestration_graph" backend/app/qualityfoundry/services/orchestrator_service.py

# Check L3 Sandbox
wc -l backend/app/qualityfoundry/execution/sandbox.py  # Should be ~319 lines

# Check L4 MCP Write Security (25 tests)
cd backend && python -m pytest tests/test_mcp_write_security.py tests/test_mcp_server_smoke.py -v

# Check L4 MCP Server
ls backend/app/qualityfoundry/protocol/mcp/

# Check L5 Golden Dataset
cat backend/app/qualityfoundry/governance/golden/dataset.yaml

# Run tests
cd backend && python -m pytest -q --tb=short
```

---

## Document History

| Date | Author | Change |
|------|--------|--------|
| 2026-01-25 | Claude (Antigravity) | v0.15: L3 Container Sandbox complete (PR#56/#57) |
| 2026-01-25 | Claude (Antigravity) | L4 MCP Write Security Phase 1 完成 (25 tests) |
| 2026-01-25 | Claude (Antigravity) | Status matrix + ChatGPT roadmap alignment |
| 2026-01-24 | Claude + ChatGPT Audit | Run unification P2 update |
| 2026-01-22 | Claude + ChatGPT Audit | Initial baseline with verification |
