# MCP Write Security Design

> **Version**: 0.1 (frozen)  
> **Status**: Design Approved — Ready for Implementation  
> **Author**: Claude (Antigravity)  
> **Date**: 2026-01-25

## 1. 目标

在不削弱现有 RBAC / Policy / Cost / Sandbox 的前提下，安全地暴露 MCP 写能力。

---

## 2. Phase 1 范围

### 允许暴露

| Tool | 暴露 | 原因 |
|------|:----:|------|
| `run_pytest` | ✅ | subprocess 可 sandbox，已有 12 集成测试验证 |

### 不暴露（Phase 1 明确排除）

| Tool | 排除原因 |
|------|----------|
| `run_playwright` | 浏览器进程，不适用 subprocess sandbox |
| `run_shell` | 高危，需更强隔离策略 |
| Any new tool | 先 read-only 证明再开放 |

---

## 3. 八问回答

### Q1: 哪些工具允许暴露为 MCP 写能力？

**回答**: Phase 1 仅暴露 `run_pytest`。

依据:
- `registry.py:SANDBOXABLE_TOOLS = frozenset({"run_pytest"})`
- Playwright 明确注释"不适用 subprocess 沙箱"

### Q2: 认证与身份传递

**方案**: stdio 模式无 HTTP header，token 通过 JSON-RPC `params.auth.token` 传递

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "run_pytest",
    "arguments": {"test_path": "tests/"},
    "auth": {"token": "<access_token>"}
  }
}
```

**映射规则**:
- `params.auth.token` → `AuthService.verify_token(db, token)` → `User | None`
- 无 token / 无效 token → 拒绝 (MCP Error: -32001)
- 复用现有 Bearer token 口径，语义统一

### Q3: 权限模型

**对齐现有 Permission 枚举**:

| MCP Tool | Required Permission | Role (最低) |
|----------|---------------------|-------------|
| `get_evidence` | `ARTIFACT_READ` | VIEWER |
| `list_artifacts` | `ARTIFACT_READ` | VIEWER |
| `get_artifact_content` | `ARTIFACT_READ` | VIEWER |
| `run_pytest` (NEW) | `ORCHESTRATION_RUN` | USER |

**检查点**: `MCPServer.handle_tool_call()` 增加权限校验

```python
if not user.has_permission(required_permission):
    return {"error": "Permission denied", "code": -32003}
```

### Q4: Policy 绑定

**Phase 1 策略**: 仅支持 current policy，不支持版本选择

```python
policy = get_policy()  # 始终使用当前策略
```

**Allowlist 检查**（**仅 MCP 写模式**，HTTP Orchestration 维持现有语义）:
```python
# MCP 写工具模式：allowlist 为空视为配置错误
if not policy.tools.allowlist:
    return {"error": "MCP write requires explicit allowlist", "code": -32004}
if tool_name not in policy.tools.allowlist:
    return {"error": "Tool blocked by policy", "code": -32004}
```

### Q5: Budget/Cost

**累计与短路**:

| 场景 | 行为 |
|------|------|
| 单次 MCP 调用 | 新建 `GovernanceBudget`，记录 elapsed_ms |
| 沙箱硬超时 | sandbox hard-kill → `-32007 TIMEOUT` |
| 预算策略短路 | elapsed_ms_total / attempts_total 等超限 → `-32005 BUDGET_EXCEEDED` |
| 记录 | `evidence.governance` 写入 run 目录 |

**evidence.governance 结构**:
```json
{
  "elapsed_ms_total": 1234,
  "attempts_total": 1,
  "short_circuited": false,
  "policy_timeout_s": 300
}
```

### Q6: Sandbox

**强制规则**:

| 条件 | Sandbox |
|------|---------|
| `tool in SANDBOXABLE_TOOLS` && `policy.sandbox.enabled` | ✅ 强制 |
| `tool in SANDBOXABLE_TOOLS` && `!policy.sandbox.enabled` | ❌ **拒绝执行** (返回 -32006) |
| `tool not in SANDBOXABLE_TOOLS` | ❌ Phase 1 不开放此类工具 |

> [!CAUTION]
> MCP 写能力 **必须** `sandbox.enabled=true`，否则直接拒绝。这是 Phase 1 核心安全边界。

**透传参数**:
```python
# 强制沙箱检查（MCP 写能力必须）
if not policy.sandbox.enabled:
    return {"error": "MCP write requires sandbox", "code": -32006}

SandboxConfig(
    timeout_s=policy.sandbox.timeout_s,
    memory_limit_mb=policy.sandbox.memory_limit_mb,
    allowed_paths=policy.sandbox.allowed_paths,
    env_whitelist=policy.sandbox.env_whitelist,
)
```

### Q7: 审计与证据链

**AuditLog 事件**:

| Event Type | 触发点 | 记录内容 | 要求 |
|------------|--------|----------|------|
| `MCP_TOOL_CALL` | `handle_tool_call()` 入口 | tool_name, args_hash, caller_user_id | MUST (NEW) |
| `SANDBOX_EXEC` | 沙箱执行完成 | exit_code, duration_ms | MUST |
| `POLICY_BLOCKED` | Policy 拒绝 | blocked_reason | MUST |
| `TOOL_STARTED` | 工具开始执行 | run_id, tool_name | OPTIONAL |
| `TOOL_FINISHED` | 工具执行完成 | status, duration_ms | OPTIONAL |

**关联**:
- `run_id`: MCP 调用生成新 UUID，全链路共享
- `artifacts`: 写入 `artifacts/{run_id}/`

### Q8: 失败模式与降级

**MCP 错误码表**:

| Code | Name | 触发条件 | 响应示例 |
|------|------|----------|----------|
| -32001 | `AUTH_REQUIRED` | 无 token / token 无效 | `{"error": {"code": -32001, "message": "Authentication required"}}` |
| -32003 | `PERMISSION_DENIED` | 用户无 `ORCHESTRATION_RUN` | `{"error": {"code": -32003, "message": "Permission denied"}}` |
| -32004 | `POLICY_BLOCKED` | 工具不在 allowlist / allowlist 为空 | `{"error": {"code": -32004, "message": "Tool blocked by policy"}}` |
| -32005 | `BUDGET_EXCEEDED` | 预算累计超限 | `{"error": {"code": -32005, "message": "Budget exceeded"}}` |
| -32006 | `SANDBOX_VIOLATION` | 沙箱阻断 / sandbox.enabled=false | `{"error": {"code": -32006, "message": "Sandbox violation: {reason}"}}` |
| -32007 | `TIMEOUT` | 沙箱硬超时 kill | `{"error": {"code": -32007, "message": "Execution timeout"}}` |
| -32602 | `INVALID_PARAMS` | 参数校验失败 | (JSON-RPC 标准) |

---

## 4. 顺序图

```
┌────────┐      ┌───────────┐      ┌──────────────┐     ┌──────────┐     ┌─────────────┐
│  MCP   │      │    MCP    │      │     Auth     │     │  Policy  │     │   Sandbox   │
│ Client │      │  Server   │      │   Service    │     │  Loader  │     │   Runner    │
└───┬────┘      └─────┬─────┘      └──────┬───────┘     └────┬─────┘     └──────┬──────┘
    │                 │                   │                  │                  │
    │ tools/call      │                   │                  │                  │
    │ (run_pytest)    │                   │                  │                  │
    ├────────────────►│                   │                  │                  │
    │                 │                   │                  │                  │
    │                 │ verify_token()    │                  │                  │
    │                 ├──────────────────►│                  │                  │
    │                 │      User         │                  │                  │
    │                 │◄──────────────────┤                  │                  │
    │                 │                   │                  │                  │
    │                 │ check_permission(ORCHESTRATION_RUN)  │                  │
    │                 ├──────────────────►│                  │                  │
    │                 │       OK          │                  │                  │
    │                 │◄──────────────────┤                  │                  │
    │                 │                   │                  │                  │
    │                 │ get_policy()      │                  │                  │
    │                 ├─────────────────────────────────────►│                  │
    │                 │    PolicyConfig   │                  │                  │
    │                 │◄─────────────────────────────────────┤                  │
    │                 │                   │                  │                  │
    │                 │ check allowlist   │                  │                  │
    │                 ├───────────────────┤                  │                  │
    │                 │                   │                  │                  │
    │                 │ build SandboxConfig                  │                  │
    │                 ├───────────────────────────────────────────────────────►│
    │                 │                   │                  │                  │
    │                 │                   │                  │   run_in_sandbox │
    │                 │                   │                  │◄─────────────────┤
    │                 │                   │                  │                  │
    │                 │                   │                  │   SandboxResult  │
    │                 │◄───────────────────────────────────────────────────────┤
    │                 │                   │                  │                  │
    │                 │ write AuditLog    │                  │                  │
    │                 ├───────────────────►                  │                  │
    │                 │                   │                  │                  │
    │   result        │                   │                  │                  │
    │◄────────────────┤                   │                  │                  │
    │                 │                   │                  │                  │
```

---

## 5. 权限矩阵

| User Role | `get_evidence` | `list_artifacts` | `run_pytest` |
|-----------|:--------------:|:----------------:|:------------:|
| ADMIN | ✅ | ✅ | ✅ |
| USER | ✅ | ✅ | ✅ |
| VIEWER | ✅ | ✅ | ❌ |
| (no auth) | ❌ | ❌ | ❌ |

---

## 6. 不做列表 (Phase 1 Scope)

| 功能 | 不做原因 |
|------|----------|
| `run_playwright` MCP 暴露 | 需 browser sandbox |
| MCP 批量调用 | 增加复杂度，先单次验证 |
| 跨 run 预算累计 | 需 session 管理 |
| Policy 热更新推送 | 先支持 reload on request |
| MCP WebSocket 模式 | stdio 先行 |

---

## 7. Phase 1 Implementation Checklist

- [ ] `AuditEventType.MCP_TOOL_CALL` 新增
- [ ] `MCPServer.handle_tool_call()` 添加 auth + permission + policy 检查
- [ ] `SAFE_TOOLS` 字典扩展 `run_pytest`（带 write 标记）
- [ ] 错误码常量定义
- [ ] 单元测试：auth failure / permission denied / policy blocked / budget exceeded / sandbox violation
- [ ] 单元测试：`sandbox.enabled=false` → `SANDBOX_VIOLATION (-32006)`

---

## Document History

| Date | Author | Change |
|------|--------|--------|
| 2026-01-25 | Claude (Antigravity) | **v0.1 frozen**: Final micro-fixes applied |
| 2026-01-25 | Claude (Antigravity) | Review fixes: stdio auth, sandbox enforcement, current-only policy, USER role |
| 2026-01-25 | Claude (Antigravity) | Initial draft |
