import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { User, LoginRequest, LoginResponse } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>('')
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  // 初始化认证状态
  const initAuth = () => {
    const savedToken = localStorage.getItem('token')
    const savedUser = localStorage.getItem('userInfo')
    
    if (savedToken && savedUser) {
      token.value = savedToken
      try {
        user.value = JSON.parse(savedUser)
      } catch (error) {
        console.error('Failed to parse user info:', error)
        clearAuth()
      }
    }
  }

  // 登录
  const login = async (credentials: LoginRequest): Promise<boolean> => {
    try {
      loading.value = true
      const response = await authApi.login(credentials)
      
      if (response.code === 200) {
        token.value = response.data.token
        user.value = response.data.user
        
        // 保存到本地存储
        localStorage.setItem('token', response.data.token)
        localStorage.setItem('userInfo', JSON.stringify(response.data.user))
        
        return true
      }
      return false
    } catch (error) {
      console.error('Login failed:', error)
      return false
    } finally {
      loading.value = false
    }
  }

  // 登出
  const logout = async () => {
    try {
      if (token.value) {
        await authApi.logout()
      }
    } catch (error) {
      console.error('Logout failed:', error)
    } finally {
      clearAuth()
    }
  }

  // 刷新令牌
  const refreshToken = async (): Promise<boolean> => {
    try {
      const response = await authApi.refresh()
      
      if (response.code === 200) {
        token.value = response.data.token
        localStorage.setItem('token', response.data.token)
        return true
      }
      return false
    } catch (error) {
      console.error('Token refresh failed:', error)
      clearAuth()
      return false
    }
  }

  // 清除认证信息
  const clearAuth = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
  }

  // 更新用户信息
  const updateUser = (newUser: User) => {
    user.value = newUser
    localStorage.setItem('userInfo', JSON.stringify(newUser))
  }

  return {
    token,
    user,
    loading,
    isAuthenticated,
    isAdmin,
    initAuth,
    login,
    logout,
    refreshToken,
    clearAuth,
    updateUser
  }
})
