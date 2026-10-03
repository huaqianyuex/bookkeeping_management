import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, Space, Card, Tag, Typography, Popconfirm, App as AntdApp } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { getCategoryList, addCategory, updateCategory, deleteCategory } from '../api/category'
import { PageHeader, EmptyState, SkeletonCard, AnimatedRoute } from '../components/ui'
import { formatDateTime } from '../utils/format'

const { Text } = Typography

export default function Categories() {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()

  const fetchList = async () => {
    setLoading(true)
    const res = await getCategoryList()
    if (res.code === 200) {
      setList(res.data)
    }
    setLoading(false)
  }

  useEffect(() => { fetchList() }, [])

  const handleAdd = () => {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  const handleEdit = (record) => {
    setEditing(record)
    form.setFieldsValue({ name: record.name, type: record.type })
    setModalOpen(true)
  }

  const handleDelete = async (id) => {
    const res = await deleteCategory(id)
    if (res.code === 200) {
      message.success('删除成功')
      fetchList()
    } else {
      message.error(res.message)
    }
  }

  const handleOk = async () => {
    const values = await form.validateFields()
    let res
    if (editing) {
      res = await updateCategory(editing.id, values)
    } else {
      res = await addCategory(values)
    }
    if (res.code === 200) {
      message.success(editing ? '修改成功' : '新增成功')
      setModalOpen(false)
      fetchList()
    } else {
      message.error(res.message)
    }
  }

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (v) => (
        <Tag color={v === 0 ? 'error' : 'success'}>{v === 0 ? '支出' : '收入'}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createTime',
      key: 'createTime',
      responsive: ['md'],
      render: (text) => <Text style={{ color: 'var(--color-text-secondary)' }}>{formatDateTime(text)}</Text>,
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            className="table-action"
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除"
            description="删除后关联账单的分类名称将保留，确定删除？"
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            okType="danger"
            cancelText="取消"
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              className="table-action"
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const renderContent = () => {
    if (loading) return <SkeletonCard type="table" rows={5} />
    if (list.length === 0) return <EmptyState title="暂无分类" description="点击右上角「新增分类」开始添加" />
    return (
      <Table
        dataSource={list}
        columns={columns}
        rowKey="id"
        size="middle"
        pagination={{ pageSize: 10, hideOnSinglePage: true, showTotal: (t) => `共 ${t} 条` }}
        scroll={{ x: 480 }}
        style={{ marginTop: 16 }}
      />
    )
  }

  return (
    <AnimatedRoute>
      <PageHeader
        title="分类管理"
        action={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增分类
          </Button>
        }
      />
      <Card variant="borderless" className="card-base">
        {renderContent()}
      </Card>

      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <span className="color-dot color-dot--primary" />
            <Text strong>{editing ? '编辑分类' : '新增分类'}</Text>
          </div>
        }
        open={modalOpen}
        onOk={handleOk}
        onCancel={() => setModalOpen(false)}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" style={{ marginTop: 24 }}>
          <Form.Item name="name" label="分类名称" rules={[{ required: true, message: '分类名称不能为空' }]}>
            <Input placeholder="请输入分类名称" />
          </Form.Item>
          <Form.Item name="type" label="分类类型" rules={[{ required: true, message: '请选择类型' }]}>
            <Select placeholder="请选择类型">
              <Select.Option value={0}>支出</Select.Option>
              <Select.Option value={1}>收入</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </AnimatedRoute>
  )
}
