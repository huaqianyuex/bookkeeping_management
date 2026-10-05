import { useState, useEffect } from 'react'
import { Row, Col } from 'antd'
import {
  UserOutlined, BookOutlined, AppstoreOutlined,
  ArrowUpOutlined, ArrowDownOutlined, WalletOutlined,
} from '@ant-design/icons'
import { getAdminOverview } from '../../api/admin'
import { PageHeader, StatCard, ErrorState, SkeletonCard, AnimatedRoute } from '../../components/ui'
import { extractErrorMessage } from '../../utils/error'

export default function AdminDashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getAdminOverview()
      if (res.code === 200) setData(res.data)
      else setError(res.message || '概览加载失败')
    } catch (e) {
      // 请求 reject 时必须落地错误态：否则 loading 永远不复位，页面卡死骨架屏
      setError(extractErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  if (loading) {
    return (
      <AnimatedRoute>
        <PageHeader title="系统概览" />
        <Row gutter={[16, 16]}>
          {Array.from({ length: 6 }).map((_, i) => (
            <Col xs={24} sm={12} lg={8} key={i}>
              <SkeletonCard type="stat" />
            </Col>
          ))}
        </Row>
      </AnimatedRoute>
    )
  }

  /* 「取不到数据」用 ErrorState 而非 EmptyState：语义上是加载失败，
     不该复用"暂无数据"的插图与语气。 */
  if (error || !data) return <ErrorState title="加载失败" description={error || '请检查网络连接后重试'} onRetry={fetchData} />

  const balance = Number(data.totalIncome) - Number(data.totalExpense)

  /* 三张计数卡片刻意用三个互不相邻的色相（cyan / violet / amber）。
     原先第二张用 info(sky)，主色从 cyan-900 提亮到 cyan-700 后两者仅差 8° 色相，
     并排时会读成"同一个色的深浅"。 */
  const cards = [
    { label: '总用户数', value: data.totalUsers, icon: UserOutlined, color: 'primary', prefix: '' },
    { label: '总账单数', value: data.totalRecords, icon: BookOutlined, color: 'accent', prefix: '' },
    { label: '总分类数', value: data.totalCategories, icon: AppstoreOutlined, color: 'warning', prefix: '' },
    { label: '总收入', value: Number(data.totalIncome), icon: ArrowUpOutlined, color: 'income', prefix: '¥' },
    { label: '总支出', value: Number(data.totalExpense), icon: ArrowDownOutlined, color: 'expense', prefix: '¥' },
    { label: '总盈余', value: balance, icon: WalletOutlined, color: 'balance', prefix: '¥', balance },
  ]

  return (
    <AnimatedRoute>
      <PageHeader title="系统概览" />
      <Row gutter={[16, 16]}>
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
