import request from './request'
import type { LoginRequest, LoginResponse, RefreshResponse, ApiResponse } from '@/types/auth'

export const authApi = {
  // 用户登录
  login: (data: LoginRequest): Promise<LoginResponse> => {
    return request.post('/auth/login', data)
  },

  // 刷新令牌
  refresh: (): Promise<RefreshResponse> => {
    return request.post('/auth/refresh')
  },

  // 用户登出
  logout: (): Promise<ApiResponse> => {
    return request.post('/auth/logout')
  }
}
