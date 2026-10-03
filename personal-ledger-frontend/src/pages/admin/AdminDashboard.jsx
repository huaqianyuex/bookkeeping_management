import { useState, useEffect } from 'react'
import { Row, Col } from 'antd'
import {
  UserOutlined, BookOutlined, AppstoreOutlined,
  ArrowUpOutlined, ArrowDownOutlined, WalletOutlined,
} from '@ant-design/icons'
import { getAdminOverview } from '../../api/admin'
import { PageHeader, StatCard, EmptyState, SkeletonCard, AnimatedRoute } from '../../components/ui'

export default function AdminDashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      const res = await getAdminOverview()
      if (res.code === 200) setData(res.data)
      setLoading(false)
    }
    fetchData()
  }, [])

  if (loading) {
    return (
      <AnimatedRoute>
        <PageHeader title="系统概览" />
        <Row gutter={[24, 24]}>
          {Array.from({ length: 6 }).map((_, i) => (
            <Col xs={24} sm={12} lg={8} key={i}>
              <SkeletonCard type="stat" />
            </Col>
          ))}
        </Row>
      </AnimatedRoute>
    )
  }

  if (!data) return <EmptyState title="加载失败" description="请检查网络连接后重试" />

  const balance = Number(data.totalIncome) - Number(data.totalExpense)

  const cards = [
    { label: '总用户数', value: data.totalUsers, icon: UserOutlined, color: 'primary', prefix: '' },
    { label: '总账单数', value: data.totalRecords, icon: BookOutlined, color: 'info', prefix: '' },
    { label: '总分类数', value: data.totalCategories, icon: AppstoreOutlined, color: 'warning', prefix: '' },
    { label: '总收入', value: Number(data.totalIncome), icon: ArrowUpOutlined, color: 'income', prefix: '¥' },
    { label: '总支出', value: Number(data.totalExpense), icon: ArrowDownOutlined, color: 'expense', prefix: '¥' },
    { label: '总盈余', value: balance, icon: WalletOutlined, color: 'balance', prefix: '¥', balance },
  ]

  return (
    <AnimatedRoute>
      <PageHeader title="系统概览" />
      <Row gutter={[24, 24]}>
        {cards.map((card) => (
          <Col xs={24} sm={12} lg={8} key={card.label}>
            <StatCard
              icon={card.icon}
              label={card.label}
              value={card.value}
              color={card.color}
              prefix={card.prefix}
              balance={card.balance}
            />
          </Col>
        ))}
      </Row>
    </AnimatedRoute>
  )
}
