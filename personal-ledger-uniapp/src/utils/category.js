// 分类功能色板：与 theme.css 的 --cat-* 七色一一对应，按分类 id 取色，
// 同分类恒同色。所有页面统一从这里取色，保证跨页色彩编码一致。
const PALETTE = ['yellow', 'pink', 'blue', 'orange', 'green', 'purple', 'gray']

export const catColorIndex = (id) => Math.abs(Number(id) || 0) % PALETTE.length

/** 分类底色（粉彩） */
export const catColorVar = (id) => `var(--cat-${PALETTE[catColorIndex(id)]})`

/** 分类前景/条形色（深） */
export const catColorDeepVar = (id) => `var(--cat-${PALETTE[catColorIndex(id)]}-deep)`
