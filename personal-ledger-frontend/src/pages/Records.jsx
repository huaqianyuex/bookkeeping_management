import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, InputNumber, DatePicker, Space, Card, Tag, Typography, App as AntdApp } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getRecordPage, addRecord, updateRecord, deleteRecord } from '../api/record'
import { getCategoryList } from '../api/category'
import SectionTitle from '../components/ui/SectionTitle'
import EmptyState from '../components/ui/EmptyState'
import SkeletonCard from '../components/ui/SkeletonCard'
import AnimatedRoute from '../components/ui/AnimatedRoute'

const { Text, Title } = Typography

export default function Records() {
  const [data, setData] = useState({ records: [], total: 0, pages: 0, current: 1, size: 10 })
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState([])
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState(null)
  const [searchForm] = Form.useForm()
  const [form] = Form.useForm()
  const [query, setQuery] = useState({ page: 1, size: 10 })
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768)
  const { message } = AntdApp.useApp()

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

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

  const renderMobileCard = (record) => (
    <Card
      key={record.id}
      className="card-base"
      style={{ marginBottom: 'var(--space-md)' }}
    >
      <div style={{ padding: 'var(--space-base)' }}>
        <div className="mobile-record-field">
          <span className="mobile-record-label">日期</span>
          <span className="mobile-record-value">{record.recordDate}</span>
        </div>
        <div className="mobile-record-field">
          <span className="mobile-record-label">类型</span>
          <Tag color={record.categoryType === 0 ? 'error' : 'success'}>
            {record.categoryType === 0 ? '支出' : '收入'}
          </Tag>
        </div>
        <div className="mobile-record-field">
          <span className="mobile-record-label">分类</span>
          <span className="mobile-record-value">{record.categoryName}</span>
        </div>
        <div className="mobile-record-field">
          <span className="mobile-record-label">金额</span>
          <span className="mobile-record-value" style={{
            color: record.categoryType === 0 ? 'var(--color-danger)' : 'var(--color-success)',
            fontWeight: 600,
          }}>
            {record.categoryType === 0 ? '-' : '+'}¥{record.amount.toFixed(2)}
          </span>
        </div>
        {record.remark && (
          <div className="mobile-record-field">
            <span className="mobile-record-label">备注</span>
            <span className="mobile-record-value" style={{ color: 'var(--color-text-secondary)' }}>
              {record.remark}
            </span>
          </div>
        )}
        <div className="mobile-record-actions">
          <Button
            type="primary"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            style={{ flex: 1, borderRadius: 'var(--radius-md)' }}
          >
            编辑
          </Button>
          <Button
            type="primary"
            danger
            size="small"
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
            style={{ flex: 1, borderRadius: 'var(--radius-md)' }}
          >
            删除
          </Button>
        </div>
      </div>
    </Card>
  )

  const columns = [
    {
      title: '日期',
      dataIndex: 'recordDate',
      key: 'recordDate',
      width: 120,
      responsive: ['md'],
    },
    {
      title: '类型',
      dataIndex: 'categoryType',
      key: 'categoryType',
      width: 80,
      responsive: ['md'],
      render: (v) => (
        <Tag color={v === 0 ? 'error' : 'success'}>{v === 0 ? '支出' : '收入'}</Tag>
      ),
    },
    {
      title: '分类',
      dataIndex: 'categoryName',
      key: 'categoryName',
      width: 100,
      responsive: ['md'],
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
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
      responsive: ['lg'],
    },
    {
      title: '创建时间',
      dataIndex: 'createTime',
      key: 'createTime',
      width: 180,
      responsive: ['xl'],
      render: (text) => <Text style={{ fontSize: 'var(--font-size-sm)' }}>{text}</Text>,
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      responsive: ['md'],
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            style={{ padding: '4px 8px' }}
          >
            编辑
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
            style={{ padding: '4px 8px' }}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ]

  const renderDesktopTable = () => {
    if (loading) {
      return <SkeletonCard type="table" rows={6} />
    }
    if (data.records.length === 0) {
      return <EmptyState title="暂无账单记录" description="点击右上角「新增账单」开始记录" />
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
          onChange: handlePageChange,
        }}
      />
    )
  }

  const renderMobileCards = () => {
    if (loading) {
      return (
        <>
          {[1, 2, 3].map(i => <SkeletonCard key={i} type="list" lines={3} />)}
        </>
      )
    }
    if (data.records.length === 0) {
      return <EmptyState title="暂无账单记录" description="点击右上角按钮开始记录" />
    }
    return (
      <>
        {data.records.map(renderMobileCard)}
        <div style={{ marginTop: 'var(--space-base)', textAlign: 'center' }}>
          <Button
            onClick={() => handlePageChange(data.current - 1, data.size)}
            disabled={data.current <= 1}
            style={{ marginRight: 8, borderRadius: 'var(--radius-md)' }}
          >
            上一页
          </Button>
          <Text className="text-secondary">
            第 {data.current} / {Math.ceil(data.total / data.size)} 页
          </Text>
          <Button
            onClick={() => handlePageChange(data.current + 1, data.size)}
            disabled={data.current >= Math.ceil(data.total / data.size)}
            style={{ marginLeft: 8, borderRadius: 'var(--radius-md)' }}
          >
            下一页
          </Button>
        </div>
      </>
    )
  }

  return (
    <AnimatedRoute>
      <Card
        title={<SectionTitle title="账单管理" />}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAdd}
          >
            新增账单
          </Button>
        }
        variant="borderless"
        className="card-base"
      >
        {/* Search Form */}
        <Form
          form={searchForm}
          layout={isMobile ? 'vertical' : 'inline'}
          style={{ marginBottom: 24 }}
        >
          <Form.Item name="categoryId" label="分类" style={{ marginBottom: isMobile ? 12 : 8 }}>
            <Select style={{ width: isMobile ? '100%' : 140 }} placeholder="全部" allowClear>
              {categories.map(c => (
                <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="month" label="月份" style={{ marginBottom: isMobile ? 12 : 8 }}>
            <DatePicker picker="month" placeholder="选择月份" style={{ width: isMobile ? '100%' : undefined }} />
          </Form.Item>
          <Form.Item style={{ marginBottom: isMobile ? 12 : 8 }}>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>查询</Button>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
            </Space>
          </Form.Item>
        </Form>

        {/* Desktop Table */}
        <div className="desktop-table">{renderDesktopTable()}</div>

        {/* Mobile Cards */}
        <div className="mobile-cards" style={{ display: 'none' }}>{renderMobileCards()}</div>

        <style>{`
          @media (max-width: 768px) {
            .desktop-table { display: none !important; }
            .mobile-cards { display: block !important; }
          }
          @media (min-width: 769px) {
            .desktop-table { display: block !important; }
            .mobile-cards { display: none !important; }
          }
          .mobile-record-field {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
          }
          .mobile-record-label {
            color: var(--color-text-secondary);
            font-size: var(--font-size-sm);
          }
          .mobile-record-value {
            font-size: var(--font-size-base);
            font-weight: var(--font-weight-medium);
            color: var(--color-text);
          }
          .mobile-record-actions {
            display: flex;
            gap: 8px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--color-border);
          }
        `}</style>
      </Card>

      {/* Add/Edit Modal */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <span className="color-dot color-dot--primary" />
            <Text strong>{editing ? '编辑账单' : '新增账单'}</Text>
          </div>
        }
        open={modalOpen}
        onOk={handleOk}
        onCancel={() => setModalOpen(false)}
        destroyOnClose
        width={window.innerWidth < 768 ? '95%' : 520}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 24 }}>
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
    </AnimatedRoute>
  )
}
