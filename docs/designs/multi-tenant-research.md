# L3 多租户支持预研文档

**状态**: 预研阶段 (不实现)  
**优先级**: P2  
**作者**: Kimi (开发工程师)  
**日期**: 2026-01-31  
**依赖**: 无（纯预研文档）

---

## 概述

本文档调研 QualityFoundry **L3 强隔离深化**方向的多租户支持方案，作为长期演进的技术储备。

### 背景

当前 QualityFoundry 架构：
- ✅ **L1-L5 核心架构** 已完成
- ✅ **单租户模式** 已支持（基于 RBAC 的用户隔离）
- 🟡 **多租户隔离** 待探索（企业级 SaaS 需求）

> 根据 `progress_baseline.md`，"L3 强隔离深化"被列为 P2 长期演进项目。

---

## 1. 多租户隔离模式

### 1.1 三种主流架构模式

| 模式 | 描述 | 优点 | 缺点 | 适用场景 |
|------|------|------|------|----------|
| **单库单 Schema** | 所有租户共享数据库和表，通过 `tenant_id` 字段区分 | 成本低，管理简单 | 隔离性弱，数据泄漏风险 | 小型 SaaS，成本敏感 |
| **单库多 Schema** | 共享数据库，每个租户独立 Schema | 中等隔离，成本可控 | Schema 管理复杂 | 中型 SaaS，平衡方案 |
| **多库独立** | 每个租户独立数据库实例 | 最高隔离，合规友好 | 成本高，运维复杂 | 大型企业，强合规要求 |

### 1.2 QualityFoundry 推荐方案：单库多 Schema

```
┌─────────────────────────────────────────────────────────┐
│                    PostgreSQL Instance                   │
├─────────────────────────────────────────────────────────┤
│  Schema: tenant_acme_corp                               │
│    ├── tables: runs, evidences, approvals...            │
│    ├── indexes, constraints                             │
│    └── RLS policies                                     │
├─────────────────────────────────────────────────────────┤
│  Schema: tenant_tech_start                              │
│    ├── tables: runs, evidences, approvals...            │
│    └── ...                                              │
├─────────────────────────────────────────────────────────┤
│  Schema: public (共享表)                                │
│    ├── tenants (租户元数据)                             │
│    ├── users_global (全局用户)                          │
│    └── audit_logs_global (全局审计)                     │
└─────────────────────────────────────────────────────────┘
```

**选择理由**:
1. **隔离性**: Schema 级别隔离，数据完全分离
2. **成本**: 共享数据库实例，资源利用率高
3. **合规**: 支持数据驻留（Schema 可绑定到特定区域）
4. **迁移**: 单租户 → 多租户迁移相对简单

### 1.3 租户标识与路由

```python
# 租户上下文管理
class TenantContext:
    """租户上下文（线程/请求级）"""
    tenant_id: str
    schema_name: str
    tier: str  # free | pro | enterprise
    features: set[str]

# 数据库连接路由
class TenantAwareEngine:
    """租户感知的数据库引擎"""
    
    def get_connection(self, tenant_id: str) -> Connection:
        conn = self.engine.connect()
        # 设置搜索路径到租户 Schema
        conn.execute(f"SET search_path TO {tenant_id}")
        return conn
```

---

## 2. 与现有 RBAC 的集成方案

### 2.1 权限模型分层

```
┌─────────────────────────────────────────────────────────┐
│  层级 1: 租户隔离（多租户层）                            │
│    - 用户只能访问所属租户的数据                          │
│    - Schema 级别完全隔离                                 │
├─────────────────────────────────────────────────────────┤
│  层级 2: RBAC 权限（租户内）                             │
│    - admin: 租户内完全控制                               │
│    - user: 创建/执行编排                                 │
│    - viewer: 只读访问                                    │
└─────────────────────────────────────────────────────────┘
```

### 2.2 用户模型扩展

```python
# 全局用户表（public schema）
class GlobalUser(Base):
    """全局用户（跨租户）"""
    __tablename__ = "users_global"
    __table_args__ = {"schema": "public"}
    
    id = Column(UUID, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)


# 租户成员表（public schema）
class TenantMembership(Base):
    """用户-租户关联"""
    __tablename__ = "tenant_memberships"
    __table_args__ = {"schema": "public"}
    
    user_id = Column(UUID, ForeignKey("public.users_global.id"))
    tenant_id = Column(String, ForeignKey("public.tenants.id"))
    role = Column(String)  # admin | user | viewer
    joined_at = Column(DateTime)
    
    # 复合主键
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "tenant_id"),
        {"schema": "public"},
    )


# 租户表（public schema）
class Tenant(Base):
    """租户元数据"""
    __tablename__ = "tenants"
    __table_args__ = {"schema": "public"}
    
    id = Column(String, primary_key=True)  # 如: tenant_acme_corp
    name = Column(String, nullable=False)
    tier = Column(String, default="free")  # free | pro | enterprise
    schema_name = Column(String, nullable=False)
    created_at = Column(DateTime)
    
    # 资源限制
    max_runs_per_day = Column(Integer, default=100)
    max_storage_mb = Column(Integer, default=1024)
```

### 2.3 JWT Token 扩展

```python
# Token Payload 扩展租户信息
class TokenPayload(BaseModel):
    sub: str           # user_id
    email: str
    tenant_id: str     # 新增：当前租户
    tenant_role: str   # 新增：租户内角色
    global_role: str   # 系统级角色（superadmin）
    exp: datetime
```

### 2.4 中间件实现

```python
class TenantMiddleware:
    """租户上下文中间件"""
    
    async def __call__(self, request: Request, call_next):
        # 从 JWT 提取租户信息
        token = request.headers.get("Authorization")
        payload = decode_token(token)
        
        tenant_id = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(400, "Tenant context required")
        
        # 设置租户上下文（使用 contextvars）
        tenant_ctx.set(TenantContext(
            tenant_id=tenant_id,
            schema_name=f"tenant_{tenant_id}",
            role=payload.get("tenant_role"),
        ))
        
        response = await call_next(request)
        return response
```

---

## 3. 沙箱环境隔离增强

### 3.1 当前沙箱 vs 多租户沙箱

| 维度 | 当前（单租户） | 多租户增强 |
|------|---------------|-----------|
| **进程隔离** | subprocess | 容器化（强制） |
| **网络隔离** | 可选禁网 | 租户级网络策略 |
| **存储隔离** | 共享 artifacts 目录 | 租户隔离存储 |
| **资源限制** | 全局配置 | 租户级配额 |

### 3.2 租户级沙箱配置

```yaml
# policy_config.yaml 扩展
tenant_sandbox:
  default:
    mode: container
    network_policy: deny
    cpu_limit: 1.0
    memory_limit_mb: 512
  
  # 企业级租户自定义
  overrides:
    - tenant_id: "acme_corp"
      network_policy: allowlist
      network_allowlist:
        - "*.acme.internal"
        - "api.github.com"
      cpu_limit: 4.0
      memory_limit_mb: 2048
```

### 3.3 容器运行时隔离

```python
class TenantAwareSandbox:
    """租户感知的沙箱执行器"""
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.config = self._load_tenant_config()
    
    def _build_container_config(self) -> ContainerConfig:
        return ContainerConfig(
            image=self.config.sandbox_image,
            network_mode=self.config.network_policy,
            mounts=[
                # 租户隔离的 workspace
                Mount(
                    source=f"/data/tenants/{self.tenant_id}/workspace",
                    target="/workspace",
                    readonly=False,
                ),
                # 只读的系统工具
                Mount(
                    source="/opt/qualityfoundry/tools",
                    target="/tools",
                    readonly=True,
                ),
            ],
            resources=Resources(
                cpus=self.config.cpu_limit,
                memory=self.config.memory_limit_mb * 1024 * 1024,
            ),
            # 租户标签（用于监控和计费）
            labels={
                "tenant_id": self.tenant_id,
                "run_id": "...",
            },
        )
```

### 3.4 存储隔离

```
/data/tenants/
├── tenant_acme_corp/
│   ├── workspace/          # 沙箱工作目录
│   ├── artifacts/          # 产物存储
│   ├── cache/              # 租户级缓存
│   └── logs/               # 审计日志
├── tenant_tech_start/
│   └── ...
└── shared/
    └── tools/              # 共享工具镜像
```

---

## 4. 数据库 Migration 策略

### 4.1 Schema 管理挑战

- 多租户 = 多 Schema = Migration 复杂度倍增
- 需要确保所有租户 Schema 结构一致
- 新增租户时的 Schema 初始化

### 4.2 推荐方案：模板 Schema + 复制

```python
class TenantSchemaManager:
    """租户 Schema 管理器"""
    
    TEMPLATE_SCHEMA = "template_tenant"
    
    def create_tenant_schema(self, tenant_id: str) -> None:
        """为新租户创建 Schema"""
        schema_name = f"tenant_{tenant_id}"
        
        # 1. 从模板复制 Schema
        self._clone_schema(self.TEMPLATE_SCHEMA, schema_name)
        
        # 2. 记录 Schema 版本
        self._set_schema_version(schema_name, current_version)
    
    def migrate_all_tenants(self, migration: Migration) -> None:
        """对所有租户 Schema 执行 Migration"""
        tenants = self._list_all_tenant_schemas()
        
        for tenant_schema in tenants:
            try:
                self._apply_migration(tenant_schema, migration)
            except Exception as e:
                # 记录失败，继续其他租户
                logger.error(f"Migration failed for {tenant_schema}: {e}")
                # 触发告警，需要人工介入

    def _clone_schema(self, source: str, target: str) -> None:
        """PostgreSQL Schema 克隆"""
        # 使用 pg_dump + pg_restore 或 CREATE SCHEMA ... LIKE
        self.db.execute(f"""
            CREATE SCHEMA {target};
            
            -- 复制表结构
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN 
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = '{source}'
                LOOP
                    EXECUTE format(
                        'CREATE TABLE %I.%I (LIKE %I.%I INCLUDING ALL)',
                        '{target}', r.table_name, '{source}', r.table_name
                    );
                END LOOP;
            END $$;
        """)
```

### 4.3 Migration 执行流程

```
┌─────────────────────────────────────────────────────────┐
│  1. 开发阶段                                              │
│     - 修改 models.py                                     │
│     - 生成 Alembic migration                             │
├─────────────────────────────────────────────────────────┤
│  2. 模板更新                                              │
│     - 对 template_tenant 执行 migration                  │
│     - 验证通过                                            │
├─────────────────────────────────────────────────────────┤
│  3. 批量应用                                              │
│     - 遍历所有租户 Schema                                 │
│     - 并行执行 migration（限制并发）                      │
│     - 记录失败，人工修复                                  │
├─────────────────────────────────────────────────────────┤
│  4. 监控与回滚                                            │
│     - 检查每个 Schema 版本                                │
│     - 失败时回滚到上一版本                                │
└─────────────────────────────────────────────────────────┘
```

### 4.4 版本兼容性

```python
# 在应用启动时检查 Schema 版本
@app.on_event("startup")
async def check_schema_versions():
    """检查所有租户 Schema 版本"""
    manager = TenantSchemaManager()
    
    outdated = manager.find_outdated_schemas()
    if outdated:
        logger.warning(f"{len(outdated)} tenants have outdated schema")
        # 触发自动 migration 或告警
```

---

## 5. 实施路线建议

### Phase 1: 基础准备 (2-3 周)
- [ ] 设计 Tenant/RBAC 数据模型
- [ ] 实现 Schema 管理器
- [ ] 创建模板 Schema
- [ ] 开发租户中间件

### Phase 2: 核心实现 (4-6 周)
- [ ] 用户系统扩展（全局用户 + 租户成员）
- [ ] JWT Token 扩展
- [ ] 数据库层租户路由
- [ ] 基础多租户 API

### Phase 3: 沙箱增强 (3-4 周)
- [ ] 租户级沙箱配置
- [ ] 容器运行时隔离
- [ ] 存储隔离实现
- [ ] 资源配额系统

### Phase 4: 生产就绪 (2-3 周)
- [ ] Migration 自动化
- [ ] 监控和告警
- [ ] 性能优化
- [ ] 文档和示例

---

## 6. 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **Schema 膨胀** | 租户过多导致管理困难 | 单实例租户上限；水平分片 |
| **Migration 失败** | 部分租户数据结构不一致 | 蓝绿部署；自动回滚 |
| **性能下降** | 多 Schema 查询开销 | 连接池优化；只读副本 |
| **数据泄漏** | 租户间数据交叉 | 严格测试；RLS 策略 |
| **运维复杂** | 故障排查难度增加 | 完善日志；监控看板 |

---

## 7. 决策点（待讨论）

| 决策项 | 选项 | 建议 |
|--------|------|------|
| 初始租户上限 | 100 / 1000 / 无限制 | **100**（初期验证） |
| 沙箱强制容器化 | 是 / 否 | **是**（企业级安全） |
| 跨租户审计 | 集中 / 分散 | **集中**（全局视图） |
| 数据驻留 | 支持 / 暂不支持 | **Phase 2 支持** |

---

## 附录：参考资源

1. [Multi-Tenant SaaS with PostgreSQL](https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/) - AWS 最佳实践
2. [Django Tenant Schemas](https://django-tenant-schemas.readthedocs.io/) - Schema 隔离模式参考
3. [Kubernetes Multi-Tenancy](https://kubernetes.io/docs/concepts/security/multi-tenancy/) - 容器隔离参考

---

*本文档为预研性质，具体实现需经架构师评审和 PM 批准。*
