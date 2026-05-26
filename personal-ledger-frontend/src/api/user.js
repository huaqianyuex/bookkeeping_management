import request from './request'

export const register = (data) => request.post('/user/register', data)

export const login = (data) => request.post('/user/login', data)

export const getUserInfo = () => request.get('/user/info')

export const updatePassword = (data) => request.put('/user/password', data)
