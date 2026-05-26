import { useEffect } from 'react'
import { Layout, Menu, Avatar, Dropdown, Button, theme } from 'antd'
import {
  DashboardOutlined,
  BookOutlined,
  AppstoreOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/dashboard', icon: <DashboardOutlined />, label: '数据概览' },
  { key: '/records', icon: <BookOutlined />, label: '账单管理' },
  { key: '/categories', icon: <AppstoreOutlined />, label: '分类管理' },
]

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, fetchUserInfo, logout } = useAuth()
  const { token: { colorBgContainer, borderRadiusLG } } = theme.useToken()

  useEffect(() => {
    fetchUserInfo()
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const userMenuItems = [
    { key: 'info', icon: <UserOutlined />, label: '个人信息', onClick: () => navigate('/user-info') },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', onClick: handleLogout },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider 
        trigger={null} 
        collapsible 
        theme="light"
        style={{ borderRight: '1px solid #f0f0f0' }}
      >
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          color: '#18181b', 
          fontSize: 20, 
          fontWeight: 600,
          letterSpacing: 1
        }}>
          记账本
        </div>
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          style={{ borderRight: 0 }}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ 
          padding: '0 24px', 
          background: colorBgContainer, 
          display: 'flex', 
          justifyContent: 'flex-end', 
          alignItems: 'center',
          borderBottom: '1px solid #f0f0f0',
          height: 64,
        }}>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Button type="text" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Avatar size="small" icon={<UserOutlined />} style={{ backgroundColor: '#18181b' }} />
              {user?.username || '加载中...'}
            </Button>
          </Dropdown>
        </Header>
        <Content style={{ margin: '24px auto', padding: 0, width: '100%', maxWidth: 1200 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
