import request from './request'

export const register = (data) => request.post('/user/register', data)

export const login = (data) => request.post('/user/login', data)

export const getUserInfo = () => request.get('/user/info')

export const updateUserInfo = (data) => request.put('/user/info', data)

export const updatePassword = (data) => request.put('/user/password', data)

/**
 * 上传用户头像
 * @param {Object} file - { uri, type, name }  来自 expo-image-picker 的 asset 对象
 * @returns {Promise}
 */
export const uploadAvatar = (file) => {
  const formData = new FormData()
  formData.append('file', {
    uri: file.uri,
    type: file.mimeType || file.type || 'image/jpeg',
    name: file.fileName || file.name || 'avatar.jpg',
  })
  return request.post('/user/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}
