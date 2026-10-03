/**
 * antd 主题配置
 *
 * 色板字面量集中在 ./palette.js，本文件只做映射，不再持有颜色字面量。
 * 之所以需要这一层：antd 的 theme token 不支持 CSS 变量，只能接收 JS 值。
 * 运行时 CSS 侧的 --color-* 由 palette.js 的 applyPalette() 写入 :root，
 * 因此 JS 主题与 CSS 变量由同一份 palette 派生，天然不会漂移。
 */

import { palette, withAlpha } from './palette'

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
      itemHoverBg: palette.bgSubtle,
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
      primaryShadow: `0 2px 8px ${withAlpha(palette.primary, 0.2)}`,
    },
    Input: {
      activeBorderColor: palette.primary,
      hoverBorderColor: palette.textSecondary,
    },
    Table: {
      headerBg: palette.bg,
      headerColor: palette.textSecondary,
      rowHoverBg: palette.bgSubtle,
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