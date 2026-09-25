---
version: 1
slug: "pages-dashboard-index-vue"
primary_target: "pages/dashboard/index.vue"
related_targets: ["pages/records/index.vue","pages/ai-chat/index.vue","pages/categories/index.vue","pages/user/index.vue"]
---

# Surface brief — 五 Tab 视觉世界替换（概览为主目标）

**Scope:** 概览 / 账单 / AI助手 / 分类 / 我的 五页 + 共享令牌 theme.css 与组件；登录/注册/记账编辑仅令牌级继承。Visitor mode: **Operate**。

**Audience / job / action:** 个人记账用户打开应用查账、记账、管理分类。首要任务：3 秒读出本月结余与收支结构；次要：趋势判断、分类管理、AI 问答。Proof：真实统计接口数据（月度汇总、分类占比、前端聚合 6 月序列），禁止编造商业数据；演示数据需可被真实数据替换。

**Constraints:** 后端仅 `/statistics/monthly`（total_income/total_expense）与 `/statistics/category`（type 区分、含 percentage）两类接口，趋势与环比由前端聚合；全局锁定浅色（暗色已移除是既有决定）；必须保留 stale-while-revalidate 缓存、401 全局跳转、记账草稿、左滑删除、AI 会话归属等既有逻辑；App 优先（webview 渲染），H5 开发演示；金额 tabular-nums；触控目标 ≥88rpx。

**Chosen direction（见 direction contract）:** 纸面结算 × 行情看板。Memorable moment：结余大数字 + 收支行情带构成的"月度结算报告"首屏，进场时趋势条与排行条生长。

**Unresolved:** 概览"AI 解读"跳转依赖 ai-chat 支持预填问题参数；若实现代价过大则降级为普通跳转（记录于 finish）。

## Direction contract

THESIS: 概览是一张月度结算报告，不是卡片仪表盘——一个主角数字（本月结余），发丝线分区，数字排版承担全部层级；拒绝记账 App 默认的白卡堆叠范式。

OWN-WORLD: 暖纸白 #F4F4F0 场 + 墨黑 #1A1C1A 文字；琥珀 #D97706 唯一强调（账期/选中/FAB/活跃数据），小字用 #B45309；收入绿 #12805C、支出红 #C93A3A 仅为财务语义；分类 7 色粉彩板为功能编码。无卡片盒：1px 发丝线 #E5E3DA 分区，阴影只给 TabBar/FAB/弹窗；数字用 Saira 等宽排版、右对齐列。

STORY: 用户 3 秒读出本月结余与收支方向（值+环比+微趋势并置），下滑看到钱花在哪（支出板块排行）与半年走势（收支双序列），AI 解读一键可达。

FIRST VIEWPORT: 账期抬头行（‹ 2025年09月 › + AI解读）→ 适度留白（96rpx）→ 结余区（84rpx 档等宽主数字 + 环比徽标，标签为数字下方注释行）→ 发丝线 → 收支行情带两列（金额 + ±% + 6 根微型趋势条，进场生长）→ 支出板块自然衔接（紧凑节奏，不以满屏留白强凑折叠线）。

> 修订记录：初版曾为满足"首屏止于行情带下缘"把两段留白推至 320rpx，独立评审通过后用户裁定留白过多（2026-09-25），据此收回折叠线承诺并改为紧凑报告版面；另在 H5 端加 `--window-width: 480px` 锁定 rpx 基准，避免宽窗口预览时间距膨胀。

FORM: 自有候选序位 7（行情看板的浅色纸面转译），seed key c1a09595。裁决：夜航仪表/裂缝队列/字母风暴/虹云边缘 declined，纪律并入——值+趋势并置（夜航仪表）、以线代盒（裂缝队列）、彩色只给数据（虹云边缘）；创作硬件台 competitive 备选，其"单一动作键"纪律体现为琥珀 FAB；无 wins。

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
