# Roadmap

按里程碑组织，顺序不承诺，欢迎在 Issue 中讨论优先级或认领。

## v1.1（工程化补齐）

- [ ] 前端 ESLint / Prettier 统一与 `npm run lint`
- [ ] `utils/format.js`、`utils/category.js` 等纯函数的 Vitest 单测
- [ ] 集成测试：auth / record / category / statistics 的 CRUD happy path（需 MySQL service）
- [ ] requirements 锁定文件（pip-tools 或 uv）

## v1.2（体验增强）

- [ ] 账单导入导出（CSV / Excel）
- [ ] 预算告警：分类预算超支提醒
- [ ] 移动端周报 / 月报页面

## v1.3（部署与国际化）

- [ ] 生产部署指南完善：HTTPS（Caddy / Nginx + certbot）、systemd 模板、数据库备份脚本
- [ ] i18n 框架接入（zh-Hans / en）

## 更远的想法

- 多账本 / 家庭共享账本
- 票据 OCR 记账
- 微信小程序端补齐（当前仅有空壳配置）

> 认领方式见 [CONTRIBUTING.md](CONTRIBUTING.md)。
