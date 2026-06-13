import BASE_URL from './config'

const request = (options) => {
	return new Promise((resolve, reject) => {
		const token = uni.getStorageSync('token')
		uni.request({
			url: BASE_URL + options.url,
			method: options.method || 'GET',
			data: options.data || {},
			header: {
				'Content-Type': 'application/json',
				'Authorization': token ? `Bearer ${token}` : '',
			},
			timeout: options.timeout || 10000, // 默认10秒，可按需覆盖（如AI对话需更长）
			success: (res) => {
				if (res.statusCode === 401) {
					uni.removeStorageSync('token')
					uni.reLaunch({ url: '/pages/login/index' })
					reject(new Error('未登录或登录已过期'))
					return
				}
				if (res.statusCode === 0 || !res.statusCode) {
					uni.showToast({ title: '网络连接失败，请检查网络', icon: 'none' })
					reject(new Error('网络连接失败'))
					return
				}
				if (res.statusCode >= 500) {
					uni.showToast({ title: '服务器错误，请稍后重试', icon: 'none' })
					reject(new Error('服务器错误'))
					return
				}
				resolve(res.data)
			},
			fail: (err) => {
				// 区分超时和连接拒绝，给用户更友好的提示
				const msg = err && err.errMsg || ''
				if (msg.includes('timeout')) {
					uni.showToast({ title: '请求超时，请检查网络', icon: 'none' })
				} else if (msg.includes('refused') || msg.includes('ERR_CONNECTION_REFUSED')) {
					uni.showToast({ title: '无法连接服务器，请确认服务已启动', icon: 'none' })
				} else {
					uni.showToast({ title: '网络连接失败', icon: 'none' })
				}
				reject(err)
			}
		})
	})
}

export const get = (url, data) => request({ url, method: 'GET', data })
export const post = (url, data) => request({ url, method: 'POST', data })
export const put = (url, data) => request({ url, method: 'PUT', data })
export const del = (url, data) => request({ url, method: 'DELETE', data })

export default request
