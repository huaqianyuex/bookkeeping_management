import { useState, useEffect } from 'react'
import { Table, Card, Typography, Tag, DatePicker, Select, Space, Button, Popconfirm, InputNumber, Modal, App as AntdApp } from 'antd'
import { SearchOutlined, DeleteOutlined, ReloadOutlined, UserOutlined } from '@ant-design/icons'
import { getAdminRecords, batchDeleteAdminRecords } from '../api/admin'
import SectionTitle from '../components/ui/SectionTitle'
import EmptyState from '../components/ui/EmptyState'
import SkeletonCard from '../components/ui/SkeletonCard'
import AnimatedRoute from '../components/ui/AnimatedRoute'

const { Text } = Typography

export default function AdminRecords() {
  const [data, setData] = useState({ records: [], total: 0, pages: 0, current: 1, size: 10 })
  const [loading, setLoading] = useState(false)
  const [type, setType] = useState(null)
  const [month, setMonth] = useState(null)
  const [userId, setUserId] = useState(null)
  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const { message } = AntdApp.useApp()

  const fetchData = async (page = 1, size = 10, filterType = type, filterMonth = month, filterUserId = userId) => {
    setLoading(true)
    const params = { page, size }
    if (filterType !== null && filterType !== undefined) params.type = filterType
    if (filterMonth) params.month = filterMonth
    if (filterUserId) params.userId = filterUserId
    const res = await getAdminRecords(params)
    if (res.code === 200) setData(res.data)
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [])

  const handleSearch = () => {
    fetchData(1, data.size, type, month, userId)
  }

  const handleReset = () => {
    setType(null)
    setMonth(null)
    setUserId(null)
    setSelectedRowKeys([])
    fetchData(1, data.size, null, null, null)
  }

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要删除的账单')
      return
    }
    Modal.confirm({
      title: '确认批量删除',
      content: `确定要删除选中的 ${selectedRowKeys.length} 条账单吗？`,
      onOk: async () => {
        const res = await batchDeleteAdminRecords(selectedRowKeys)
        if (res.code === 200) {
          message.success('批量删除成功')
          setSelectedRowKeys([])
          fetchData(data.current, data.size)
        } else {
          message.error(res.message)
        }
      },
    })
  }

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '用户',
      dataIndex: 'username',
      key: 'username',
      render: (text, record) => (
        <div>
          <Text strong>{text || '-'}</Text>
          <Text className="text-tertiary" style={{ fontSize: 'var(--font-size-xs)', marginLeft: 4 }}>
            ID:{record.userId}
          </Text>
        </div>
      ),
    },
    {
      title: '日期',
      dataIndex: 'recordDate',
      key: 'recordDate',
    },
    {
      title: '类型',
      dataIndex: 'categoryType',
      key: 'categoryType',
      width: 80,
      render: (v) => (
        <Tag color={v === 0 ? 'error' : 'success'}>{v === 0 ? '支出' : '收入'}</Tag>
      ),
    },
    {
      title: '分类',
      dataIndex: 'categoryName',
      key: 'categoryName',
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      render: (v, r) => (
        <Text strong style={{ color: r.categoryType === 0 ? 'var(--color-danger)' : 'var(--color-success)' }}>
          {r.categoryType === 0 ? '-' : '+'}¥{v.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '备注',
      dataIndex: 'remark',
      key: 'remark',
    },
    {
      title: '创建时间',
      dataIndex: 'createTime',
      key: 'createTime',
      width: 180,
      render: (text) => <Text style={{ fontSize: 'var(--font-size-sm)' }}>{text}</Text>,
    },
  ]

  const renderContent = () => {
    if (loading) return <SkeletonCard type="table" rows={6} />
    if (data.records.length === 0) return <EmptyState title="暂无账单数据" description="没有找到匹配的账单记录" />
    return (
      <Table
        dataSource={data.records}
        columns={columns}
        rowKey="id"
        size="middle"
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys),
        }}
        pagination={{
          current: data.current,
          pageSize: data.size,
          total: data.total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (page, size) => fetchData(page, size),
        }}
      />
    )
  }

  return (
    <AnimatedRoute>
      <Card
        title={<SectionTitle title="全量账单" />}
        variant="borderless"
        className="card-base"
      >
        <div style={{
          marginBottom: 24,
          display: 'flex',
          gap: 'var(--space-md)',
          flexWrap: 'wrap',
          alignItems: 'center',
        }}>
          <InputNumber
            placeholder="用户ID"
            value={userId}
            onChange={(v) => setUserId(v)}
            min={1}
            precision={0}
            style={{ width: 120 }}
            prefix={<UserOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
          />
          <Select
            placeholder="类型筛选"
            value={type}
            onChange={(v) => setType(v)}
            allowClear
            style={{ width: 140 }}
          >
            <Select.Option value={0}>支出</Select.Option>
            <Select.Option value={1}>收入</Select.Option>
          </Select>
          <DatePicker
            picker="month"
            placeholder="月份筛选"
            value={month}
            onChange={(d) => setMonth(d)}
            style={{ width: 160 }}
          />
          <Space>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>查询</Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
            {selectedRowKeys.length > 0 && (
              <Popconfirm
                title="确认批量删除"
                description={`确定要删除 ${selectedRowKeys.length} 条账单吗？`}
                onConfirm={handleBatchDelete}
                okText="确认"
                cancelText="取消"
              >
                <Button type="primary" danger icon={<DeleteOutlined />}>
                  批量删除 ({selectedRowKeys.length})
                </Button>
              </Popconfirm>
            )}
          </Space>
        </div>

        {renderContent()}
      </Card>
    </AnimatedRoute>
  )
}
