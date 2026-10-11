import { Navigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

/**
 * RegularUserRoute - 用户侧业务路由守卫
 *
 * 记账 / 分类 / AI 助手 / 会员中心属于**普通用户**的功能范围；
 * 管理员账号（role === 1）直接输入这些路径时重定向到管理后台，
 * 避免落到一个所有接口都返回 403 的页面。
 *
 * ⚠️ 这只是体验对齐，**不是权限边界**：真正的拦截在服务端
 * （用户侧业务端点统一挂 get_current_regular_user，管理员一律 403）。
 * 角色功能范围矩阵见 utils/auth.py 模块 docstring。
 */
export default function RegularUserRoute({ children }) {
  const { user, loading } = useAuth()
  const token = localStorage.getItem('token')

  if (loading) return null

  if (!token || !user) {
    return <Navigate to="/login" replace />
  }

  if (user.role === 1) {
    return <Navigate to="/admin/dashboard" replace />
  }

  return children
}
