# 「简记」风格 UI 改版说明

依据设计稿 `E:\一些毕设探索\记账管理系统_fastapi\记账App设计稿\01~11.png` 对 personal-ledger-uniapp 做的**纯视觉改版**。

## 硬性约束执行情况

- ✅ **所有网络请求保持不变**：未改动 `src/api/*`（request.js、user.js、record.js、category.js、statistics.js、ai.js）、`src/utils/*`、`src/manifest.json`；所有 `<script>` 中的请求地址、方法、参数、触发时机、响应处理逻辑均未修改。
- ✅ **不改动业务逻辑与数据流**：所有改动限于 `<style>` 段、`theme.css` 设计 token、组件/页面 `<template>` 的纯静态结构调整。仅有的少量例外见下文「最小脚本调整」，均为纯视图状态，不涉及任何请求与数据流。

## 一、设计语言（提炼自 11 张设计稿）

| Token | 值 | 用途（对应设计稿） |
|---|---|---|
| `--color-bg` | `#F5F6F7` | 全局浅灰底（01-11 全部） |
| `--color-surface` | `#FFFFFF` 白卡 | 卡片，大圆角、无边框、弥散阴影 |
| `--color-primary` | `#1A1A1A` 墨黑 | 主按钮/分段选中/Tab 选中胶囊/用户气泡（01/02/03/04） |
| `--color-accent` | `#FACC15` 简记黄 | Logo、选中分类、FAB、进度高亮、空态按钮（01/02/03/10） |
| `--color-success` | `#22A45D` | 收入语义绿（03） |
| `--cat-*` 色板 7 色 | 黄/粉/蓝/橙/绿/紫/灰 粉彩 | 分类图标圆角方块（02/05/08） |

`theme.css` 中**所有变量名保持不变、仅替换值**，因此全部页面零改动即继承新风格；dark 模式块同步更新。

## 二、改动文件清单与关键 diff

### 全局
| 文件 | 改动 | 设计稿 |
|---|---|---|
| `src/styles/theme.css` | token 全量重定义：primary→墨黑、accent→黄、bg→浅灰、圆角整体加大、阴影改弥散无边框风格、新增 `--cat-*` 分类色板与 `--shadow-tabbar`；dark 块同步 | 全局 |
| `src/App.vue` | `:focus-visible` 轮廓改黄色；page 基调注释 | 全局 |
| `src/components/TabBar.vue` | ① 悬浮白色胶囊底栏（左右留边、`--shadow-tabbar`）②选中项黑色圆胶囊、PNG 图标 CSS 滤镜反白 ③新增中央黄色「+」按钮，`uni.navigateTo('/pages/records/add-edit')`（纯新增入口，原 5 tab 及 reLaunch 逻辑不动） | 03/10 底栏 |
| `src/components/EmptyState.vue` | 标题/描述改灰色调；slot 按钮默认渲染为黄色胶囊（「去记一笔」） | 10 |
| `src/components/SkeletonCard.vue` | 骨架条改胶囊圆角 | 11 |
| `src/components/RecordCard.vue` | 图标改粉彩圆角方块；左侧色条隐藏；支出金额改墨黑、收入绿 | 03 |
| `src/components/StatCard.vue` | 去边框；支出/结余大数字改墨黑、收入绿 | 03/09 |

### 页面
| 文件 | 关键改动 | 设计稿 |
|---|---|---|
| `src/pages/login/index.vue` | 居中品牌区（黄圆角 Logo「🧾」+ 简记 + slogan）；输入改无边框灰底圆角（去 label）；按钮改黑色胶囊；底部固定协议文案。**字段仍为用户名/密码，登录逻辑未动** | 01 |
| `src/pages/register/index.vue` | 同 01 风格（缩小版品牌区 + 灰底输入 + 黑胶囊按钮） | 01 |
| `src/pages/password/index.vue` | 白卡居中 + 黄色圆角图标块 + 灰底输入 + 黑胶囊按钮 | 01 |
| `src/pages/records/add-edit.vue` | ①支出/收入改灰底胶囊分段（选中墨黑）②金额左对齐、字号加大、光标改黄色 ③新增「已选分类 · ××」灰字提示（模板表达式读取既有 state）④分类改 4 列粉彩网格（横滚改 wrap），选中项黄底 ⑤键盘改极简透明按键 ⑥「完成」改黑色胶囊 | 02 |
| `src/pages/records/index.vue` | ①新增左上大标题「账单」，筛选按钮改白色圆胶囊 ②日期分组头改小灰字（隐藏日期方块）③同组账单合并进一张白卡（`:deep()` 去除单卡阴影）④空态按钮改黄色胶囊 ⑤筛选弹层改底部弹层、选项改胶囊、选中黄色高亮、确定改黑色胶囊 ⑥原角落 FAB 隐藏（入口由 TabBar 中央「+」与空态按钮承担） | 03/08/10 |
| `src/pages/dashboard/index.vue` | 月份选择器改白胶囊；统计卡/图表卡/表格卡去边框；趋势柱改灰底+黄色高亮当前柱；对比条选中改黄；模式切换/计数改胶囊；支出条与金额改中性灰墨；FAB 隐藏 | 03 |
| `src/pages/ai-chat/index.vue` | 顶栏改透明+左大标题「AI 助手」+白圆操作钮；快捷提问改无边框白胶囊；隐藏头像；用户气泡改墨黑全圆、助手气泡改白卡；流式光标改黄；输入条透明+灰胶囊输入+黑色圆形发送。`calcLayout` 中 TabBar 占位常量 100rpx→170rpx（纯布局常量） | 04 |
| `src/pages/ai-history/index.vue` | 顶栏/搜索/卡片同 04 风格；排序选中下划线改黄色；底部留位加大适配悬浮 TabBar | 04/08 |
| `src/pages/categories/index.vue` | ①大标题+白色圆添加钮 ②新增支出/收入胶囊分段（**仅视图筛选**，见下）③列表改 4 列粉彩网格 + emoji 图标 ④新增「长按分类可删除」提示 ⑤弹窗改底部弹层胶囊风 ⑥FAB 隐藏 | 05/08 |
| `src/pages/user/index.vue` | ①大标题「我的」②用户卡改横排：黄色圆形头像占位（显示用户名首字）+ 名称/ID 右侧 ③信息卡/菜单卡去边框改弥散阴影 ④退出改红描边胶囊 ⑤弹窗改胶囊风 ⑥FAB 隐藏 | 06 |

## 三、最小脚本调整（纯视图态，无请求/数据流影响）

1. `pages/categories/index.vue`：新增 `viewType` data 字段 + `filteredList` computed（客户端视图筛选，`fetchList`/增删改逻辑不变）；新增 `getCategoryEmoji` 纯展示映射（与 add-edit 页一致）。
2. `pages/ai-chat/index.vue`：`calcLayout` 中 TabBar 高度常量 100→170rpx（配合悬浮 TabBar 的布局占位）。
3. `components/TabBar.vue`：新增 `goAddRecord()` 方法（`uni.navigateTo` 到已有记账页，纯新增入口）。

## 四、状态覆盖

| 状态 | 处理 |
|---|---|
| 默认 | 全局 token 重涂 |
| 按压(hover) | 沿用并重涂各页 `:active`（透明度/缩放/底色） |
| 禁用 | `btn[disabled]`、`.confirm-btn.disabled`、AI 发送 `send-btn--disabled` 灰阶 token 化 |
| 空态 | `EmptyState` 灰字+黄胶囊按钮（账单/分类/概览/AI 内联空态同步） |
| 加载态 | `SkeletonCard` 胶囊骨架 + 「加载中/没有更多了」footer（样式重涂） |
| 报错态 | 保留 `uni.showToast/showModal` 机制不变；内联错误文本（用户名弹窗 `modal-error`）红字样式重涂；danger token 更新 |

## 五、冲突标注（未改动，仅说明）

1. **登录方式**：设计稿01为手机号+验证码；现有为账号密码（既有 API）。→ 保留现有字段与请求，仅改视觉。
2. **07 账单详情页**：项目无此页，点击账单仍进入编辑页（`add-edit?id=`）。→ 未新建页面。
3. **09 预算设置页**：无对应功能与 API。→ 跳过；如需实现建议后端先提供预算接口。
4. **06 我的页菜单项**（预算管理/月度报告/数据导出/深色模式/关于我们）：无对应功能。→ 保留现有菜单项（修改密码），未新增死入口；「深色模式」已随 token 支持 `prefers-color-scheme` 自动适配。
5. **TabBar 结构**：设计稿无「概览」tab。→ 按确认方案保留 5 个 tab，新增中央黄色「+」。
6. **05 分类管理「拖拽排序」**：现有无排序接口。→ 提示文案改为「长按分类可删除」，交互为点按编辑/长按删除（原行内编辑/删除按钮的功能保留）。
7. **03 账单页统计卡与周柱状图**：该数据能力在概览页，账单页保持列表结构；概览页已按同风格（白卡+黄色高亮柱）改造。
8. **uni.showToast 原生样式**：无法深度自定义（设计稿11的黑色/黄色 toast 胶囊）。→ 保留原生 toast；如需完全一致可后续引入自定义 toast 组件（会改动提示调用点，属逻辑改动，本次不做）。
9. **02 记账页「今天」日期选择器与语音输入**：语音输入无对应能力，未实现；日期选择保留现状。

## 六、响应式说明

移动端项目，全部使用 rpx（375 设计基准，自动随屏宽缩放）；dashboard 保留原有 `max-width: 360px` 小屏降级断点。设计稿中的 768/1440 桌面断点不适用于本 UniApp 移动端工程，未引入。

## 七、验证

`npm run build:h5` 构建通过（Compiler 5.12, vue3）。
