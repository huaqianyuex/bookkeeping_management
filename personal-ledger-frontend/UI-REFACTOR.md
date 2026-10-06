# 管理后台纯 UI 层视觉重构说明

> 范围：`personal-ledger-frontend`（React 18 + Ant Design 5 + Vite）
> 性质：**仅表现层**。接口契约、状态管理、路由、鉴权、业务校验、字段名与数据结构零改动。
> 验证：生产构建通过 + 12 张真实渲染截图（桌面 / 平板 / 移动）逐页核对，控制台无异常。

---

## 一、现状梳理

### 1.1 页面清单（14 条路由）

| 路由 | 文件 | 说明 | 本轮处理 |
|---|---|---|---|
| `/login` `/register` | `pages/auth/Login.jsx` `Register.jsx` | 认证页，共用 `AuthLayout` | ✅ 重构 |
| `/records` | `pages/Records.jsx` | 记账 + 账单列表（主战场） | ✅ 重构 |
| `/dashboard` | `pages/Dashboard.jsx` | 统计概览（Recharts） | ✅ 重构 |
| `/categories` | `pages/Categories.jsx` | 分类 CRUD | ✅ 重构 |
| `/ai-chat` | `pages/AiChat.jsx` | AI 流式对话 + 会话侧栏 | ✅ 重构 |
| `/settings/profile` | `pages/UserInfo.jsx` | 个人资料 | ✅ 重构 |
| `/settings/password` | `pages/ChangePassword.jsx` | 修改密码 | ✅ 重构 |
| `/settings/*` | `pages/settings/SettingsLayout.jsx` | 设置页 Tabs 外壳 | ✅ 微调 |
| `/admin/dashboard` | `pages/admin/AdminDashboard.jsx` | 系统概览 6 卡 | ✅ 重构 |
| `/admin/users` | `pages/admin/AdminUsers.jsx` | 用户管理 | ✅ 重构 |
| `/admin/records` | `pages/admin/AdminRecords.jsx` | 全量账单 | ✅ 重构 |
| `/admin/faq` | `pages/admin/AdminFaq.jsx` | FAQ 知识库 | ✅ 重构 |
| `/membership` | `pages/Membership.jsx` | 会员中心 | ⏸ 仅骨架（TODO 未实装），未动 |
| `/admin/membership` | `pages/admin/AdminMembership.jsx` | 兑换码管理 | ⏸ 仅骨架（TODO 未实装），未动 |

### 1.2 组件清单

**业务壳层**：`components/MainLayout.jsx`（侧边栏 + 顶栏 + 快捷记账弹窗）· `components/CommandPalette.jsx`（⌘K）· `components/guards/{AuthRoute,AdminRoute}.jsx`

**通用 UI（`components/ui/`）**：`StatCard` · `PageHeader` · `SectionTitle` · `EmptyState` · `ErrorState` · `SkeletonCard`/`StatsRowSkeleton` · `AnimatedRoute` · `Money` · `AuthLayout` · `ListToolbar` · **`SemanticTag`（本轮新增）**

**设计系统层**：
```
src/theme/palette.js      ← 颜色唯一真源 → antdTheme.js + 运行时注入 :root
src/theme/tokens.js       ← 标量唯一真源（本轮新增）
src/theme/antdTheme.js    ← 令牌 → antd token 映射
src/styles/design-tokens.css ← 纯结构层（工具类 / 动画 / 基线）
src/main.jsx              ← 渲染前 applyPalette() + applyTokens()
```

> 该架构本身是好的（颜色已收敛到单一真源），本轮做的是**补上标量那一半**并**把令牌真正用到组件上**。

### 1.3 需保留的部分（刻意不动）

- **整体的 Slate Cyan 青石调性** —— 低饱和、可信赖，符合财务场景，没有换成通用 AI 紫色/渐变。
- **`card-base` 细描边 + 弱阴影**的卡片语言，以及 8pt 间距体系。
- **`AuthLayout` 左品牌右表单**的双栏结构、`Money` 的 tabular-nums、`SectionTitle` 的语义圆点。
- **`design-tokens.css` 里的工具类层**（`.flex-*` / `.gap-*` / `.text-*` 等）。其中约 40% 当前无引用，但删除属于独立议题，且存在"删除即破坏兼容"的风险，故原样保留（见 §5）。

---

## 二、改动项 vs 不可触碰项

### 2.1 纯 UI 改动项（本轮实际做的事）

| # | 类别 | 具体改动 |
|---|---|---|
| 1 | 设计令牌 | 新建 `theme/tokens.js`：圆角/间距/字号/字重/行高/阴影/聚焦环/动效/z-index/布局常量的唯一真源，`applyTokens()` 渲染前注入 `:root` |
| 2 | 设计令牌 | `palette.js` 重校：主色、语义色、文本层级、描边、遮罩、on-brand 白系、新增 accent 位 |
| 3 | 设计令牌 | 圆角阶梯 `6/10/12/14/18` → `4/6/8/12/16/20`（原中段 10 与 12、14 与 18 视觉不可分辨） |
| 4 | 设计令牌 | 字号阶梯去掉 17px，`11/12/14/15/17/20` → `12/13/14/15/16/20` |
| 5 | 设计令牌 | 阴影重写，`--shadow-primary` / `--shadow-fab` 改由 `palette.primary` 派生（原先写死 `rgba(22,78,99,·)`，换主色即失效） |
| 6 | 组件外观 | `antdTheme.js` 组件级 token 从 12 个补到 **34 个**（Modal / Drawer / Dropdown / Select / DatePicker / Pagination / Tooltip / Form / Descriptions / Skeleton / Message 等此前全走 antd 默认样式） |
| 7 | 组件外观 | 把 antd 的 `colorSuccess/Error/Warning/Info` 对齐自定义色板 —— 修掉"同一行表格里两种绿" |
| 8 | 组件外观 | 新增 `SemanticTag`，替换 5 处各写一套的 Tag 实现 |
| 9 | 组件外观 | 表格：表头改 `bg-subtle` 底 + 主色 4% 的行 hover；单元格左右内边距 8→16px |
| 10 | 组件外观 | 修复 `SkeletonCard` 与真实卡片不同构导致的加载跳版 |
| 11 | 交互反馈 | 统一聚焦环（`controlOutline` + `--ring-focus`）；修正 Input hover 描边比 focus 还重的问题 |
| 12 | 交互反馈 | 统一"大号控件"高度为 44px（原手写 40/44/48 三种） |
| 13 | 交互反馈 | 新增纤细滚动条、选中态配色；`--gradient-brand` 拆出（见 §4.1） |
| 14 | 可访问性 | `--color-text-tertiary` 对比度 2.56:1 → 4.76:1；`success` 3.77→5.48；`warning` 3.19→5.02 |
| 15 | 可访问性 | 图标按钮补 `aria-label`（6 处）；空态插画标 `aria-hidden` |
| 16 | 响应式 | 移动端主 CTA 撑满宽度；平板收起态 CTA 图标不再被 `fontSize:0` 清零；操作列加宽避免裁切 |
| 17 | 代码卫生 | 清掉 60+ 处 JSX 内硬编码 `fontSize/rgba/#fff/padding`，一律改吃令牌；修 2 处 antd 废弃属性告警 |

### 2.2 不可触碰项（本轮零改动，可逐条核对）

| 类别 | 说明 | 核对方式 |
|---|---|---|
| 接口调用 | `src/api/*.js` **8 个文件一行未改**：URL、method、参数名、请求体字段全部原样 | `git diff --stat src/api` 无输出 |
| 请求层 | `api/request.js` 的 axios 实例、baseURL、超时、token 注入、401 跳转逻辑未改 | 同上 |
| 状态管理 | `context/AuthContext.jsx` 未改；各页 `useState/useEffect/fetchData` 的数据流与依赖数组未改 | `git diff` 无输出 |
| 路由 | `App.jsx` 路由表未改（其中已有的 settings 嵌套路由是本次会话之前的未提交改动，非本轮引入） | `git diff src/App.jsx` 与本轮无关 |
| 鉴权 | `guards/AuthRoute.jsx`、`guards/AdminRoute.jsx` 未改 | `git diff` 无输出 |
| 业务校验 | 所有 `Form rules` / `PASSWORD_REGEX` / `USERNAME_REGEX` / 头像大小校验未改 | 逐文件 diff |
| 字段名与结构 | 所有 `dataIndex` / `rowKey` / `name=` / `res.data.xxx` 未改 | `git diff` 中无 `dataIndex` / `name=` 行 |
| 流式对话 | `AiChat.jsx` 的 SSE 解析（`data: {...}` 拆包、`type: content/error/done`）、`fetch` 调用、3s 延迟刷列表未改 | 仅样式行变更 |
| 分页/筛选逻辑 | `pagination.onChange`、`fetchData(page,size,...)` 参数传递未改 | 逐文件 diff |
| 权限语义 | 管理员不可删除/禁用自身的逻辑、批量删除过滤未改 | 逐文件 diff |

**唯一的"功能相邻"改动**：`AdminDashboard.jsx` 把加载失败时的 `EmptyState` 换成 `ErrorState`（二者 props 兼容，`onRetry` 可选，不涉及数据流）。

---

## 三、新设计规范（可直接查阅的一页表）

### 3.1 色板（真源：`src/theme/palette.js`）

| 角色 | 旧值 | 新值 | 说明 |
|---|---|---|---|
| primary | `#164e63` cyan-900 | `#0e7490` cyan-700 | 原色接近黑，主按钮压得发闷；提亮后白字 5.36:1 仍达 AA |
| primaryDeep | `#0f3846` | `#155e75` cyan-800 | 渐变深端 / hover |
| primaryLight | `#0e7490` | `#0891b2` cyan-600 | 图标色块渐变亮端 |
| success / 收入 | `#059669` | `#047857` | 3.77:1 → **5.48:1** |
| danger / 支出 | `#e11d48` | 不变 | 4.70:1 已达标 |
| warning | `#d97706` | `#b45309` | 3.19:1 → **5.02:1** |
| info | `#0284c7` | 不变 | 仅用于 ≥24px 与图表，4.10:1 满足大字号 3:1；加深会与 primary 撞色 |
| **accent（新增）** | — | `#7c3aed` violet-600 | 第四个互不冲突的强调位 |
| textTertiary | `#94a3b8` | `#64748b` | **2.56:1 → 4.76:1**（原不达 AA，且被大量用于表格辅助信息） |
| overlay（新增） | — | `rgba(15,23,42,.45)` | 遮罩统一，原为各处手写 `.3` |
| on-brand 白系（新增） | 各处手写 `.03/.04/.1/.12/.18/.72` | `faint/weak/soft/line/text/textStrong` | 5 档，品牌区层次统一 |

新增的还有每个语义色的 `·Border`（浅描边）与 `·Bg`（浅底）档位，供标签与状态块使用。

### 3.2 阶梯

| 类别 | 旧 | 新 |
|---|---|---|
| 圆角 | 6 / 10 / 12 / 14 / 18 / 9999 | **4 / 6 / 8 / 12 / 16 / 20 / 9999** |
| 字号 | 11 / 12 / 14 / 15 / 17 / 20 / 24 / 30 | **12 / 13 / 14 / 15 / 16 / 20 / 24 / 30** |
| 间距 | 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 | 同前 + **64** |
| 阴影 | 5 档，primary 档写死色值 | 5 档 + primary/hover/fab/fabHover，**全部派生自 palette** |
| 控件高度 | 40 / 44 / 48 混用 | 默认 32 / large **44**（删除 7 处手写 `height: 48`） |
| 动效 | `ease` 浏览器默认 | 统一 `cubic-bezier(.4,0,.2,1)`，位移类用 `(.16,1,.3,1)` |

---

## 四、需要你知道的四个设计决策

### 4.1 品牌渐变拆成两支（`--gradient-primary` / `--gradient-brand`）

原先只有一支 `primary → primaryDeep`，而 `.logo-gradient` 却是 `primary → primaryLight` —— **同一套系统里两个渐变方向相反**。

本轮拆成两支，判据是"上面压不压文字"：

- `--gradient-primary`（亮，`primaryLight → primary`）：只用于承载图标的色块（侧边栏 Logo 方块、移动端 FAB），其上无文字。
- `--gradient-brand`（暗，`primary → primaryDeep`）：用于承载白字的登录页品牌区，保证最亮端仍有 5.36:1。

> 这是我在验证截图中发现并修正的一个**自己引入的回归**：第一版把品牌区也换成亮渐变后，白字对比掉到 2.83:1（不达标），装饰圆点也从"极淡"变成抢眼的大圆。

### 4.2 新增 accent（violet）色位

主色从 cyan-900 提亮到 cyan-700 后，与 info（sky-600）只差 **8° 色相**，两者并排会读成"同一个色的深浅"。因此：

- `AdminDashboard` 的「总账单数」卡从 `info` 改到 `accent`，三张计数卡现在是 cyan / violet / amber，色相互不相邻；
- 「管理员」角色标签从 antd 预设 `gold` 改为 `accent` —— 角色是*身份*不是*状态*，用琥珀会和"警告"混淆；
- 图表色序重排为「相邻两色色相尽量远离」（cyan → amber → violet → emerald → rose → sky → …），避免环形图相邻扇区撞色。

### 4.3 结余不再借用"收入绿"

`StatCard` 的 `balance` 变体原先数字用主色、顶部色条却用成功/危险色，同一张卡片出现两种语义。现统一按正负取主色 / 危险色 —— 结余是派生指标，不该与"收入"共用绿色。

### 4.4 骨架屏必须与真实卡片同构

`StatCard` 桌面版早已改成"标签 + 大数字"的纯文字版式，但 `SkeletonCard` 仍在渲染一个 56×56 的图标方块、且只有两行短输入 —— 加载完成时整行高度会缩水。另外 `StatsRowSkeleton` 用 CSS Grid（`.stats-grid`）而 `Dashboard` 用 `Row/Col`，两者 gutter 算法不同（Row 走负外边距），也会有细微位移。现已统一为与真实卡片同构、同 `Row/Col`。

---

## 五、顺带修掉的既有缺陷

这些是改动过程中真实渲染验证发现的，都不是本轮引入：

| # | 位置 | 现象 | 处理 |
|---|---|---|---|
| 1 | `MainLayout.jsx` 收起态 | 侧边栏收起时「快速记账」是一个**空白色块** —— 原代码用 `fontSize: 0` 隐藏文案，而图标字号继承自按钮，被一起清零 | 改为仅靠条件渲染隐藏文案，图标恢复正常 |
| 2 | `Records.jsx` 移动端 | 主 CTA「记一笔」没有撑满宽度，与上方全宽表单项不成体系（`Space` 垂直模式不拉伸子项） | 换普通 flex 容器 + `align-items: stretch` |
| 3 | 各列表页 | 单元格内边距调宽后，「操作」列的「删除」被裁掉 | `操作` 列宽 140→168 / 150→176 / 160→184，同步调整 `scroll.x` |
| 4 | `AdminDashboard.jsx` | 加载失败时用「暂无数据」的空态插画与语气，且无重试入口 | 改用语义正确的 `ErrorState` |
| 5 | `theme/antdTheme.js` | `Input.hoverBorderColor` 用的是 `textSecondary(#475569)`，**比 focus 态还重** | 改为主色浅描边 `primaryBorder` |
| 6 | `EmptyState.jsx` / `UserInfo.jsx` | antd 废弃属性告警（`imageStyle` / `labelStyle`） | 迁移到 `styles={{ image / label }}` |

---

## 六、明确未处理（遗留项）

诚实列出，避免误以为已全清：

1. **`design-tokens.css` 工具类约 40% 无引用** —— `.flex-*` / `.gap-*` / `.mt-*` / `.card-elevated` / `.col-2-grid` / `.auto-grid` / `.w-full` 等，共约 120 行。属于独立清理议题，删除需先确认无跨仓库引用，本轮保留。`.stats-grid` 在本轮后也不再被引用（`StatsRowSkeleton` 已改用 `Row/Col`）。
2. **antd 弹层 z-index 与自定义层级是两套体系** —— 自定义层用 `--z-*`（100–900），antd 弹出层走 1000+。当前恰好不冲突（antd 恒在上），但属于隐式约定，未统一。
3. **未做暗色模式** —— `palette.js` 目前是单主题。结构上已具备（全部消费 CSS 变量），但反色映射工作量大，本轮未纳入。
4. **`AdminFaq.jsx` 有一个无效属性 `showAllowClear`**（`Select` 的真实属性是 `allowClear`）。该属性无视觉与功能效果，属逻辑边界，按"不碰业务"的约束未改。
5. **`/membership` 与 `/admin/membership` 仍是 TODO 骨架页**，未实装，因此只保证不破坏，未做视觉重构。
6. **图表 tick 字号等 Recharts 参数**仍是数字（`tokens.chart.*`）而非 CSS 变量 —— Recharts 不接受 CSS 变量，已集中到令牌文件作为折中。

---

## 七、验证方式与结果

### 7.1 构建

```
npx vite build  →  ✓ 3715 modules transformed，built in ~20s
```

> 注：`npm run build` 在本机会因沙箱的回收站 shim 无法清理 `dist/assets` 而报错（`safe-delete ... trash operation aborted`），这是环境问题，与代码无关。改用 `--outDir` 指向新目录即可正常构建。

### 7.2 真实渲染核对

用本机 Chrome headless + CDP 驱动（脚本见 `.workbuddy/screenshots/ui-refactor/shot.cjs`），配套 mock API（`mock-api.cjs`，起在 8000 端口以命中 vite 既有代理，**未改动任何项目文件**），逐页截图并采集控制台异常：

| 截图 | 尺寸 | 结果 |
|---|---|---|
| `app-records.png` | 1440×1040 | ✅ 表格标签绿与金额绿一致 |
| `app-records-tablet.png` | 1024×900 | ✅ 侧栏自动收起为 icon rail，CTA 图标正常 |
| `app-records-mobile.png` | 390×844 | ✅ CTA 撑满宽度 |
| `app-dashboard.png` | 1440×1120 | ✅ 环形图相邻扇区无撞色 |
| `app-categories.png` | 1440×860 | ✅ |
| `app-ai-chat.png` | 1440×900 | ✅ 会话列表 / 流式容器正常 |
| `app-settings-profile.png` | 1440×900 | ✅ 角色徽章已用 accent |
| `admin-dashboard.png` | 1440×900 | ✅ 6 卡色相互不冲突 |
| `admin-users.png` | 1440×780 | ✅ 管理员标签 accent、状态标签 emerald |
| `admin-records.png` | 1440×780 | ✅ |
| `admin-faq.png` | 1440×820 | ✅ 操作列不再裁切 |
| `auth-login-mobile.png` | 390×844 | ✅ |

**控制台结果**：12 个页面全部 0 异常、0 React 报错、0 antd 告警（仅 `/records` 有一次 favicon 404，与代码无关）。

---

## 八、如何回滚 / 如何改色

- **整轮回滚**：全部改动集中在这 25 个文件（23 改 + 2 新增），未触碰 `src/api`、`src/context`、`src/components/guards`、`App.jsx` 路由。`git checkout -- personal-ledger-frontend/src` 即可还原（注意会一并丢弃本会话之前就已存在的未提交改动）。
- **只改主色**：改 `src/theme/palette.js` 的 `primary/primaryDeep/primaryLight` 三行即可 —— antd 主题、CSS 变量、阴影、聚焦环、图表色序会全部自动跟随。
- **只改密度**：改 `src/theme/tokens.js` 的 `space` / `fontSize` / `radius` 三组。
- **只改组件外观**：改 `src/theme/antdTheme.js`，无需碰任何页面。

---

*重构执行：UI Designer　|　日期：2026-10-03*
