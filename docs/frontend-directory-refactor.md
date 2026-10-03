# 前端目录与组件布局优化方案

> 项目：`personal-ledger-frontend`
> 分支：`refactor/frontend-directory-by-domain`
> 日期：2026-10-03
> 范围：**仅文件/目录组织与 import 路径**。业务逻辑、API 接口、样式表现零改动。

---

## 0. 任务前提校正（重要）

原任务描述中的若干前提与仓库实际情况不符，方案基于实测结果调整。**请先阅读本节再评审。**

| 原任务前提 | 实测结果 | 证据 |
|---|---|---|
| 技术栈 React + **TypeScript** + Vite | React 18 + **纯 JS/JSX** + Vite 5 | `src` 下 `.ts`/`.tsx` 文件数 = **0**；无 `tsconfig.json`；`typescript` 不在 `devDependencies`（仅 `@types/react`） |
| 验收 `npm run lint && npm run build && npm run test` | 仅 `build` 存在 | `npm run lint` → `Missing script: "lint"`；`npm run test` → `Missing script: "test"`；无 ESLint 配置文件；测试文件数 = **0** |
| `tsc --noEmit` 必须通过 | 无法执行 | TypeScript 未安装，`npx tsc` 只会拉取同名无关包 |
| P0：**消除循环依赖** | **项目本来就没有循环依赖** | 见 §1 分层图，导入图为严格 DAG；重构后仍为 0（脚本实测） |
| 遵循《前端工程化目录规范 v2》 | 仓库内**不存在**该文档 | 全仓库检索 `工程化规范\|目录规范` 命中 0 |
| P1：公共组件抽离到 `packages/ui` | 无 monorepo | `package.json` 无 `workspaces` 字段，单包工程 |

**结论**：P0 的头号事项（循环依赖）是空操作；P1 要求的工作区拆分需要引入新的构建管线，与"禁止改动构建"约束冲突且对本项目（单包 / 51 个源文件）不成比例。经确认后，本次采用**最小真实清理**方案，验收以 `npm run build` 为准。

---

## 1. 现状 → 目标结构对比

### 导入依赖分层（重构前后均无环）

```
重构前（严格 DAG，实测 0 环）        重构后（分层不变）
L0  api/request · hooks · utils · theme      L0  api/request · hooks · utils · theme
L1  api/{user,record,category,...}          L1  api/{user,record,category,...}
L2  context/AuthContext · components/ui/*   L2  context/AuthContext · components/ui/*
L3  components/* · pages/*                  L3  components/* · pages/*
L4  App.jsx                                 L4  App.jsx
L5  main.jsx                                L5  main.jsx
```

`pages/*` 与 `components/*` 同处 L3、彼此无引用，重构未改变任何依赖方向。

### 目录结构

**重构前** —— `pages/` 平铺 14 个文件，管理端与用户端混放：

```
src/
├── App.jsx
├── main.jsx
├── api/                      9 个文件，按资源域平铺
│   ├── request.js            HTTP 实例 + 拦截器
│   ├── admin.js  ai-session.js  category.js  faq.js
│   ├── membership.js  record.js  statistics.js  user.js
├── components/
│   ├── AdminRoute.jsx        路由守卫 —— 与布局、UI 混放
│   ├── AuthRoute.jsx         路由守卫
│   ├── MainLayout.jsx        应用外壳
│   └── ui/                   10 个设计系统组件
├── context/AuthContext.jsx
├── hooks/useMediaQuery.js
├── pages/                    ⚠ 14 个文件平铺
│   ├── AdminDashboard.jsx  AdminRecords.jsx  AdminUsers.jsx
│   ├── AdminFaq.jsx  AdminMembership.jsx    ← 5 个管理端
│   ├── AiChat.jsx  Categories.jsx  ChangePassword.jsx
│   ├── Dashboard.jsx  Login.jsx  Membership.jsx
│   ├── Records.jsx  Register.jsx  UserInfo.jsx
├── styles/design-tokens.css
├── theme/antdTheme.js
└── utils/format.js
```

**重构后** —— 按业务域分组，管理端 / 认证入口各自成目录：

```
src/
├── App.jsx
├── main.jsx
├── api/                      ✅ 不变（已内聚：传输层 + 资源端点）
│   ├── request.js
│   ├── admin.js  ai-session.js  category.js  faq.js
│   ├── membership.js  record.js  statistics.js  user.js
├── components/
│   ├── MainLayout.jsx        ✅ 应用外壳（单例，保留原位）
│   ├── guards/               🆕 路由守卫成对
│   │   ├── AdminRoute.jsx
│   │   └── AuthRoute.jsx
│   └── ui/                   ✅ 设计系统，不变
│       ├── AnimatedRoute.jsx  AuthLayout.jsx  EmptyState.jsx
│       ├── ListToolbar.jsx  Money.jsx  PageHeader.jsx
│       ├── SectionTitle.jsx  SkeletonCard.jsx  StatCard.jsx
│       └── index.js          唯一公共出口
├── context/AuthContext.jsx
├── hooks/useMediaQuery.js
├── pages/
│   ├── admin/                🆕 管理端
│   │   ├── AdminDashboard.jsx  AdminRecords.jsx
│   │   ├── AdminUsers.jsx  AdminFaq.jsx  AdminMembership.jsx
│   ├── auth/                 🆕 认证入口
│   │   ├── Login.jsx  Register.jsx
│   ├── AiChat.jsx            用户端核心功能，保持平铺
│   ├── Categories.jsx
│   ├── ChangePassword.jsx
│   ├── Dashboard.jsx
│   ├── Membership.jsx
│   ├── Records.jsx
│   └── UserInfo.jsx
├── styles/design-tokens.css
├── theme/antdTheme.js
└── utils/format.js
```

---

## 2. 文件级变更清单

### 2.1 目录移动（9 个文件，仅改路径）

| # | 原路径 | 新路径 | import 深度修正 |
|---|---|---|---|
| 1 | `src/pages/AdminDashboard.jsx` | `src/pages/admin/AdminDashboard.jsx` | `../` → `../../`（2 处） |
| 2 | `src/pages/AdminRecords.jsx` | `src/pages/admin/AdminRecords.jsx` | `../` → `../../`（3 处） |
| 3 | `src/pages/AdminUsers.jsx` | `src/pages/admin/AdminUsers.jsx` | `../` → `../../`（3 处） |
| 4 | `src/pages/AdminFaq.jsx` | `src/pages/admin/AdminFaq.jsx` | `../` → `../../`（2 处） |
| 5 | `src/pages/AdminMembership.jsx` | `src/pages/admin/AdminMembership.jsx` | `../` → `../../`（2 处） |
| 6 | `src/pages/Login.jsx` | `src/pages/auth/Login.jsx` | `../` → `../../`（3 处） |
| 7 | `src/pages/Register.jsx` | `src/pages/auth/Register.jsx` | `../` → `../../`（2 处） |
| 8 | `src/components/AuthRoute.jsx` | `src/components/guards/AuthRoute.jsx` | `../` → `../../`（1 处） |
| 9 | `src/components/AdminRoute.jsx` | `src/components/guards/AdminRoute.jsx` | `../` → `../../`（1 处） |

> 文件**内容**除 import 行外零改动；无重命名。

### 2.2 import 路径更新（11 个文件，无移动）

| # | 文件 | 变更 |
|---|---|---|
| 10 | `src/App.jsx` | 6 条路径改写：`./components/AuthRoute` → `./components/guards/AuthRoute`、`./components/AdminRoute` → `./components/guards/AdminRoute`、`./pages/{Login,Register}` → `./pages/auth/*`、5 个 `./pages/Admin*` → `./pages/admin/*` |
| 11 | `src/App.jsx` | 将误置于文件中部的 `import { antdTheme } from './theme/antdTheme'`（原第 52 行，位于组件定义之后）上移至 import 区，与其他 import 归拢 |
| 12 | `src/pages/Dashboard.jsx` | 7 条深路径 → 1 条 barrel |
| 13 | `src/pages/Records.jsx` | 5 条 → 1 条 |
| 14 | `src/pages/UserInfo.jsx` | 3 条 → 1 条 |
| 15 | `src/pages/Categories.jsx` | 4 条 → 1 条 |
| 16 | `src/pages/Membership.jsx` | 2 条 → 1 条 |
| 17 | `src/pages/ChangePassword.jsx` | 1 条深路径 → barrel |
| 18 | `src/pages/AiChat.jsx` | 1 条深路径 → barrel |
| 19 | `src/pages/admin/AdminMembership.jsx` | 2 条深路径 → barrel |
| 20 | `src/pages/auth/Login.jsx` | 1 条深路径 → barrel |
| 21 | `src/pages/auth/Register.jsx` | 1 条深路径 → barrel |

**统一示例**（`Dashboard.jsx`）：
```diff
- import StatCard from '../components/ui/StatCard'
- import PageHeader from '../components/ui/PageHeader'
- import SectionTitle from '../components/ui/SectionTitle'
- import EmptyState from '../components/ui/EmptyState'
- import Money from '../components/ui/Money'
- import SkeletonCard, { StatsRowSkeleton } from '../components/ui/SkeletonCard'
- import AnimatedRoute from '../components/ui/AnimatedRoute'
+ import { StatCard, PageHeader, SectionTitle, EmptyState, Money, SkeletonCard, StatsRowSkeleton, AnimatedRoute } from '../components/ui'
```

---

## 3. 改动理由

### 3.1 消除 `components/ui` 的双入口（一致性问题）

重构前，同一个模块存在**两种并行写法**，无任何规则说明何时用哪种：

- barrel 写法（4 个文件）：`AdminDashboard` `AdminRecords` `AdminUsers` `AdminFaq`
- 深路径写法（10 个文件）：`pages/Login` `pages/Records` `pages/Dashboard` 等

新人无法判断哪种是规范。已统一到 `components/ui/index.js` 这一个出口——该文件原本就带有 `// UI Components barrel export` 注释，即设计意图中的公共 API。Rollup 对 barrel re-export 可正常 tree-shaking，且**单一入口天然规避了 barrel 反向引用导致的循环依赖**（本项目 P0 关注的正是环）。

净效果：`components/ui` 的 import 语句从 **31 条降至 14 条**（14 个页面文件各恰好 1 条），双入口问题消除。

### 3.2 按业务域分组（内聚性 + 可发现性）

- **管理端 5 个页面**此前与用户端混放于平铺目录。搜索 `admin` 相关改动需逐个打开 14 个文件判断；现在 `pages/admin/` 一目了然。
- **认证页 2 个**是全站唯一不走 `MainLayout` 的页面，与应用外壳页面分离后可一眼识别出"公开路由"集合。
- **路由守卫成对**：`AuthRoute` / `AdminRoute` 逻辑高度相似（同一套 `token`/`loading` 判断，`AdminRoute` 多一层 `role !== 1`），置于 `components/guards/` 使这对文件的关联可见，也与 `components/ui/`（设计系统）在语义上区分开。

### 3.3 刻意未改动的部分

| 目录 | 决策 |
|---|---|
| `api/` | **保持不动**。已满足内聚：仅 1 个传输层（`request.js`）+ 8 个资源端点文件。强行按业务域重组（如 `api/admin/`）只会让 8 个 5~10 行的文件散落各处，降低而非提升可发现性 |
| `context/` `hooks/` `theme/` `styles/` `utils/` | 均为单文件目录或全局单例，移动无收益 |
| `components/ui/` | 设计系统，10 个组件已扁平且职责单一，无需再分组 |
| `components/MainLayout.jsx` | 应用外壳单例，保留原位 |

---

## 4. 验证结果

| 检查项 | 命令 / 方法 | 结果 |
|---|---|---|
| 相对导入可解析 | 自写脚本遍历 `src`，解析 42 文件 / **84 条**相对导入 | **0 broken** |
| 循环依赖 | 同上，DFS 三色标记 | **0 环**（与重构前一致） |
| 生产构建 | `npm run build` | ✅ 通过 |
| 产物指纹对比 | 与重构前基线比对 | 见下 |

构建产物基线 → 重构后对比（`vite build`，3708 modules transformed，两次一致）：

| 产物 | 重构前 | 重构后 | 差异 |
|---|---|---|---|
| CSS | `index-DQbloOPL.css` 12.52 kB / gzip 3.24 kB | `index-DQbloOPL.css` 12.52 kB / gzip 3.24 kB | **完全一致**（hash 未变，逐字节相同） |
| JS（raw） | 1,768.04 kB | 1,772.82 kB | +4.78 kB（+0.27%） |
| JS（gzip） | 549.20 kB | 548.62 kB | **−0.58 kB（略小）** |

**关于 JS 体积变化**：raw 增大 4.78 kB、gzip 反而减小 0.58 kB，原因是统一走 barrel 后 Rollup 生成的 re-export 中间层增加了少量 raw 代码，而该部分高度重复、在 gzip 下被折叠。实际网络传输量无变化。此差异不影响"零行为变更"的结论：本次重构未新增/删除任何依赖、未引入新模块，仅改变文件位置与 import 写法。

> 若评审认为体积**绝对值**不应有任何变化，可将页面改回深路径导入；但那样会恢复 barrel/深路径双入口问题（§3.1）。经权衡，gzip 后体积更小且换来单一入口，保留当前方案。

### 未能执行的验收项

- `npm run lint` —— 脚本不存在（`Missing script: "lint"`）
- `npm run test` —— 脚本不存在，且无测试文件
- `tsc --noEmit` —— 无 TypeScript 依赖、无 `tsconfig.json`、无 `.ts`/`.tsx` 源文件

以上三项需先引入 ESLint / 测试运行器 / TypeScript 迁移，属于工具链建设，超出"目录优化"范围。建议作为独立任务排期，见 §5。

---

## 5. 后续建议（本次未执行）

1. **引入 ESLint + Vitest**，使 CI 门禁真实可跑。仓库已有 GitHub Actions（`.github/workflows`），可在其中加 lint/test 步骤。
2. **首屏体积**：构建已提示 chunk > 500 kB（gzip 549 kB）。`App.jsx` 静态导入全部 15 个页面，`Admin*` 与 `AiChat` 被打进首屏包。改用 `React.lazy` + 路由级 `Suspense` 可显著降低首屏体积——这是当前**收益最高**的优化项，但会改变加载行为，需单独评审。
3. **是否拆 `packages/ui`**：待设计系统组件数超过 ~20、或出现第二个消费方（如 `personal-ledger-uniapp`）时再评估。当前拆分需引入 workspace 配置与独立构建管线，属过度设计。
4. **测试文件同目录（colocation）**：待测试运行器就位后执行，届时无测试文件需要迁移。