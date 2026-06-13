import './styles/design-tokens.css'
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, App as AntdApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { AuthProvider } from './context/AuthContext'
import MainLayout from './components/MainLayout'
import AuthRoute from './components/AuthRoute'
import AdminRoute from './components/AdminRoute'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Records from './pages/Records'
import Categories from './pages/Categories'
import UserInfo from './pages/UserInfo'
import ChangePassword from './pages/ChangePassword'
import AdminDashboard from './pages/AdminDashboard'
import AdminUsers from './pages/AdminUsers'
import AdminRecords from './pages/AdminRecords'
import AiChatPage from './pages/AiChat'

function AppContent() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={
        <AuthRoute>
          <MainLayout />
        </AuthRoute>
      }>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="records" element={<Records />} />
        <Route path="categories" element={<Categories />} />
        <Route path="user-info" element={<UserInfo />} />
        <Route path="change-password" element={<ChangePassword />} />
        <Route path="admin/dashboard" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
        <Route path="admin/users" element={<AdminRoute><AdminUsers /></AdminRoute>} />
        <Route path="admin/records" element={<AdminRoute><AdminRecords /></AdminRoute>} />
        <Route path="ai-chat" element={<AiChatPage />} />
      </Route>
    </Routes>
  )
}

const customTheme = {
  token: {
    colorPrimary: '#1a1a2e',
    colorPrimaryBg: '#f0f0ff',
    colorBgLayout: '#f5f5f7',
    colorBgContainer: '#ffffff',
    colorBorder: '#e5e5ea',
    colorBorderSecondary: '#eaeaef',
    colorText: '#1a1a2e',
    colorTextSecondary: '#636e72',
    borderRadius: 10,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  components: {
    Layout: {
      siderBg: '#ffffff',
      headerBg: '#ffffff',
      bodyBg: '#f5f5f7',
      triggerBg: '#f5f5f7',
    },
    Menu: {
      itemBg: '#ffffff',
      itemActiveBg: '#f0f0ff',
      itemSelectedBg: '#f0f0ff',
      itemSelectedColor: '#1a1a2e',
      itemHoverBg: '#f8f8fa',
      itemColor: '#636e72',
      itemBorderRadius: 8,
      itemMarginInline: 8,
      itemPaddingInline: 16,
    },
    Card: {
      headerBg: 'transparent',
      borderRadiusLG: 12,
    },
    Button: {
      primaryShadow: '0 2px 8px rgba(26, 26, 46, 0.2)',
    },
    Input: {
      activeBorderColor: '#1a1a2e',
      hoverBorderColor: '#636e72',
    },
    Table: {
      headerBg: '#fafafa',
      headerColor: '#636e72',
      rowHoverBg: '#f8f8fa',
    },
    Tag: {
      borderRadiusSM: 6,
    },
    Empty: {
      colorTextDisabled: '#b2bec3',
    },
  },
}

export default function App() {
  return (
    <ConfigProvider locale={zhCN} theme={customTheme}>
      <AntdApp>
        <AuthProvider>
          <HashRouter>
            <AppContent />
          </HashRouter>
        </AuthProvider>
      </AntdApp>
    </ConfigProvider>
  )
}
