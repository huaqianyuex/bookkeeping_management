import { get, post, put, del } from './request'

export const getCategoryList = (params) => get('/categories', params)
export const addCategory = (data) => post('/categories', data)
export const updateCategory = (id, data) => put(`/categories/${id}`, data)
export const deleteCategory = (id) => del(`/categories/${id}`)
