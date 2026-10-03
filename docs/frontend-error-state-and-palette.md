# 前端整改：错误状态缺陷修复 + 色板单一来源

> 分支：`refactor/frontend-directory-by-domain`
> 提交：`ae7b7f8`（承接 `bf9854b` 目录重构）
> 日期：2026-10-03
> 起因：`personal-ledger-frontend/AUDIT.md` 的 P1「硬编码颜色」与 P2「缺少错误状态」

---

## 0. 先复核：AUDIT.md 已过期

AUDIT.md 生成于提交 `d88b734`（前端 UI/UX 全面优化）**之前**。逐条复核后，6 条问题中 4 条已被该提交修复：

| # | AUDIT.md 记载 | 复核结论 |
|---|---|---|
| 1 | P1 表格移动端溢出 | ✅ 已修 — `Records` 有 `scroll={{x:700}}` + 列级 `responsive:['md']`；`Dashboard` 有 `scroll={isMobile?{x:300}:undefined}` |
| 2 | P1 硬编码颜色 | ⚠️ **位置已变** — `Records.jsx` 现为 0 处 hex；剩余全部集中在 `theme/antdTheme.js` 与 `Dashboard` 的图表色 |
| 3 | P2 缺少错误状态 | ❌ **仍成立，且掩盖了一个真实缺陷**（见 §1） |
| 4 | P2 缺少空状态 | ✅ 已修 — `EmptyState` 组件已存在并用于 `Records` / `Dashboard` |
| 5 | P2 侧边栏宽度固定 | ✅ 已修 — `MainLayout` 已有 `isMobile` + Drawer，移动端不渲染 Sider，宽度走 `--sider-collapsed-width` |
| 6 | P3 字体层级 | ✅ 基本已修 — `design-tokens.css` 已有 8 级字号 token 与 `.text-*` 工具类 |

因此本轮**只整改仍然成立的两项**，不对已修复项重复改动。

---

## 1. 错误状态：修复「永久卡骨架屏」缺陷

### 问题

`api/request.js` 的 axios 拦截器对 4xx / 5xx / 断网一律 `Promise.reject`。而各页面的取数函数没有 `try/catch`，`setLoading(false)` 写在 `await` 之后：

```js
// 整改前 —— Records.jsx
const fetchData = async (params) => {
  setLoading(true)
  const res = await getRecordPage(params || query)   // reject 时直接抛出
  if (res.code === 200) setData(res.data)
  setLoading(false)                                  // 永远执行不到
}
```

**后果**：任何一次请求失败，界面永久停在骨架屏，用户既看不到原因、也没有重试入口，只能刷新页面。

`Dashboard.jsx` 更严重：它用 `Promise.all` 并发 9 个请求，任意一个失败即导致整个 `fetchData` 抛错。值得注意的是，该文件趋势图部分本就写了防御分支：

```js
收入: res?.code === 200 ? Number(res.data.totalIncome) : 0,
```

这段「单个失败降级为 0」的意图，在 `Promise.all` 下**永远不可达**。

### 处理

1. **新增 `components/ui/ErrorState.jsx`** —— 常驻错误态 + 重试按钮。
   版式刻意沿用 `EmptyState` 的同一套 padding / min-height / 字号 token，
   使二者成为并列语义：**`EmptyState` = 取到了但没有数据；`ErrorState` = 没取到**。
   带 `role="alert"` + `aria-live`，满足 WCAG 2.1 AA 3.3.1。

2. **新增 `utils/error.js`** —— `extractErrorMessage()` 统一错误文案降级顺序：
   后端 `message` → HTTP 状态码 → 网络中断 → 兜底文案。
   替代原先散落 5 处的 `error?.response?.data?.message || '请求失败…'`。

3. **五个页面改为 `try / catch / finally`** —— 保证 `setLoading(false)` 必定执行：
   `Records`、`Dashboard`、`Categories`、`AdminUsers`、`AdminRecords`。

4. **`Dashboard` 趋势图改用 `Promise.allSettled`** —— 三个核心请求（决定整页能否渲染）
   仍用 `Promise.all`，任一失败进入错误态；六个趋势请求改为 `allSettled`，
   使上述既有的降级分支真正生效，单月失败不再拖垮整页。

---

## 2. 色板：单一来源

### 问题

同一套色板在两处各存一份字面量，`theme/antdTheme.js` 的文件头注释即自述这一点：

> antd token 无法读取 CSS 变量，故此处以字面量维护；**改色请两处同步**

此外 `antdTheme.js` 内部还有 4 处绕开 `palette` 对象的内联重复色值，
`Dashboard.jsx` 的 `PIE_COLORS` 也是 10 个独立 hex。改一次主题要动三个文件。

### 处理

新建 `src/theme/palette.js` 作为**唯一色板来源**，并确立单向数据流：

```
palette.js ──┬──► antdTheme.js        （ConfigProvider theme，直接引用 JS 值）
             │
             └──► applyPalette()      （main.jsx 渲染前写入 :root 的 --color-*）
                        │
                        └──► design-tokens.css 与组件内联样式消费 var(--color-*)
```

- `design-tokens.css` 移除 **29 处**颜色字面量，仅保留推导别名
  （`--color-income` / `--color-expense` / `--gradient-primary`，它们由其他变量计算，无第二份真值）
- `antdTheme.js` 移除 4 处内联重复色值；`Button.primaryShadow` 改由
  `withAlpha(palette.primary, 0.2)` 推导，随主色自动跟随
- `Dashboard.jsx` 的 `PIE_COLORS` → `palette.chartColors`（保持原有色序，观感不变）
- `main.jsx` 在 `createRoot().render()` **之前**调用 `applyPalette()`，
  确保首帧变量已就位，否则颜色会回退为浏览器默认色

### 为什么不让 CSS 反向生成 JS

若以 CSS 为唯一源、JS 运行时 `getComputedStyle` 反读，则 `antdTheme` 的取值变成
运行时依赖：失去静态可分析性，且每次取值触发样式重算。当前方案让 `palette`
保持为一个普通静态对象，可被 grep、可被静态审阅，同时 JS 主题与 CSS 变量
由同一对象派生，**一致性由构造保证，而非靠人工同步**。

### 已知遗留

`design-tokens.css` 的阴影 token 中仍有 9 处 `rgba(...)`，如
`--shadow-xs: 0 1px 2px rgba(15, 23, 42, 0.03)`。它们属于「高度/投影」域
而非调色板域，且与 `--color-primary` 耦合（如 `--shadow-fab`）。
本次未纳入统一范围，以免牵连过多；若日后换主色，需一并复核这 9 处。

---

## 3. 验证

| 检查项 | 方法 | 结果 |
|---|---|---|
| 生产构建 | `npm run build` | ✅ 通过，3711 modules |
| 导入完整性 | 遍历 `src`，解析 93 条相对导入 | ✅ 0 broken |
| 循环依赖 | DFS 三色标记 | ✅ 0 环 |
| 颜色字面量收敛 | 全 `src` 检索 `#rrggbb` | ✅ 仅 `theme/palette.js`（29 处） |
| **错误态端到端** | 浏览器注入 `/api` 网络故障 → 观察页面 | ✅ 进入错误态：含「网络连接异常，请检查网络后重试」+ 重试按钮，**无残留骨架屏** |
| **重试可恢复** | 恢复网络后点击「重试」 | ✅ 正常回到数据（实测 `共 9 条记录`，含 `2026-09-25 支出 餐饮 -¥11.00`） |
| **调色板无回归** | `getComputedStyle` 校验 12 个 CSS 变量 | ✅ `--color-primary: #164e63` 等全部与原值一致 |
| **实际渲染元素** | 抽查计算样式 | ✅ 卡片边框 `rgb(226,232,240)`、primary 按钮 `rgb(22,78,99)`、表格头 `rgb(248,250,252)`、支出金额语义色 `rgb(225,29,72)` 均与整改前一致 |

浏览器验证期间控制台无新增错误；仅有两条整改前既已存在的告警
（React Router v7 future flag 提示、`EmptyState` 中 antd `imageStyle` 弃用提示）。

---

## 4. 未处理项

1. **`npm run lint` / `npm run test` 仍不存在**，本项目无 ESLint 配置、无测试文件。
   本轮验证依赖 `npm run build` + 浏览器端到端实测。
2. **首屏体积未处理**：`App.jsx` 静态导入全部 15 个页面，
   管理端与 `AiChat` 均进入首屏包（gzip 约 549 kB，Vite 已就此告警）。
   改 `React.lazy` + 路由级 `Suspense` 收益最大，但会改变加载行为，需单独评审。
3. **9 处阴影色 rgba 未纳入调色板**，见 §2「已知遗留」。