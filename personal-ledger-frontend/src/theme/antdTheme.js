/**
 * antd 主题配置
 *
 * 色板字面量集中在 ./palette.js，标量（圆角/字号/阴影/动效）集中在 ./tokens.js，
 * 本文件只做「设计令牌 → antd token 名」的映射，不持有任何字面量。
 * 之所以需要这一层：antd 的 theme token 不支持 CSS 变量，只能接收 JS 值。
 *
 * 覆盖原则：只配置本项目**实际使用**的组件，避免堆砌未验证的配置项。
 * antd 会忽略不认识的 key，因此多写不会报错，但仍以可维护为先。
 */

import { palette, withAlpha } from './palette'
import { tokens, shadows } from './tokens'

export const antdTheme = {
  token: {
    /* ── 品牌色 ── */
    colorPrimary: palette.primary,
    colorPrimaryHover: palette.primaryDeep,
    colorPrimaryActive: '#0f4c5c',
    colorPrimaryBg: palette.primaryBg,
    colorPrimaryBgHover: withAlpha(palette.primary, 0.12),
    colorPrimaryBorder: palette.primaryBorder,
    colorPrimaryText: palette.primary,

    /* ── 语义色 ──
     * 关键：把 antd 的语义色统一到自定义色板。
     * 此前 <Tag color="success"> 走的是 antd 默认绿 #52c41a，而 <Money> 走的是
     * --color-success(#059669)，同一行表格里出现两种绿。对齐后预设色标签
     * （success / error / warning / processing）自动使用调色板色值。
     */
    colorSuccess: palette.success,
    colorSuccessHover: '#046c4e',
    colorSuccessActive: '#065f46',
    colorSuccessBg: palette.successBg,
    colorSuccessBorder: palette.successBorder,
    colorSuccessText: palette.success,

    colorError: palette.danger,
    colorErrorHover: '#be123c',
    colorErrorActive: '#9f1239',
    colorErrorBg: palette.dangerBg,
    colorErrorBorder: palette.dangerBorder,
    colorErrorText: palette.danger,

    colorWarning: palette.warning,
    colorWarningHover: '#92400e',
    colorWarningActive: '#78350f',
    colorWarningBg: palette.warningBg,
    colorWarningBorder: palette.warningBorder,
    colorWarningText: palette.warning,

    colorInfo: palette.info,
    colorInfoHover: '#0369a1',
    colorInfoActive: '#075985',
    colorInfoBg: palette.infoBg,
    colorInfoBorder: palette.infoBorder,
    colorInfoText: palette.info,

    /* ── 文本层级 ── */
    colorText: palette.text,
    colorTextHeading: palette.text,
    colorTextSecondary: palette.textSecondary,
    colorTextTertiary: palette.textTertiary,
    colorTextQuaternary: '#94a3b8',
    colorTextDescription: palette.textTertiary,
    colorTextPlaceholder: '#94a3b8',
    colorTextDisabled: palette.textDisabled,
    colorTextLabel: palette.text,
    colorIcon: palette.textTertiary,
    colorIconHover: palette.textSecondary,
    colorLink: palette.primary,
    colorLinkHover: palette.primaryDeep,

    /* ── 背景层 ── */
    colorBgLayout: palette.bg,
    colorBgContainer: palette.surface,
    colorBgElevated: palette.surfaceElevated,
    colorBgContainerDisabled: palette.bgSubtle,
    colorBgTextHover: palette.bgSubtle,
    colorBgTextActive: palette.bgSubtle,
    colorBgSpotlight: '#1e293b',

    /* ── 填充色（滑动条/表头/hover 层） ── */
    colorFill: 'rgba(15, 23, 42, 0.06)',
    colorFillSecondary: 'rgba(15, 23, 42, 0.04)',
    colorFillTertiary: 'rgba(15, 23, 42, 0.03)',
    colorFillQuaternary: 'rgba(15, 23, 42, 0.02)',
    colorFillContent: 'rgba(15, 23, 42, 0.04)',
    colorFillContentHover: 'rgba(15, 23, 42, 0.06)',
    colorFillAlter: palette.bgSubtle,

    /* ── 描边 ── */
    colorBorder: palette.border,
    colorBorderSecondary: palette.borderSecondary,
    colorSplit: palette.border,

    /* ── 圆角 / 尺寸 ── */
    borderRadius: 8, // = tokens.radius.md
    borderRadiusXS: 4, // = tokens.radius.xs
    borderRadiusSM: 6, // = tokens.radius.sm
    borderRadiusLG: 12, // = tokens.radius.lg

    controlHeightLG: 44, // 统一「大号控件」高度，此前各地手写 40/44/48 三种

    /* ── 聚焦环 ── 与 CSS 侧 --ring-focus 保持同一视觉 */
    controlOutline: withAlpha(palette.primary, 0.14),
    controlOutlineWidth: 3,

    /* ── 字体 ── */
    fontFamily: tokens.fontFamily,
    fontSize: 14,
    fontSizeSM: 13,
    fontSizeLG: 16,
    fontSizeXL: 20,
    fontWeightStrong: 600,
    lineHeight: 1.55,
    lineHeightSM: 1.5,
    lineHeightLG: 1.4,

    /* ── 阴影 ── */
    boxShadow: shadows.md,
    boxShadowSecondary: shadows.lg,
    boxShadowTertiary: shadows.sm,

    /* ── 动效 ── */
    motionDurationFast: '0.15s',
    motionDurationMid: '0.2s',
    motionDurationSlow: '0.3s',
    motionEaseInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },

  components: {
    /* ── 骨架 ── */
    Layout: {
      siderBg: palette.surface,
      headerBg: palette.surface,
      bodyBg: palette.bg,
      triggerBg: palette.bg,
    },

    /* ── 导航 ── */
    Menu: {
      itemBg: 'transparent',
      itemColor: palette.textSecondary,
      itemHoverBg: palette.bgSubtle,
      itemHoverColor: palette.text,
      itemActiveBg: palette.primaryBg,
      itemSelectedBg: palette.primaryBg,
      itemSelectedColor: palette.primary,
      itemBorderRadius: tokens.radius.md,
      itemMarginInline: 8,
      itemMarginBlock: 4,
      itemPaddingInline: 12,
      itemHeight: 36,
      subMenuItemBg: 'transparent',
      groupTitleColor: palette.textTertiary,
      groupTitleFontSize: 12,
      iconSize: 16,
    },

    /* ── 卡片 ── */
    Card: {
      headerBg: 'transparent',
      headerFontSize: 16,
      headerFontSizeSM: 14,
      borderRadiusLG: tokens.radius.lg,
      actionsBg: 'transparent',
    },

    /* ── 按钮 ── */
    Button: {
      fontWeight: 500,
      primaryShadow: `0 1px 2px ${withAlpha(palette.primary, 0.18)}`,
      dangerShadow: `0 1px 2px ${withAlpha(palette.danger, 0.18)}`,
      defaultShadow: 'none',
      defaultBorderColor: palette.border,
      defaultColor: palette.text,
      textHoverBg: palette.bgSubtle,
      linkHoverBg: 'transparent',
      paddingInline: 16,
    },

    /* ── 表单控件 ──
     * hoverBorderColor 原为 textSecondary(#475569)，比 focus 态还重，
     * 视觉上"悬停比聚焦更强调"，这里改成主色的浅色描边。
     */
    Input: {
      activeBorderColor: palette.primary,
      hoverBorderColor: palette.primaryBorder,
      activeShadow: `0 0 0 3px ${withAlpha(palette.primary, 0.12)}`,
      errorActiveShadow: `0 0 0 3px ${withAlpha(palette.danger, 0.12)}`,
      warningActiveShadow: `0 0 0 3px ${withAlpha(palette.warning, 0.12)}`,
      addonBg: palette.bgSubtle,
      colorBgContainer: palette.surface,
    },

    InputNumber: {
      activeBorderColor: palette.primary,
      hoverBorderColor: palette.primaryBorder,
      activeShadow: `0 0 0 3px ${withAlpha(palette.primary, 0.12)}`,
      colorBgContainer: palette.surface,
    },

    Select: {
      optionSelectedBg: palette.primaryBg,
      optionSelectedColor: palette.primary,
      optionSelectedFontWeight: 600,
      optionActiveBg: palette.bgSubtle,
      optionPadding: '6px 12px',
      selectorBg: palette.surface,
      clearBg: palette.surface,
      borderRadius: tokens.radius.md,
    },

    DatePicker: {
      activeBorderColor: palette.primary,
      hoverBorderColor: palette.primaryBorder,
      activeShadow: `0 0 0 3px ${withAlpha(palette.primary, 0.12)}`,
      cellHoverBg: palette.bgSubtle,
      cellActiveWithRangeBg: palette.primaryBg,
      todayBorder: palette.primary,
      addonBg: palette.bgSubtle,
    },

    /* ── 数据展示 ── */
    Table: {
      headerBg: palette.bgSubtle,
      headerColor: palette.textSecondary,
      headerSplitColor: 'transparent',
      headerBorderRadius: tokens.radius.md,
      borderColor: palette.border,
      rowHoverBg: withAlpha(palette.primary, 0.04),
      /* size="middle" 走 MD 档，因此要覆盖 MD 而非基础值 */
      cellPaddingBlockMD: 12,
      cellPaddingInlineMD: 16,
      cellPaddingBlockSM: 8,
      cellPaddingInlineSM: 12,
      footerBg: 'transparent',
    },

    Tag: {
      defaultBg: palette.bgSubtle,
      defaultColor: palette.textSecondary,
      borderRadiusSM: tokens.radius.sm,
      fontSizeSM: 12,
    },

    Tabs: {
      itemColor: palette.textSecondary,
      itemHoverColor: palette.primaryDeep,
      itemSelectedColor: palette.primary,
      itemActiveColor: palette.primary,
      inkBarColor: palette.primary,
      titleFontSize: 14,
      titleFontSizeLG: 15,
      horizontalItemPadding: '10px 0',
      horizontalItemGutter: 24,
    },

    Descriptions: {
      labelColor: palette.textSecondary,
      contentColor: palette.text,
      titleColor: palette.text,
      itemPaddingBottom: 16,
    },

    Empty: {
      colorTextDisabled: palette.textDisabled,
    },

    Skeleton: {
      gradientFromColor: 'rgba(15, 23, 42, 0.05)',
      gradientToColor: 'rgba(15, 23, 42, 0.02)',
      blockRadius: tokens.radius.md,
    },

    /* ── 弹层 ── */
    Modal: {
      contentBg: palette.surface,
      headerBg: 'transparent',
      titleColor: palette.text,
      titleFontSize: 16,
      footerBg: 'transparent',
      borderRadiusLG: tokens.radius.xl,
    },

    Drawer: {
      colorBgElevated: palette.surface,
      footerPaddingBlock: 12,
      footerPaddingInline: 16,
    },

    Dropdown: {
      paddingBlock: 6,
      groupTitleColor: palette.textTertiary,
      groupTitleFontSize: 12,
    },

    Tooltip: {
      colorBgSpotlight: '#1e293b',
      borderRadius: tokens.radius.md,
    },

    Pagination: {
      itemBg: 'transparent',
      itemSize: 32,
      itemSizeSM: 24,
      itemActiveBg: palette.primaryBg,
      itemActiveBgDisabled: palette.bgSubtle,
      itemLinkColor: palette.textSecondary,
      itemLinkColorHover: palette.primary,
      itemInputBg: palette.surface,
    },

    /* ── 反馈 ── */
    Message: {
      contentBg: palette.surface,
      contentPadding: '10px 16px',
      borderRadiusLG: tokens.radius.lg,
    },

    Notification: {
      borderRadiusLG: tokens.radius.lg,
    },

    Form: {
      labelColor: palette.text,
      labelFontSize: 14,
      labelRequiredMarkColor: palette.danger,
      itemMarginBottom: 20,
      verticalLabelPadding: '0 0 6px',
    },

    Checkbox: {
      borderRadiusSM: tokens.radius.xs,
    },
  },
}
