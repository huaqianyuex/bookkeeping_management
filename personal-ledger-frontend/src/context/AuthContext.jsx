import { createContext, useContext, useState, useCallback } from 'react'
import { getUserInfo } from '../api/user'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(false)

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
