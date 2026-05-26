import { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic, Table, DatePicker, Spin } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, WalletOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getMonthlyStatistics, getCategoryStatistics } from '../api/statistics'

const { MonthPicker } = DatePicker

export default function Dashboard() {
  const now = dayjs()
  const [month, setMonth] = useState(now)
  const [monthlyData, setMonthlyData] = useState(null)
  const [expenseData, setExpenseData] = useState([])
  const [incomeData, setIncomeData] = useState([])
  const [loading, setLoading] = useState(false)

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
    { title: '分类', dataIndex: 'categoryName', key: 'categoryName' },
    {
      title: '金额', dataIndex: 'amount', key: 'amount',
      render: (v) => `¥${v.toFixed(2)}`,
    },
    {
      title: '占比', dataIndex: 'percentage', key: 'percentage',
      render: (v) => `${v}%`,
    },
  ]

  return (
    <Spin spinning={loading}>
      <div style={{ marginBottom: 16 }}>
        <MonthPicker value={month} onChange={(d) => setMonth(d || now)} allowClear={false} />
      </div>

      {monthlyData && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Card bordered={false} style={{ boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)' }}>
              <Statistic
                title={<span style={{ color: '#8c8c8c' }}>收入</span>}
                value={monthlyData.totalIncome}
                precision={2}
                prefix={<ArrowUpOutlined />}
                suffix="元"
                valueStyle={{ color: '#3f8600', fontWeight: 500 }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card bordered={false} style={{ boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)' }}>
              <Statistic
                title={<span style={{ color: '#8c8c8c' }}>支出</span>}
                value={monthlyData.totalExpense}
                precision={2}
                prefix={<ArrowDownOutlined />}
                suffix="元"
                valueStyle={{ color: '#cf1322', fontWeight: 500 }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card bordered={false} style={{ boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)' }}>
              <Statistic
                title={<span style={{ color: '#8c8c8c' }}>结余</span>}
                value={monthlyData.balance}
                precision={2}
                prefix={<WalletOutlined />}
                suffix="元"
                valueStyle={{ color: monthlyData.balance >= 0 ? '#3f8600' : '#cf1322', fontWeight: 500 }}
              />
            </Card>
          </Col>

        </Row>
      )}

      <Row gutter={16}>
        <Col span={12}>
          <Card title="支出分类统计" bordered={false} style={{ boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)' }}>
            <Table
              dataSource={expenseData}
              columns={categoryColumns}
              rowKey="categoryId"
              pagination={false}
              size="middle"
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="收入分类统计" bordered={false} style={{ boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)' }}>
            <Table
              dataSource={incomeData}
              columns={categoryColumns}
              rowKey="categoryId"
              pagination={false}
              size="middle"
            />
          </Card>
        </Col>
      </Row>
    </Spin>
  )
}
