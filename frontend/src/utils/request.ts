/**
 * HTTP请求工具
 * 集成缓存、错误处理、认证等功能
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'
import { apiCache } from '@/utils/cache'

// 请求配置接口
interface RequestConfig extends AxiosRequestConfig {
  cache?: boolean | number // 是否缓存或缓存时间（毫秒）
  silent?: boolean // 是否静默处理错误
  retry?: number // 重试次数
  retryDelay?: number // 重试延迟（毫秒）
}

// 响应接口
interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

/**
 * 创建HTTP客户端
 */
function createHttpClient(): AxiosInstance {
  const instance = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json'
    }
  })

  // 请求拦截器
  instance.interceptors.request.use(
    (config) => {
      // 添加认证token
      const authStore = useAuthStore()
      if (authStore.token) {
        config.headers.Authorization = `Bearer ${authStore.token}`
      }

      // 添加CSRF token
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
      if (csrfToken) {
        config.headers['X-CSRF-Token'] = csrfToken
      }

      // 添加请求ID用于追踪
      config.headers['X-Request-ID'] = generateRequestId()

      return config
    },
    (error) => {
      return Promise.reject(error)
    }
  )

  // 响应拦截器
  instance.interceptors.response.use(
    (response: AxiosResponse<ApiResponse>) => {
      const { data } = response

      // 检查业务状态码
      if (data.code !== 200) {
        const config = response.config as RequestConfig
        if (!config.silent) {
          ElMessage.error(data.message || '请求失败')
        }
        return Promise.reject(new Error(data.message || '请求失败'))
      }

      return response
    },
    (error) => {
      const config = error.config as RequestConfig

      // 处理网络错误
      if (!error.response) {
        if (!config?.silent) {
          ElMessage.error('网络连接失败，请检查网络设置')
        }
        return Promise.reject(error)
      }

      const { status } = error.response

      // 处理认证错误
      if (status === 401) {
        const authStore = useAuthStore()
        authStore.logout()
        router.push('/login')
        ElMessage.error('登录已过期，请重新登录')
        return Promise.reject(error)
      }

      // 处理权限错误
      if (status === 403) {
        if (!config?.silent) {
          ElMessage.error('权限不足，无法访问该资源')
        }
        return Promise.reject(error)
      }

      // 处理服务器错误
      if (status >= 500) {
        if (!config?.silent) {
          ElMessage.error('服务器内部错误，请稍后重试')
        }
        return Promise.reject(error)
      }

      // 处理其他错误
      if (!config?.silent) {
        const message = error.response.data?.message || '请求失败'
        ElMessage.error(message)
      }

      return Promise.reject(error)
    }
  )

  return instance
}

/**
 * 生成请求ID
 */
function generateRequestId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

/**
 * 请求重试函数
 */
async function retryRequest<T>(
  requestFn: () => Promise<T>,
  retries: number = 3,
  delay: number = 1000
): Promise<T> {
  try {
    return await requestFn()
  } catch (error) {
    if (retries > 0) {
      await new Promise(resolve => setTimeout(resolve, delay))
      return retryRequest(requestFn, retries - 1, delay * 2) // 指数退避
    }
    throw error
  }
}

/**
 * HTTP请求类
 */
class HttpClient {
  private instance: AxiosInstance

  constructor() {
    this.instance = createHttpClient()
  }

  /**
   * GET请求
   */
  async get<T = any>(url: string, config: RequestConfig = {}): Promise<ApiResponse<T>> {
    const { cache, retry = 0, retryDelay = 1000, ...axiosConfig } = config

    // 检查缓存
    if (cache) {
      const cached = apiCache.getCachedResponse(url, axiosConfig.params)
      if (cached) {
        return cached
      }
    }

    const requestFn = async () => {
      const response = await this.instance.get<ApiResponse<T>>(url, axiosConfig)
      
      // 缓存响应
      if (cache) {
        const ttl = typeof cache === 'number' ? cache : undefined
        apiCache.cacheResponse(url, axiosConfig.params, response.data, ttl)
      }
      
      return response.data
    }

    if (retry > 0) {
      return retryRequest(requestFn, retry, retryDelay)
    }

    return requestFn()
  }

  /**
   * POST请求
   */
  async post<T = any>(url: string, data?: any, config: RequestConfig = {}): Promise<ApiResponse<T>> {
    const { retry = 0, retryDelay = 1000, ...axiosConfig } = config

    const requestFn = async () => {
      const response = await this.instance.post<ApiResponse<T>>(url, data, axiosConfig)
      
      // POST请求成功后清理相关缓存
      this.clearRelatedCache(url)
      
      return response.data
    }

    if (retry > 0) {
      return retryRequest(requestFn, retry, retryDelay)
    }

    return requestFn()
  }

  /**
   * PUT请求
   */
  async put<T = any>(url: string, data?: any, config: RequestConfig = {}): Promise<ApiResponse<T>> {
    const { retry = 0, retryDelay = 1000, ...axiosConfig } = config

    const requestFn = async () => {
      const response = await this.instance.put<ApiResponse<T>>(url, data, axiosConfig)
      
      // PUT请求成功后清理相关缓存
      this.clearRelatedCache(url)
      
      return response.data
    }

    if (retry > 0) {
      return retryRequest(requestFn, retry, retryDelay)
    }

    return requestFn()
  }

  /**
   * DELETE请求
   */
  async delete<T = any>(url: string, config: RequestConfig = {}): Promise<ApiResponse<T>> {
    const { retry = 0, retryDelay = 1000, ...axiosConfig } = config

    const requestFn = async () => {
      const response = await this.instance.delete<ApiResponse<T>>(url, axiosConfig)
      
      // DELETE请求成功后清理相关缓存
      this.clearRelatedCache(url)
      
      return response.data
    }

    if (retry > 0) {
      return retryRequest(requestFn, retry, retryDelay)
    }

    return requestFn()
  }

  /**
   * PATCH请求
   */
  async patch<T = any>(url: string, data?: any, config: RequestConfig = {}): Promise<ApiResponse<T>> {
    const { retry = 0, retryDelay = 1000, ...axiosConfig } = config

    const requestFn = async () => {
      const response = await this.instance.patch<ApiResponse<T>>(url, data, axiosConfig)
      
      // PATCH请求成功后清理相关缓存
      this.clearRelatedCache(url)
      
      return response.data
    }

    if (retry > 0) {
      return retryRequest(requestFn, retry, retryDelay)
    }

    return requestFn()
  }

  /**
   * 上传文件
   */
  async upload<T = any>(url: string, file: File, config: RequestConfig = {}): Promise<ApiResponse<T>> {
    const formData = new FormData()
    formData.append('file', file)

    const uploadConfig: RequestConfig = {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...config.headers
      },
      onUploadProgress: config.onUploadProgress
    }

    return this.post<T>(url, formData, uploadConfig)
  }

  /**
   * 下载文件
   */
  async download(url: string, filename?: string, config: RequestConfig = {}): Promise<void> {
    const response = await this.instance.get(url, {
      ...config,
      responseType: 'blob'
    })

    const blob = new Blob([response.data])
    const downloadUrl = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = filename || 'download'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(downloadUrl)
  }

  /**
   * 清理相关缓存
   */
  private clearRelatedCache(url: string): void {
    // 根据URL模式清理相关缓存
    const urlParts = url.split('/')
    const resource = urlParts[urlParts.length - 2] || urlParts[urlParts.length - 1]
    
    if (resource) {
      apiCache.clearApiCache(resource)
    }
  }

  /**
   * 手动清理缓存
   */
  clearCache(pattern?: string): void {
    if (pattern) {
      apiCache.clearApiCache(pattern)
    } else {
      apiCache.clear()
    }
  }

  /**
   * 获取缓存统计
   */
  getCacheStats() {
    return {
      hitRate: apiCache.getHitRate(),
      ...apiCache.getStats()
    }
  }
}

// 导出请求实例
export const request = new HttpClient()

// 导出类型
export type { RequestConfig, ApiResponse }
