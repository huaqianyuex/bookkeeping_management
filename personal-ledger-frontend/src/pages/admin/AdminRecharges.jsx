import { useState, useEffect, useCallback } from 'react'
import {
  Table, Button, Card, Modal, Typography, Input, Space, Select, Popconfirm, Drawer,
  Timeline, App as AntdApp,
} from 'antd'
import { SearchOutlined, ReloadOutlined, AuditOutlined } from '@ant-design/icons'
import { listRechargeOrders, approveRecharge, rejectRecharge, getRechargeLogs } from '../../api/recharge'
import { PageHeader, EmptyState, ErrorState, SkeletonCard, AnimatedRoute, ListToolbar, SemanticTag } from '../../components/ui'
import { formatDateTime } from '../../utils/format'
import { extractErrorMessage } from '../../utils/error'

const { Text } = Typography

/**
 * 充值审批（管理端）— 风控拦截订单的人工终审工作台
 *
 * 订单状态机：0待支付 1待审批 2已支付 3已拒绝 4已取消 5已关闭。
 * 只有「待审批」可操作（通过=放行到账并延期会员；拒绝=原因必填、模拟渠道原路退回）；
 * 其余状态只读，操作留痕见「审计轨迹」抽屉（append-only，不提供修改/删除）。
 */

// 订单状态 → 展示（SemanticTag 语义：warning=待办、success=已完成、danger=异常、neutral=无关态）
const STATUS_META = {
  0: { text: '待支付', variant: 'neutral' },
  1: { text: '待审批', variant: 'warning' },
  2: { text: '已支付', variant: 'success' },
  3: { text: '已拒绝', variant: 'danger' },
  4: { text: '已取消', variant: 'neutral' },
  5: { text: '已关闭', variant: 'neutral' },
}

// 审计动作 → 时间线文案
const ACTION_TEXT = {
  CREATE: '创建订单',
  PAY_SUCCESS: '支付成功',
  PAY_FAIL: '支付失败',
  RISK_HOLD: '风控拦截',
  APPROVE: '审批通过',
  REJECT: '审批拒绝',
  CANCEL: '用户取消',
  EXPIRE_CLOSE: '超时关闭',
  EXTEND_MEMBERSHIP: '会员延期',
}

// 审计操作方：0=用户 1=系统（风控/超时/回调） 2=管理员
const ACTOR_TEXT = { 0: '用户', 1: '系统', 2: '管理员' }

const STATUS_OPTIONS = Object.entries(STATUS_META).map(([value, meta]) => ({
  value: Number(value),
  label: meta.text,
}))

export default function AdminRecharges() {
  const [data, setData] = useState({ records: [], total: 0, pages: 0, current: 1, size: 10 })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState(null)
  const [rejecting, setRejecting] = useState(null)     // 待拒绝的订单行
  const [rejectReason, setRejectReason] = useState('')
  const [rejectSubmitting, setRejectSubmitting] = useState(false)
  const [logDrawer, setLogDrawer] = useState(null)     // 审计轨迹抽屉：订单行
  const [logs, setLogs] = useState([])
  const [logsLoading, setLogsLoading] = useState(false)
  const { message } = AntdApp.useApp()

  const fetchData = async (page = 1, size = 10, kw = keyword, st = status) => {
    setLoading(true)
    setError(null)
    try {
      const res = await listRechargeOrders({ page, size, status: st ?? undefined, keyword: kw || undefined })
      if (res.code === 200) setData(res.data)
      else setError(res.message || '充值订单加载失败')
    } catch (e) {
      setError(extractErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  const handleSearch = () => { fetchData(1, data.size, keyword) }

  const handleReset = () => {
    setKeyword('')
    setStatus(null)
    fetchData(1, data.size, '', null)
  }

  const handleApprove = async (record) => {
    const res = await approveRecharge(record.id)
    if (res.code === 200) {
      message.success(res.message || '已通过')
      fetchData(data.current, data.size)
    } else {
      message.error(res.message)
    }
  }

  const openReject = (record) => {
    setRejecting(record)
    setRejectReason('')
  }

  const handleRejectSubmit = async () => {
    if (!rejectReason.trim()) {
      message.warning('请填写拒绝原因（将写入审计留痕）')
      return
    }
    setRejectSubmitting(true)
    try {
      const res = await rejectRecharge(rejecting.id, rejectReason.trim())
      if (res.code === 200) {
        message.success(res.message || '已拒绝')
        setRejecting(null)
        fetchData(data.current, data.size)
      } else {
        message.error(res.message)
      }
    } finally {
      setRejectSubmitting(false)
    }
  }

  const openLogs = useCallback(async (record) => {
    setLogDrawer(record)
    setLogs([])
    setLogsLoading(true)
    try {
      const res = await getRechargeLogs(record.id)
      if (res.code === 200) setLogs(res.data?.records || [])
      else message.error(res.message || '审计轨迹加载失败')
    } catch (e) {
      message.error(extractErrorMessage(e))
    } finally {
      setLogsLoading(false)
    }
  }, [message])

  const columns = [
    {
      title: '订单号',
      dataIndex: 'orderNo',
      key: 'orderNo',
      width: 220,
      render: (text) => <Text copyable={{ text }} style={{ fontFamily: 'var(--font-family-base)' }}>{text}</Text>,
    },
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      width: 120,
      render: (text, record) => <Text strong>{text || `UID ${record.userId}`}</Text>,
    },
    {
      title: '套餐',
      dataIndex: 'planName',
      key: 'planName',
      width: 150,
      responsive: ['md'],
      render: (text, record) => `${text} · ${record.days}天`,
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      width: 100,
      render: (text) => <Text strong>¥{text}</Text>,
    },
    {
      title: '风控标记',
      dataIndex: 'riskFlags',
      key: 'riskFlags',
      width: 170,
      responsive: ['md'],
      render: (text) => (text
        ? <SemanticTag variant="danger">{text}</SemanticTag>
        : <Text type="secondary">—</Text>),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (v) => {
        const meta = STATUS_META[v] || { text: `未知(${v})`, variant: 'neutral' }
        return <SemanticTag variant={meta.variant}>{meta.text}</SemanticTag>
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 160,
      responsive: ['lg'],
      render: (text) => <Text style={{ color: 'var(--color-text-secondary)' }}>{formatDateTime(text)}</Text>,
    },
    {
      title: '操作',
      key: 'action',
      width: 210,
      render: (_, record) => (
        <Space size="small">
          {record.status === 1 ? (
            <>
              <Popconfirm
                title="确认通过"
                description={`通过后将为用户「${record.username || record.userId}」延长 ${record.days} 天会员，且不可撤销。`}
                onConfirm={() => handleApprove(record)}
                okText="通过"
                cancelText="取消"
              >
                <Button type="link" className="table-action">通过</Button>
              </Popconfirm>
              <Button type="link" danger className="table-action" onClick={() => openReject(record)}>
                拒绝
              </Button>
            </>
          ) : (
            <Text type="secondary">—</Text>
          )}
          <Button
            type="link"
            icon={<AuditOutlined />}
            className="table-action"
            onClick={() => openLogs(record)}
          >
            审计
          </Button>
        </Space>
      ),
    },
  ]

  const renderContent = () => {
    if (loading) return <SkeletonCard type="table" rows={6} />
    if (error) return <ErrorState description={error} onRetry={() => fetchData()} />
    if (data.records.length === 0) return <EmptyState title="暂无充值订单" description="没有匹配当前筛选条件的订单" />
    return (
      <Table
        dataSource={data.records}
        columns={columns}
        rowKey="id"
        size="middle"
        pagination={{
          current: data.current,
          pageSize: data.size,
          total: data.total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (page, size) => fetchData(page, size),
        }}
        scroll={{ x: 980 }}
      />
    )
  }

  return (
    <AnimatedRoute>
      <PageHeader
        title="充值审批"
        subtitle="大额/异常交易的人工终审工作台；所有操作与支付回调均写入审计日志"
      />
      <Card variant="borderless" className="card-base">
        <ListToolbar>
          <Input
            placeholder="搜索用户名 / 订单号 / 套餐名"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={handleSearch}
            allowClear
            style={{ width: 260 }}
            prefix={<SearchOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
          />
          <Select
            placeholder="全部状态"
            value={status}
            onChange={(v) => { setStatus(v); fetchData(1, data.size, keyword, v) }}
            onClear={() => { setStatus(null); fetchData(1, data.size, keyword, null) }}
            allowClear
            options={STATUS_OPTIONS}
            style={{ width: 140 }}
          />
          <Space>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>搜索</Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
          </Space>
        </ListToolbar>

        {renderContent()}
      </Card>

      {/* 拒绝弹窗：原因必填并写入订单与审计 */}
      <Modal
        title={rejecting ? `拒绝订单 ${rejecting.orderNo}` : ''}
        open={!!rejecting}
        onOk={handleRejectSubmit}
        onCancel={() => setRejecting(null)}
        okText="确认拒绝"
        okType="danger"
        cancelText="取消"
        confirmLoading={rejectSubmitting}
        destroyOnHidden
      >
        <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          拒绝后订单进入「已拒绝」终态，模拟渠道款项按原路退回处理；原因将写入审计日志。
        </Text>
        <Input.TextArea
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
          placeholder="请填写拒绝原因（必填，最多 200 字）"
          maxLength={200}
          showCount
          rows={3}
        />
      </Modal>

      {/* 审计轨迹抽屉：append-only 时间线 */}
      <Drawer
        title={logDrawer ? `审计轨迹 · ${logDrawer.orderNo}` : ''}
        open={!!logDrawer}
        onClose={() => setLogDrawer(null)}
        width={460}
      >
        {logsLoading ? (
          <SkeletonCard type="table" rows={4} />
        ) : logs.length === 0 ? (
          <EmptyState title="暂无审计记录" />
        ) : (
          <Timeline
            items={logs.map((log) => ({
              color: log.action === 'RISK_HOLD' || log.action === 'REJECT' || log.action === 'PAY_FAIL' ? 'red'
                : log.action === 'PAY_SUCCESS' || log.action === 'APPROVE' || log.action === 'EXTEND_MEMBERSHIP' ? 'green'
                : 'gray',
              children: (
                <div>
                  <Text strong>{ACTION_TEXT[log.action] || log.action}</Text>
                  <Text type="secondary" style={{ marginLeft: 8 }}>
                    {ACTOR_TEXT[log.actorType] || '未知'}
                    {log.actorId ? ` #${log.actorId}` : ''}
                  </Text>
                  {log.detail && (
                    <div><Text style={{ fontSize: 12 }}>{log.detail}</Text></div>
                  )}
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {formatDateTime(log.createdAt)}
                      {log.ip ? ` · IP ${log.ip}` : ''}
                    </Text>
                  </div>
                </div>
              ),
            }))}
          />
        )}
      </Drawer>
    </AnimatedRoute>
  )
}
