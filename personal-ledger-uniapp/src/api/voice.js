import BASE_URL from './config'

/**
 * 语音转写 / 开关下发 — 配套后端 /api/ai/voice/*（docs/语音记账实施指南.md §4.2）。
 *
 * 不能复用 api/request.js：uni.uploadFile 的 res.data 是字符串、不走 request
 * 的拦截器，因此单独封装，仅对齐其 401 / 错误提示口径。
 */

/** 与 request.js 同口径的 401 处理：清 token 回登录页 */
function handleUnauthorized() {
	uni.removeStorageSync('token')
	uni.reLaunch({ url: '/pages/login/index' })
}

/**
 * 语音转写：上传录音文件，返回识别文本。
 * @param {string} filePath - 录音临时文件路径（recorder.onStop 的 tempFilePath）
 * @returns {Promise<{text:string, language?:string, confidence?:number}>}
 *   text 为空字符串表示没听清（不是故障，由调用方提示重试）
 */
export const transcribeVoice = (filePath) => {
	return new Promise((resolve, reject) => {
		const token = uni.getStorageSync('token')
		uni.uploadFile({
			url: BASE_URL + '/ai/voice/transcribe',
			filePath,
			name: 'file',
			header: { 'Authorization': token ? `Bearer ${token}` : '' },
			timeout: 30000,
			success: (res) => {
				if (res.statusCode === 401) {
					handleUnauthorized()
					reject(new Error('未登录或登录已过期'))
					return
				}
				let body = null
				try { body = JSON.parse(res.data) } catch (e) { body = null }
				if (!body) { reject(new Error('语音识别返回异常')); return }
				if (body.error) { reject(new Error(body.error)); return }
				resolve(body)
			},
			fail: (err) => {
				const msg = (err && err.errMsg) || ''
				reject(new Error(msg.includes('timeout') ? '识别超时，请重试' : '语音上传失败'))
			}
		})
	})
}

/**
 * 语音功能开关（前端据此隐藏话筒入口）。
 * @returns {Promise<{enabled:boolean, maxSeconds:number}>}
 */
export const getVoiceConfig = () => {
	return new Promise((resolve, reject) => {
		const token = uni.getStorageSync('token')
		uni.request({
			url: BASE_URL + '/ai/voice/config',
			method: 'GET',
			header: { 'Authorization': token ? `Bearer ${token}` : '' },
			timeout: 15000,
			success: (res) => {
				if (res.statusCode === 401) {
					handleUnauthorized()
					reject(new Error('未登录或登录已过期'))
					return
				}
				if (res.statusCode !== 200 || !res.data || res.data.error) {
					reject(new Error('语音配置获取失败'))
					return
				}
				resolve(res.data)
			},
			fail: () => reject(new Error('网络连接失败'))
		})
	})
}
