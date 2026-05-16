import request from '@/utils/request'
import type {
  ApiResponse,
  PageResult,
  LoginDTO,
  RegisterDTO,
  PasswordDTO,
  CategoryDTO,
  RecordDTO,
  CategoryVO,
  RecordVO,
  MonthlyStatsVO,
  CategoryStatVO,
  UserInfoVO
} from '@/types'

export const userApi = {
  login(data: LoginDTO): Promise<ApiResponse<string>> {
    return request.post('/api/user/login', data)
  },

  register(data: RegisterDTO): Promise<ApiResponse<void>> {
    return request.post('/api/user/register', data)
  },

  getInfo(): Promise<ApiResponse<UserInfoVO>> {
    return request.get('/api/user/info')
  },

  updatePassword(data: PasswordDTO): Promise<ApiResponse<void>> {
    return request.put('/api/user/password', data)
  }
}

export const categoryApi = {
  getList(type?: number): Promise<ApiResponse<CategoryVO[]>> {
    const params = type !== undefined ? { type } : {}
    return request.get('/api/categories', { params })
  },

  add(data: CategoryDTO): Promise<ApiResponse<void>> {
    return request.post('/api/categories', data)
  },

  update(id: number, data: CategoryDTO): Promise<ApiResponse<void>> {
    return request.put(`/api/categories/${id}`, data)
  },

  delete(id: number): Promise<ApiResponse<void>> {
    return request.delete(`/api/categories/${id}`)
  }
}

export const recordApi = {
  getPage(params: {
    page?: number
    size?: number
    categoryId?: number
    month?: string
  }): Promise<ApiResponse<PageResult<RecordVO>>> {
    return request.get('/api/records', { params })
  },

  getDetail(id: number): Promise<ApiResponse<RecordVO>> {
    return request.get(`/api/records/${id}`)
  },

  add(data: RecordDTO): Promise<ApiResponse<void>> {
    return request.post('/api/records', data)
  },

  update(id: number, data: RecordDTO): Promise<ApiResponse<void>> {
    return request.put(`/api/records/${id}`, data)
  },

  delete(id: number): Promise<ApiResponse<void>> {
    return request.delete(`/api/records/${id}`)
  }
}

export const statisticsApi = {
  getMonthly(year: number, month: number): Promise<ApiResponse<MonthlyStatsVO>> {
    return request.get('/api/statistics/monthly', { params: { year, month } })
  },

  getCategory(params: {
    year: number
    month: number
    type?: number
  }): Promise<ApiResponse<CategoryStatVO[]>> {
    return request.get('/api/statistics/category', { params })
  }
}
