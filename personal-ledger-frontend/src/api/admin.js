import request from './request'

export const getAdminUserList = (params) => request.get('/admin/users', { params })

export const getAdminUserDetail = (id) => request.get(`/admin/users/${id}`)

export const deleteAdminUser = (id) => request.delete(`/admin/users/${id}`)

export const batchDeleteAdminUsers = (ids) => request.post('/admin/users/batch-delete', { ids })

export const getAdminRecords = (params) => request.get('/admin/records', { params })

export const batchDeleteAdminRecords = (ids) => request.post('/admin/records/batch-delete', { ids })

export const getAdminOverview = () => request.get('/admin/statistics/overview')
