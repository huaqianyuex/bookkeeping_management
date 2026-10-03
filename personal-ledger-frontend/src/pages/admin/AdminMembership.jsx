import { Card, Typography } from 'antd'
import { PageHeader, AnimatedRoute } from '../../components/ui'

const { Text } = Typography

/**
 * 兑换码管理（管理端）— 页面骨架（实装规格：docs/membership-plan.md §8.4，照 AdminFaq 页面模式）
 *
 * TODO: ListToolbar（Button「生成兑换码」打开 Modal + Select 状态筛选 全部/未使用/已使用/已作废）
 * TODO: Table（rowKey=id, scroll={{x:720}}）：ID(md) / 兑换码(.money 等宽 4-4-4-4 分组) / 天数 / 状态 Tag
 *       （0=default 1=success 2=error）/ 批次号(md) / 核销用户(md) / 核销时间(formatDateTime, md) / 操作(未使用→Popconfirm 作废)
 * TODO: 生成 Modal（count InputNumber 1-500 默认 10 + days InputNumber 默认 30）→ generateCodes
 *       → 结果 Modal：TextArea 只读逐行展示纯码，便于整批复制；刷新表格
 * TODO: 数据 listCodes({page, size, status})；作废 voidCode(id)（Popconfirm 确认）
 */
export default function AdminMembership() {
  return (
    <AnimatedRoute>
      <PageHeader title="会员管理" />
      <Card variant="borderless" className="card-base">
        <Text type="secondary">
          兑换码管理待实装：生成 / 列表 / 作废（规格见 docs/membership-plan.md §8.4，接口见 src/api/membership.js）
        </Text>
      </Card>
    </AnimatedRoute>
  )
}
