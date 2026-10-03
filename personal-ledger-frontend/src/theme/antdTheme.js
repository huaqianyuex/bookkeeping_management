/**
 * antd 主题 — 与 src/styles/design-tokens.css 为同一色板的两处映射。
 * antd token 无法读取 CSS 变量，故此处以字面量维护；改色请两处同步。
 */

export const palette = {
  primary: '#1a1a2e',
  primaryDeep: '#16213e',
  primaryBg: '#f0f0ff',
  success: '#00b894',
  danger: '#e94560',
  warning: '#feca57',
  info: '#54a0ff',
  bg: '#f5f5f7',
  bgSubtle: '#fafafa',
  surface: '#ffffff',
  text: '#1a1a2e',
  textSecondary: '#636e72',
  textTertiary: '#a0a0a8',
  textDisabled: '#b2bec3',
  border: '#e5e5ea',
  borderSecondary: '#eaeaef',
}

export const antdTheme = {
  token: {
    colorPrimary: palette.primary,
    colorPrimaryBg: palette.primaryBg,
    colorBgLayout: palette.bg,
    colorBgContainer: palette.surface,
    colorBorder: palette.border,
    colorBorderSecondary: palette.borderSecondary,
    colorText: palette.text,
    colorTextSecondary: palette.textSecondary,
    borderRadius: 10,
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  components: {
    Layout: {
      siderBg: palette.surface,
      headerBg: palette.surface,
      bodyBg: palette.bg,
      triggerBg: palette.bg,
    },
    Menu: {
      itemBg: palette.surface,
      itemActiveBg: palette.primaryBg,
      itemSelectedBg: palette.primaryBg,
      itemSelectedColor: palette.primary,
      itemHoverBg: '#f8f8fa',
      itemColor: palette.textSecondary,
      itemBorderRadius: 8,
      itemMarginInline: 8,
      itemPaddingInline: 16,
    },
    Card: {
      headerBg: 'transparent',
      borderRadiusLG: 12,
    },
    Button: {
      primaryShadow: '0 2px 8px rgba(26, 26, 46, 0.2)',
    },
    Input: {
      activeBorderColor: palette.primary,
      hoverBorderColor: palette.textSecondary,
    },
    Table: {
      headerBg: '#fafafa',
      headerColor: palette.textSecondary,
      rowHoverBg: '#f8f8fa',
    },
    Tag: {
      borderRadiusSM: 6,
    },
    Empty: {
      colorTextDisabled: palette.textDisabled,
    },
    Tabs: {
      itemSelectedColor: palette.primary,
      itemHoverColor: palette.primary,
    },
  },
}
