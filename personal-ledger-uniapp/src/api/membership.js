import { get, post } from './request'

/**
 * 会员模块接口（用户侧 /api/membership/**，标准 {code, message, data} 信封）
 *
 * status 出参 data：
 *   { tier, tierName, expiresAt,
 *     benefits: { dailyChat, concurrency, dailyAnalyze, dailyBookkeeping, premiumModel },
 *     usage: { date, chat: {used, limit}, analyze: {used, limit}, bookkeeping: {used, limit} } }
 * 权益数值唯一来源为后端 MEMBERSHIP_PLANS，页面动态渲染、不硬编码额度。
 */

// 我的会员状态：等级 + 到期时间 + 今日用量 + 权益矩阵
export const getMembershipStatus = () => get('/membership/status')

// 兑换码开通/续费：body {code}（服务端归一化：去空格/连字符、转大写）
export const redeemMembership = (code) => post('/membership/redeem', { code })
