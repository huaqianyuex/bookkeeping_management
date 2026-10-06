import request from './request'

/**
 * 会员模块接口统一管理（docs/membership-plan.md §8.1）
 * 用户侧：/api/membership/**；管理侧：/api/admin/membership/**
 * 均走标准 {code, message, data} 信封（request.js 拦截器已解包为整个响应体）
 */

// 我的会员状态：{tier, tierName, expiresAt, benefits, usage{date, chat, analyze, bookkeeping}}
export const getMembershipStatus = () => request.get('/membership/status')

// 兑换码开通/续费：body {code}（服务端归一化：去空格/连字符、转大写）
export const redeemMembership = (code) => request.post('/membership/redeem', { code })

// —— 管理端 ——

// 批量生成兑换码：body {count, days, batchNo?} → {batchNo, codes[]}
export const generateCodes = (data) => request.post('/admin/membership/codes', data)

// 兑换码分页列表：params {page, size, status?}（status: 0未使用 1已使用 2已作废）
export const listCodes = (params) => request.get('/admin/membership/codes', { params })

// 作废兑换码（仅未使用可作废）
export const voidCode = (id) => request.put(`/admin/membership/codes/${id}/void`)

// 手动开通/延期会员：body {userId, days}（叠加语义：从 max(NOW, 现有到期) 起算）
export const grantMembership = (data) => request.post('/admin/membership/grant', data)
