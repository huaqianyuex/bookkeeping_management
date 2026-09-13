import BASE_URL from './config'

// 防止多个并发请求同时返回 401 时重复 reLaunch 到登录页，
// 否则 uni-app 会抛出 "do not operate continuously" 并导致导航卡死/无响应。
let isRedirectingToLogin = false

/**
 * 重置登录跳转标记。
 * 在成功登录后调用，确保后续若再次出现 401 仍能正常跳转。
 */
export const resetLoginRedirect = () => {
	isRedirectingToLogin = false
}

const redirectToLogin = () => {
	if (isRedirectingToLogin) return
	isRedirectingToLogin = true
	uni.removeStorageSync('token')
	uni.reLaunch({ url: '/pages/login/index' })
	// 延时重置标记：uni-app 的 complete 回调在 reLaunch 调用后立即执行，
	// 而非跳转完成后执行，所以不能用 complete 来重置。
	// 2 秒延时足以让 uni-app 完成页面切换，之后标记重置允许后续跳转。
	setTimeout(() => {
		isRedirectingToLogin = false
	}, 2000)
}

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
			timeout: options.timeout || 15000, // 默认15秒，避免并发请求超时
			success: (res) => {
				if (res.statusCode === 401) {
					// 登录接口自身的 401（如密码错误）不能当作"登录过期"处理，
					// 否则会误跳回登录页并吞掉后端返回的真实错误信息。
					if (options.url && options.url.includes('/user/login')) {
						const msg = (res.data && res.data.message) || '用户名或密码错误'
						reject(new Error(msg))
						return
					}
					redirectToLogin()
					reject(new Error('未登录或登录已过期'))
					return
				}
				if (res.statusCode === 0 || !res.statusCode) {
					uni.showToast({ title: '网络连接失败，请检查网络', icon: 'none' })
					reject(new Error('网络连接失败'))
					return
				}
				if (res.statusCode >= 500) {
					const msg = (res.data && res.data.message) || '服务器错误，请稍后重试'
					uni.showToast({ title: msg, icon: 'none' })
					reject(new Error(msg))
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

/**
 * 带重试的 GET 请求
 * @param {Function} apiFn - API 函数（如 getMonthlyStatistics）
 * @param {Object} params - 请求参数
 * @param {number} retries - 重试次数（默认 2）
 * @param {number} delayMs - 每次重试间隔（默认 800ms）
 */
export const getWithRetry = async (apiFn, params, retries = 2, delayMs = 800) => {
	let lastErr = null
	for (let attempt = 0; attempt <= retries; attempt++) {
		try {
			return await apiFn(params)
		} catch (err) {
			lastErr = err
			if (attempt < retries) {
				console.warn(`[Request] 第 ${attempt + 1} 次请求失败，${delayMs}ms 后重试...`, err.message || err)
				await new Promise(r => setTimeout(r, delayMs))
			}
		}
	}
	throw lastErr
}

export const get = (url, data) => request({ url, method: 'GET', data })
export const post = (url, data) => request({ url, method: 'POST', data })
export const put = (url, data) => request({ url, method: 'PUT', data })
export const patch = (url, data) => request({ url, method: 'PATCH', data })
export const del = (url, data) => request({ url, method: 'DELETE', data })

export default request
