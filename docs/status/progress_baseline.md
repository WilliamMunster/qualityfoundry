# QualityFoundry Progress Baseline

> **Release Anchor**: `main@9a3003d` (2026-01-24)
> **Last Verified**: 2026-01-24
> **Git Tag**: `v0.13-run-unification`
> **Verification Method**: Code grep + pytest (286 passed, 7 skipped)

This document serves as the **single source of truth** for project progress. All claims are verifiable via the commands provided.

### Bootstrap Guarantees

> **Auto-seed**: Backend startup will auto-seed a default environment (`Local`) **only if** the `environments` table is empty.
>
> **Policy API**: `GET /api/v1/policies/current` always returns current policy metadata (version, hash, summary).

### Run 体系唯一入口（P2 统一后）

> **Run Center 数据源**：
> - 列表：`GET /api/v1/orchestrations/runs`
> - 详情：`GET /api/v1/orchestrations/runs/{id}`
>
> **Legacy 端点**（deprecated，Sunset: 2026-02-23）：
> - `GET /api/v1/runs*`：只读、deprecated、不可写
> - 前端代码禁止引用 `qf.ts`（使用 `api/orchestrations.ts`）
>
> **契约测试**：`test_api_contract_run_detail.py` + `test_legacy_runs_readonly.py`

---

## L1-L5 Architecture Status

| Layer | Name | Status | Verification |
|-------|------|--------|--------------|
| **L1** | Policy (规则与门禁) | ✅ Complete | `ls governance/policy_loader.py gate.py` |
| **L2** | Orchestration (编排层) | ✅ Phase 2.2 Complete (LangGraph) | `from langgraph.graph import StateGraph` in orchestrator_service.py |
| **L3** | Execution (执行层) | 🟡 Partial | Tool contract + runners ✅; Sandbox/permissions 🔴 |
| **L4** | Protocol (MCP) | 🟡 MCP Server (read-only) + Client | `protocol/mcp/server.py` exists, 14 tests passed |
| **L5** | Governance & Evals | ✅ Phase 5.2 Complete | `ls governance/evals/ golden/` |

---

## Phase Completion Status

### ✅ Merged to Main (Verified)

| Phase | Feature | Verification Command | Status |
|-------|---------|---------------------|--------|
| **Phase 0** | Project skeleton | Directory structure exists | ✅ |
| **Phase 1.1** | Requirement/Scenario/TestCase CRUD | `ls api/v1/routes_requirements.py` | ✅ |
| **Phase 1.2** | OrchestratorService (5 nodes) | `git show main:...services/orchestrator_service.py` | ✅ |
| **Phase 2.2** | LangGraph state machine | `build_orchestration_graph()` in orchestrator_service.py | ✅ |
| **Phase 1.3** | ReproMeta reproducibility | `git show main:...governance/repro.py` | ✅ |
| **Phase 5.2** | Golden Dataset + Regression CLI | `ls governance/golden/dataset.yaml governance/evals/runner.py` | ✅ |

### 🟡 Partial / Needs Clarification

| Feature | Claimed | Actual | Corrected Status |
|---------|---------|--------|------------------|
| **Authentication** | "JWT" | `secrets.token_urlsafe()` simple token | 🟡 Basic token (not JWT) |
| **Role-based access** | "RBAC" | `UserRole` enum exists, no middleware enforcement | 🟡 Model exists, not enforced |
| **MCP Integration** | "L4 Complete" | `MCPClient` + `protocol/mcp/server.py` (read-only) | 🟡 MCP Server read-only + Client |

### 🔴 Not Started / Not Exists

| Feature | Claimed | Code Verification | Corrected Status |
|---------|---------|-------------------|------------------|
| **Audit Log** | ✅ | `services/audit_service.py`, `database/audit_log_models.py`, 6+ tests | ✅ Complete |
| **MCP Server** | L4 ✅ | `protocol/mcp/server.py`, 14 tests passed | ✅ Complete (read-only) |
| **LangGraph Integration** | ✅ Phase 2.2 | `from langgraph.graph import StateGraph` | ✅ Complete |
| **Cost Governance** | Phase 5.1 ✅ | `_enforce_budget()` + GovernanceBudget | ✅ Complete (budget + short-circuit) |

---

## Key Files Reference

| Function | File Path |
|----------|-----------|
| Orchestrator Service | `backend/app/qualityfoundry/services/orchestrator_service.py` |
| Gate Decision | `backend/app/qualityfoundry/governance/gate.py` |
| Policy Loader | `backend/app/qualityfoundry/governance/policy_loader.py` |
| ReproMeta | `backend/app/qualityfoundry/governance/repro.py` |
| Evidence Collector | `backend/app/qualityfoundry/governance/tracing/collector.py` |
| Golden Dataset | `backend/app/qualityfoundry/governance/golden/dataset.yaml` |
| Regression Runner | `backend/app/qualityfoundry/governance/evals/runner.py` |
| Tool Contracts | `backend/app/qualityfoundry/tools/contracts.py` |
| User Model | `backend/app/qualityfoundry/database/user_models.py` |

---

## Version Anchoring Policy

| Type | Value | Purpose |
|------|-------|---------|
| **External version anchor** | Git tag / commit SHA | Use for releases, PRs, documentation |
| **Internal package version** | `pyproject.toml: version` | Use for pip/dependency management |

**Current anchors:**
- Git tag: `v0.13-run-unification`
- Main HEAD: `9a3003d`
- pyproject.toml: `0.1.0` (not updated)

---

## Next Priorities (Aligned with ChatGPT Roadmap)

1. **Phase 5.3 Monitoring/Alerting** - Use `evidence.governance` and `decision_source` for failure clustering.
2. **L4 MCP Server 化** - Expose tools as MCP server.
3. **Security Enhancement Pack** - JWT/RBAC/Audit as separate epic (not mixed with LangGraph)

---

## Verification Commands

```bash
# Check OrchestratorService exists on main
git show main:backend/app/qualityfoundry/services/orchestrator_service.py | head -20

# Check ReproMeta exists
git show main:backend/app/qualityfoundry/governance/repro.py | head -20

# Check Golden Dataset
cat backend/app/qualityfoundry/governance/golden/dataset.yaml

# Verify no audit_log
grep -r "audit_log" backend/app/ | wc -l  # Should be 0

# Verify no MCP server
ls backend/app/qualityfoundry/mcp_server/ 2>&1  # Should fail

# Check auth implementation (NOT JWT)
grep -A5 "def create_access_token" backend/app/qualityfoundry/services/auth_service.py
```

---

## Document History

| Date | Author | Change |
|------|--------|--------|
| 2026-01-22 | Claude + ChatGPT Audit | Initial baseline with verification |
