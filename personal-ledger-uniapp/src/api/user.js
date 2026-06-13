import { post, get, put } from './request'
import BASE_URL from './config'

export const login = (data) => post('/user/login', data)
export const register = (data) => post('/user/register', data)
export const getUserInfo = () => get('/user/info')
export const updateUserInfo = (data) => put('/user/info', data)
export const updatePassword = (data) => put('/user/password', data)

/**
 * 上传用户头像
 * uni-app 文件上传需使用 uni.uploadFile
 * @param {string} filePath - 本地文件临时路径（来自 uni.chooseImage 返回的 tempFilePaths）
 * @returns {Promise}
 */
export const uploadAvatar = (filePath) => {
	const token = uni.getStorageSync('token')
	return new Promise((resolve, reject) => {
		uni.uploadFile({
			url: BASE_URL + '/user/avatar',
			filePath: filePath,
			name: 'file',
			header: {
				'Authorization': token ? `Bearer ${token}` : '',
			},
			success: (res) => {
				try {
					const data = JSON.parse(res.data)
					resolve(data)
				} catch (e) {
					reject(new Error('解析服务器响应失败'))
				}
			},
			fail: (err) => {
				const msg = err && err.errMsg || ''
				if (msg.includes('timeout')) {
					uni.showToast({ title: '上传超时，请重试', icon: 'none' })
				} else {
					uni.showToast({ title: '网络连接失败', icon: 'none' })
				}
				reject(err)
			},
		})
	})
}
