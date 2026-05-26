import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function AuthRoute({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  const token = localStorage.getItem('token')

  if (loading) return null

  if (!token || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}
