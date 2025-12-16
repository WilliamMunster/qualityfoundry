# QualityFoundry

**QualityFoundry — From Specs to Stable Tests.**

QualityFoundry is a Python-first open-source test intelligence platform focused on two outcomes:

1) Generate reviewable, structured test assets (modules → objectives → test points → test cases) from requirements/documents  
2) Execute cases reliably by compiling natural-language steps into a controlled **DSL**, then running them deterministically via Playwright with evidence and diagnostics.

## Quickstart (local)

### 1) Create venv and install
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -U pip
pip install -e "backend"
```

### 2) Install Playwright browsers
```bash
playwright install
```

### 3) Run API
```bash
qf serve
# Open: http://127.0.0.1:8000/docs
```

### 4) Generate a sample bundle
```bash
qf generate --title "Login" --text "Users can login with username/password; lock after 5 failures."
```

### 5) Execute a sample (DSL) against a URL
```bash
qf run --url "https://example.com"
```

## MVP scope
- Structured schemas (Requirement / Module / Objective / TestPoint / Case)
- JSON-schema-first LLM outputs (Pydantic validation)
- DSL → Playwright deterministic runner with evidence (screenshots + logs)
- Extensible placeholders for RAG and controlled self-healing

> Note: LLM integration is intentionally provider-agnostic in this scaffold.

## Windows 快速开始（本地开发）

> 首次运行建议在 PowerShell 执行策略允许的情况下运行脚本（仅对当前窗口生效）：
> `Set-ExecutionPolicy -Scope Process Bypass`

1. 一键初始化环境（创建 .venv + 安装依赖，可选安装 Playwright 浏览器）
   - 安装浏览器（可跑 UI 自动化 execute）：
     - `.\scripts\setup.ps1`
   - 不安装浏览器（仅启动 API/开发调试）：
     - `.\scripts\setup.ps1 -InstallPlaywright:$false`

2. 启动服务（默认 8000）
   - `.\scripts\dev.ps1`

3. 冒烟自检（需要服务已启动）
   - `.\scripts\smoke.ps1`
