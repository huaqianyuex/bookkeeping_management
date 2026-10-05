import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      // 只清 localStorage 不重置 AuthContext 内存 user：守卫要到下一次渲染
      // 读 localStorage 才"侥幸"生效，中间态里页面仍显示已登录。广播事件让
      // AuthProvider 立即 setUser(null)。
      window.dispatchEvent(new CustomEvent('auth-expired'))
      window.location.hash = '#/login'
    }
    return Promise.reject(error)
  }
)

export default request
