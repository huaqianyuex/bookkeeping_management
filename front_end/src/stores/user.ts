import { defineStore } from 'pinia'
import { ref } from 'vue'
import { userApi } from '@/api'
import type { UserInfoVO } from '@/types'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const userInfo = ref<UserInfoVO | null>(null)

  const setToken = (newToken: string) => {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  const clearToken = () => {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
  }

  const fetchUserInfo = async () => {
    try {
      const res = await userApi.getInfo()
      userInfo.value = res.data
    } catch (error) {
      console.error('获取用户信息失败', error)
    }
  }

  const logout = () => {
    clearToken()
  }

  return {
    token,
    userInfo,
    setToken,
    clearToken,
    fetchUserInfo,
    logout
  }
})
