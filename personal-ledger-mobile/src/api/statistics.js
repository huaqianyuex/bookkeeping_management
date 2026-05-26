import request from './request'

export const getMonthlyStatistics = (params) => request.get('/statistics/monthly', { params })

export const getCategoryStatistics = (params) => request.get('/statistics/category', { params })
