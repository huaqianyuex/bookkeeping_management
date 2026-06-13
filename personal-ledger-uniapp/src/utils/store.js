import { defineStore } from 'pinia'
import { getUserInfo, updateUserInfo } from '../api/user'

export const useUserStore = defineStore('user', {
	state: () => ({
		token: uni.getStorageSync('token') || '',
		userInfo: null,
	}),
	getters: {
		isLoggedIn: (state) => !!state.token,
		username: (state) => state.userInfo?.username || '',
		userId: (state) => state.userInfo?.id || '',
	},
	actions: {
		setToken(token) {
			this.token = token
			uni.setStorageSync('token', token)
		},
		clearToken() {
			this.token = ''
			this.userInfo = null
			uni.removeStorageSync('token')
		},
		async fetchUserInfo() {
			try {
				const res = await getUserInfo()
				if (res.code === 200) {
					this.userInfo = res.data
					return res.data
				}
			} catch (e) {
				console.error('获取用户信息失败', e)
			}
			return null
		},
		/** 更新用户信息到 store（不调接口，用于头像上传等场景） */
		setUserInfo(userInfo) {
			this.userInfo = userInfo
		},
		logout() {
			this.clearToken()
			uni.reLaunch({ url: '/pages/login/index' })
		},
	},
})
