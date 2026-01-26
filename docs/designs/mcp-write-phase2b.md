# MCP Write Phase 2B 设计文档

**状态**: 设计阶段 (不实现)  
**依赖**: Phase 2A 护栏已完成 (rate limit + quota)  
**作者**: Claude (Antigravity)  
**日期**: 2026-01-26

---

## 概述

Phase 2B 扩展 MCP 写能力至高危工具：
- `run_playwright`: 浏览器自动化
- `run_shell`: 命令行执行

这些工具风险显著高于 `run_pytest`，需要强隔离容器沙箱。

---

## 工具设计

### run_playwright

**用途**: 执行 Playwright 浏览器测试

**风险**:
- 网络访问：可访问任意 URL
- 文件系统：截图/downloads 写入
- 资源消耗：headless browser 内存/CPU

**容器沙箱需求**:

```yaml
sandbox:
  mode: container  # 强制容器模式
  image: "mcr.microsoft.com/playwright:v1.40.0-focal"
  network:
    mode: "none"  # 默认禁网
    allowlist:    # 可选白名单
      - "*.example.com"
  mounts:
    - type: tmpfs
      target: /tmp
      size: 100m
    - type: bind
      source: /output
      target: /output
      readonly: false
  resources:
    memory: 512m
    cpu: 1.0
    timeout_s: 60
```

**Policy 约束**:

```yaml
tools:
  allowlist:
    - run_playwright
  playwright:
    allowed_urls: ["https://localhost:*", "https://*.internal.corp"]
    blocked_urls: ["*"]  # 默认拒绝
    screenshots: true
    videos: false
```

---

### run_shell

**用途**: 执行 shell 命令（极高危）

**风险**:
- 任意命令执行
- 文件系统完全访问
- 网络访问
- 系统调用

**设计原则**: **默认长期不开放**

如确需开放，必须满足：

1. **容器强隔离**: 只读根文件系统 + tmpfs + 禁网
2. **命令白名单**: 仅允许特定命令集
3. **用户隔离**: non-root + capabilities dropped
4. **审计增强**: 记录完整命令 + 输出

**容器沙箱需求**:

```yaml
sandbox:
  mode: container
  image: "alpine:3.18"
  readonly_rootfs: true  # 只读根文件系统
  network:
    mode: "none"
  user: "nobody:nogroup"
  cap_drop:
    - ALL
  no_new_privs: true
  mounts:
    - type: tmpfs
      target: /tmp
      size: 50m
  resources:
    memory: 128m
    cpu: 0.5
    timeout_s: 30
```

**Policy 约束**:

```yaml
tools:
  allowlist:
    - run_shell
  shell:
    command_allowlist:
      - "ls"
      - "cat"
      - "head"
      - "tail"
      - "grep"
      - "wc"
    command_blocklist:
      - "*"  # 默认拒绝
    env_passthrough: []  # 不传递环境变量
```

---

## 安全链扩展

Phase 2B 安全链:

```
auth → permission → rate_limit → policy → container_sandbox
                                              ↓
                                    (image pull + run + cleanup)
```

**新增检查点**:
- `_check_container_sandbox()`: 验证容器配置
- `_spawn_container()`: 创建隔离容器
- `_cleanup_container()`: 销毁容器

---

## 审计增强

| 事件类型 | 说明 |
|----------|------|
| `MCP_CONTAINER_SPAWN` | 容器创建 |
| `MCP_CONTAINER_EXEC` | 命令执行 |
| `MCP_CONTAINER_CLEANUP` | 容器销毁 |
| `MCP_NETWORK_BLOCKED` | 网络请求被拒绝 |
| `MCP_COMMAND_BLOCKED` | 命令被策略拒绝 |

---

## 依赖项

| 依赖 | 状态 | 说明 |
|------|------|------|
| Phase 2A 护栏 | ✅ 完成 | rate limit + quota |
| 容器运行时 | ❌ 待实现 | Docker / podman |
| 镜像仓库 | ❌ 待配置 | 预构建沙箱镜像 |
| 禁网策略 | ❌ 待实现 | network=none + allowlist |
| 磁盘挂载策略 | ❌ 待实现 | tmpfs + readonly + bind |

---

## 实施路线

1. **Phase 2B-1**: 容器沙箱基础设施 (2-3d)
   - ContainerSandbox 抽象
   - Docker/podman 适配器
   - 资源限制实现

2. **Phase 2B-2**: run_playwright (1-2d)
   - Playwright 容器镜像
   - 网络白名单
   - 截图/视频输出

3. **Phase 2B-3**: run_shell (1d, 可选)
   - 命令白名单引擎
   - 极简 alpine 镜像
   - **需要 explicit approval**

---

## 风险评估

| 工具 | 风险等级 | 建议 |
|------|----------|------|
| `run_pytest` | 🟡 中 | 已发布 (Phase 1) |
| `run_playwright` | 🟠 高 | 容器强隔离 + 禁网默认 |
| `run_shell` | 🔴 极高 | 默认不开放；如开放需逐案审批 |

---

## 决策点

> [!IMPORTANT]
> 以下决策需要用户确认：

1. **容器运行时选择**: Docker vs Podman?
2. **run_shell 是否开放**: 建议默认不开放
3. **网络白名单粒度**: 域名级 vs IP 级?
4. **资源配额**: 内存/CPU 默认值?
