# QualityFoundry 🏗️

QualityFoundry 是一个 **Python-first** 的测试与质量闸门（Quality Gate）工具链，提供完整的企业级测试管理平台功能。

## 当前版本：V0.85

### 核心功能

- ✅ **需求管理**：支持需求文档上传、版本控制、状态追踪、自动编号
- ✅ **场景管理**：AI 辅助生成测试场景，支持人工审核、自动编号
- ✅ **用例管理**：从场景生成测试用例，支持独立编辑和审核、自动编号
- ✅ **环境管理**：多环境配置，健康检查，变量管理
- ✅ **执行管理**：DSL/MCP 执行模式，实时状态追踪
- ✅ **用户管理**：基于 JWT 的认证，角色权限控制
- ✅ **AI 配置**：支持多个 AI 提供商（OpenAI、DeepSeek 等）
- ✅ **测试报表**：仪表盘统计，执行历史记录
- ✅ **批量操作**：支持多选删除，确认弹窗

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- SQLite（内置）

### 后端启动

```powershell
# 1. 创建虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 安装依赖
pip install -e .\backend

# 3. 初始化数据库
cd backend
alembic upgrade head
cd ..

# 4. 创建管理员账号
python seed_admin.py

# 5. 启动服务
uvicorn qualityfoundry.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```powershell
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173，使用 `admin/admin` 登录。

---

## 项目结构

```
qualityfoundry/
├── backend/                    # 后端代码
│   ├── app/qualityfoundry/    # 主应用
│   │   ├── api/v1/            # API 路由
│   │   ├── database/          # 数据库模型
│   │   ├── services/          # 业务逻辑
│   │   └── main.py            # FastAPI 入口
│   ├── migrations/            # Alembic 迁移
│   └── tests/                 # 测试用例
├── frontend/                   # 前端代码
│   └── src/
│       ├── pages/             # 页面组件
│       └── layouts/           # 布局组件
├── scripts/                    # 启动脚本
└── pyproject.toml             # 项目配置
```

---

## API 文档

启动后端后访问：

- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

### 主要 API 端点

| 模块 | 端点                     | 说明                 |
| ---- | ------------------------ | -------------------- |
| 认证 | POST /api/v1/users/login | 用户登录             |
| 需求 | /api/v1/requirements     | 需求 CRUD            |
| 场景 | /api/v1/scenarios        | 场景 CRUD + AI 生成  |
| 用例 | /api/v1/testcases        | 用例 CRUD + AI 生成  |
| 环境 | /api/v1/environments     | 环境 CRUD + 健康检查 |
| 执行 | /api/v1/executions       | 执行管理             |
| 报表 | /api/v1/reports          | 仪表盘统计           |
| AI   | /api/v1/ai-configs       | AI 配置管理          |
| 用户 | /api/v1/users            | 用户管理             |

---

## 数据库模型

| 表名         | 说明     |
| ------------ | -------- |
| users        | 用户账号 |
| requirements | 需求文档 |
| scenarios    | 测试场景 |
| testcases    | 测试用例 |
| environments | 环境配置 |
| executions   | 执行记录 |
| approvals    | 审核记录 |
| reports      | 测试报告 |
| uploads      | 上传文件 |
| ai_configs   | AI 配置  |

---

## 开发指南

### 运行测试

```powershell
cd backend
pytest tests -v
```

### 代码检查

```powershell
ruff check backend
```

### 数据库迁移

```powershell
cd backend
alembic revision --autogenerate -m "描述"
alembic upgrade head
```

---

## CI/CD

GitHub Actions 配置：

- `ci.yml`：代码检查（ruff）+ 单元测试（pytest）
- `quality-gate.yml`：Smoke 测试门禁

---

## 许可证

MIT License

---

## 更新日志

### V0.85 (2026-01-16)

**多 AI 模型支持 (Multi-AI Support)**

- ✅ **多模型切换**：支持 OpenAI (GPT-4/3.5)、DeepSeek (Chat/Coder)、ZhipuAI (GLM-4)、Ollama 等多种模型动态切换
- ✅ **模型联动**：选择提供商后自动加载对应模型列表，支持自定义模型名称
- ✅ **连接测试**：新增配置连接测试功能，验证 API Key 和 Base URL 可用性
- ✅ **Prompt 优化**：针对不同模型优化了 JSON 生成的 Prompt 结构，提高成功率

**稳定性与体验 (Stability & UX)**

- ✅ **生成持久化**：修复 AI 生成内容（场景/用例）偶尔无法保存的问题
- ✅ **容错增强**：增强对 AI 返回 Markdown 代码块的解析能力 (` ```json ` wrapper)
- ✅ **事务安全**：优化 `seq_id` 生成逻辑，防止并发下的编号冲突
- ✅ **UI 优化**：配置中心界面重构，支持更直观的模型配置

### V0.8 (2026-01-15)

**自动编号系统**

- ✅ 需求、场景、用例增加 `seq_id` 自动递增编号字段
- ✅ 支持按 `seq_id` 查询（如 REQ-1、SCN-1、TC-1）
- ✅ 前端列表页展示 seq_id 列，便于快速检索

**批量操作**

- ✅ 需求、场景、用例列表支持多选复选框
- ✅ 批量删除功能，带确认弹窗防误删
- ✅ 全选/取消全选快捷操作

**前端交互优化**

- ✅ 统一的加载状态提示（Spin + Toast）
- ✅ 删除/批量删除确认弹窗
- ✅ 表单验证增强

---

### V0.7 (2026-01-13)

**配置中心增强**

- ✅ AI 提示词配置页面：支持在线编辑场景生成、用例生成等步骤的提示词模板
- ✅ 提示词初始化功能：一键创建默认提示词
- ✅ 支持变量模板：`{requirement}`、`{scenario}` 等

**Bug 修复**

- ✅ 修复数据库表缺失问题（`ai_prompts`、`ai_configs` 表）
- ✅ 修复场景步骤序号重复显示问题（AI 返回带序号 + 前端 ol 列表重复）

### V0.6 (2026-01-10)

**执行引擎升级**

- ✅ 异步任务调度（可扩展架构，预留 Redis/Celery 接入）
- ✅ 实时进度查询 API
- ✅ 停止执行功能
- ✅ 执行日志聚合

**报告功能完善**

- ✅ 报告详情页：实时进度条、日志时间线、状态标签
- ✅ 报告仪表盘：真实执行记录加载
- ✅ 报告导出：JSON/CSV 导出 + 日期/状态筛选
- ✅ 报告趋势：每日统计 + 成功率 + 可视化图表

**前端交互优化**

- ✅ WebSocket 实时进度推送（`/ws/executions/{id}`）
- ✅ 表单验证增强（空选择禁用提交按钮）
- ✅ 分页功能完善（场景/用例列表）
- ✅ AI 生成加载提示优化

**AI 集成完善**

- ✅ 场景生成：真实 AI 调用（替换 Mock）
- ✅ 用例生成：真实 AI 调用（替换 Mock）
- ✅ 支持 Word 文档内容提取

**测试覆盖**

- ✅ 60 个测试用例通过
- ✅ 测试配置统一（conftest.py 修复）

### V0.5.1 (2026-01-10)

- ✅ 实现前端完整 CRUD 交互功能
- ✅ 需求管理：详情页、编辑页、查看/编辑/新建/删除按钮
- ✅ 场景管理：数据加载、AI 生成弹窗、审核、删除
- ✅ 用例管理：数据加载、AI 生成弹窗、执行、审核、删除
- ✅ 执行管理：数据加载、环境筛选、查看详情/日志、停止
- ✅ 修复异步通知处理（asyncio 兼容）
- ✅ 添加安全头中间件
- ✅ 创建数据播种脚本（`seed_data.py`）
- ✅ 修复数据库迁移（添加 result/completed_at 列）

### V0.5 (2026-01-10)

- ✅ 修复前端菜单顺序
- ✅ 修复仪表盘 Running 图标动画
- ✅ 添加登出功能
- ✅ 修复 CI lint 错误
- ✅ 修复 CI smoke 测试依赖
- ✅ 添加测试数据库统一配置

### V0.4 (2026-01-09)

- ✅ 完成阶段 1-3 核心功能
- ✅ 32 个管理 API 接口
- ✅ 完整的需求 → 场景 → 用例 → 执行链路

---

## 开发工具

### 数据播种

```powershell
cd backend/app
python seed_data.py
```

### 清理数据库

```powershell
Remove-Item qualityfoundry.db -Force
cd backend && alembic upgrade head
```
