import { get, post } from './request'

/**
 * 充值模块 API（套餐直购 + 模拟支付）
 * 金额/天数全部服务端定价，客户端只传套餐 ID；状态流转只能由支付回调/管理审批推进。
 */

/** 套餐目录（服务端唯一定价源） */
export const getRechargePlans = () => get('/recharge/plans')

/** 创建充值订单：只传 planId，返回订单快照（15 分钟内有效） */
export const createRechargeOrder = (planId) => post('/recharge/orders', { planId })

/** 模拟收银台支付：result 仅演示用（success/fail），真实渠道接入后由回调替代 */
export const mockPayOrder = (orderNo, result = 'success') =>
	post(`/recharge/orders/${orderNo}/mock-pay`, { result })

/** 取消待支付订单（关闭收银台时调用，释放进行中订单名额） */
export const cancelRechargeOrder = (orderNo) => post(`/recharge/orders/${orderNo}/cancel`)

/** 我的充值记录（分页） */
export const listMyRechargeOrders = (params) => get('/recharge/orders', params)
