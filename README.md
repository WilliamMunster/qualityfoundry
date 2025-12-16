# QualityFoundry

**QualityFoundry — 从需求到稳定可执行的测试资产。**

QualityFoundry 是一个 Python 优先的开源“测试智能平台”脚手架，聚焦两个核心结果：

1. **从需求/文档生成可评审、结构化的测试资产**（模块 → 目标 → 测试点 → 测试用例）
2. **将自然语言步骤编译为受控 DSL 并确定性执行**（Playwright 驱动 + 证据与诊断产物）

> 说明：当前版本更偏“可运行的工程骨架（scaffold）”，LLM 供应商保持解耦，方便后续接入任意模型或企业内模型。

---

## 你能得到什么

- 结构化测试资产：Requirement / Module / Objective / TestPoint / Case
- JSON-schema-first 输出约束（Pydantic 校验），减少“模型胡编”
- 自然语言步骤 → 受控 DSL → Playwright 确定性执行
- 自动证据产出（截图、执行记录、错误信息），便于回溯与复现
- 为 RAG、受控自愈（controlled self-healing）预留扩展位

---

## 快速开始（本地开发）

### 方式一：使用脚本（推荐，Windows 最省心）

> 首次运行建议在 PowerShell 设置执行策略（仅对当前窗口生效）：
> `Set-ExecutionPolicy -Scope Process Bypass`

1) 一键初始化环境（创建 `.venv` + 安装依赖，可选安装 Playwright 浏览器）
- 安装浏览器（可跑 UI 自动化 execute）：
  - `.\scripts\setup.ps1`
- 不安装浏览器（仅启动 API/开发调试）：
  - `.\scripts\setup.ps1 -InstallPlaywright:$false`

2) 启动服务（默认 8000）
- `.\scripts\dev.ps1`

3) 冒烟自检（需要服务已启动）
- `.\scripts\smoke.ps1`

---

### 开发依赖说明（ruff / pytest）

`.\scripts\setup.ps1` 在安装后端依赖后，会自动检测并安装 `backend/requirements-dev.txt` 中定义的开发依赖（如 `ruff`、`pytest`），用于保证本地检查与 CI 行为一致。

如需手动安装（不运行 setup 脚本）：
```powershell
python -m pip install -r .\backend\requirements-dev.txt