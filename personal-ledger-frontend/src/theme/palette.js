/**
 * palette.js — 设计系统**唯一色板来源**（single source of truth）
 *
 * 为什么存在：antd 的 theme token 无法读取 CSS 自定义属性，因此历史上同一套色板
 * 在 `styles/design-tokens.css` 和 `theme/antdTheme.js` 各存了一份字面量，
 * 改色必须手工同步两处（易漂移）。本文件把字面量收敛到一处：
 *
 *   palette.js ──► antdTheme.js   （ConfigProvider theme，JS 直接引用）
 *              └─► applyPalette() 运行时写入 :root 的 --color-* 自定义属性
 *                  └─► design-tokens.css 与组件内联样式消费这些变量
 *
 * 改色只需改本文件一处；CSS 侧不再出现颜色字面量。
 *
 * ── 色板说明 ──────────────────────────────────────────────────────────
 * Slate Cyan & Teal：低饱和、高可信度的财务质感，主色为青（cyan 系），
 * 与收入绿（emerald）/ 支出红（rose）在色相上明确分离，避免语义混淆。
 *
 * 本轮校准的三个要点：
 *   1. 主色从 cyan-900(#164e63，接近黑) 提到 cyan-700，按钮不再压得发闷，
 *      同时白字对比度 5.4:1 仍满足 WCAG AA。
 *   2. textTertiary 从 #94a3b8（白底 2.6:1，**不达 AA**）提到 #64748b（4.7:1）。
 *      该色被大量用于表格辅助信息与小字注释，是原先最实际的可用性缺陷。
 *   3. 新增 accent（violet）语义位。info(sky) 与新的 primary(cyan) 色相仅差 8°，
 *      两者在选择/统计场景中难以区分，因此需要第四个互不冲突的强调色位，
 *      用于「管理员」这类角色标识与多分类计数卡片。
 */

/** #0e7490 → '14, 116, 144'；供 withAlpha() 复用 */
function hexToRgbTriplet(hex) {
  const h = hex.replace('#', '')
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  const int = parseInt(full, 16)
  return `${(int >> 16) & 255}, ${(int >> 8) & 255}, ${int & 255}`
}

/** 用调色板里的色值生成 rgba，避免在别处再写死一份色值 */
export function withAlpha(hex, alpha) {
  return `rgba(${hexToRgbTriplet(hex)}, ${alpha})`
}

export const palette = {
  /* Primary — Cyan / Deep Teal */
  primary: '#0e7490',
  primaryDeep: '#155e75',
  primaryLight: '#0891b2',
  primaryBg: '#ecfeff',
  primaryBorder: '#a5f3fc',
  primarySoft: 'rgba(14, 116, 144, 0.08)',

  /* Success / Income
   * 用 emerald-700 而非 -600：收入金额会在表格里以 14px 呈现，
   * -600 的白底对比只有 3.77:1，达不到 WCAG AA 的 4.5:1；-700 为 5.48:1。
   * 账本应用里"收入的绿"是阅读频次最高的文字之一，值得为它加深一档。 */
  success: '#047857',
  successLight: '#10b981',
  successBg: 'rgba(4, 120, 87, 0.08)',
  successBorder: '#a7f3d0',

  /* Danger / Expense —— #e11d48 白底 4.70:1，已满足 AA，保持不动 */
  danger: '#e11d48',
  dangerLight: '#f43f5e',
  dangerBg: 'rgba(225, 29, 72, 0.08)',
  dangerBorder: '#fecdd3',

  /* Warning
   * 白底 #d97706 只有 3.19:1，只在 >=24px 时才勉强过 3:1；
   * 加深到 amber-700 得 5.02:1，小字号（标签、图标）也能安全使用。 */
  warning: '#b45309',
  warningLight: '#f59e0b',
  warningBg: 'rgba(180, 83, 9, 0.08)',
  warningBorder: '#fde68a',

  /* Info — sky
   * 本项目中 info 只用于 24px 统计值、图表填充与装饰圆点，
   * 从不作为小字号正文，因此保留 -600（4.10:1 已满足大字号 3:1）。
   * 不再加深，否则会与同为青蓝系的 primary 撞色。 */
  info: '#0284c7',
  infoLight: '#38bdf8',
  infoBg: 'rgba(2, 132, 199, 0.08)',
  infoBorder: '#bae6fd',

  /* Accent — violet，第四个互不冲突的强调位（角色标识 / 多分类计数） */
  accent: '#7c3aed',
  accentLight: '#8b5cf6',
  accentBg: 'rgba(124, 58, 237, 0.08)',
  accentBorder: '#ddd6fe',

  /* Background layers */
  bg: '#f8fafc',
  bgSubtle: '#f1f5f9',

  /* Surface */
  surface: '#ffffff',
  surfaceElevated: '#ffffff',

  /* Overlay — 弹层遮罩（Drawer / 移动端侧边栏 / 命令面板） */
  overlay: 'rgba(15, 23, 42, 0.45)',

  /* On-brand：叠在主色渐变之上的白系层次（登录页品牌区）
   * 注意这组值不能随意调淡 —— 品牌区承载正文（副标题 15px、功能标签 13px），
   * 必须满足 WCAG AA 4.5:1。经计算，在 gradient-brand 最亮的 #0e7490 端：
   *   onBrandText 0.92 → 4.8:1 ✓   onBrandTextStrong 1.0 → 5.4:1 ✓
   * 若把 onBrandText 降到 0.78 则只有 3.9:1，不达标。 */
  onBrandFaint: 'rgba(255, 255, 255, 0.04)',
  onBrandWeak: 'rgba(255, 255, 255, 0.08)',
  onBrandSoft: 'rgba(255, 255, 255, 0.14)',
  onBrandLine: 'rgba(255, 255, 255, 0.18)',
  onBrandText: 'rgba(255, 255, 255, 0.92)',
  onBrandTextStrong: '#ffffff',

  /* Text hierarchy */
  text: '#0f172a',
  textSecondary: '#475569',
  textTertiary: '#64748b',
  textInverse: '#ffffff',
  textDisabled: '#cbd5e1',

  /* Border */
  border: '#e2e8f0',
  borderSecondary: '#f1f5f9',
  borderStrong: '#cbd5e1',
  borderFocus: '#0e7490',
}

/**
 * 图表扩展色：语义色（primary/danger/info/warning/success/accent）之外的补充色轮。
 * 仅供图表消费，不参与 --color-* 注入。
 */
export const chartExtras = {
  violet: '#8b5cf6',
  teal: '#0d9488',
  orange: '#f97316',
  slate: '#64748b',
}

/**
 * 分类图表色序。
 *
 * 为什么调整顺序：原顺序为 [primary, danger, info, warning, success, …]，
 * 其中 primary 是接近黑的 cyan-900，与第 3 位的 info(sky-600) 靠明度差勉强分开。
 * 主色提亮到 cyan-700 后两者仅差 8° 色相，在环形图里会糊成一片。
 * 现按"相邻两色色相尽量远离"重排，避免任何两个相邻扇区撞色。
 */
export const chartColors = [
  palette.primary, // cyan
  palette.warning, // amber
  palette.accent, // violet
  palette.success, // emerald
  palette.danger, // rose
  palette.info, // sky
  chartExtras.orange,
  chartExtras.teal,
  chartExtras.violet,
  chartExtras.slate,
]

/**
 * CSS 自定义属性映射。变量名必须与 design-tokens.css 中的消费点保持一致。
 * 纯别名（如 --color-income、--gradient-primary）留在 CSS，因为它们由其他变量推导。
 */
const cssVars = {
  '--color-primary': palette.primary,
  '--color-primary-deep': palette.primaryDeep,
  '--color-primary-light': palette.primaryLight,
  '--color-primary-bg': palette.primaryBg,
  '--color-primary-border': palette.primaryBorder,
  '--color-primary-soft': palette.primarySoft,
  '--color-success': palette.success,
  '--color-success-light': palette.successLight,
  '--color-success-bg': palette.successBg,
  '--color-success-border': palette.successBorder,
  '--color-danger': palette.danger,
  '--color-danger-light': palette.dangerLight,
  '--color-danger-bg': palette.dangerBg,
  '--color-danger-border': palette.dangerBorder,
  '--color-warning': palette.warning,
  '--color-warning-light': palette.warningLight,
  '--color-warning-bg': palette.warningBg,
  '--color-warning-border': palette.warningBorder,
  '--color-info': palette.info,
  '--color-info-light': palette.infoLight,
  '--color-info-bg': palette.infoBg,
  '--color-info-border': palette.infoBorder,
  '--color-accent': palette.accent,
  '--color-accent-light': palette.accentLight,
  '--color-accent-bg': palette.accentBg,
  '--color-accent-border': palette.accentBorder,
  '--color-bg': palette.bg,
  '--color-bg-subtle': palette.bgSubtle,
  '--color-surface': palette.surface,
  '--color-surface-elevated': palette.surfaceElevated,
  '--color-overlay': palette.overlay,
  '--color-on-brand-faint': palette.onBrandFaint,
  '--color-on-brand-weak': palette.onBrandWeak,
  '--color-on-brand-soft': palette.onBrandSoft,
  '--color-on-brand-line': palette.onBrandLine,
  '--color-on-brand-text': palette.onBrandText,
  '--color-on-brand-text-strong': palette.onBrandTextStrong,
  '--color-text': palette.text,
  '--color-text-secondary': palette.textSecondary,
  '--color-text-tertiary': palette.textTertiary,
  '--color-text-inverse': palette.textInverse,
  '--color-text-disabled': palette.textDisabled,
  '--color-border': palette.border,
  '--color-border-secondary': palette.borderSecondary,
  '--color-border-strong': palette.borderStrong,
  '--color-border-focus': palette.borderFocus,
}

export { cssVars as paletteCssVars }

/**
 * 把色板写入 :root，使 CSS 与组件内联样式都能消费 var(--color-*)。
 * 在 main.jsx 中于 React 渲染前调用一次，避免首帧变量缺失。
 */
export function applyPalette(target) {
  const el =
    target ?? (typeof document !== 'undefined' ? document.documentElement : null)
  if (!el) return
  for (const [name, value] of Object.entries(cssVars)) {
    el.style.setProperty(name, value)
  }
}
