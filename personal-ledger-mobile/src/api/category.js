import request from './request'

export const getCategoryList = (params) => request.get('/categories', { params })

export const addCategory = (data) => request.post('/categories', data)

export const updateCategory = (id, data) => request.put(`/categories/${id}`, data)

export const deleteCategory = (id) => request.delete(`/categories/${id}`)
