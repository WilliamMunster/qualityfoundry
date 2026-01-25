# Run Center Acceptance Walkthrough

> **Version**: 0.1  
> **Status**: Draft  
> **Date**: 2026-01-25

本文档定义 Run Center 主路径的验收标准，确保前端可以正常消费后端 API。

---

## 1. Readiness Check

在使用 Run Center 之前，以下端点必须返回有效数据。

### 1.1 Environments API

```bash
curl -s http://localhost:8000/api/v1/environments | jq
```

**期望**:
```json
{
  "items": [
    {"id": "...", "name": "Local", "type": "local", ...}
  ]
}
```

> [!NOTE]
> 后端启动时会自动 seed `Local` 环境。如果返回空数组，检查 startup seed 逻辑。

### 1.2 Current Policy API

```bash
curl -s http://localhost:8000/api/v1/policies/current | jq
```

**期望**:
```json
{
  "id": "...",
  "name": "default",
  "tools": {"allowlist": ["run_pytest", ...]},
  "sandbox": {"enabled": true, ...},
  ...
}
```

> [!IMPORTANT]
> `sandbox.enabled` 必须为 `true`，否则 MCP 写工具将被拒绝 (-32006)。

### 1.3 Runs List API

```bash
curl -s http://localhost:8000/api/v1/orchestrations/runs | jq
```

**期望**: 返回 `items` 数组（空数组也是 OK）。

---

## 2. 主路径验收

### 2.1 发起新 Run

**UI 路径**: `/runs/new` → 填写参数 → 提交

**API 等价**:
```bash
curl -X POST http://localhost:8000/api/v1/orchestrations/runs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"environment_id": "<uuid>", "test_path": "tests/"}'
```

**期望返回**:
```json
{
  "id": "<uuid>",
  "status": "PENDING",
  "created_at": "..."
}
```

### 2.2 查看 Run 详情

**UI 路径**: `/runs/:id`

**API**:
```bash
curl -s http://localhost:8000/api/v1/orchestrations/runs/<run_id> | jq
```

**期望字段**:
- `id`, `status`, `created_at`, `updated_at`
- `evidence`: 证据摘要（如有）
- `run_kind`: `orchestration`

### 2.3 Evidence Tabs

**UI**: Run 详情页应显示以下 tabs:
- **Summary**: 基本信息
- **Evidence**: `evidence.json` 内容
- **Artifacts**: 产物列表 + 下载链接
- **Audit Timeline**: 审计日志时间线

### 2.4 Audit Timeline 必含字段

| 字段 | 说明 |
|------|------|
| `event_type` | `tool_started`, `tool_finished`, `mcp_tool_call`, etc. |
| `tool_name` | 工具名 |
| `ts` | 时间戳 |
| `status` | 状态 |
| `actor` | 操作者（可空） |

---

## 3. 失败注入测试

### 3.1 空 Environments

**模拟**: 清空 `environments` 表

**期望 UI**: 显示 "No environments configured. Please contact admin."

### 3.2 空 Policy Allowlist

**模拟**: 设置 `policy.tools.allowlist = []`

**期望**: 执行 `run_pytest` 返回 `-32004 POLICY_BLOCKED`

### 3.3 Sandbox Disabled

**模拟**: 设置 `policy.sandbox.enabled = false`

**期望**: 执行 `run_pytest` 返回 `-32006 SANDBOX_VIOLATION`

---

## 4. 验收检查清单

- [ ] `/api/v1/environments` 返回至少一个环境
- [ ] `/api/v1/policies/current` 返回有效策略
- [ ] `/runs/new` 可以成功发起 run
- [ ] `/runs/:id` 显示完整的 evidence tabs
- [ ] Audit Timeline 显示完整事件链
- [ ] 错误场景有明确 UI 提示

---

## Document History

| Date | Author | Change |
|------|--------|--------|
| 2026-01-25 | Claude (Antigravity) | Initial draft |
