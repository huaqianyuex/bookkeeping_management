import request from './request'

export const register = (data) => request.post('/user/register', data)

export const login = (data) => request.post('/user/login', data)

export const getUserInfo = () => request.get('/user/info')

export const updateUserInfo = (data) => request.put('/user/info', data)

export const updatePassword = (data) => request.put('/user/password', data)

export const uploadAvatar = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/user/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}
