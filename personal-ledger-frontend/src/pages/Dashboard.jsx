import { useState, useEffect } from 'react'
import { Row, Col, Table, DatePicker, Typography } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, WalletOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getMonthlyStatistics, getCategoryStatistics } from '../api/statistics'
import StatCard from '../components/ui/StatCard'
import PageHeader from '../components/ui/PageHeader'
import SectionTitle from '../components/ui/SectionTitle'
import EmptyState from '../components/ui/EmptyState'
import SkeletonCard, { StatsRowSkeleton } from '../components/ui/SkeletonCard'
import AnimatedRoute from '../components/ui/AnimatedRoute'

const { MonthPicker } = DatePicker
const { Text } = Typography

export default function Dashboard() {
  const now = dayjs()
  const [month, setMonth] = useState(now)
  const [monthlyData, setMonthlyData] = useState(null)
  const [expenseData, setExpenseData] = useState([])
  const [incomeData, setIncomeData] = useState([])
  const [loading, setLoading] = useState(false)
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768)

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const fetchData = async (date) => {
    setLoading(true)
    const year = date.year()
    const m = date.month() + 1

    const [monthlyRes, expenseRes, incomeRes] = await Promise.all([
      getMonthlyStatistics({ year, month: m }),
      getCategoryStatistics({ year, month: m, type: 0 }),
      getCategoryStatistics({ year, month: m, type: 1 }),
    ])

    if (monthlyRes.code === 200) setMonthlyData(monthlyRes.data)
    if (expenseRes.code === 200) setExpenseData(expenseRes.data)
    if (incomeRes.code === 200) setIncomeData(incomeRes.data)
    setLoading(false)
  }

  useEffect(() => { fetchData(month) }, [month])

  const categoryColumns = [
    {
      title: '分类',
      dataIndex: 'categoryName',
      key: 'categoryName',
      render: (text) => <Text strong style={{ color: 'var(--color-text)' }}>{text}</Text>,
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      render: (v) => (
        <Text strong style={{ color: 'var(--color-text)' }}>¥{v.toFixed(2)}</Text>
      ),
    },
    {
      title: '占比',
      dataIndex: 'percentage',
      key: 'percentage',
      render: (v) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${v}%` }} />
          </div>
          <Text style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>{v}%</Text>
        </div>
      ),
    },
  ]

  if (loading) {
    return (
      <AnimatedRoute>
        <PageHeader
          title="数据概览"
          action={<MonthPicker value={month} allowClear={false} style={{ width: 180 }} size="large" />}
        />
        <StatsRowSkeleton count={3} />
        <Row gutter={24}>
          <Col xs={24} md={12}>
            <SkeletonCard type="table" rows={4} />
          </Col>
          <Col xs={24} md={12}>
            <SkeletonCard type="table" rows={4} />
          </Col>
        </Row>
      </AnimatedRoute>
    )
  }

  if (!monthlyData) {
    return (
      <AnimatedRoute>
        <PageHeader
          title="数据概览"
          action={<MonthPicker value={month} onChange={(d) => setMonth(d || now)} allowClear={false} style={{ width: 180 }} size="large" />}
        />
        <EmptyState title="暂无统计数据" description="请选择月份查看账单统计" />
      </AnimatedRoute>
    )
  }

  return (
    <AnimatedRoute>
      <PageHeader
        title={isMobile ? undefined : '数据概览'}
        action={
          <MonthPicker
            value={month}
            onChange={(d) => setMonth(d || now)}
            allowClear={false}
            style={{ width: isMobile ? '100%' : 180 }}
            size={isMobile ? 'middle' : 'large'}
          />
        }
      />

      {/* Stats Cards */}
      <Row gutter={isMobile ? 12 : 24} style={{ marginBottom: 24 }}>
        <Col xs={8} md={8}>
          <StatCard
            icon={ArrowUpOutlined}
            label="本月收入"
            value={monthlyData.totalIncome}
            color="income"
            compact={isMobile}
          />
        </Col>
        <Col xs={8} md={8}>
          <StatCard
            icon={ArrowDownOutlined}
            label="本月支出"
            value={monthlyData.totalExpense}
            color="expense"
            compact={isMobile}
          />
        </Col>
        <Col xs={8} md={8}>
          <StatCard
            icon={WalletOutlined}
            label="本月结余"
            value={monthlyData.balance}
            color="balance"
            balance={monthlyData.balance}
            compact={isMobile}
          />
        </Col>
      </Row>

      {/* Category Tables */}
      <Row gutter={isMobile ? 0 : 24}>
        <Col xs={24} md={12}>
          <div className="card-base" style={{ padding: '20px 24px', marginBottom: isMobile ? 16 : 0 }}>
            <SectionTitle title="支出分类统计" dotColor="danger" />
            <Table
              dataSource={expenseData}
              columns={categoryColumns}
              rowKey="categoryId"
              pagination={false}
              size={isMobile ? 'small' : 'middle'}
              scroll={isMobile ? { x: 300 } : undefined}
              style={{ marginTop: 16 }}
              locale={{ emptyText: <EmptyState title="暂无支出数据" size="small" /> }}
            />
          </div>
        </Col>
        <Col xs={24} md={12}>
          <div className="card-base" style={{ padding: '20px 24px' }}>
            <SectionTitle title="收入分类统计" dotColor="success" />
            <Table
              dataSource={incomeData}
              columns={categoryColumns}
              rowKey="categoryId"
              pagination={false}
              size={isMobile ? 'small' : 'middle'}
              scroll={isMobile ? { x: 300 } : undefined}
              style={{ marginTop: 16 }}
              locale={{ emptyText: <EmptyState title="暂无收入数据" size="small" /> }}
            />
          </div>
        </Col>
      </Row>
    </AnimatedRoute>
  )
}
