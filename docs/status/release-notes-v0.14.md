# QualityFoundry v0.14 Release Notes

> **Release**: `v0.14-mcp-write-p1`  
> **Tag Commit**: `827cfaf` (Merge PR #53)  
> **Date**: 2026-01-25  
> **CI Status**: ✅ All checks passed

---

## Executive Summary

本版本完成了 **L4 MCP Write Security Phase 1**，首次向 MCP 客户端开放受控写能力（`run_pytest`），并建立了完整的四重安全链（认证→权限→策略→沙箱）。这标志着 QualityFoundry 从"只读协议层"演进到"受控写协议层"的关键里程碑。

---

## Blueprint L1–L5 对齐矩阵

| Layer | Component | v0.14 Status | Gap |
|:-----:|-----------|:------------:|-----|
| **L1** | Policy + RBAC + Ownership | ✅ | — |
| **L2** | LangGraph Orchestration | ✅ | — |
| **L3** | Sandbox (subprocess) | ✅ MVP | 🔴 容器级强隔离 |
| **L4** | MCP Server (read + write) | ✅ | 🟡 Phase 2: playwright/shell |
| **L5** | Golden + Regression + Audit | ✅ | 🟡 趋势 Dashboard |

### 核心哲学达成度

| Principle | Status | Implementation |
|-----------|:------:|----------------|
| Evidence-First | ✅ | `evidence.json` + artifact index + audit log |
| Reproducibility | ✅ | `ReproMeta`: git_sha, branch, dirty, deps_fingerprint |
| Least Privilege | ✅ | RBAC + allowlist + MCP write security chain |
| Cost Governance | ✅ | timeout + max_retries + budget short-circuit |
| Hybrid Quality | 🟡 | Deterministic checks strong; AI Judge TBD |

---

## What's New in v0.14

### L4 MCP Write Security Phase 1 ⭐

**首个受控写工具：`run_pytest`**

MCP 服务端现在支持通过 `run_pytest` 工具执行测试，并强制要求通过以下安全链：

```
Auth (token) → Permission (RBAC) → Policy (allowlist) → Sandbox (enabled)
```

| Feature | Description |
|---------|-------------|
| **安全链强制执行** | 四重校验必须全部通过，任一失败立即返回结构化错误 |
| **错误码体系** | `-32001 AUTH_REQUIRED`, `-32003 PERMISSION_DENIED`, `-32004 POLICY_BLOCKED`, `-32006 SANDBOX_VIOLATION` |
| **审计事件** | `MCP_TOOL_CALL` 类型，记录 tool_name、args_hash、caller_user_id |
| **设计文档** | [mcp-write-security.md](file:///Users/william/project/qualityfoundry/docs/designs/mcp-write-security.md) v0.1 frozen |

**安全测试覆盖**

- 11 项专项安全测试 (`test_mcp_write_security.py`)
- 14 项 MCP 冒烟测试 (`test_mcp_server_smoke.py`)
- **合计 25 项 L4 安全测试全部通过**

### 开发体验优化

| Feature | File |
|---------|------|
| 启动脚本 (避免 TTY 挂起) | `scripts/start-all.sh`, `start-backend.sh`, `start-frontend.sh` |
| Run Center E2E 测试 | `frontend/e2e/test_run_center.py` |
| 验收检查清单 | `docs/walkthroughs/run-center-acceptance.md` |

---

## Test Results Summary

```
Backend Tests: 333+ tests passed
MCP Security:  25/25 tests passed
CI Workflows:  quality-gate ✅ | CI ✅ | mcp-security ✅
```

---

## Key Files Added/Modified

### New Files

| File | Purpose |
|------|---------|
| `backend/app/qualityfoundry/protocol/mcp/errors.py` | MCP 结构化错误码 |
| `backend/tests/test_mcp_write_security.py` | 11 项安全边界测试 |
| `docs/designs/mcp-write-security.md` | 设计文档 (frozen) |
| `.github/workflows/mcp-security.yml` | CI MCP 安全测试 Job |

### Modified Files

| File | Change |
|------|--------|
| `backend/app/qualityfoundry/protocol/mcp/server.py` | 写能力 + 安全链集成 |
| `backend/app/qualityfoundry/protocol/mcp/tools.py` | `WRITABLE_TOOLS` 常量 + 权限检查 |
| `backend/app/qualityfoundry/governance/policy_loader.py` | `SandboxPolicy` 配置 |
| `docs/status/progress_baseline.md` | L4 状态更新 |

---

## Migration Guide

### 无破坏性变更

本版本完全向后兼容，无需迁移。

### 新增配置项（可选）

如需启用 MCP 写能力，确保 `policy_config.yaml` 包含：

```yaml
tools:
  allowlist:
    - run_pytest  # 显式 allowlist 才能写

sandbox:
  enabled: true   # 写工具必须开启沙箱
```

---

## Known Gaps & Next Priorities

### P0-2 (本周可完成)

| Item | Status |
|------|--------|
| Frontend Run Center 主路径验收 | E2E 测试已覆盖，待团队验收 |

### P1 (能力跃迁)

| Item | Effort |
|------|--------|
| L3 Container Sandbox (`run_pytest`) | 3-5d |
| L5 Dashboard/趋势 | 2-3d |

### P2 (长期演进)

| Item | Description |
|------|-------------|
| MCP Write Phase 2 | `run_playwright`, `run_shell` 等高危工具 |
| Hybrid Quality (AI Judge) | 多模型评审资产 |

---

## Verification Commands

```bash
# 验证 L4 MCP 安全测试
cd backend && python -m pytest tests/test_mcp_write_security.py tests/test_mcp_server_smoke.py -v

# 验证全量测试
cd backend && python -m pytest -q --tb=short

# 验证 CI 状态
gh run list --limit 5
```

---

## Contributors

- Claude (Antigravity) — Implementation
- ChatGPT — Roadmap alignment & review

---

*Generated: 2026-01-25T22:28 UTC+8*
