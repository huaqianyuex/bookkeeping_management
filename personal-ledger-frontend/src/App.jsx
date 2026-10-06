import './styles/design-tokens.css'
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, App as AntdApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { AuthProvider } from './context/AuthContext'
import { antdTheme } from './theme/antdTheme'
import MainLayout from './components/MainLayout'
import AuthRoute from './components/guards/AuthRoute'
import AdminRoute from './components/guards/AdminRoute'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import Dashboard from './pages/Dashboard'
import Records from './pages/Records'
import Categories from './pages/Categories'
import UserInfo from './pages/UserInfo'
import ChangePassword from './pages/ChangePassword'
import Membership from './pages/Membership'
import AiChatPage from './pages/AiChat'
import SettingsLayout from './pages/settings/SettingsLayout'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminUsers from './pages/admin/AdminUsers'
import AdminRecords from './pages/admin/AdminRecords'
import AdminFaq from './pages/admin/AdminFaq'
import AdminMembership from './pages/admin/AdminMembership'
import AdminRecharges from './pages/admin/AdminRecharges'

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
        <Route path="settings" element={<SettingsLayout />}>
          <Route index element={<Navigate to="profile" replace />} />
          <Route path="profile" element={<UserInfo />} />
          <Route path="password" element={<ChangePassword />} />
        </Route>
        <Route path="user-info" element={<Navigate to="/settings/profile" replace />} />
        <Route path="change-password" element={<Navigate to="/settings/password" replace />} />
        <Route path="admin/dashboard" element={<AdminRoute><AdminDashboard /></AdminRoute>} />
        <Route path="admin/users" element={<AdminRoute><AdminUsers /></AdminRoute>} />
        <Route path="admin/records" element={<AdminRoute><AdminRecords /></AdminRoute>} />
        <Route path="admin/faq" element={<AdminRoute><AdminFaq /></AdminRoute>} />
        <Route path="ai-chat" element={<AiChatPage />} />
        <Route path="membership" element={<Membership />} />
        <Route path="admin/membership" element={<AdminRoute><AdminMembership /></AdminRoute>} />
        <Route path="admin/recharges" element={<AdminRoute><AdminRecharges /></AdminRoute>} />
      </Route>
    </Routes>
  )
}

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
