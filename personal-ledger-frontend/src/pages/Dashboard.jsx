import { useState, useEffect } from 'react'
import { Row, Col, Table, DatePicker, Typography } from 'antd'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  PieChart, Pie, Cell, ResponsiveContainer,
} from 'recharts'
import { ArrowUpOutlined, ArrowDownOutlined, WalletOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getMonthlyStatistics, getCategoryStatistics } from '../api/statistics'
import { chartColors } from '../theme/palette'
import { tokens } from '../theme/tokens'
import { StatCard, PageHeader, SectionTitle, EmptyState, ErrorState, Money, SkeletonCard, StatsRowSkeleton, AnimatedRoute } from '../components/ui'
import useMediaQuery from '../hooks/useMediaQuery'
import { extractErrorMessage } from '../utils/error'

const { MonthPicker } = DatePicker
const { Text } = Typography

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="card-base" style={{ padding: '8px 12px', fontSize: 'var(--font-size-sm)' }}>
      {label !== undefined && (
        <div style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-xs)' }}>{label}</div>
      )}
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ width: 8, height: 8, borderRadius: 'var(--radius-full)', flexShrink: 0, background: p.color || p.payload?.fill }} />
          <span style={{ color: 'var(--color-text-secondary)' }}>{p.name}</span>
          <span className="money" style={{ fontWeight: 600, color: 'var(--color-text)' }}>
            ¥{Number(p.value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const now = dayjs()
  const [month, setMonth] = useState(now)
  const [monthlyData, setMonthlyData] = useState(null)
  const [expenseData, setExpenseData] = useState([])
  const [incomeData, setIncomeData] = useState([])
  const [trendData, setTrendData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const isMobile = useMediaQuery('(max-width: 767px)')

  const fetchData = async (date) => {
    setLoading(true)
    setError(null)
    const year = date.year()
    const m = date.month() + 1

    /* 近 6 个月趋势：复用现有 monthly 接口并行取数，无后端改动 */
    const months = Array.from({ length: 6 }, (_, i) => date.subtract(5 - i, 'month'))

    try {
      // 三个核心请求决定整页能否渲染，任一失败即进入错误态；
      // 趋势属辅助信息，用 allSettled 允许单月降级为 0（下方 res?.code 分支即为此准备）。
      const [core, trend] = await Promise.all([
        Promise.all([
          getMonthlyStatistics({ year, month: m }),
          getCategoryStatistics({ year, month: m, type: 0 }),
          getCategoryStatistics({ year, month: m, type: 1 }),
        ]),
        Promise.allSettled(
          months.map((d) => getMonthlyStatistics({ year: d.year(), month: d.month() + 1 })),
        ),
      ])

      const [monthlyRes, expenseRes, incomeRes] = core

      if (monthlyRes.code === 200) setMonthlyData(monthlyRes.data)
      if (expenseRes.code === 200) setExpenseData(expenseRes.data)
      if (incomeRes.code === 200) setIncomeData(incomeRes.data)
      setTrendData(months.map((d, i) => {
        const res = trend[i]
        const ok = res.status === 'fulfilled' && res.value?.code === 200
        return {
          label: `${d.month() + 1}月`,
          收入: ok ? Number(res.value.data.totalIncome) : 0,
          支出: ok ? Number(res.value.data.totalExpense) : 0,
        }
      }))
    } catch (e) {
      setError(extractErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData(month) }, [month])

  const categoryColumns = (type) => [
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
      render: (v) => <Money value={v} type={type} />,
    },
    {
      title: '占比',
      dataIndex: 'percentage',
      key: 'percentage',
      render: (v) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <div className="progress-bar-track">
            <div className="progress-bar-fill" style={{ width: `${v}%` }} />
          </div>
          <Text style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>{v}%</Text>
        </div>
      ),
    },
  ]

  const monthPicker = (
    <MonthPicker
      value={month}
      onChange={(d) => setMonth(d || now)}
      allowClear={false}
      style={{ width: isMobile ? '100%' : 180 }}
      size={isMobile ? 'middle' : 'large'}
    />
  )

  if (loading) {
    return (
      <AnimatedRoute>
        <PageHeader title="数据概览" action={monthPicker} />
        <StatsRowSkeleton count={3} compact={isMobile} />
        <Row gutter={[isMobile ? 0 : 24, isMobile ? 16 : 0]}>
          <Col xs={24} lg={14}>
            <SkeletonCard type="table" rows={4} />
          </Col>
          <Col xs={24} lg={10}>
            <SkeletonCard type="table" rows={4} />
          </Col>
        </Row>
      </AnimatedRoute>
    )
  }

  if (error) {
    return (
      <AnimatedRoute>
        <PageHeader title="数据概览" action={monthPicker} />
        <ErrorState description={error} onRetry={() => fetchData(month)} />
      </AnimatedRoute>
    )
  }

  if (!monthlyData) {
    return (
      <AnimatedRoute>
        <PageHeader title="数据概览" action={monthPicker} />
        <EmptyState title="暂无统计数据" description="请选择月份查看账单统计" />
      </AnimatedRoute>
    )
  }

  return (
    <AnimatedRoute>
      <PageHeader title="数据概览" action={monthPicker} />

      {/* Stats Cards: 8pt grid compliant gutter [16, 16] on desktop, [8, 8] on mobile */}
      <Row gutter={isMobile ? [8, 8] : [16, 16]} style={{ marginBottom: 'var(--space-base)' }}>
        <Col xs={8} md={8}>
          <StatCard
            icon={ArrowUpOutlined}
            label="本月收入"
            value={Number(monthlyData.totalIncome)}
            color="income"
            compact={isMobile}
          />
        </Col>
        <Col xs={8} md={8}>
          <StatCard
            icon={ArrowDownOutlined}
            label="本月支出"
            value={Number(monthlyData.totalExpense)}
            color="expense"
            compact={isMobile}
          />
        </Col>
        <Col xs={8} md={8}>
          <StatCard
            icon={WalletOutlined}
            label="本月结余"
            value={Number(monthlyData.balance)}
            color="balance"
            balance={Number(monthlyData.balance)}
            compact={isMobile}
          />
        </Col>
      </Row>

      {/* Charts: height optimized to 224px (28*8pt) to ensure above-the-fold visibility */}
      <Row gutter={isMobile ? [8, 8] : [16, 16]} style={{ marginBottom: 'var(--space-base)' }}>
        <Col xs={24} lg={14}>
          <div className="card-base" style={{ padding: isMobile ? 'var(--space-base)' : 'var(--space-base) var(--space-xl)', height: '100%', boxSizing: 'border-box' }}>
            <SectionTitle title="近 6 个月收支趋势" dotColor="primary" />
            <div style={{ marginTop: 'var(--space-md)' }}>
              <ResponsiveContainer width="100%" height={tokens.chart.height}>
                <LineChart data={trendData} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border-secondary)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: tokens.chart.tickFontSize, fill: 'var(--color-text-tertiary)' }} axisLine={false} tickLine={false} />
                  <YAxis
                    tick={{ fontSize: tokens.chart.tickFontSize, fill: 'var(--color-text-tertiary)' }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v) => (v >= 10000 ? `${(v / 10000).toFixed(1)}万` : v)}
                  />
                  <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'var(--color-border)' }} />
                  <Legend wrapperStyle={{ fontSize: tokens.chart.legendFontSize }} iconType="circle" iconSize={8} />
                  <Line type="monotone" dataKey="收入" stroke="var(--color-success)" strokeWidth={tokens.chart.strokeWidth} dot={{ r: tokens.chart.dotRadius, fill: 'var(--color-success)', strokeWidth: 0 }} activeDot={{ r: tokens.chart.activeDotRadius }} />
                  <Line type="monotone" dataKey="支出" stroke="var(--color-danger)" strokeWidth={tokens.chart.strokeWidth} dot={{ r: tokens.chart.dotRadius, fill: 'var(--color-danger)', strokeWidth: 0 }} activeDot={{ r: tokens.chart.activeDotRadius }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </Col>
        <Col xs={24} lg={10}>
          <div className="card-base" style={{ padding: isMobile ? 'var(--space-base)' : 'var(--space-base) var(--space-xl)', height: '100%', boxSizing: 'border-box' }}>
            <SectionTitle title="本月支出构成" dotColor="danger" />
            <div style={{ marginTop: 'var(--space-md)' }}>
              {expenseData.length === 0 ? (
                <EmptyState title="暂无支出数据" size="small" />
              ) : (
                <ResponsiveContainer width="100%" height={tokens.chart.height}>
                  <PieChart>
                    <Pie
                      data={expenseData}
                      dataKey="amount"
                      nameKey="categoryName"
                      innerRadius="54%"
                      outerRadius="80%"
                      paddingAngle={2}
                      stroke="none"
                    >
                      {expenseData.map((entry, i) => (
                        <Cell key={entry.categoryId ?? i} fill={chartColors[i % chartColors.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                    <Legend
                      wrapperStyle={{ fontSize: tokens.chart.legendFontSize }}
                      iconType="circle"
                      iconSize={8}
                      formatter={(value) => <span style={{ color: 'var(--color-text-secondary)' }}>{value}</span>}
                    />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </Col>
      </Row>

      {/* Category Tables: Clean 8pt paddings and tabular density */}
      <Row gutter={isMobile ? [8, 8] : [16, 16]}>
        <Col xs={24} md={12}>
          <div className="card-base" style={{ padding: isMobile ? 'var(--space-base)' : 'var(--space-base) var(--space-xl)' }}>
            <SectionTitle title="支出分类统计" dotColor="danger" />
            <Table
              dataSource={expenseData}
              columns={categoryColumns('expense')}
              rowKey="categoryId"
              pagination={false}
              size={isMobile ? 'small' : 'middle'}
              scroll={isMobile ? { x: 300 } : undefined}
              style={{ marginTop: 12 }}
              locale={{ emptyText: <EmptyState title="暂无支出数据" size="small" /> }}
            />
          </div>
        </Col>
        <Col xs={24} md={12}>
          <div className="card-base" style={{ padding: isMobile ? 'var(--space-base)' : 'var(--space-base) var(--space-xl)' }}>
            <SectionTitle title="收入分类统计" dotColor="success" />
            <Table
              dataSource={incomeData}
              columns={categoryColumns('income')}
              rowKey="categoryId"
              pagination={false}
              size={isMobile ? 'small' : 'middle'}
              scroll={isMobile ? { x: 300 } : undefined}
              style={{ marginTop: 12 }}
              locale={{ emptyText: <EmptyState title="暂无收入数据" size="small" /> }}
            />
          </div>
        </Col>
      </Row>
    </AnimatedRoute>
  )
}
