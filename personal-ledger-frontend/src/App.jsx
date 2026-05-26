import { useEffect } from 'react'
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { AuthProvider } from './context/AuthContext'
import MainLayout from './components/MainLayout'
import AuthRoute from './components/AuthRoute'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Records from './pages/Records'
import Categories from './pages/Categories'
import UserInfo from './pages/UserInfo'
import ChangePassword from './pages/ChangePassword'

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
      </Route>
    </Routes>
  )
}

const customTheme = {
  token: {
    colorPrimary: '#18181b',
    colorBgLayout: '#fafafa',
    colorBgContainer: '#ffffff',
    colorBorderSecondary: '#f4f4f5',
    borderRadius: 6,
    wireframe: false,
    boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02)',
  },
  components: {
    Layout: {
      siderBg: '#ffffff',
      headerBg: '#ffffff',
      bodyBg: '#fafafa',
    },
    Menu: {
      itemBg: '#ffffff',
      itemActiveBg: '#f4f4f5',
      itemSelectedBg: '#f4f4f5',
      itemSelectedColor: '#18181b',
      itemHoverBg: '#f4f4f5',
    },
    Card: {
      headerBg: 'transparent',
    },
  },
}

export default function App() {
  return (
    <ConfigProvider locale={zhCN} theme={customTheme}>
      <AuthProvider>
        <HashRouter>
          <AppContent />
        </HashRouter>
      </AuthProvider>
    </ConfigProvider>
  )
}
