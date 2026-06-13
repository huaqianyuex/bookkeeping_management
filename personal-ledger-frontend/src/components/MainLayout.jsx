import { useState, useEffect, useMemo } from 'react'
import { Layout, Menu, Avatar, Dropdown, Button, theme, Drawer, Typography } from 'antd'
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
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import AiChatDrawer from './AiChatDrawer'

const { Header, Sider, Content } = Layout
const { Text } = Typography

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '数据概览' },
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
  const navigate = useNavigate()
  const location = useLocation()
  const { user, fetchUserInfo, logout } = useAuth()
  const { token: { colorBgContainer } } = theme.useToken()

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
      <Menu
        theme="light"
        mode="inline"
        selectedKeys={[location.pathname]}
        items={allMenuItems}
        style={{
          borderRight: 0,
          padding: '12px 8px',
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
    </Layout>
  )
}
