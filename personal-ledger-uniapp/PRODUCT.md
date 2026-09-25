# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

普通个人记账用户（毕业设计面向的大众用户：学生、职场新人）：注册登录后手动记账或通过 AI 自然语言记账，管理自定义分类，查看月度收支与分类统计。管理员仅使用 Web 端后台，不属于本移动端范围。

## Product Purpose

「简记」— 个人记账管理系统移动端。让用户快速记一笔（数字键盘或 AI 自然语言），并一眼看清每月收支全貌、分类构成与趋势。成功标准：用户能坚持记账，且打开应用 3 秒内读出"这个月结余多少、钱花在哪"。

## Positioning

记账与 AI 助手一体：自然语言记账、对话式分析、常见问题解答——AI 是五个主 Tab 之一而非附加页。前后端分离（FastAPI + MySQL 后端、uni-app 移动端、React Web 端），个人毕业设计项目。

## Operating Context

- 一套 uni-app 代码运行 H5 / App / 微信小程序；主要交付端为 App（app-plus，Android/iOS，页面由 webview 渲染），开发调试与演示常用 H5（`npm run dev:h5`，端口 5174，`/api` 代理本地 8000）。
- 微信小程序端仅有空壳配置（appid 为空），未实际接入。
- 后端统计能力：`/statistics/monthly`（月度 total_income / total_expense）与 `/statistics/category`（分类占比，后端算好百分比）两类；趋势与日粒度数据由前端自行聚合。
- 金额统一 DECIMAL(10,2)，人民币计价。

## Capabilities and Constraints

- 5 个主 Tab：概览、账单、AI助手、分类、我的；TabBar 悬浮「+」为记账入口；记账页含数字键盘、草稿自动恢复、成功动画。
- 暗色模式已明确移除，全局锁定浅色（pages.json 导航栏白色配套）。
- 必须保留的既有逻辑：dashboard/账单页 stale-while-revalidate 缓存、全局 401 跳转去重、记账草稿 record_draft、左滑删除、AI 会话归属校验。
- 预设 16 个分类，emoji 图标 + 7 色粉彩底板（按分类 id 取色，同分类恒同色）。

## Brand Commitments

- 名称「简记」。
- 现有实现中的黄色 #FACC15 / 墨黑 / 粉彩分类色板为 incumbent 视觉，非用户确认的品牌承诺，重设计中可整体替换。

## Evidence on Hand

- 统计接口两个，返回字段已确认（见 Operating Context）。
- 无真实用户数据、无设计资产；方案示意可用合成演示数据，需标注为演示数据。
- Android 真机调试指南与全套 App 图标/启动屏配置已就绪。

## Product Principles

1. 一眼看清：概览首屏 3 秒内读出本月结余与收支结构——数据呈现优先于装饰。
2. 记账要快：任意页面一次点击进入记账；键盘输入流不被打断。
3. 财务语义色恒定：收入/支出/结余的颜色语义全端一致，不挪作纯装饰。
4. 克制而精致：留白、层级与对比承担质感，不靠堆卡片、堆阴影。

## Accessibility & Inclusion

- 全中文界面；金额一律 tabular-nums 等宽数字排版。
- 触控目标 ≥ 88rpx；文本对比度满足 WCAG AA（webview 渲染）。
