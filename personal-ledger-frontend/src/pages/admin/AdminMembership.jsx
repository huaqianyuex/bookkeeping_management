import { useState, useEffect } from 'react'
import {
  Table, Button, Card, Modal, Form, Input, InputNumber, Select, Space,
  Popconfirm, Typography, App as AntdApp,
} from 'antd'
import { PlusOutlined, ReloadOutlined, CopyOutlined } from '@ant-design/icons'
import { listCodes, generateCodes, voidCode } from '../../api/membership'
import {
  PageHeader, EmptyState, ErrorState, SkeletonCard, AnimatedRoute, ListToolbar, SemanticTag,
} from '../../components/ui'
import { formatDateTime } from '../../utils/format'
import { extractErrorMessage } from '../../utils/error'

const { Text } = Typography

/**
 * 会员管理（管理端）— 兑换码的生成 / 列表 / 作废
 *
 * 业务链路：管理员在此批量生成兑换码 → 线下分发给用户 →
 * 用户在「会员中心」用 POST /api/membership/redeem 核销 → 会员（体验）资格立即生效。
 * 完整流程与权限矩阵见 docs/兑换码流程与权限范围说明.md。
 *
 * 兑换码状态机：0 未使用 → 1 已使用 / 2 已作废（两者均为终态、不可逆）。
 * 仅「未使用」可作废；已核销的码不提供任何撤销入口（会员天数已计入用户账户）。
 */

// 状态 → 展示（SemanticTag 语义：success=可用、neutral=已核销、danger=已作废）
const STATUS_META = {
  0: { text: '未使用', variant: 'success' },
  1: { text: '已使用', variant: 'neutral' },
  2: { text: '已作废', variant: 'danger' },
}

const STATUS_OPTIONS = Object.entries(STATUS_META).map(([value, meta]) => ({
  value: Number(value),
  label: meta.text,
}))

// 兑换码为等宽展示，避免 0/O、1/I 视觉混淆（码表本身已剔除这 4 个字符）
const CODE_FONT = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'

/** 16 位兑换码 → 4-4-4-4 分组，便于肉眼核对与手抄 */
function groupCode(code) {
  const s = String(code || '')
  return s.length === 16 ? s.replace(/(.{4})(?=.)/g, '$1-') : s
}

export default function AdminMembership() {
  const [data, setData] = useState({ records: [], total: 0, pages: 0, current: 1, size: 10 })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [status, setStatus] = useState(null)
  const [genOpen, setGenOpen] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState(null)   // 生成结果：{batchNo, codes[]}
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()

  const fetchData = async (page = 1, size = data.size, st = status) => {
    setLoading(true)
    setError(null)
    try {
      const res = await listCodes({ page, size, status: st ?? undefined })
      if (res.code === 200) setData(res.data)
      else setError(res.message || '兑换码加载失败')
    } catch (e) {
      setError(extractErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData(1) }, [])   // 首屏加载，后续翻页/筛选由事件驱动

  const openGenerate = () => {
    form.resetFields()
    setGenOpen(true)
  }

  const handleGenerate = async () => {
    let values
    try {
      values = await form.validateFields()
    } catch {
      return   // 校验失败由 antd 内联提示
    }
    setGenerating(true)
    try {
      const res = await generateCodes({
        count: values.count,
        days: values.days,
        batchNo: values.batchNo?.trim() || undefined,
      })
      if (res.code === 200) {
        message.success(res.message || '生成成功')
        setGenOpen(false)
        form.resetFields()
        setResult(res.data)          // 打开结果弹窗，便于整批复制
        fetchData(1)
      } else {
        message.error(res.message)
      }
    } catch (e) {
      message.error(extractErrorMessage(e))
    } finally {
      setGenerating(false)
    }
  }

  const handleCopyAll = async () => {
    const text = (result?.codes || []).map((c) => c.code).join('\n')
    try {
      await navigator.clipboard.writeText(text)
      message.success('已复制全部兑换码')
    } catch {
      // 非 HTTPS / 无剪贴板权限时降级：引导手动选中
      message.warning('复制失败，请手动选中文本复制')
    }
  }

  const handleVoid = async (record) => {
    try {
      const res = await voidCode(record.id)
      if (res.code === 200) {
        message.success(res.message || '已作废')
        fetchData(data.current, data.size)
      } else {
        message.error(res.message)
      }
    } catch (e) {
      message.error(extractErrorMessage(e))
    }
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 70, responsive: ['md'] },
    {
      title: '兑换码',
      dataIndex: 'code',
      key: 'code',
      width: 220,
      render: (text) => (
        <Text copyable={{ text }} style={{ fontFamily: CODE_FONT, letterSpacing: '0.5px' }}>
          {groupCode(text)}
        </Text>
      ),
    },
    {
      title: '天数',
      dataIndex: 'days',
      key: 'days',
      width: 90,
      render: (v) => `${v} 天`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (v) => {
        const meta = STATUS_META[v] || { text: `未知(${v})`, variant: 'neutral' }
        return <SemanticTag variant={meta.variant}>{meta.text}</SemanticTag>
      },
    },
    {
      title: '批次号',
      dataIndex: 'batchNo',
      key: 'batchNo',
      width: 160,
      responsive: ['md'],
      render: (t) => t || <Text type="secondary">—</Text>,
    },
    {
      title: '核销用户',
      dataIndex: 'usedBy',
      key: 'usedBy',
      width: 110,
      responsive: ['md'],
      render: (v) => (v ? <Text strong>UID {v}</Text> : <Text type="secondary">—</Text>),
    },
    {
      title: '核销时间',
      dataIndex: 'usedAt',
      key: 'usedAt',
      width: 160,
      responsive: ['lg'],
      render: (t) => (
        <Text style={{ color: 'var(--color-text-secondary)' }}>{t ? formatDateTime(t) : '—'}</Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        record.status === 0 ? (
          <Popconfirm
            title="确认作废"
            description="作废后该码不可再被核销，且不可恢复。"
            onConfirm={() => handleVoid(record)}
            okText="作废"
            okType="danger"
            cancelText="取消"
          >
            <Button type="link" danger className="table-action">作废</Button>
          </Popconfirm>
        ) : (
          <Text type="secondary">—</Text>
        )
      ),
    },
  ]

  const renderContent = () => {
    if (loading) return <SkeletonCard type="table" rows={6} />
    if (error) return <ErrorState description={error} onRetry={() => fetchData()} />
    if (data.records.length === 0) {
      return (
        <EmptyState
          title="暂无兑换码"
          description={status === null ? '点击「生成兑换码」批量创建，供用户自助开通会员' : '没有匹配当前筛选条件的兑换码'}
        />
      )
    }
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
        scroll={{ x: 900 }}
      />
    )
  }

  return (
    <AnimatedRoute>
      <PageHeader
        title="会员管理"
        subtitle="批量生成兑换码供用户自助开通会员；仅「未使用」的码可作废，已核销的不可撤销"
      />
      <Card variant="borderless" className="card-base">
        <ListToolbar>
          <Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={openGenerate}>生成兑换码</Button>
            <Button icon={<ReloadOutlined />} onClick={() => fetchData(data.current, data.size)}>刷新</Button>
          </Space>
          <Select
            placeholder="全部状态"
            value={status}
            onChange={(v) => { setStatus(v); fetchData(1, data.size, v) }}
            onClear={() => { setStatus(null); fetchData(1, data.size, null) }}
            allowClear
            options={STATUS_OPTIONS}
            style={{ width: 140 }}
          />
        </ListToolbar>

        {renderContent()}
      </Card>

      {/* 生成弹窗：数量/天数由服务端 schema 再校验一次（count 1-500、days 1-3650） */}
      <Modal
        title="生成兑换码"
        open={genOpen}
        onOk={handleGenerate}
        onCancel={() => setGenOpen(false)}
        confirmLoading={generating}
        okText="生成"
        cancelText="取消"
        destroyOnHidden
      >
        <Form form={form} layout="vertical" initialValues={{ count: 10, days: 30 }}>
          <Form.Item
            name="count"
            label="生成数量"
            rules={[{ required: true, message: '请输入生成数量' }]}
          >
            <InputNumber min={1} max={500} style={{ width: '100%' }} placeholder="1-500" />
          </Form.Item>
          <Form.Item
            name="days"
            label="每张开通天数"
            rules={[{ required: true, message: '请输入开通天数' }]}
          >
            <InputNumber min={1} max={3650} style={{ width: '100%' }} placeholder="1-3650" />
          </Form.Item>
          <Form.Item
            name="batchNo"
            label="批次号"
            extra="留空则使用生成时间戳，便于按批次筛选与管理"
          >
            <Input placeholder="如：2026双十一（可选，最多 32 字）" maxLength={32} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 生成结果弹窗：只读逐行展示纯码，便于整批复制分发 */}
      <Modal
        title={result ? `生成成功 · 共 ${result.codes?.length || 0} 张` : ''}
        open={!!result}
        onCancel={() => setResult(null)}
        footer={[
          <Button key="copy" icon={<CopyOutlined />} onClick={handleCopyAll}>复制全部</Button>,
          <Button key="ok" type="primary" onClick={() => setResult(null)}>完成</Button>,
        ]}
        width={480}
        destroyOnHidden
      >
        <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
          批次号 {result?.batchNo || '—'}。兑换码为一次性凭证，请及时复制分发给用户。
        </Text>
        <Input.TextArea
          readOnly
          value={(result?.codes || []).map((c) => c.code).join('\n')}
          rows={Math.min(Math.max(result?.codes?.length || 3, 3), 12)}
          style={{ fontFamily: CODE_FONT }}
        />
      </Modal>
    </AnimatedRoute>
  )
}
