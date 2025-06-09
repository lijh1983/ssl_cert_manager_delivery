/**
 * 缓存工具类
 * 提供内存缓存、本地存储缓存和API响应缓存功能
 */

// 缓存项接口
interface CacheItem<T = any> {
  data: T
  timestamp: number
  expiry: number
  key: string
}

// 缓存配置接口
interface CacheConfig {
  defaultTTL: number // 默认过期时间（毫秒）
  maxSize: number // 最大缓存项数量
  storage: 'memory' | 'localStorage' | 'sessionStorage'
  prefix: string // 缓存键前缀
}

// 默认配置
const defaultConfig: CacheConfig = {
  defaultTTL: 5 * 60 * 1000, // 5分钟
  maxSize: 100,
  storage: 'memory',
  prefix: 'ssl_cert_manager_'
}

/**
 * 通用缓存类
 */
class Cache {
  private config: CacheConfig
  private memoryCache = new Map<string, CacheItem>()

  constructor(config: Partial<CacheConfig> = {}) {
    this.config = { ...defaultConfig, ...config }
  }

  /**
   * 设置缓存
   * @param key 缓存键
   * @param data 缓存数据
   * @param ttl 过期时间（毫秒），可选
   */
  set<T>(key: string, data: T, ttl?: number): void {
    const expiry = ttl || this.config.defaultTTL
    const timestamp = Date.now()
    const cacheKey = this.config.prefix + key

    const item: CacheItem<T> = {
      data,
      timestamp,
      expiry: timestamp + expiry,
      key: cacheKey
    }

    if (this.config.storage === 'memory') {
      // 内存缓存
      this.memoryCache.set(cacheKey, item)
      this.cleanup()
    } else {
      // 浏览器存储
      try {
        const storage = this.getStorage()
        storage.setItem(cacheKey, JSON.stringify(item))
      } catch (error) {
        console.warn('缓存存储失败:', error)
        // 降级到内存缓存
        this.memoryCache.set(cacheKey, item)
      }
    }
  }

  /**
   * 获取缓存
   * @param key 缓存键
   * @returns 缓存数据或null
   */
  get<T>(key: string): T | null {
    const cacheKey = this.config.prefix + key

    let item: CacheItem<T> | null = null

    if (this.config.storage === 'memory') {
      // 内存缓存
      item = this.memoryCache.get(cacheKey) as CacheItem<T> || null
    } else {
      // 浏览器存储
      try {
        const storage = this.getStorage()
        const cached = storage.getItem(cacheKey)
        if (cached) {
          item = JSON.parse(cached) as CacheItem<T>
        }
      } catch (error) {
        console.warn('缓存读取失败:', error)
        return null
      }
    }

    if (!item) {
      return null
    }

    // 检查是否过期
    if (Date.now() > item.expiry) {
      this.delete(key)
      return null
    }

    return item.data
  }

  /**
   * 删除缓存
   * @param key 缓存键
   */
  delete(key: string): void {
    const cacheKey = this.config.prefix + key

    if (this.config.storage === 'memory') {
      this.memoryCache.delete(cacheKey)
    } else {
      try {
        const storage = this.getStorage()
        storage.removeItem(cacheKey)
      } catch (error) {
        console.warn('缓存删除失败:', error)
      }
    }
  }

  /**
   * 检查缓存是否存在且未过期
   * @param key 缓存键
   */
  has(key: string): boolean {
    return this.get(key) !== null
  }

  /**
   * 清空所有缓存
   */
  clear(): void {
    if (this.config.storage === 'memory') {
      this.memoryCache.clear()
    } else {
      try {
        const storage = this.getStorage()
        const keys = Object.keys(storage)
        keys.forEach(key => {
          if (key.startsWith(this.config.prefix)) {
            storage.removeItem(key)
          }
        })
      } catch (error) {
        console.warn('缓存清空失败:', error)
      }
    }
  }

  /**
   * 获取缓存大小
   */
  size(): number {
    if (this.config.storage === 'memory') {
      return this.memoryCache.size
    } else {
      try {
        const storage = this.getStorage()
        const keys = Object.keys(storage)
        return keys.filter(key => key.startsWith(this.config.prefix)).length
      } catch (error) {
        return 0
      }
    }
  }

  /**
   * 获取所有缓存键
   */
  keys(): string[] {
    if (this.config.storage === 'memory') {
      return Array.from(this.memoryCache.keys()).map(key => 
        key.replace(this.config.prefix, '')
      )
    } else {
      try {
        const storage = this.getStorage()
        const keys = Object.keys(storage)
        return keys
          .filter(key => key.startsWith(this.config.prefix))
          .map(key => key.replace(this.config.prefix, ''))
      } catch (error) {
        return []
      }
    }
  }

  /**
   * 清理过期缓存
   */
  private cleanup(): void {
    if (this.config.storage !== 'memory') return

    const now = Date.now()
    const toDelete: string[] = []

    this.memoryCache.forEach((item, key) => {
      if (now > item.expiry) {
        toDelete.push(key)
      }
    })

    toDelete.forEach(key => this.memoryCache.delete(key))

    // 如果缓存项过多，删除最旧的项
    if (this.memoryCache.size > this.config.maxSize) {
      const entries = Array.from(this.memoryCache.entries())
      entries.sort((a, b) => a[1].timestamp - b[1].timestamp)
      
      const toRemove = entries.slice(0, entries.length - this.config.maxSize)
      toRemove.forEach(([key]) => this.memoryCache.delete(key))
    }
  }

  /**
   * 获取存储对象
   */
  private getStorage(): Storage {
    if (this.config.storage === 'localStorage') {
      return localStorage
    } else if (this.config.storage === 'sessionStorage') {
      return sessionStorage
    }
    throw new Error('Invalid storage type')
  }
}

/**
 * API缓存类
 * 专门用于缓存API响应
 */
class ApiCache extends Cache {
  constructor() {
    super({
      defaultTTL: 5 * 60 * 1000, // 5分钟
      maxSize: 50,
      storage: 'memory',
      prefix: 'api_cache_'
    })
  }

  /**
   * 生成API缓存键
   * @param url 请求URL
   * @param params 请求参数
   */
  generateKey(url: string, params?: any): string {
    const paramStr = params ? JSON.stringify(params) : ''
    return `${url}_${paramStr}`
  }

  /**
   * 缓存API响应
   * @param url 请求URL
   * @param params 请求参数
   * @param data 响应数据
   * @param ttl 缓存时间
   */
  setApiResponse(url: string, params: any, data: any, ttl?: number): void {
    const key = this.generateKey(url, params)
    this.set(key, data, ttl)
  }

  /**
   * 获取API缓存
   * @param url 请求URL
   * @param params 请求参数
   */
  getApiResponse<T>(url: string, params?: any): T | null {
    const key = this.generateKey(url, params)
    return this.get<T>(key)
  }

  /**
   * 删除API缓存
   * @param url 请求URL
   * @param params 请求参数
   */
  deleteApiResponse(url: string, params?: any): void {
    const key = this.generateKey(url, params)
    this.delete(key)
  }

  /**
   * 清除特定URL的所有缓存
   * @param urlPattern URL模式
   */
  clearByUrlPattern(urlPattern: string): void {
    const keys = this.keys()
    keys.forEach(key => {
      if (key.includes(urlPattern)) {
        this.delete(key.replace('api_cache_', ''))
      }
    })
  }
}

// 创建缓存实例
export const memoryCache = new Cache({
  storage: 'memory',
  defaultTTL: 10 * 60 * 1000, // 10分钟
  maxSize: 100
})

export const localCache = new Cache({
  storage: 'localStorage',
  defaultTTL: 24 * 60 * 60 * 1000, // 24小时
  maxSize: 200
})

export const sessionCache = new Cache({
  storage: 'sessionStorage',
  defaultTTL: 60 * 60 * 1000, // 1小时
  maxSize: 50
})

export const apiCache = new ApiCache()

// 缓存工具函数
export const cacheUtils = {
  /**
   * 带缓存的异步函数包装器
   * @param fn 异步函数
   * @param cacheKey 缓存键
   * @param ttl 缓存时间
   * @param cache 缓存实例
   */
  async withCache<T>(
    fn: () => Promise<T>,
    cacheKey: string,
    ttl?: number,
    cache: Cache = memoryCache
  ): Promise<T> {
    // 先尝试从缓存获取
    const cached = cache.get<T>(cacheKey)
    if (cached !== null) {
      return cached
    }

    // 执行函数并缓存结果
    const result = await fn()
    cache.set(cacheKey, result, ttl)
    return result
  },

  /**
   * 清除所有缓存
   */
  clearAll(): void {
    memoryCache.clear()
    localCache.clear()
    sessionCache.clear()
    apiCache.clear()
  },

  /**
   * 获取缓存统计信息
   */
  getStats() {
    return {
      memory: {
        size: memoryCache.size(),
        keys: memoryCache.keys().length
      },
      local: {
        size: localCache.size(),
        keys: localCache.keys().length
      },
      session: {
        size: sessionCache.size(),
        keys: sessionCache.keys().length
      },
      api: {
        size: apiCache.size(),
        keys: apiCache.keys().length
      }
    }
  }
}

// 导出默认实例
export default {
  Cache,
  ApiCache,
  memoryCache,
  localCache,
  sessionCache,
  apiCache,
  cacheUtils
}
