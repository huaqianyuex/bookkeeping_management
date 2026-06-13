import { get, post, put, del } from './request'

export const getRecordPage = (params) => get('/records', params)
export const getRecordDetail = (id) => get(`/records/${id}`)
export const addRecord = (data) => post('/records', data)
export const updateRecord = (id, data) => put(`/records/${id}`, data)
export const deleteRecord = (id) => del(`/records/${id}`)
