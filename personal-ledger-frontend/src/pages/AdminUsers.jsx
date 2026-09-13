import { useState, useEffect } from 'react'
import { Table, Button, Card, Modal, Typography, Tag, Input, Space, Popconfirm, Switch, App as AntdApp } from 'antd'
import { SearchOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons'
import { getAdminUserList, deleteAdminUser, batchDeleteAdminUsers, updateAdminUserStatus } from '../api/admin'
import SectionTitle from '../components/ui/SectionTitle'
import EmptyState from '../components/ui/EmptyState'
import SkeletonCard from '../components/ui/SkeletonCard'
import AnimatedRoute from '../components/ui/AnimatedRoute'

const { Text } = Typography

export default function AdminUsers() {
  const [data, setData] = useState({ records: [], total: 0, pages: 0, current: 1, size: 10 })
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [selectedRowKeys, setSelectedRowKeys] = useState([])
  const { message } = AntdApp.useApp()

  const fetchData = async (page = 1, size = 10, kw = keyword) => {
    setLoading(true)
    const res = await getAdminUserList({ page, size, keyword: kw || undefined })
    if (res.code === 200) setData(res.data)
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [])

  const handleSearch = () => {
    fetchData(1, data.size, keyword)
  }

  const handleReset = () => {
    setKeyword('')
    fetchData(1, data.size, '')
  }

  const handleDelete = async (id) => {
    const res = await deleteAdminUser(id)
    if (res.code === 200) {
      message.success('删除成功')
      fetchData(data.current, data.size)
    } else {
      message.error(res.message)
    }
  }

  const handleToggleStatus = async (record) => {
    const next = record.status === 1 ? 0 : 1
    const res = await updateAdminUserStatus(record.id, next)
    if (res.code === 200) {
      message.success(next === 1 ? '已启用' : '已禁用')
      fetchData(data.current, data.size)
    } else {
      message.error(res.message)
    }
  }

  const handleBatchDelete = async () => {
    const deletable = selectedRowKeys.filter(id => {
      const user = data.records.find(u => u.id === id)
      return user && user.role !== 1
    })
    if (deletable.length === 0) {
      message.warning('所选用户均为管理员，不可删除')
      return
    }
    Modal.confirm({
      title: '确认批量删除',
      content: `确定要删除 ${deletable.length} 个用户及其所有数据吗？管理员账户将被跳过。`,
      onOk: async () => {
        const res = await batchDeleteAdminUsers(deletable)
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
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 100,
      render: (v) => (
        <Tag color={v === 1 ? 'gold' : 'default'}>{v === 1 ? '管理员' : '普通用户'}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (v, record) => (
        record.role === 1 ? (
          <Tag color="success">启用</Tag>
        ) : (
          <Popconfirm
            title={v === 1 ? '确认禁用' : '确认启用'}
            description={v === 1 ? '禁用后该账号将无法登录' : '启用后该账号可正常登录'}
            onConfirm={() => handleToggleStatus(record)}
            okText="确认"
            cancelText="取消"
          >
            <Switch size="small" checked={v === 1} />
          </Popconfirm>
        )
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createTime',
      key: 'createTime',
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        record.role === 1 ? (
          <Tag color="default">不可操作</Tag>
        ) : (
          <Popconfirm
            title="确认删除"
            description="删除后该用户的所有数据将被清除"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              style={{ padding: '4px 8px' }}
            >
              删除
            </Button>
          </Popconfirm>
        )
      ),
    },
  ]

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys) => setSelectedRowKeys(keys),
    getCheckboxProps: (record) => ({
      disabled: record.role === 1,
    }),
  }

  const renderContent = () => {
    if (loading) return <SkeletonCard type="table" rows={6} />
    if (data.records.length === 0) return <EmptyState title="暂无用户数据" description="没有找到匹配的用户" />
    return (
      <Table
        dataSource={data.records}
        columns={columns}
        rowKey="id"
        size="middle"
        rowSelection={rowSelection}
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
        title={<SectionTitle title="用户管理" />}
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
          <Input
            placeholder="搜索用户名"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onPressEnter={handleSearch}
            style={{ width: 240 }}
            prefix={<SearchOutlined style={{ color: 'var(--color-text-tertiary)' }} />}
          />
          <Space>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>搜索</Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
            {selectedRowKeys.length > 0 && (
              <Popconfirm
                title="确认批量删除"
                description={`确定要删除 ${selectedRowKeys.length} 个用户吗？`}
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
