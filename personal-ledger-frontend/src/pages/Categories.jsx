import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, Space, message, Card, Tag } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { getCategoryList, addCategory, updateCategory, deleteCategory } from '../api/category'

export default function Categories() {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form] = Form.useForm()

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
    Modal.confirm({
      title: '确认删除',
      content: '删除后关联账单的分类名称将保留，确定删除？',
      onOk: async () => {
        const res = await deleteCategory(id)
        if (res.code === 200) {
          message.success('删除成功')
          fetchList()
        } else {
          message.error(res.message)
        }
      },
    })
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
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: '名称', dataIndex: 'name', key: 'name' },
    {
      title: '类型', dataIndex: 'type', key: 'type',
      render: (v) => v === 0 ? <Tag color="red">支出</Tag> : <Tag color="green">收入</Tag>,
    },
    { title: '创建时间', dataIndex: 'createTime', key: 'createTime' },
    {
      title: '操作', key: 'action', width: 160,
      render: (_, record) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>删除</Button>
        </Space>
      ),
    },
  ]

  return (
    <Card 
      title="分类管理" 
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新增分类</Button>}
      bordered={false} 
      style={{ boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)' }}
    >
      <Table dataSource={list} columns={columns} rowKey="id" loading={loading} pagination={false} size="middle" />
      <Modal

        title={editing ? '编辑分类' : '新增分类'}
        open={modalOpen}
        onOk={handleOk}
        onCancel={() => setModalOpen(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
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
    </Card>
  )
}
