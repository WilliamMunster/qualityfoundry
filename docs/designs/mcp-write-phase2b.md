# MCP Write Phase 2B 设计文档

**状态**: 设计阶段 (不实现)  
**版本**: v0.2 (已采纳 6 项设计反馈)  
**依赖**: Phase 2A 护栏已完成 (rate limit + quota)  
**作者**: Claude (Antigravity)  
**日期**: 2026-01-26

---

## 概述

Phase 2B 扩展 MCP 写能力至高危工具：
- `run_playwright`: 浏览器自动化
- `run_shell`: **默认 HARD BLOCK，Phase 2B 不开放**

> [!IMPORTANT]
> MCP 写工具不直接管理容器生命周期，统一复用 L3 ContainerSandbox 执行层。

---

## 架构原则：复用 L3 Container Sandbox

```
MCP Server → ToolRegistry → ExecutionRunner → L3 ContainerSandbox
                                                    ↓
                                               container_sandbox.py (现有)
```

**关键约束**：
- MCP 层只做"安全链检查 + 参数包装"
- 容器生命周期由 L3 ExecutionRunner 统一管理
- 避免 MCP 与 L3 出现两套 container runner（必然漂移）

---

## 工具设计

### run_playwright

**用途**: 执行 Playwright 浏览器测试

**风险**:
- 网络访问：可访问任意 URL
- 文件系统：截图/downloads 写入
- 资源消耗：headless browser 内存/CPU

**容器配置** (复用 L3 ContainerSandbox):

```yaml
sandbox:
  mode: container
  image: "mcr.microsoft.com/playwright:v1.40.0-focal"
  network:
    mode: "none"  # Phase 2B-1: 默认禁网
  mounts:
    - source: /work      # 只读代码
      target: /work
      readonly: true
    - source: /output    # 可写输出
      target: /output
      readonly: false
  resources:
    memory: 1024m
    cpu: 1.0
    timeout_s: 120
```

**审计事件 (Audit Events)**:
- `MCP_CONTAINER_SPAWN`: 记录容器创建时间、镜像、资源限制
- `MCP_CONTAINER_EXEC`: 记录在容器内执行的具体 playwright 命令
- `MCP_CONTAINER_CLEANUP`: 记录容器销毁时间、退出状态
- `MCP_FILE_WRITE`: 记录写入 `/output` 的产物元数据

**输出目录契约**:

| 容器路径 | 宿主路径 | 用途 |
|----------|----------|------|
| `/work` | `{workspace}` | 只读代码 |
| `/output` | `artifacts/{run_id}/output/` | 可写：截图/trace/video |

> [!NOTE]
> artifacts 索引生成规则：`evidence.json.files[]` 自动收集 `/output/**`

**Policy 约束**:

```yaml
tools:
  allowlist:
    - run_playwright
  playwright:
    screenshots: true
    videos: false
    traces: true
```

---

### run_shell

**状态**: **HARD BLOCK - Phase 2B 不实现、不暴露、不注册**

**用途**: 执行 shell 命令（极高危）

> [!CAUTION]
> Phase 2B scope：不实现、不暴露、不注册为 MCP write tool

**未来开放条件**（全部同时满足才可执行）:

1. `feature_flag: mcp_shell_enabled = true`
2. `explicit_approval` 逐案审批
3. `policy.tools.allowlist` 包含 `run_shell`
4. `policy.shell.command_allowlist` 非空

**否则**: 直接返回 `POLICY_BLOCKED (-32004)`

**如果未来开放，容器配置**:

```yaml
sandbox:
  mode: container
  image: "alpine:3.18"
  readonly_rootfs: true
  network:
    mode: "none"
  user: "nobody:nogroup"
  cap_drop:
    - ALL
  no_new_privs: true
  resources:
    memory: 128m         # 保守默认
    cpu: 0.5
    timeout_s: 15
```

---

## 网络隔离策略

> [!WARNING]
> network allowlist 在 Docker 里不是一句话能完成的

| Phase | 网络策略 | 说明 |
|-------|----------|------|
| **2B-1** | `network: none` | 完全禁网，最低可行 |
| **2B-2** (可选) | allowlist | 需要 sidecar/代理 或 自建 DNS + egress 控制 |

**Phase 2B-1 不承诺 allowlist**，避免"文档说支持，现实做不到"。

---

## 资源限制优先级

区分"容器限制"与"应用预算"：

| 优先级 | 类型 | 错误码 | 说明 |
|--------|------|--------|------|
| 1 | 容器硬超时 kill | `TIMEOUT -32007` | 容器被强制终止 |
| 2 | 预算短路 | `BUDGET_EXCEEDED -32005` | GovernanceBudget.max_retries/elapsed |
| 3 | 沙箱违规 | `SANDBOX_VIOLATION -32006` | 策略检查失败 |
| 4 | 策略拦截 | `POLICY_BLOCKED -32004` | allowlist/feature_flag 检查失败 |

**默认资源配额**:

| 工具 | memory | cpu | timeout_s |
|------|--------|-----|-----------|
| `run_playwright` | 1024m | 1.0 | 120 |
| `run_shell` (不开放) | 128m | 0.5 | 15 |

---

## 审计事件

| 类型 | 级别 | 说明 |
|------|------|------|
| `MCP_TOOL_CALL` | **MUST** | 工具调用入口 |
| `POLICY_BLOCKED` | **MUST** | 策略拦截 |
| `SANDBOX_EXEC` | **MUST** | 沙箱执行 |
| `TOOL_FINISHED` | **MUST** | 工具完成 |
| `MCP_CONTAINER_SPAWN` | OPTIONAL | 容器创建（L3 runner 可能已审计） |
| `MCP_CONTAINER_EXEC` | OPTIONAL | 容器内命令执行 |
| `MCP_CONTAINER_CLEANUP` | OPTIONAL | 容器销毁 |
| `MCP_NETWORK_BLOCKED` | OPTIONAL | 网络请求被拒绝 |
| `MCP_COMMAND_BLOCKED` | OPTIONAL | 命令被策略拒绝 |

---

## 依赖项

| 依赖 | 状态 | 说明 |
|------|------|------|
| Phase 2A 护栏 | ✅ 完成 | rate limit + quota |
| L3 ContainerSandbox | ✅ 存在 | `container_sandbox.py` 265 行 |
| ContainerSandbox 抽象复用 | ❌ 待适配 | MCP 侧调用 L3 执行层 |
| 禁网策略 | ❌ 待实现 | `network: none` (Phase 2B-1) |
| 输出目录契约 | ❌ 待固化 | `/output` → `artifacts/{run_id}/output/` |

---

## 实施路线

### Phase 2B-1: 基础能力 (2-3d)

- [x] 复用 L3 ContainerSandbox 抽象（而非新造 _spawn_container）
- [ ] MCP → ToolRegistry → ExecutionRunner 调用链
- [ ] 完全禁网 (`network: none`)
- [ ] 输出目录契约固化 (`/work`, `/output`)

### Phase 2B-2: run_playwright (1-2d)

- [ ] Playwright 容器镜像集成
- [ ] 截图/trace/video 输出收集
- [ ] artifacts 索引生成

### Phase 2B-3: 网络白名单 (可选, 2-3d)

- [ ] sidecar/代理实现
- [ ] DNS + egress 控制
- [ ] **不在 2B-1 承诺**

### Phase 2B-X: run_shell (明确不开放)

- **默认 HARD BLOCK**
- 只允许"只读类命令 + 无参数或受限参数"
- 必须：容器强隔离 + 非 root + cap_drop=ALL + no_new_privs
- **需要 feature_flag + explicit approval**

---

## 决策点（已采纳）

| 决策 | 结论 |
|------|------|
| 容器运行时 | **Docker 为主**（CI 生态最稳定），Podman 作为后续兼容层 |
| run_shell 是否开放 | **默认不开放**（明确写死），未来需 4 重条件同时满足 |
| 网络白名单 | **Phase 2B-1 不承诺**（默认禁网），2B-2+ 可选增强 |
| 资源配额 | `run_playwright: 1024m/1.0/120s`, `run_shell: 128m/0.5/15s` |

---

## 风险评估

| 工具 | 风险等级 | Phase 2B 状态 |
|------|----------|---------------|
| `run_pytest` | 🟡 中 | 已发布 (Phase 1) |
| `run_playwright` | 🟠 高 | 2B-2 实现（禁网） |
| `run_shell` | 🔴 极高 | **HARD BLOCK** |
