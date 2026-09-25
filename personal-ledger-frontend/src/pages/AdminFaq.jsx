import { useState, useEffect } from 'react'
import { Table, Button, Card, Modal, Form, Input, Select, Tag, Space, Popconfirm, App as AntdApp } from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined, SyncOutlined } from '@ant-design/icons'
import { listFaq, createFaq, updateFaq, deleteFaq, rebuildFaqIndex } from '../api/faq'
import SectionTitle from '../components/ui/SectionTitle'
import EmptyState from '../components/ui/EmptyState'
import SkeletonCard from '../components/ui/SkeletonCard'
import AnimatedRoute from '../components/ui/AnimatedRoute'

const { TextArea } = Input

const CATEGORY_OPTIONS = ['记账操作', '账单查询', '统计分析', '预算管理', '其他']

export default function AdminFaq() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [rebuilding, setRebuilding] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null) // null=新增，否则为待编辑行
  const [submitting, setSubmitting] = useState(false)
  const [form] = Form.useForm()
  const { message } = AntdApp.useApp()

  const fetchData = async () => {
    setLoading(true)
    const res = await listFaq()
    if (res.code === 200) setData(res.data)
    setLoading(false)
  }

  useEffect(() => { fetchData() }, [])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (record) => {
    setEditing(record)
    form.setFieldsValue(record)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    setSubmitting(true)
    const res = editing
      ? await updateFaq(editing.id, values)
      : await createFaq(values)
    setSubmitting(false)
    if (res.code === 200) {
      message.success(editing ? '更新成功' : '创建成功')
      setModalOpen(false)
      fetchData()
    } else {
      message.error(res.message)
    }
  }

  const handleDelete = async (id) => {
    const res = await deleteFaq(id)
    if (res.code === 200) {
      message.success('删除成功')
      fetchData()
    } else {
      message.error(res.message)
    }
  }

  const handleRebuild = async () => {
    setRebuilding(true)
    const res = await rebuildFaqIndex()
    setRebuilding(false)
    // 该接口为 AI 模块裸返回：成功 {success,count}，失败 {error}
    if (res.success) {
      message.success(`索引重建完成，共 ${res.count} 条`)
    } else {
      message.error(res.error || '重建失败')
    }
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
    {
      title: '问题',
      dataIndex: 'question',
      key: 'question',
      render: (text) => <strong>{text}</strong>,
    },
    {
      title: '回答',
      dataIndex: 'answer',
      key: 'answer',
      ellipsis: true,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} style={{ padding: '4px 8px' }} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除"
            description="删除后需重建索引才会从 AI 检索中移除"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />} style={{ padding: '4px 8px' }}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const renderContent = () => {
    if (loading) return <SkeletonCard type="table" rows={6} />
    if (data.length === 0) return <EmptyState title="暂无 FAQ" description="点击「新增 FAQ」添加知识库条目" />
    return (
      <Table
        dataSource={data}
        columns={columns}
        rowKey="id"
        size="middle"
        pagination={false}
      />
    )
  }

  return (
    <AnimatedRoute>
      <Card
        title={<SectionTitle title="FAQ 管理" />}
        variant="borderless"
        className="card-base"
      >
        <div style={{ marginBottom: 24, display: 'flex', gap: 'var(--space-md)', flexWrap: 'wrap' }}>
          <Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增 FAQ</Button>
            <Button icon={<SyncOutlined spin={rebuilding} />} loading={rebuilding} onClick={handleRebuild}>
              重建向量索引
            </Button>
          </Space>
        </div>

        {renderContent()}

        <Modal
          title={editing ? `编辑 FAQ #${editing.id}` : '新增 FAQ'}
          open={modalOpen}
          onOk={handleSubmit}
          onCancel={() => setModalOpen(false)}
          confirmLoading={submitting}
          okText="保存"
          cancelText="取消"
          destroyOnHidden
        >
          <Form form={form} layout="vertical">
            <Form.Item
              name="question"
              label="问题"
              rules={[{ required: true, message: '请输入问题' }]}
            >
              <Input placeholder="如：如何添加一笔消费记录？" maxLength={200} />
            </Form.Item>
            <Form.Item
              name="answer"
              label="回答"
              rules={[{ required: true, message: '请输入回答' }]}
            >
              <TextArea rows={4} placeholder="问题的标准答案" maxLength={1000} />
            </Form.Item>
            <Form.Item
              name="category"
              label="分类"
              rules={[{ required: true, message: '请选择或输入分类' }]}
            >
              <Select
                showAllowClear={false}
                options={CATEGORY_OPTIONS.map((c) => ({ value: c, label: c }))}
                placeholder="选择分类"
              />
            </Form.Item>
          </Form>
        </Modal>
      </Card>
    </AnimatedRoute>
  )
}
