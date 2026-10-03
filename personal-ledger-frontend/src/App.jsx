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
import AdminFaq from './pages/AdminFaq'
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
        <Route index element={<Navigate to="/records" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="records" element={<Records />} />
        <Route path="categories" element={<Categories />} />
        <Route path="user-info" element={<UserInfo />} />
        <Route path="change-password" element={<ChangePassword />} />
        <Route path="admin/dashboard" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
        <Route path="admin/users" element={<AdminRoute><AdminUsers /></AdminRoute>} />
        <Route path="admin/records" element={<AdminRoute><AdminRecords /></AdminRoute>} />
        <Route path="admin/faq" element={<AdminRoute><AdminFaq /></AdminRoute>} />
        <Route path="ai-chat" element={<AiChatPage />} />
      </Route>
    </Routes>
  )
}

import { antdTheme } from './theme/antdTheme'

export default function App() {
  return (
    <ConfigProvider locale={zhCN} theme={antdTheme}>
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
