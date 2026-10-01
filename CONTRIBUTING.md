# 贡献指南

感谢关注本项目！以下约定能让协作更顺畅。

## 开发环境

1. 按 [README](README.md) 的「安装与运行方式」把三端跑起来（或直接 `docker compose up`）。
2. 后端测试：`cd fast_backend && pip install -r requirements-dev.txt && pytest`。
3. 敏感信息扫描钩子（强烈建议）：`pip install pre-commit && pre-commit install`。
   钩子基于 [gitleaks](https://github.com/gitleaks/gitleaks)，在每次提交前扫描密钥、
   令牌、口令与连接串；数据库备份（`database_backup_*.sql` 等）已在 `.gitignore` 拦截。

## 分支与提交

- 从 `master` 拉出功能分支：`git checkout -b feat/xxx` 或 `fix/xxx`。
- 提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)：
  `feat / fix / docs / refactor / test / chore / build` + 中文描述，例如
  `fix: 账单页触底分页不触发的问题`。
- 一个提交只做一件事；UI 改动请附截图。

## 代码风格

- 后端：遵循现有分层（routers → crud → models），金额一律 `Decimal`，新接口纳入 `schemas/` 校验。
- 移动端：颜色 / 间距 / 字号使用 `styles/theme.css` 的设计令牌，规范见 [DESIGN.md](personal-ledger-uniapp/DESIGN.md)。
- 注释与文案使用中文，与现有风格一致。

## 提交 Pull Request 前

- [ ] `pytest` 全绿
- [ ] 涉及三端构建的改动本地 `npm run build` / `build:h5` 通过
- [ ] 不包含个人资料、密钥或与本功能无关的文件
- [ ] 已安装并运行 pre-commit 钩子（gitleaks 扫描通过）

## 报告缺陷

使用 Issue 模板并附：复现步骤、期望与实际行为、环境（浏览器 / 手机型号 / 后端日志）。
