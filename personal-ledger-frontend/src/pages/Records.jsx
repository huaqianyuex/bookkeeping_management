import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, InputNumber, DatePicker, Space, message, Card, Tag } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getRecordPage, addRecord, updateRecord, deleteRecord } from '../api/record'
import { getCategoryList } from '../api/category'

export default function Records() {
  const [data, setData] = useState({ records: [], total: 0, pages: 0, current: 1, size: 10 })
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState([])
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [searchForm] = Form.useForm()
  const [form] = Form.useForm()
  const [query, setQuery] = useState({ page: 1, size: 10 })

  const fetchCategories = async () => {
    const res = await getCategoryList()
    if (res.code === 200) setCategories(res.data)
  }

  const fetchData = async (params) => {
    setLoading(true)
    const res = await getRecordPage(params || query)
    if (res.code === 200) setData(res.data)
    setLoading(false)
  }

  useEffect(() => { fetchCategories(); fetchData() }, [])

  const handleSearch = () => {
    const values = searchForm.getFieldsValue()
    const params = {
      page: 1,
      size: 10,
      categoryId: values.categoryId || undefined,
      month: values.month ? values.month.format('YYYY-MM') : undefined,
    }
    setQuery(params)
    fetchData(params)
  }

  const handleReset = () => {
    searchForm.resetFields()
    const params = { page: 1, size: 10 }
    setQuery(params)
    fetchData(params)
  }

  const handlePageChange = (page, size) => {
    const params = { ...query, page, size }
    setQuery(params)
    fetchData(params)
  }

  const handleAdd = () => {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  const handleEdit = async (record) => {
    setEditing(record)
    form.setFieldsValue({
      categoryId: record.categoryId,
      amount: record.amount,
      remark: record.remark,
      recordDate: dayjs(record.recordDate),
    })
    setModalOpen(true)
  }

  const handleDelete = async (id) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除该账单记录吗？',
      onOk: async () => {
        const res = await deleteRecord(id)
        if (res.code === 200) {
          message.success('删除成功')
          fetchData(query)
        } else {
          message.error(res.message)
        }
      },
    })
  }

  const handleOk = async () => {
    const values = await form.validateFields()
    const payload = {
      categoryId: values.categoryId,
      amount: values.amount,
      remark: values.remark,
      recordDate: values.recordDate.format('YYYY-MM-DD'),
    }
    let res
    if (editing) {
      res = await updateRecord(editing.id, payload)
    } else {
      res = await addRecord(payload)
    }
    if (res.code === 200) {
      message.success(editing ? '修改成功' : '新增成功')
      setModalOpen(false)
      fetchData(query)
    } else {
      message.error(res.message)
    }
  }

  const expenseCategories = categories.filter(c => c.type === 0)
  const incomeCategories = categories.filter(c => c.type === 1)

  const columns = [
    { title: '日期', dataIndex: 'recordDate', key: 'recordDate', width: 120 },
    {
      title: '类型', dataIndex: 'categoryType', key: 'categoryType', width: 70,
      render: (v) => v === 0 ? <Tag color="red">支出</Tag> : <Tag color="green">收入</Tag>,
    },
    { title: '分类', dataIndex: 'categoryName', key: 'categoryName', width: 100 },
    {
      title: '金额', dataIndex: 'amount', key: 'amount', width: 120,
      render: (v, r) => (
        <span style={{ color: r.categoryType === 0 ? '#f5222d' : '#52c41a', fontWeight: 'bold' }}>
          {r.categoryType === 0 ? '-' : '+'}¥{v.toFixed(2)}
        </span>
      ),
    },
    { title: '备注', dataIndex: 'remark', key: 'remark' },
    { title: '创建时间', dataIndex: 'createTime', key: 'createTime', width: 180 },
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
      title="账单管理" 
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新增账单</Button>}
      bordered={false} 
      style={{ boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03)' }}
    >
      <Form form={searchForm} layout="inline" style={{ marginBottom: 24 }}>
        <Form.Item name="categoryId" label="分类">
          <Select style={{ width: 140 }} placeholder="全部" allowClear>
            {categories.map(c => (
              <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item name="month" label="月份">
          <DatePicker picker="month" placeholder="选择月份" />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>查询</Button>
            <Button onClick={handleReset}>重置</Button>
          </Space>
        </Form.Item>
      </Form>

      <Table
        dataSource={data.records}
        columns={columns}
        rowKey="id"
        loading={loading}
        size="middle"
        pagination={{
          current: data.current,
          pageSize: data.size,
          total: data.total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: handlePageChange,
        }}
      />

      <Modal
        title={editing ? '编辑账单' : '新增账单'}
        open={modalOpen}
        onOk={handleOk}
        onCancel={() => setModalOpen(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="categoryId" label="分类" rules={[{ required: true, message: '请选择分类' }]}>
            <Select placeholder="请选择分类">
              <Select.OptGroup label="支出">
                {expenseCategories.map(c => (
                  <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>
                ))}
              </Select.OptGroup>
              <Select.OptGroup label="收入">
                {incomeCategories.map(c => (
                  <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>
                ))}
              </Select.OptGroup>
            </Select>
          </Form.Item>
          <Form.Item name="amount" label="金额" rules={[
            { required: true, message: '请输入金额' },
            { type: 'number', min: 0.01, message: '金额必须大于0' },
          ]}>
            <InputNumber style={{ width: '100%' }} precision={2} prefix="¥" placeholder="请输入金额" />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} placeholder="可选" />
          </Form.Item>
          <Form.Item name="recordDate" label="日期" rules={[{ required: true, message: '请选择日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
