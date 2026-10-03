import { useState, useEffect, useRef } from 'react'
import { Row, Col, Table, Button, Form, Input, Select, InputNumber, DatePicker, Space, Card, Tag, Typography, Tabs, Popconfirm, App as AntdApp } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined, ReloadOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getRecordPage, addRecord, updateRecord, deleteRecord } from '../api/record'
import { getCategoryList } from '../api/category'
import EmptyState from '../components/ui/EmptyState'
import Money from '../components/ui/Money'
import PageHeader from '../components/ui/PageHeader'
import SkeletonCard from '../components/ui/SkeletonCard'
import AnimatedRoute from '../components/ui/AnimatedRoute'
import useMediaQuery from '../hooks/useMediaQuery'

const { Text } = Typography

export default function Records() {
  const [data, setData] = useState({ records: [], total: 0, pages: 0, current: 1, size: 10 })
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState([])
  const [editing, setEditing] = useState(null)
  const [addForm] = Form.useForm()
  const [searchForm] = Form.useForm()
  const [query, setQuery] = useState({ page: 1, size: 10 })
  const isMobile = useMediaQuery('(max-width: 767px)')
  const [activeType, setActiveType] = useState('0')
  const [addLoading, setAddLoading] = useState(false)
  const [highlight, setHighlight] = useState(false)
  const formCardRef = useRef(null)
  const highlightTimer = useRef(null)
  const { message } = AntdApp.useApp()

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

  useEffect(() => () => clearTimeout(highlightTimer.current), [])

  const handleQuickAdd = async () => {
    try {
      const values = await addForm.validateFields()
      setAddLoading(true)
      const payload = {
        categoryId: values.categoryId,
        amount: values.amount,
        remark: values.remark,
        recordDate: values.recordDate.format('YYYY-MM-DD'),
      }
      const res = await addRecord(payload)
      if (res.code === 200) {
        message.success('记账成功')
        addForm.resetFields()
        addForm.setFieldsValue({ recordDate: dayjs() })
        fetchData({ page: 1, size: query.size })
      } else {
        message.error(res.message)
      }
    } catch (e) {
      // validation error
    } finally {
      setAddLoading(false)
    }
  }

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

  const handleEdit = (record) => {
    setEditing(record)
    setActiveType(String(record.categoryType))
    addForm.setFieldsValue({
      categoryId: record.categoryId,
      amount: record.amount,
      remark: record.remark,
      recordDate: dayjs(record.recordDate),
    })
    // 滚动定位到表单卡并短暂高亮，让"编辑"有着落点
    formCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    setHighlight(true)
    clearTimeout(highlightTimer.current)
    highlightTimer.current = setTimeout(() => setHighlight(false), 1600)
  }

  const handleDelete = async (id) => {
    const res = await deleteRecord(id)
    if (res.code === 200) {
      message.success('删除成功')
      fetchData(query)
    } else {
      message.error(res.message)
    }
  }

  const handleCancelEdit = () => {
    setEditing(null)
    addForm.resetFields()
    addForm.setFieldsValue({ recordDate: dayjs(), categoryId: undefined })
  }

  const expenseCategories = categories.filter(c => c.type === 0)
  const incomeCategories = categories.filter(c => c.type === 1)
  const filteredCategories = activeType === '0' ? expenseCategories : incomeCategories

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
      width: 130,
      render: (v, r) => (
        <Money value={v} categoryType={r.categoryType} signed />
      ),
    },
    {
      title: '备注',
      dataIndex: 'remark',
      responsive: ['lg'],
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 140,
      responsive: ['md'],
      render: (_, record) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)} className="table-action">
            编辑
          </Button>
          <Popconfirm
            title="确认删除"
            description="删除后无法恢复，确定删除该账单？"
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            okType="danger"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />} className="table-action">
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <AnimatedRoute>
      <PageHeader title="账单管理" />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* 记账区域 - 核心 */}
        <div ref={formCardRef}>
        <Card
          variant="borderless"
          className="card-base"
          style={highlight ? { boxShadow: '0 0 0 3px rgba(26, 26, 46, 0.35), var(--shadow-md)', transition: 'box-shadow var(--transition-base)' } : { transition: 'box-shadow var(--transition-base)' }}
          styles={{ body: { padding: isMobile ? 20 : 28 } }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
            <div className="gradient-icon gradient-icon--primary" style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-md)',
            }}>
              <PlusOutlined style={{ color: '#fff', fontSize: 16 }} />
            </div>
            <Text strong style={{ fontSize: 18 }}>{editing ? '编辑账单' : '快速记账'}</Text>
          </div>

          <Tabs
            activeKey={activeType}
            onChange={setActiveType}
            items={[
              { key: '0', label: <span><ArrowUpOutlined style={{ color: 'var(--color-expense)' }} /> 支出</span> },
              { key: '1', label: <span><ArrowDownOutlined style={{ color: 'var(--color-income)' }} /> 收入</span> },
            ]}
            style={{ marginBottom: 16 }}
          />

          <Form
            form={addForm}
            layout="vertical"
            initialValues={{ recordDate: dayjs() }}
            onFinish={handleQuickAdd}
          >
            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item name="categoryId" label="分类" rules={[{ required: true, message: '请选择' }]} style={{ marginBottom: isMobile ? 12 : 16 }}>
                  <Select placeholder="选择分类" size="large">
                    {filteredCategories.map(c => (
                      <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item name="amount" label="金额" rules={[{ required: true, message: '请输入金额' }]} style={{ marginBottom: isMobile ? 12 : 16 }}>
                  <InputNumber
                    min={0.01}
                    precision={2}
                    placeholder="0.00"
                    prefix="¥"
                    size="large"
                    style={{ width: '100%' }}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item name="recordDate" label="日期" rules={[{ required: true, message: '请选择日期' }]} style={{ marginBottom: isMobile ? 12 : 16 }}>
                  <DatePicker style={{ width: '100%' }} size="large" />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} sm={16}>
                <Form.Item name="remark" label="备注" style={{ marginBottom: 16 }}>
                  <Input.TextArea placeholder="添加备注（可选）" rows={1} autoSize={{ minRows: 1, maxRows: 3 }} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item style={{ marginBottom: 0 }}>
                  <Space style={{ width: '100%' }} direction={isMobile ? 'vertical' : 'horizontal'}>
                    {editing && (
                      <Button size="large" onClick={handleCancelEdit} style={{ flex: 1 }}>
                        取消
                      </Button>
                    )}
                    <Button
                      type="primary"
                      htmlType="submit"
                      size="large"
                      loading={addLoading}
                      icon={<PlusOutlined />}
                      style={{
                        flex: 1,
                        height: 44,
                        fontWeight: 600,
                        borderRadius: 'var(--radius-md)',
                      }}
                    >
                      {editing ? '保存修改' : '记一笔'}
                    </Button>
                  </Space>
                </Form.Item>
              </Col>
            </Row>
          </Form>
        </Card>
        </div>

        {/* 账单列表 */}
        <Card
          title={<Text strong style={{ fontSize: 16 }}>最近账单</Text>}
          extra={
            <Text type="secondary" style={{ fontSize: 13 }}>
              共 {data.total} 条记录
            </Text>
          }
          variant="borderless"
          className="card-base"
          styles={{ body: { padding: isMobile ? 16 : 24 } }}
        >
          {/* 搜索 */}
          <Form form={searchForm} layout={isMobile ? 'vertical' : 'inline'} style={{ marginBottom: 16 }}>
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
                <Button icon={<SearchOutlined />} onClick={handleSearch}>查询</Button>
                <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
              </Space>
            </Form.Item>
          </Form>

          {/* 表格 */}
          {loading ? (
            <SkeletonCard type="table" rows={5} />
          ) : data.records.length === 0 ? (
            <EmptyState title="暂无账单" description="开始记一笔吧" />
          ) : (
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
              scroll={{ x: 700 }}
            />
          )}
        </Card>
      </div>
    </AnimatedRoute>
  )
}
