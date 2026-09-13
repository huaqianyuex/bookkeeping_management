import { useState, useEffect, useMemo } from 'react'
import { Layout, Menu, Avatar, Dropdown, Button, theme, Drawer, Typography, Modal, Form, Input, Select, InputNumber, DatePicker, Space, App as AntdApp } from 'antd'
import {
  DashboardOutlined,
  BookOutlined,
  AppstoreOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  WalletOutlined,
  LockOutlined,
  SafetyOutlined,
  TeamOutlined,
  FileTextOutlined,
  RobotOutlined,
  HomeOutlined,
  PlusCircleOutlined,
  LineChartOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import AiChatDrawer from './AiChatDrawer'
import { getCategoryList } from '../api/category'
import { addRecord } from '../api/record'
import dayjs from 'dayjs'

const { Header, Sider, Content } = Layout
const { Text } = Typography

const menuItems = [
  { key: '/records',   icon: <BookOutlined />,      label: '账单管理' },
  { key: '/categories', icon: <AppstoreOutlined />,  label: '分类管理' },
  { key: '/ai-chat',   icon: <RobotOutlined />,     label: 'AI助手' },
]

const adminMenuItems = [
  { key: '/admin/dashboard', icon: <SafetyOutlined />,   label: '系统概览' },
  { key: '/admin/users',    icon: <TeamOutlined />,      label: '用户管理' },
  { key: '/admin/records',  icon: <FileTextOutlined />,  label: '全量账单' },
]

const breadcrumbMap = {
  '/dashboard': '数据概览',
  '/records': '账单管理',
  '/categories': '分类管理',
  '/user-info': '个人信息',
  '/change-password': '修改密码',
  '/ai-chat': 'AI助手',
  '/admin/dashboard': '系统概览',
  '/admin/users': '用户管理',
  '/admin/records': '全量账单',
}

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768)
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [categories, setCategories] = useState([])
  const [form] = Form.useForm()
  const [addLoading, setAddLoading] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, fetchUserInfo, logout } = useAuth()
  const { token: { colorBgContainer } } = theme.useToken()
  const { message } = AntdApp.useApp()

  useEffect(() => {
    getCategoryList().then(res => {
      if (res.code === 200) setCategories(res.data)
    })
  }, [])

  const handleQuickAdd = async () => {
    try {
      const values = await form.validateFields()
      setAddLoading(true)
      const data = {
        ...values,
        recordDate: values.recordDate.format('YYYY-MM-DD'),
      }
      const res = await addRecord(data)
      if (res.code === 200) {
        message.success('记账成功')
        setAddModalOpen(false)
        form.resetFields()
        window.dispatchEvent(new CustomEvent('record-added'))
      } else {
        message.error(res.message)
      }
    } catch (e) {
      // validation error
    } finally {
      setAddLoading(false)
    }
  }

  useEffect(() => {
    fetchUserInfo()

    const handleResize = () => {
      const mobile = window.innerWidth < 768
      setIsMobile(mobile)
      if (!mobile) setDrawerOpen(false)
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const userMenuItems = [
    {
      key: 'info',
      icon: <UserOutlined />,
      label: '个人信息',
      onClick: () => navigate('/user-info'),
    },
    {
      key: 'password',
      icon: <LockOutlined />,
      label: '修改密码',
      onClick: () => navigate('/change-password'),
    },
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ]

  const allMenuItems = useMemo(() => {
    if (user?.role === 1) {
      return [...menuItems, { type: 'divider' }, ...adminMenuItems]
    }
    return menuItems
  }, [user?.role])

  const currentPageTitle = useMemo(() => {
    return breadcrumbMap[location.pathname] || ''
  }, [location.pathname])

  const siderContent = (
    <>
      <div style={{
        height: 64,
        display: 'flex',
        alignItems: 'center',
        justifyContent: isMobile ? 'center' : 'flex-start',
        padding: isMobile ? '0' : '0 24px',
        borderBottom: '1px solid var(--color-border)',
      }}>
        <div className="gradient-icon--primary" style={{
          width: 36,
          height: 36,
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginRight: collapsed || isMobile ? '0' : '12px',
        }}>
          <WalletOutlined style={{ fontSize: 18, color: '#fff' }} />
        </div>
        {(!collapsed || isMobile) && (
          <Text strong style={{
            fontSize: 'var(--font-size-lg)',
            color: 'var(--color-text)',
            letterSpacing: '0.5px',
          }}>
            记账本
          </Text>
        )}
      </div>

      <div style={{ padding: '16px 12px 8px' }}>
        <Button
          type="primary"
          icon={<PlusCircleOutlined />}
          block
          size="large"
          collapsed={collapsed}
          onClick={() => setAddModalOpen(true)}
          style={{
            height: 48,
            fontSize: 16,
            fontWeight: 600,
            borderRadius: 12,
            boxShadow: '0 4px 12px rgba(26, 26, 46, 0.25)',
          }}
        >
          {collapsed ? '' : '快速记账'}
        </Button>
      </div>

      <Menu
        theme="light"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={allMenuItems}
        style={{
          borderRight: 0,
          padding: '8px 8px',
        }}
        onClick={({ key }) => {
          navigate(key)
          if (isMobile) setDrawerOpen(false)
        }}
      />
    </>
  )

  return (
    <Layout style={{ minHeight: '100vh', position: 'relative', background: 'var(--color-bg)' }}>
      {isMobile ? (
        <Drawer
          placement="left"
          onClose={() => setDrawerOpen(false)}
          open={drawerOpen}
          width={260}
          styles={{ body: { padding: 0, margin: 0 } }}
          closable={false}
        >
          {siderContent}
        </Drawer>
      ) : (
        <Sider
          trigger={null}
          collapsible
          collapsed={collapsed}
          theme="light"
          width={240}
          collapsedWidth={72}
          style={{
            borderRight: 'none',
            boxShadow: 'var(--shadow-sider)',
          }}
        >
          {siderContent}
        </Sider>
      )}
      <Layout>
        <Header style={{
          padding: isMobile ? '0 16px' : '0 24px',
          background: colorBgContainer,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid var(--color-border)',
          height: 64,
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {isMobile ? (
              <Button
                type="text"
                icon={<MenuUnfoldOutlined />}
                onClick={() => setDrawerOpen(true)}
                style={{ fontSize: 18 }}
              />
            ) : (
              <Button
                type="text"
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setCollapsed(!collapsed)}
                style={{ fontSize: 18 }}
              />
            )}
            {!isMobile && currentPageTitle && (
              <div className="breadcrumb-nav">
                <HomeOutlined style={{ marginRight: 6 }} />
                <span style={{ color: 'var(--color-text-tertiary)' }}>首页</span>
                <span style={{ margin: '0 6px', color: 'var(--color-text-tertiary)' }}>/</span>
                <span className="breadcrumb-current">{currentPageTitle}</span>
              </div>
            )}
          </div>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Button
              type="text"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                transition: 'all var(--transition-fast)',
              }}
            >
              <Avatar
                size="small"
                icon={<UserOutlined />}
                style={{ backgroundColor: 'var(--color-primary)' }}
              />
              {!isMobile && (
                <Text style={{ color: 'var(--color-text)', fontWeight: 500 }}>
                  {user?.username || '加载中...'}
                </Text>
              )}
            </Button>
          </Dropdown>
        </Header>
        <Content style={{
          margin: isMobile ? '16px' : '24px auto',
          padding: 0,
          width: '100%',
          maxWidth: 1200,
        }}>
          <Outlet />
        </Content>
      </Layout>
      <AiChatDrawer open={location.pathname === '/ai-chat'} />

      {/* 浮动记账按钮 - 仅移动端显示 */}
      {isMobile && (
        <div
          onClick={() => setAddModalOpen(true)}
          style={{
            position: 'fixed',
            bottom: 80,
            right: 20,
            width: 56,
            height: 56,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 16px rgba(26, 26, 46, 0.4)',
            zIndex: 999,
            cursor: 'pointer',
          }}
        >
          <PlusCircleOutlined style={{ fontSize: 24, color: '#fff' }} />
        </div>
      )}

      {/* 快速记账弹窗 */}
      <Modal
        title="快速记账"
        open={addModalOpen}
        onOk={handleQuickAdd}
        onCancel={() => { setAddModalOpen(false); form.resetFields() }}
        confirmLoading={addLoading}
        okText="保存"
        cancelText="取消"
        width={480}
      >
        <Form form={form} layout="vertical" initialValues={{ recordDate: dayjs() }}>
          <Form.Item name="categoryId" label="分类" rules={[{ required: true, message: '请选择分类' }]}>
            <Select placeholder="选择分类">
              {categories.filter(c => c.type === 0).map(c => (
                <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>
              ))}
              <Select.Option disabled label="收入" />
              {categories.filter(c => c.type === 1).map(c => (
                <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="amount" label="金额" rules={[{ required: true, message: '请输入金额' }]}>
            <InputNumber
              min={0.01}
              precision={2}
              placeholder="0.00"
              style={{ width: '100%' }}
              prefix="¥"
              size="large"
            />
          </Form.Item>
          <Form.Item name="recordDate" label="日期" rules={[{ required: true, message: '请选择日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea placeholder="添加备注（可选）" rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  )
}
