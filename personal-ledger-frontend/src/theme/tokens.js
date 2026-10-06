/**
 * tokens.js — 设计系统**标量令牌唯一来源**（single source of truth）
 *
 * 为什么存在：与 palette.js 同一动机。此前标量令牌（圆角/间距/字号/阴影/动效/层级）
 * 的"真值"散落在两处：
 *   1. `styles/design-tokens.css` 的 :root
 *   2. `theme/antdTheme.js` 里的 JS 字面量（如 borderRadius: 10）
 * 两处必须手工保持相等，且阴影里写死了 `rgba(22, 78, 99, …)` —— 一旦改主色，
 * 阴影仍是旧色，属于静默漂移。
 *
 * 现在的链路与色板完全对称：
 *
 *   tokens.js ──► antdTheme.js   （ConfigProvider theme，JS 直接引用）
 *             └─► applyTokens() 运行时写入 :root 的 --space-* / --radius-* / …
 *                 └─► design-tokens.css 与组件内联样式消费这些变量
 *
 * 改尺寸只需改本文件一处；CSS 侧不再出现标量字面量。
 * 阴影/聚焦环由 palette 派生，因此改主色时它们自动跟随。
 */

import { palette, withAlpha } from './palette'

/** 阴影基色：slate-900。所有中性阴影共用，避免各处写死不同的黑 */
const SHADOW_RGB = '15, 23, 42'

export const tokens = {
  /* ── Spacing Scale (4pt base) ── */
  space: {
    xs: '4px',
    sm: '8px',
    md: '12px',
    base: '16px',
    lg: '20px',
    xl: '24px',
    '2xl': '32px',
    '3xl': '40px',
    '4xl': '48px',
    '5xl': '64px',
  },

  /* ── Border Radius Scale ──
   * 干净的 4/6/8/12/16/20 阶梯。此前是 6/10/12/14/18，
   * 中段 10 与 12、14 与 18 视觉上几乎不可分辨，等于四档只用了两档。
   */
  radius: {
    xs: '4px',
    sm: '6px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    '2xl': '20px',
    full: '9999px',
  },

  /* ── Font Size Scale ──
   * 去掉 17 这一档（与 16、18 都太近），并保持 20 作为页面标题。
   */
  fontSize: {
    xs: '12px',
    sm: '13px',
    base: '14px',
    md: '15px',
    lg: '16px',
    xl: '20px',
    '2xl': '24px',
    '3xl': '30px',
  },

  /* 字体栈：原先 antdTheme.js 与 design-tokens.css 各写了一份相同字符串 */
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Roboto, "Helvetica Neue", Arial, sans-serif',

  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  lineHeight: {
    tight: 1.25,
    base: 1.55,
    relaxed: 1.7,
  },

  letterSpacing: {
    tight: '-0.02em',
    normal: '0',
    wide: '0.05em',
  },

  /* ── Motion ── 统一缓动曲线，此前各处的 `ease` 是浏览器默认值 */
  transition: {
    fast: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
    base: '200ms cubic-bezier(0.4, 0, 0.2, 1)',
    slow: '300ms cubic-bezier(0.4, 0, 0.2, 1)',
    /* 进场/位移类动画用更"顺"的减速曲线 */
    slower: '420ms cubic-bezier(0.16, 1, 0.3, 1)',
  },

  /* ── Z-Index Scale ── */
  zIndex: {
    base: 0,
    dropdown: 100,
    sticky: 200,
    overlay: 300,
    modal: 400,
    toast: 500,
    fab: 900,
  },

  /* ── Layout Constants ── */
  layout: {
    siderWidth: '220px',
    siderCollapsedWidth: '64px',
    headerHeight: '56px',
    contentMaxWidth: '1200px',
  },

  /* ── Chart (Recharts 只接受 number，无法消费 CSS 变量) ── */
  chart: {
    tickFontSize: 12,
    legendFontSize: 12,
    height: 224,
    strokeWidth: 2.5,
    dotRadius: 3,
    activeDotRadius: 5,
  },
}

/**
 * 阴影：全部由同一阴影基色派生，避免各处写死不同深浅的黑。
 * primary / fab 两档由 palette 派生，改主色时自动跟随。
 */
export const shadows = {
  xs: `0 1px 2px 0 rgba(${SHADOW_RGB}, 0.04)`,
  sm: `0 1px 2px 0 rgba(${SHADOW_RGB}, 0.04), 0 1px 3px 0 rgba(${SHADOW_RGB}, 0.06)`,
  md: `0 2px 4px -1px rgba(${SHADOW_RGB}, 0.04), 0 4px 12px -2px rgba(${SHADOW_RGB}, 0.07)`,
  lg: `0 4px 8px -2px rgba(${SHADOW_RGB}, 0.05), 0 12px 24px -4px rgba(${SHADOW_RGB}, 0.09)`,
  xl: `0 8px 16px -4px rgba(${SHADOW_RGB}, 0.06), 0 24px 48px -8px rgba(${SHADOW_RGB}, 0.12)`,
  sider: `2px 0 8px rgba(${SHADOW_RGB}, 0.03)`,
  primary: `0 4px 12px ${withAlpha(palette.primary, 0.24)}`,
  primaryHover: `0 6px 18px ${withAlpha(palette.primary, 0.3)}`,
  fab: `0 6px 16px ${withAlpha(palette.primary, 0.32)}`,
  fabHover: `0 10px 28px ${withAlpha(palette.primary, 0.36)}`,
}

/** 聚焦环：键盘可达性与"编辑定位高亮"共用同一套，避免各处手写 rgba */
export const rings = {
  focus: `0 0 0 3px ${withAlpha(palette.primary, 0.22)}`,
  primary: `0 0 0 3px ${withAlpha(palette.primary, 0.3)}`,
  danger: `0 0 0 3px ${withAlpha(palette.danger, 0.22)}`,
}

/**
 * CSS 自定义属性映射。变量名与 design-tokens.css 的消费点一致。
 * 纯别名（如 --gradient-primary）留在 CSS，因为它们由其他变量推导。
 */
const cssVars = {
  /* Spacing */
  '--space-xs': tokens.space.xs,
  '--space-sm': tokens.space.sm,
  '--space-md': tokens.space.md,
  '--space-base': tokens.space.base,
  '--space-lg': tokens.space.lg,
  '--space-xl': tokens.space.xl,
  '--space-2xl': tokens.space['2xl'],
  '--space-3xl': tokens.space['3xl'],
  '--space-4xl': tokens.space['4xl'],
  '--space-5xl': tokens.space['5xl'],

  /* Radius */
  '--radius-xs': tokens.radius.xs,
  '--radius-sm': tokens.radius.sm,
  '--radius-md': tokens.radius.md,
  '--radius-lg': tokens.radius.lg,
  '--radius-xl': tokens.radius.xl,
  '--radius-2xl': tokens.radius['2xl'],
  '--radius-full': tokens.radius.full,

  /* Typography */
  '--font-family-base': tokens.fontFamily,
  '--font-size-xs': tokens.fontSize.xs,
  '--font-size-sm': tokens.fontSize.sm,
  '--font-size-base': tokens.fontSize.base,
  '--font-size-md': tokens.fontSize.md,
  '--font-size-lg': tokens.fontSize.lg,
  '--font-size-xl': tokens.fontSize.xl,
  '--font-size-2xl': tokens.fontSize['2xl'],
  '--font-size-3xl': tokens.fontSize['3xl'],
  '--font-weight-normal': String(tokens.fontWeight.normal),
  '--font-weight-medium': String(tokens.fontWeight.medium),
  '--font-weight-semibold': String(tokens.fontWeight.semibold),
  '--font-weight-bold': String(tokens.fontWeight.bold),
  '--line-height-tight': String(tokens.lineHeight.tight),
  '--line-height-base': String(tokens.lineHeight.base),
  '--line-height-relaxed': String(tokens.lineHeight.relaxed),

  /* Motion */
  '--transition-fast': tokens.transition.fast,
  '--transition-base': tokens.transition.base,
  '--transition-slow': tokens.transition.slow,
  '--transition-slower': tokens.transition.slower,

  /* Shadows */
  '--shadow-xs': shadows.xs,
  '--shadow-sm': shadows.sm,
  '--shadow-md': shadows.md,
  '--shadow-lg': shadows.lg,
  '--shadow-xl': shadows.xl,
  '--shadow-sider': shadows.sider,
  '--shadow-primary': shadows.primary,
  '--shadow-primary-hover': shadows.primaryHover,
  '--shadow-fab': shadows.fab,
  '--shadow-fab-hover': shadows.fabHover,
  '--ring-focus': rings.focus,
  '--ring-primary': rings.primary,

  /* Z-Index */
  '--z-base': String(tokens.zIndex.base),
  '--z-dropdown': String(tokens.zIndex.dropdown),
  '--z-sticky': String(tokens.zIndex.sticky),
  '--z-overlay': String(tokens.zIndex.overlay),
  '--z-modal': String(tokens.zIndex.modal),
  '--z-toast': String(tokens.zIndex.toast),
  '--z-fab': String(tokens.zIndex.fab),

  /* Layout */
  '--sider-width': tokens.layout.siderWidth,
  '--sider-collapsed-width': tokens.layout.siderCollapsedWidth,
  '--header-height': tokens.layout.headerHeight,
  '--content-max-width': tokens.layout.contentMaxWidth,
}

export { cssVars as tokensCssVars }

/**
 * 把标量令牌写入 :root。与 applyPalette() 一样，在 main.jsx 中于 React 渲染前
 * 调用一次 —— 晚于这一步渲染会导致间距/圆角/高度变量缺失，首帧布局塌陷。
 */
export function applyTokens(target) {
  const el =
    target ?? (typeof document !== 'undefined' ? document.documentElement : null)
  if (!el) return
  for (const [name, value] of Object.entries(cssVars)) {
    el.style.setProperty(name, value)
  }
}
