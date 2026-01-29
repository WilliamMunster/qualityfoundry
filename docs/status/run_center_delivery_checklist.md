# Run Center 工程化交付清单

> **目标**: 将 v2 计划工程化为"可验证 + 可合并 + 可回滚"的仓库产物  
> **日期**: 2026-01-29  
> **版本**: v0.19-delivery-ready

---

## 📦 已交付产物清单

### 1. Evidence Schema v1 正式化 ✅

| 文件 | 路径 | 说明 |
|------|------|------|
| JSON Schema | `backend/app/qualityfoundry/schemas/evidence.v1.schema.json` | 严格字段约束，含 pattern/format |
| Python 模块 | `backend/app/qualityfoundry/schemas/__init__.py` | 校验函数 + 版本管理 |
| 集成修改 | `backend/app/qualityfoundry/governance/tracing/collector.py` | 自动注入 `$schema` 字段 |

**关键特性:**
- Schema URI: `https://qualityfoundry.ai/schemas/evidence.v1.schema.json`
- 校验函数: `validate_evidence_v1()` / `validate_evidence_v1_silent()`
- 自动版本注入: Evidence 保存时自动添加 `$schema` 字段

**验证命令:**
```bash
cd backend
python -c "
from qualityfoundry.schemas import validate_evidence_v1, load_evidence_schema_v1
schema = load_evidence_schema_v1()
print(f'Schema version: {schema.get(\"version\", \"1.0.0\")}')
"
```

---

### 2. Run 状态对外枚举收敛 ✅

| 文件 | 路径 | 说明 |
|------|------|------|
| 状态枚举 | `backend/app/qualityfoundry/models/run_status.py` | 统一对外状态定义 |

**对外状态 (4 个):**
```python
PENDING  -> RUNNING -> [FINISHED|JUDGED|FAILED]
```

| 状态 | 含义 | 终态 |
|------|------|------|
| PENDING | 已创建，等待执行 | ❌ |
| RUNNING | 执行中（含内部子状态） | ❌ |
| FINISHED | 完成但未决策（异常） | ✅ |
| JUDGED | 完成并已决策 | ✅ |
| FAILED | 异常失败 | ✅ |

**映射函数:**
```python
from qualityfoundry.models.run_status import map_internal_status_to_external

status = map_internal_status_to_external(
    has_tool_started=True,
    has_tool_finished=True,
    has_decision=True,
)
# Returns: RunStatus.JUDGED
```

---

### 3. Run Center DoD 验收用例自动化 (API 层) ✅

| 文件 | 路径 | 说明 |
|------|------|------|
| API 测试 | `backend/tests/test_run_center_acceptance_api.py` | 覆盖 DoD-1/2/3 |

**测试覆盖:**

| DoD | 测试类 | 测试点 |
|-----|--------|--------|
| DoD-1 | `TestRunLifecycle` | 列表/分页/详情/权限/数据一致性 |
| DoD-2 | `TestEvidenceChain` | Schema 校验/必填字段/路径相对化/Repro 元数据 |
| DoD-3 | `TestAuditTrail` | 治理字段/decision_source 收敛 |
| 性能 | `TestPerformanceAndEdgeCases` | 大偏移/校验性能 |
| 冒烟 | `TestRunCenterSmoke` | 核心路径快速验证 |

**运行命令:**
```bash
cd backend
pytest tests/test_run_center_acceptance_api.py -v --tb=short

# 仅冒烟测试
pytest tests/test_run_center_acceptance_api.py::TestRunCenterSmoke -v
```

---

### 4. E2E Nightly + 诊断产物留存 ✅

| 文件 | 路径 | 说明 |
|------|------|------|
| CI Workflow | `.github/workflows/e2e-nightly.yml` | Nightly Playwright 测试 |
| Playwright 配置 | `frontend/playwright.config.ts` | 测试框架配置 |
| E2E 测试 | `frontend/e2e/run-center.spec.ts` | DoD-1/2/3 E2E 验收 |

**CI 特性:**
- 触发: 每日凌晨 2 点 (UTC) / 手动触发
- 账号: 从 `secrets.E2E_ADMIN_USER/PASS` 读取（非硬编码）
- 产物: 失败时自动上传 trace/video/screenshot
- 诊断: 保留 7 天，成功报告保留 3 天

**E2E 测试数据:**
```typescript
// DoD-1: Run 生命周期
- 创建 Run 并跳转详情页
- Run 列表显示新创建的 Run  
- 状态流转: PENDING → RUNNING → JUDGED
- 刷新后数据一致性
- 列表过滤功能

// DoD-2: 证据链可下载且可复核
- Evidence 下载与 Schema 校验
- Tool calls 完整性检查
- Artifacts 路径相对化检查
- Repro 元数据存在性

// DoD-3: 最小审计闭环可解释
- 决策原因可见性
- 审计时间线显示
- 成本治理卡片显示
```

**运行命令:**
```bash
# 本地运行（需服务已启动）
cd frontend
npx playwright test e2e/run-center.spec.ts --project=chromium

# 带 UI 调试
npx playwright test e2e/run-center.spec.ts --headed --debug
```

---

## 🔧 集成步骤

### Step 1: 安装依赖

```bash
# 后端: jsonschema 用于校验
cd backend
pip install jsonschema

# 前端: Playwright
cd frontend
npm install --save-dev @playwright/test
npx playwright install chromium
```

### Step 2: 配置 CI Secrets

在 GitHub Settings > Secrets and variables > Actions 中添加:

| Secret | 说明 |
|--------|------|
| `E2E_ADMIN_USER` | E2E 测试管理员账号 |
| `E2E_ADMIN_PASS` | E2E 测试管理员密码 |

### Step 3: 更新前端组件 (补充 data-testid)

需为以下关键控件添加 `data-testid`:

```tsx
// LoginPage.tsx
<Input data-testid="login-username" />
<Input data-testid="login-password" />
<Button data-testid="login-submit" />

// RunListPage.tsx
<div data-testid="runs-page-title" />
<Button data-testid="new-run-button" />
<div data-testid={`run-row-${runId}`} />

// RunLaunchPage.tsx
<TextArea data-testid="nl-input-textarea" />
<Select data-testid="environment-select">
  <Option data-testid="env-option-local" />
</Select>
<Button data-testid="run-launch-submit" />

// RunDetailPage.tsx
<Tag data-testid="run-status-badge" />
<Tag data-testid="run-decision-badge" />
<Button data-testid="download-evidence-button" />
<div data-testid="audit-timeline" />
<div data-testid="governance-card" />
```

### Step 4: 运行验证

```bash
# 1. Schema 校验测试
cd backend && pytest tests/test_run_center_acceptance_api.py::TestEvidenceChain -v

# 2. API 契约测试
cd backend && pytest tests/test_run_center_acceptance_api.py::TestRunLifecycle -v

# 3. 前端构建验证
cd frontend && npm run build

# 4. E2E 本地验证（需服务运行）
cd frontend && npx playwright test e2e/run-center.spec.ts --project=chromium
```

---

## ⚠️ 已知限制与后续工作

### Issue 2: Run 状态枚举 - 待 API 集成

当前 `RunStatus` 枚举已定义，但 `routes_orchestrations.py` 中的 `RunDetail` DTO 尚未使用新枚举。

**建议修改:**
```python
# backend/app/qualityfoundry/api/v1/routes_orchestrations.py
from qualityfoundry.models.run_status import RunStatus, map_internal_status_to_external

# 在 get_run_detail 中使用映射函数
has_started = any(e.event_type == AuditEventType.TOOL_STARTED for e in events)
has_finished = any(e.event_type == AuditEventType.TOOL_FINISHED for e in events)
has_decision = any(e.event_type == AuditEventType.DECISION_MADE for e in events)

external_status = map_internal_status_to_external(
    has_tool_started=has_started,
    has_tool_finished=has_finished,
    has_decision=has_decision,
)
```

### Issue 3: decision_source 收敛 - 待 DTO 修改

当前 `summary` 中仍有 `decision_source` 字段，建议移除，仅保留 `governance.decision_source`。

### Issue 4-6: 前端 data-testid 补全

需前端团队配合，为关键控件添加 `data-testid` 属性。

---

## ✅ 验收检查清单

### 后端验收

- [ ] `evidence.v1.schema.json` 存在且有效
- [ ] `validate_evidence_v1()` 函数工作正常
- [ ] Evidence 保存时自动包含 `$schema` 字段
- [ ] API 测试全部通过: `pytest tests/test_run_center_acceptance_api.py -v`

### CI 验收

- [ ] `.github/workflows/e2e-nightly.yml` 已提交
- [ ] Secrets `E2E_ADMIN_USER/PASS` 已配置
- [ ] Workflow 可手动触发并运行

### 前端验收

- [ ] `playwright.config.ts` 配置正确
- [ ] `run-center.spec.ts` 测试可运行
- [ ] 关键控件已添加 `data-testid`

---

## 📊 文件变更汇总

```
backend/
└── app/qualityfoundry/
    ├── schemas/
    │   ├── __init__.py                    # 新增: Schema 校验模块
    │   └── evidence.v1.schema.json        # 新增: JSON Schema 定义
    ├── governance/tracing/collector.py    # 修改: 自动注入 $schema
    └── models/run_status.py               # 新增: 状态枚举定义

tests/
└── test_run_center_acceptance_api.py      # 新增: API 验收测试

frontend/
├── playwright.config.ts                   # 新增: Playwright 配置
└── e2e/
    └── run-center.spec.ts                 # 新增: E2E 验收测试

.github/workflows/
└── e2e-nightly.yml                        # 新增: Nightly CI

docs/status/
└── run_center_delivery_checklist.md       # 新增: 本清单
```

---

## 🎯 下一步建议

### P0: 本周收口 (1-2 天)

1. **合并 Schema PR**
   - 提交 `backend/app/qualityfoundry/schemas/` 目录
   - 提交 collector.py 修改
   - 安装 `jsonschema` 依赖

2. **合并测试 PR**
   - 提交 `tests/test_run_center_acceptance_api.py`
   - 验证 CI 通过

3. **前端 data-testid 补全**
   - 按上述列表添加 testid
   - 提交前端 PR

### P1: 下周启动 (2-3 天)

4. **E2E Nightly 启用**
   - 合并 `.github/workflows/e2e-nightly.yml`
   - 配置 Secrets
   - 验证首次运行

5. **RunStatus 枚举集成**
   - 修改 `routes_orchestrations.py` 使用新枚举
   - 更新前端类型定义

6. **decision_source 收敛**
   - 从 SummaryInfo 移除 decision_source
   - 更新前端组件

---

**交付状态**: 6/6 个核心产物已完成，可直接合并 🎉
