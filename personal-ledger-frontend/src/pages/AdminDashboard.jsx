import { useState, useEffect } from 'react'
import { Card, Row, Col, Typography, Spin } from 'antd'
import { UserOutlined, BookOutlined, AppstoreOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import { getAdminOverview } from '../api/admin'
import SectionTitle from '../components/ui/SectionTitle'
import EmptyState from '../components/ui/EmptyState'
import AnimatedRoute from '../components/ui/AnimatedRoute'

const { Text } = Typography

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

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />

  if (!data) return <EmptyState title="加载失败" description="请检查网络连接后重试" />

  const cards = [
    {
      title: '总用户数',
      value: data.totalUsers,
      icon: <UserOutlined style={{ fontSize: 24, color: '#fff' }} />,
      gradientClass: 'gradient-icon--primary',
    },
    {
      title: '总账单数',
      value: data.totalRecords,
      icon: <BookOutlined style={{ fontSize: 24, color: '#fff' }} />,
      gradientClass: 'gradient-icon--success',
    },
    {
      title: '总分类数',
      value: data.totalCategories,
      icon: <AppstoreOutlined style={{ fontSize: 24, color: '#fff' }} />,
      gradientClass: 'gradient-icon--primary',
      styleOverride: { opacity: 0.7 },
    },
    {
      title: '总收入',
      value: data.totalIncome,
      prefix: '¥',
      icon: <ArrowUpOutlined style={{ fontSize: 24, color: '#fff' }} />,
      gradientClass: 'gradient-icon--success',
    },
    {
      title: '总支出',
      value: data.totalExpense,
      prefix: '¥',
      icon: <ArrowDownOutlined style={{ fontSize: 24, color: '#fff' }} />,
      gradientClass: 'gradient-icon--danger',
    },
    {
      title: '总盈余',
      value: data.totalIncome - data.totalExpense,
      prefix: '¥',
      icon: <ArrowUpOutlined style={{ fontSize: 24, color: '#fff' }} />,
      gradientClass: (data.totalIncome - data.totalExpense) >= 0 ? 'gradient-icon--primary' : 'gradient-icon--danger',
    },
  ]

  return (
    <AnimatedRoute>
      <div style={{ marginBottom: 24 }}>
        <SectionTitle title="系统概览" dotColor="primary" />
      </div>
      <Row gutter={[24, 24]}>
        {cards.map((card, idx) => (
          <Col xs={24} sm={12} lg={8} key={idx}>
            <Card variant="borderless" className="card-base">
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-base)' }}>
                <div className={`gradient-icon ${card.gradientClass}`}
                  style={card.styleOverride}>
                  {card.icon}
                </div>
                <div>
                  <Text className="text-secondary" style={{ fontSize: 'var(--font-size-base)' }}>
                    {card.title}
                  </Text>
                  <div style={{
                    fontSize: 'var(--font-size-2xl)',
                    fontWeight: 700,
                    color: 'var(--color-text)',
                    marginTop: 'var(--space-xs)',
                  }}>
                    {card.prefix || ''}{typeof card.value === 'number' ? card.value.toLocaleString() : 0}
                  </div>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </AnimatedRoute>
  )
}
