export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface PageResult<T> {
  records: T[]
  total: number
  pages: number
  current: number
  size: number
}

export type CategoryType = 0 | 1

export interface CategoryVO {
  id: number
  name: string
  type: CategoryType
  userId: number
  createTime: string
  updateTime: string
}

export interface RecordVO {
  id: number
  userId: number
  categoryId: number
  categoryName: string
  categoryType: CategoryType
  amount: number
  remark?: string
  recordDate: string
  createTime: string
  updateTime: string
}

export interface MonthlyStatsVO {
  year: number
  month: number
  totalIncome: number
  totalExpense: number
  balance: number
}

export interface CategoryStatVO {
  categoryId: number
  categoryName: string
  amount: number
  percentage: number
}

export interface LoginDTO {
  username: string
  password: string
}

export interface RegisterDTO {
  username: string
  password: string
}

export interface PasswordDTO {
  oldPassword: string
  newPassword: string
}

export interface CategoryDTO {
  name: string
  type: CategoryType
}

export interface RecordDTO {
  categoryId: number
  amount: number
  remark?: string
  recordDate: string
}

export interface UserInfoVO {
  id: number
  username: string
  createTime: string
  updateTime: string
}
