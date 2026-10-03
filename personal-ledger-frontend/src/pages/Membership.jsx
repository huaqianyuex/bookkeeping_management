import { Card, Typography } from 'antd'
import { PageHeader, AnimatedRoute } from '../components/ui'

const { Text } = Typography

/**
 * 会员中心 — 页面骨架（实装规格：docs/membership-plan.md §8.3；接口：src/api/membership.js）
 *
 * TODO: 挂载时 getMembershipStatus() 拉取等级/今日用量/权益（loading 用 SkeletonCard，失败 EmptyState）
 * TODO: 等级卡（gradient-icon--primary + CrownOutlined + tierName + expiresAt「YYYY-MM-DD 到期」）
 * TODO: 兑换码输入行（Input 16 位码，粘贴归一化 replace(/[\s-]/g,'').toUpperCase() + Button → redeemMembership，成功后刷新 status）
 * TODO: 今日用量三行进度条（chat/analyze/bookkeeping，复用 .progress-bar-track--wide，用尽行 fill 用 --color-expense）
 * TODO: 权益对比（数据来自 status.benefits，不硬编码数值；premiumModel 为 true 时标注「已启用高级模型」）
 */
export default function Membership() {
  return (
    <AnimatedRoute>
      <PageHeader title="会员中心" />
      <Card variant="borderless" className="card-base">
        <Text type="secondary">
          会员中心待实装：等级卡 / 今日用量 / 权益对比 / 兑换码输入（规格见 docs/membership-plan.md §8.3）
        </Text>
      </Card>
    </AnimatedRoute>
  )
}
