# Changelog

本项目的所有显著变更记录于此文件。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-09-26

首个正式开源版本。

### Added
- 三端完整实现：FastAPI 后端 + React Web 端 + uni-app 移动端
- 记账核心：账单增删改查、分类管理、月度收支与分类统计
- AI 能力：自然语言记账（含澄清追问与幂等去重）、对话（已实时接入账单数据）、消费分析、预算规划、FAQ 语义检索
- 移动端「纸面结算 × 行情看板」视觉体系与设计系统文档（DESIGN.md）
- pytest 最小测试集（安全工具 / 记账归一化 / 应用健康）
- GitHub Actions CI 流水线（后端测试 / Web 构建 / 移动端构建）
- Docker Compose 一键部署编排（MySQL + 后端 + Web 端）

### Fixed
- 全新环境按 README 安装后应用无法启动的依赖缺陷（langchain 系列移入正式依赖）
- 账单页滚动失效与触底分页不触发（scroll-view 有界化）
- Windows GBK 控制台日志 UnicodeEncodeError（SQL echo 默认关闭，控制台切 UTF-8）

### Changed
- 仓库开源化清理：移除僵尸目录、重复文档与内部文件，补全 .gitignore
