import request from './request'

/**
 * 充值模块接口（管理端审批）
 * 管理侧：/api/admin/recharges/**，均走标准 {code, message, data} 信封。
 * 订单状态只能由支付回调与审批端点推进，前端无任何改单能力（安全审批链路的边界）。
 */

// 充值订单分页列表：params {page, size, status?, keyword?}
// status: 0待支付 1待审批 2已支付 3已拒绝 4已取消 5已关闭；keyword 匹配用户名/订单号/套餐名
export const listRechargeOrders = (params) => request.get('/admin/recharges', { params })

// 通过待审批订单：放行到账（同事务延期会员）
export const approveRecharge = (id, note) =>
  request.post(`/admin/recharges/${id}/approve`, note ? { note } : {})

// 拒绝待审批订单：reason 必填（写入订单与审计）
export const rejectRecharge = (id, reason) =>
  request.post(`/admin/recharges/${id}/reject`, { reason })

// 订单审计轨迹（创建/支付/风控/审批/延期，append-only）
export const getRechargeLogs = (id) => request.get(`/admin/recharges/${id}/logs`)
