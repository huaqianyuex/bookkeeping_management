import { get } from './request'

export const getMonthlyStatistics = (params) => get('/statistics/monthly', params)
export const getCategoryStatistics = (params) => get('/statistics/category', params)
