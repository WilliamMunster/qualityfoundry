---
description: 推送代码前的本地验证流程
---
# Pre-Push 验证

在推送代码到远程仓库之前，必须运行本地验证确保不会在 CI 失败。

## 步骤

// turbo
1. 运行 pre-push 验证脚本：
```bash
./scripts/pre-push.sh
```

2. 如果 lint 或测试失败，先修复再推送

3. 验证通过后再执行 `git push`

## 脚本会检查

- **Ruff Lint**: 代码风格和未使用导入
- **Contract Tests**: API 契约测试
- **Legacy Runs Tests**: Legacy 只读保护测试
- **TypeScript**: 前端类型检查
