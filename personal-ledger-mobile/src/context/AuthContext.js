import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { getUserInfo } from '../api/user'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [initializing, setInitializing] = useState(true)

  const fetchUserInfo = useCallback(async () => {
    const token = await AsyncStorage.getItem('token')
    if (!token) {
      setInitializing(false)
      return null
    }
    setLoading(true)
    try {
      const res = await getUserInfo()
      if (res.code === 200) {
        setUser(res.data)
        return res.data
      } else {
        await AsyncStorage.removeItem('token')
      }
    } catch {
      await AsyncStorage.removeItem('token')
    } finally {
      setLoading(false)
      setInitializing(false)
    }
    return null
  }, [])

  useEffect(() => {
    fetchUserInfo()
  }, [fetchUserInfo])

  const logout = useCallback(async () => {
    await AsyncStorage.removeItem('token')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, setUser, loading, initializing, fetchUserInfo, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
