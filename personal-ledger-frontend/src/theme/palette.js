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
 * 色板：Slate Cyan & Teal — 低饱和、高可信度的财务质感。
 */

/** #164e63 → '22, 78, 99'；供 withAlpha() 复用 */
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
  /* Primary — Slate Cyan / Deep Teal */
  primary: '#164e63',
  primaryDeep: '#0f3846',
  primaryLight: '#0e7490',
  primaryBg: '#ecfeff',

  /* Success / Income */
  success: '#059669',
  successLight: '#10b981',
  successBg: 'rgba(5, 150, 105, 0.08)',

  /* Danger / Expense */
  danger: '#e11d48',
  dangerLight: '#f43f5e',
  dangerBg: 'rgba(225, 29, 72, 0.08)',

  /* Warning */
  warning: '#d97706',
  warningLight: '#f59e0b',
  warningBg: 'rgba(217, 119, 6, 0.08)',

  /* Info */
  info: '#0284c7',
  infoLight: '#38bdf8',
  infoBg: 'rgba(2, 132, 199, 0.08)',

  /* Background layers */
  bg: '#f8fafc',
  bgSubtle: '#f1f5f9',

  /* Surface */
  surface: '#ffffff',
  surfaceElevated: '#ffffff',

  /* Text hierarchy */
  text: '#0f172a',
  textSecondary: '#475569',
  textTertiary: '#94a3b8',
  textInverse: '#ffffff',
  textDisabled: '#cbd5e1',

  /* Border */
  border: '#e2e8f0',
  borderSecondary: '#f1f5f9',
  borderFocus: '#164e63',
}

/**
 * 图表扩展色：语义色（primary/danger/info/warning/success）之外的补充色轮。
 * 仅供图表消费，不参与 --color-* 注入。
 */
export const chartExtras = {
  violet: '#8b5cf6',
  teal: '#0d9488',
  orange: '#f97316',
  slate: '#64748b',
}

/**
 * 分类图表色序：前 5 档取语义色锚定，后 5 档为扩展色。
 * 保持既有顺序以免改变已上线图表的观感。
 */
export const chartColors = [
  palette.primary,
  palette.danger,
  palette.info,
  palette.warning,
  palette.success,
  chartExtras.violet,
  chartExtras.teal,
  chartExtras.orange,
  chartExtras.slate,
  palette.textTertiary,
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
  '--color-success': palette.success,
  '--color-success-light': palette.successLight,
  '--color-success-bg': palette.successBg,
  '--color-danger': palette.danger,
  '--color-danger-light': palette.dangerLight,
  '--color-danger-bg': palette.dangerBg,
  '--color-warning': palette.warning,
  '--color-warning-light': palette.warningLight,
  '--color-warning-bg': palette.warningBg,
  '--color-info': palette.info,
  '--color-info-light': palette.infoLight,
  '--color-info-bg': palette.infoBg,
  '--color-bg': palette.bg,
  '--color-bg-subtle': palette.bgSubtle,
  '--color-surface': palette.surface,
  '--color-surface-elevated': palette.surfaceElevated,
  '--color-text': palette.text,
  '--color-text-secondary': palette.textSecondary,
  '--color-text-tertiary': palette.textTertiary,
  '--color-text-inverse': palette.textInverse,
  '--color-text-disabled': palette.textDisabled,
  '--color-border': palette.border,
  '--color-border-secondary': palette.borderSecondary,
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