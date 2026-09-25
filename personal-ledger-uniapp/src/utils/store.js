import { defineStore } from 'pinia'
import { getUserInfo, updateUserInfo } from '../api/user'
import { resetLoginRedirect } from '../api/request'

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
			// 登录成功后重置 401 跳转标记，确保后续若再次出现 401 仍能正常跳转到登录页。
			resetLoginRedirect()
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

/**
 * 账本数据缓存（stale-while-revalidate）：
 * 自定义 TabBar 用 reLaunch 切页会销毁页面栈，这里把账单列表和仪表盘统计
 * 缓存一份，页面 onShow 时先渲染缓存再后台刷新，避免每次切 tab 都白屏等请求。
 */
const emptyRecordsCache = () => ({
	key: '',
	records: [],
	total: 0,
	pages: 0,
	current: 1,
	size: 20,
})

export const useLedgerStore = defineStore('ledger', {
	state: () => ({
		records: emptyRecordsCache(),
		dashboard: { key: '', monthlyData: null, expenseData: [], incomeData: [], monthSeries: [] },
	}),
	actions: {
		setRecordsCache(payload) {
			this.records = { ...this.records, ...payload }
		},
		clearRecordsCache() {
			this.records = emptyRecordsCache()
		},
		setDashboardCache(payload) {
			this.dashboard = { ...this.dashboard, ...payload }
		},
	},
})
