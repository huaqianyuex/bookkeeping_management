---
name: 简记
description: 个人记账管理系统的「纸面结算 × 行情看板」设计系统
colors:
  paper: "#F4F4F0"
  surface: "#FFFFFF"
  surface-raised: "#ECEBE4"
  ink: "#1A1C1A"
  ink-heading: "#161815"
  text: "#232522"
  text-secondary: "#5D5C54"
  text-tertiary: "#717065"
  amber: "#D97706"
  amber-deep: "#B45309"
  amber-light: "#FBEEDB"
  income-green: "#12805C"
  income-green-light: "#E4F3ED"
  expense-red: "#C93A3A"
  expense-red-light: "#FAEAEA"
  hairline: "#E5E3DA"
  divider: "#E8E6DE"
  cat-yellow: "#F6E7B8"
  cat-pink: "#F8DBD6"
  cat-blue: "#DCE3F8"
  cat-orange: "#F9E3C8"
  cat-green: "#D8EEDF"
  cat-purple: "#E8E2F8"
  cat-gray: "#ECEBE4"
typography:
  display:
    fontFamily: "Saira, DIN Alternate, Bahnschrift, Helvetica Neue, Arial, sans-serif"
    fontSize: "144rpx"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.02em"
  title:
    fontFamily: "PingFang SC, Hiragino Sans GB, Microsoft YaHei, Noto Sans SC, sans-serif"
    fontSize: "52rpx"
    fontWeight: 800
    lineHeight: 1.25
  headline:
    fontFamily: "PingFang SC, Hiragino Sans GB, Microsoft YaHei, Noto Sans SC, sans-serif"
    fontSize: "32rpx"
    fontWeight: 700
    lineHeight: 1.25
  numeric:
    fontFamily: "Saira, DIN Alternate, Bahnschrift, Helvetica Neue, Arial, sans-serif"
    fontSize: "56rpx"
    fontWeight: 700
    lineHeight: 1.2
    fontFeature: "tabular-nums"
  body:
    fontFamily: "PingFang SC, Hiragino Sans GB, Microsoft YaHei, Noto Sans SC, sans-serif"
    fontSize: "28rpx"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Saira, DIN Alternate, Bahnschrift, PingFang SC, sans-serif"
    fontSize: "22rpx"
    fontWeight: 600
    fontFeature: "tabular-nums"
rounded:
  xs: "6rpx"
  sm: "8rpx"
  md: "12rpx"
  lg: "16rpx"
  xl: "20rpx"
  full: "999rpx"
spacing:
  2xs: "4rpx"
  xs: "8rpx"
  sm: "12rpx"
  md: "16rpx"
  lg: "24rpx"
  xl: "32rpx"
  2xl: "40rpx"
  3xl: "48rpx"
  4xl: "64rpx"
  5xl: "80rpx"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.full}"
    height: "96rpx"
    padding: "0 48rpx"
  fab-action:
    backgroundColor: "{colors.amber}"
    textColor: "{colors.ink}"
    rounded: "{rounded.full}"
    size: "108rpx"
  input-field:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.lg}"
    height: "96rpx"
    padding: "0 32rpx"
  mom-chip:
    backgroundColor: "{colors.income-green-light}"
    textColor: "{colors.income-green}"
    rounded: "{rounded.full}"
    padding: "4rpx 16rpx"
  mom-chip-down:
    backgroundColor: "{colors.expense-red-light}"
    textColor: "{colors.expense-red}"
  nav-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.full}"
---

# Design System: 简记

## Overview

**Creative North Star: "月度结算报告"（纸面结算 × 行情看板）**

简记的界面不是"卡片仪表盘"，而是一份摊开在暖纸白上的月度结算报告：一个主角数字（本月结余）占据报告封面位，收支以行情带并置，分类以板块排行呈现，全部层级由数字排版（字号落差、字重对比、等宽右对齐列）与发丝线分区承担，而不是由卡片盒子承担。数据的密度借自行情看板的版式传统——值与趋势并置、涨跌色编码、金额列右对齐；气质来自结算单据的印刷编辑排版——留白、纸面、细线。

**Key Characteristics:**
- 暖纸白场（#F4F4F0）上直接排版，内容区几乎不用白色卡片盒
- 结余主数字 144rpx Saira 等宽加粗，是每屏唯一的视觉焦点
- 1rpx 发丝线（#E5E3DA）承担全部分区，阴影只属于悬浮物
- 琥珀 #D97706 是唯一强调色，只出现在账期、选中态、FAB 与活跃数据
- 收入绿 / 支出红 / 结余墨黑的语义纪律贯穿五页

## Colors

暖纸白底 + 墨黑正文的低饱和编辑版式，色彩只出现在数据与语义上。

### Primary
- **墨黑 Ink** (#1A1C1A): 主文字、主按钮、TabBar 选中胶囊——界面的"印刷油墨"。
- **结算琥珀 Amber** (#D97706): 唯一强调色。账期操作、FAB、选中分类、活跃数据；小号文字用深琥珀 (#B45309) 保证对比度。

### Secondary
- **收入绿** (#12805C): 仅用于收入语义——金额、环比上涨、趋势柱。
- **支出红** (#C93A3A): 仅用于支出语义——金额、环比下降、趋势柱；浅底 (#FAEAEA) 用于语义徽标。

### Neutral
- **暖纸白 Paper** (#F4F4F0): 全局页面底色，替换常见冷灰蓝。
- **版面白 Surface** (#FFFFFF): 输入底、弹窗、浮层。
- **浅盒 Raised** (#ECEBE4): 迷你趋势条轨道、输入底、占位图形。
- **发丝线 Hairline** (#E5E3DA) / **分隔线 Divider** (#E8E6DE): 全部分区线条。
- **正文灰阶** Text (#232522) / Secondary (#5D5C54) / Tertiary (#717065): 三档正文，均在纸面满足 AA 对比。

### Named Rules
**The 色彩只给数据 Rule.** 彩色只出现在数据与语义上（金额、涨跌、占比条、分类身份色板）；正文场保持无彩。装饰性用色不存在。
**The 唯一琥珀 Rule.** 琥珀在一屏内的出现不超过一处主要时刻（FAB、账期或选中态）；它是"结算动作"的颜色，不是品牌铺陈。

## Typography

**Numeric Font:** Saira（自托管 woff2 500/600/700，DIN 血统——结算单据与仪表数字的印刷载体）
**Body Font:** PingFang SC / Microsoft YaHei 系统中文栈
**Mixed Font:** Saira 打头、中文黑体兜底的混排栈（年月等数字+汉字场景）

**Character:** 数字是这个世界的主角——Saira 的紧凑工程感给金额以"仪表读数"的精确气质；中文正文退居安静的系统黑体，让数字站出来。

### Hierarchy
- **Display** (Saira 700, 144rpx, 1.05): 结余主数字，每页最多一个。
- **Numeric** (Saira 700, 56rpx): 行情带金额；区块主数字用 56rpx 档（--font-kpi）。
- **Headline** (700, 32rpx): 大标题（账单/我的）。
- **Body** (400, 28rpx, 1.5): 正文与说明。
- **Label** (Saira 600, 22rpx, tabular-nums): 金额列、百分比、环比徽标——右对齐等宽。

### Named Rules
**The 数字等宽 Rule.** 凡是钱出现的地方，一律 `font-family: var(--font-amount)` + `font-variant-numeric: tabular-nums`，列内右对齐；小数与货币符号降级为次级灰。

## Layout

移动端 750rpx 设计宽（390pt 基准视口），左右页边距 32–40rpx；H5 宽屏预览通过 `--window-width: 480px` 锁定 rpx 基准，间距不随窗口膨胀。概览首屏是紧凑的"报告封面"版面：账期抬头行 → 适度留白（96rpx）→ 结余主数字 + 注释行 → 收支行情带（下缘发丝线）→ 支出板块自然衔接。第二屏节奏：板块排行 → 走势带 → 收入构成，区块间距 96rpx——标题上方的空间略大于下方。列表页（账单）以日期分组头 + 发丝线分组，无卡片容器。

## Elevation & Depth

无内容阴影。层次由发丝线（1rpx #E5E3DA）、纸面留白与字号落差承担；阴影只属于真正悬浮的东西——TabBar（0 12rpx 36rpx rgba(22,24,21,0.14)）、FAB（琥珀投影）与弹窗遮罩。零偏移的彩色光晕不存在。

### Named Rules
**The 发丝线代阴影 Rule.** 版面层次的第一选择永远是发丝线 + 留白；`box-shadow` 出现在内容区即为违规，悬浮层（TabBar/FAB/弹窗）除外。

## Shapes

收敛的圆角语言：内容分区几乎无圆角（发丝线直角），控件用 12–20rpx，按钮与徽标用全胶囊（999rpx）。无斜切、无多边形裁切；分类身份色板（7 色粉彩，按分类 id 恒定取色）提供唯一的"彩色几何"。

## Components

### Buttons
- **Shape:** 全胶囊（999rpx），高度 96rpx
- **Primary:** 墨黑底 (#1A1C1A) + 纸白字；按下轻微缩放（0.97）+ 平滑减速
- **Action (FAB):** 琥珀底 (#D97706) + 墨黑"+"，108rpx 圆形，琥珀弥散投影，悬浮于 TabBar 右上

### Chips
- **环比徽标 (mom-chip):** 涨=绿浅底/降=红浅底/平=浅盒，Saira 600 小字 + ▲▼
- **筛选胶囊:** 浅盒底未选 / 琥珀浅底选中（文字深琥珀）

### Cards / Containers
- **默认无盒:** 内容直接排在纸面上，行与组用发丝线分隔；例外只有弹窗与 TabBar

### Inputs / Fields
- **Style:** 浅盒底 (#ECEBE4)、无边框、16rpx 圆角、高 96rpx
- **Focus:** 光标为深琥珀；错误态红浅底
- **选区:** 文本选区为琥珀 24% 透明

### Navigation
- **TabBar:** 悬浮白色胶囊（左右 24rpx 边距、发丝圆角、弥散投影），选中项为墨黑胶囊反白；琥珀 FAB 悬于右上
- **页内返回/操作:** 白底圆形 + 发丝线描边（72rpx）

### 板块排行行（签名组件）
分类单字章（粉彩底 + 深色字）+ 名称 + 发丝轨道上的深色占比条 + 右对齐等宽金额/百分比；进场时占比条从左向右生长（expo，55ms 阶梯）。

## Do's and Don'ts

### Do:
- **Do** 金额一律 Saira + tabular-nums + 右对齐；千分位分隔（`formatAmount`）。
- **Do** 用发丝线（1rpx #E5E3DA）+ 留白分区；区块间距 128rpx，标题上方空间大于下方。
- **Do** 每个关键指标同时给出值与趋势（环比箭头或微型趋势条）。
- **Do** 触控目标 ≥ 88rpx（TabBar 项、月份箭头、AI 入口）。

### Don't:
- **Don't** 给内容套白色卡片盒或内容阴影——层次属于发丝线与留白。
- **Don't** 用 emoji 充当界面图标——界面图标一律 AppIcon 自绘 SVG 集（24 viewBox / 2px 圆头笔画）；分类 emoji 是产品内容惯例，不是图标系统。
- **Don't** 让语义色（收入绿/支出红）挪作装饰，或让琥珀在一屏出现多个主要时刻。
- **Don't** 使用回弹/弹性缓动（bounce/elastic）——统一平滑减速曲线 cubic-bezier(0.16, 1, 0.3, 1)。
