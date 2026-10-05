import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { getUserInfo } from '../api/user'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // 有 token 先置 loading：AuthRoute 须等会话恢复完成，否则刷新页面会被误判
  // 未登录直接踢回 /login（user 只存内存，刷新即失）
  const [loading, setLoading] = useState(() => !!localStorage.getItem('token'))

  const fetchUserInfo = useCallback(async () => {
    const token = localStorage.getItem('token')
    if (!token) return null
    setLoading(true)
    try {
      const res = await getUserInfo()
      if (res.code === 200) {
        setUser(res.data)
        return res.data
      }
    } catch {
      localStorage.removeItem('token')
    } finally {
      setLoading(false)
    }
    return null
  }, [])

  // 启动时带 token 则静默恢复登录态
  useEffect(() => {
    if (localStorage.getItem('token')) fetchUserInfo()
  }, [fetchUserInfo])

  // api/request.js 拦截到 401（token 过期/失效）时广播 auth-expired，
  // 立即清掉内存 user，避免「localStorage 已无 token 但 UI 仍显示登录」的中间态
  useEffect(() => {
    const onExpired = () => setUser(null)
    window.addEventListener('auth-expired', onExpired)
    return () => window.removeEventListener('auth-expired', onExpired)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, setUser, loading, fetchUserInfo, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
