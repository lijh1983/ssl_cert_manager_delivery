export interface User {
  id: number
  username: string
  email: string
  role: 'admin' | 'user'
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  code: number
  message: string
  data: {
    token: string
    expires_in: number
    user: User
  }
}

export interface RefreshResponse {
  code: number
  message: string
  data: {
    token: string
    expires_in: number
  }
}

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}
