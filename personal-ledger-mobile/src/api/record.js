import request from './request'

export const getRecordPage = (params) => request.get('/records', { params })

export const getRecordDetail = (id) => request.get(`/records/${id}`)

export const addRecord = (data) => request.post('/records', data)

export const updateRecord = (id, data) => request.put(`/records/${id}`, data)

export const deleteRecord = (id) => request.delete(`/records/${id}`)
