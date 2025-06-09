/**
 * 异步组件加载工具
 * 提供组件懒加载、预加载和错误处理功能
 */

import { defineAsyncComponent, Component } from 'vue'
import type { AsyncComponentLoader } from 'vue'

// 加载状态接口
interface LoadingState {
  isLoading: boolean
  error: Error | null
  retryCount: number
}

// 组件预加载器类
class ComponentPreloader {
  private preloadedComponents = new Map<string, Promise<Component>>()
  private loadingStates = new Map<string, LoadingState>()

  /**
   * 添加组件到预加载队列
   * @param name 组件名称
   * @param loader 组件加载器函数
   */
  add(name: string, loader: AsyncComponentLoader): void {
    if (!this.preloadedComponents.has(name)) {
      this.loadingStates.set(name, {
        isLoading: true,
        error: null,
        retryCount: 0
      })

      const promise = loader()
        .then((component) => {
          this.loadingStates.set(name, {
            isLoading: false,
            error: null,
            retryCount: 0
          })
          return component
        })
        .catch((error) => {
          const state = this.loadingStates.get(name)!
          this.loadingStates.set(name, {
            isLoading: false,
            error,
            retryCount: state.retryCount + 1
          })
          throw error
        })

      this.preloadedComponents.set(name, promise)
    }
  }

  /**
   * 获取预加载的组件
   * @param name 组件名称
   */
  get(name: string): Promise<Component> | undefined {
    return this.preloadedComponents.get(name)
  }

  /**
   * 获取组件加载状态
   * @param name 组件名称
   */
  getLoadingState(name: string): LoadingState | undefined {
    return this.loadingStates.get(name)
  }

  /**
   * 清除预加载的组件
   * @param name 组件名称，如果不提供则清除所有
   */
  clear(name?: string): void {
    if (name) {
      this.preloadedComponents.delete(name)
      this.loadingStates.delete(name)
    } else {
      this.preloadedComponents.clear()
      this.loadingStates.clear()
    }
  }

  /**
   * 批量预加载组件
   * @param components 组件映射表
   */
  preloadBatch(components: Record<string, AsyncComponentLoader>): void {
    Object.entries(components).forEach(([name, loader]) => {
      this.add(name, loader)
    })
  }
}

// 创建全局预加载器实例
export const componentPreloader = new ComponentPreloader()

/**
 * 创建带有错误处理和加载状态的异步组件
 * @param loader 组件加载器函数
 * @param options 配置选项
 */
export function createRouteComponent(
  loader: AsyncComponentLoader,
  options: {
    loadingComponent?: Component
    errorComponent?: Component
    delay?: number
    timeout?: number
    retryDelay?: number
    maxRetries?: number
  } = {}
) {
  const {
    loadingComponent,
    errorComponent,
    delay = 200,
    timeout = 30000,
    retryDelay = 1000,
    maxRetries = 3
  } = options

  let retryCount = 0

  const retryableLoader = (): Promise<Component> => {
    return loader().catch((error) => {
      console.error('组件加载失败:', error)
      
      if (retryCount < maxRetries) {
        retryCount++
        console.log(`正在重试加载组件 (${retryCount}/${maxRetries})...`)
        
        return new Promise((resolve, reject) => {
          setTimeout(() => {
            retryableLoader().then(resolve).catch(reject)
          }, retryDelay * retryCount)
        })
      }
      
      throw error
    })
  }

  return defineAsyncComponent({
    loader: retryableLoader,
    loadingComponent: loadingComponent || {
      template: `
        <div class="flex items-center justify-center min-h-[200px]">
          <div class="flex flex-col items-center space-y-4">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p class="text-sm text-gray-600">加载中...</p>
          </div>
        </div>
      `
    },
    errorComponent: errorComponent || {
      template: `
        <div class="flex items-center justify-center min-h-[200px]">
          <div class="text-center">
            <div class="text-red-500 text-4xl mb-4">⚠️</div>
            <h3 class="text-lg font-medium text-gray-900 mb-2">组件加载失败</h3>
            <p class="text-sm text-gray-600 mb-4">请检查网络连接或刷新页面重试</p>
            <button 
              @click="$router.go(0)"
              class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              刷新页面
            </button>
          </div>
        </div>
      `
    },
    delay,
    timeout
  })
}

/**
 * 预加载关键路由组件
 * 在应用启动时预加载常用组件以提升用户体验
 */
export function preloadCriticalComponents(): void {
  // 预加载核心组件
  componentPreloader.preloadBatch({
    MainLayout: () => import('@/layouts/MainLayout.vue'),
    Dashboard: () => import('@/views/Dashboard.vue'),
    Login: () => import('@/views/Login.vue')
  })

  // 延迟预加载次要组件
  setTimeout(() => {
    componentPreloader.preloadBatch({
      CertificateList: () => import('@/views/certificates/CertificateList.vue'),
      ServerList: () => import('@/views/servers/ServerList.vue'),
      ActiveAlerts: () => import('@/views/alerts/ActiveAlerts.vue')
    })
  }, 2000)
}

/**
 * 根据路由路径智能预加载相关组件
 * @param path 当前路由路径
 */
export function smartPreload(path: string): void {
  if (path.startsWith('/certificates')) {
    componentPreloader.preloadBatch({
      CertificateCreate: () => import('@/views/certificates/CertificateCreate.vue'),
      CertificateDetail: () => import('@/views/certificates/CertificateDetail.vue')
    })
  } else if (path.startsWith('/servers')) {
    componentPreloader.preloadBatch({
      ServerCreate: () => import('@/views/servers/ServerCreate.vue'),
      ServerDetail: () => import('@/views/servers/ServerDetail.vue')
    })
  } else if (path.startsWith('/alerts')) {
    componentPreloader.preloadBatch({
      AlertRules: () => import('@/views/alerts/AlertRules.vue')
    })
  } else if (path.startsWith('/logs')) {
    componentPreloader.preloadBatch({
      LogList: () => import('@/views/logs/LogList.vue')
    })
  }
}

/**
 * 组件加载性能监控
 */
export class ComponentLoadMonitor {
  private static loadTimes = new Map<string, number>()
  private static loadErrors = new Map<string, number>()

  static recordLoadTime(componentName: string, loadTime: number): void {
    this.loadTimes.set(componentName, loadTime)
  }

  static recordLoadError(componentName: string): void {
    const currentErrors = this.loadErrors.get(componentName) || 0
    this.loadErrors.set(componentName, currentErrors + 1)
  }

  static getLoadStats(): {
    averageLoadTime: number
    totalErrors: number
    slowestComponent: string | null
    errorProneComponents: string[]
  } {
    const loadTimes = Array.from(this.loadTimes.values())
    const averageLoadTime = loadTimes.length > 0 
      ? loadTimes.reduce((sum, time) => sum + time, 0) / loadTimes.length 
      : 0

    const totalErrors = Array.from(this.loadErrors.values())
      .reduce((sum, errors) => sum + errors, 0)

    const slowestComponent = loadTimes.length > 0
      ? Array.from(this.loadTimes.entries())
          .reduce((slowest, [name, time]) => 
            time > (this.loadTimes.get(slowest[0]) || 0) ? [name, time] : slowest
          )[0]
      : null

    const errorProneComponents = Array.from(this.loadErrors.entries())
      .filter(([, errors]) => errors > 2)
      .map(([name]) => name)

    return {
      averageLoadTime,
      totalErrors,
      slowestComponent,
      errorProneComponents
    }
  }
}

// 导出默认配置
export default {
  createRouteComponent,
  componentPreloader,
  preloadCriticalComponents,
  smartPreload,
  ComponentLoadMonitor
}
