# QualityFoundry Progress Baseline

> **Release Anchor**: `main@983acf2` (2026-01-22)
> **Last Verified**: 2026-01-22
> **Git Tag**: `v0.12-cost-governance`
> **Verification Method**: Code grep + file existence checks

This document serves as the **single source of truth** for project progress. All claims are verifiable via the commands provided.

---

## L1-L5 Architecture Status

| Layer | Name | Status | Verification |
|-------|------|--------|--------------|
| **L1** | Policy (规则与门禁) | ✅ Complete | `ls governance/policy_loader.py gate.py` |
| **L2** | Orchestration (编排层) | ✅ Phase 2.2 Complete (LangGraph) | `from langgraph.graph import StateGraph` in orchestrator_service.py |
| **L3** | Execution (执行层) | 🟡 Partial | Tool contract + runners ✅; Sandbox/permissions 🔴 |
| **L4** | Protocol (MCP) | 🟡 Client-only | No independent MCP Server (`mcp_server/` not exists) |
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
| **MCP Integration** | "L4 Complete" | Only `MCPClient` calling external servers | 🟡 MCP Client only |

### 🔴 Not Started / Not Exists

| Feature | Claimed | Code Verification | Corrected Status |
|---------|---------|-------------------|------------------|
| **Audit Log** | ✅ | `grep -r "audit_log" backend/` = 0 results | 🔴 Not exists |
| **MCP Server** | L4 ✅ | No `mcp_server/`, no FastMCP entry | 🔴 Not started |
| **LangGraph Integration** | ✅ Phase 2.2 | `from langgraph.graph import StateGraph` | ✅ Complete |
| **Cost Governance** | Phase 5.1 ✅ | Budget/timeout circuit breaker logic | ✅ Minimal (timeout) |

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
- Git tag: `v0.12-cost-governance`
- Main HEAD: `983acf2`
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
