/**
 * 性能监控工具
 * 提供页面性能、组件性能、API性能等监控功能
 */

// 性能指标接口
interface PerformanceMetric {
  name: string
  value: number
  timestamp: number
  type: 'timing' | 'counter' | 'gauge'
  tags?: Record<string, string>
}

// 页面性能指标
interface PagePerformance {
  loadTime: number
  domContentLoaded: number
  firstPaint: number
  firstContentfulPaint: number
  largestContentfulPaint: number
  firstInputDelay: number
  cumulativeLayoutShift: number
  timeToInteractive: number
}

// 组件性能指标
interface ComponentPerformance {
  name: string
  mountTime: number
  updateTime: number
  renderCount: number
  lastRenderTime: number
}

// API性能指标
interface ApiPerformance {
  url: string
  method: string
  duration: number
  status: number
  size: number
  cached: boolean
  timestamp: number
}

/**
 * 性能监控管理器
 */
export class PerformanceMonitor {
  private static instance: PerformanceMonitor
  private metrics: PerformanceMetric[] = []
  private componentMetrics = new Map<string, ComponentPerformance>()
  private apiMetrics: ApiPerformance[] = []
  private observers: PerformanceObserver[] = []
  private isEnabled = true

  static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor()
    }
    return PerformanceMonitor.instance
  }

  constructor() {
    this.initializeObservers()
  }

  /**
   * 初始化性能观察器
   */
  private initializeObservers() {
    if (!this.isEnabled || typeof window === 'undefined') return

    try {
      // 观察导航时间
      if ('PerformanceObserver' in window) {
        const navigationObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            this.recordNavigationTiming(entry as PerformanceNavigationTiming)
          }
        })
        navigationObserver.observe({ entryTypes: ['navigation'] })
        this.observers.push(navigationObserver)

        // 观察资源加载时间
        const resourceObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            this.recordResourceTiming(entry as PerformanceResourceTiming)
          }
        })
        resourceObserver.observe({ entryTypes: ['resource'] })
        this.observers.push(resourceObserver)

        // 观察用户交互时间
        const measureObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            this.recordMeasure(entry as PerformanceMeasure)
          }
        })
        measureObserver.observe({ entryTypes: ['measure'] })
        this.observers.push(measureObserver)

        // 观察长任务
        if ('PerformanceObserver' in window && 'longtask' in PerformanceObserver.supportedEntryTypes) {
          const longTaskObserver = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
              this.recordLongTask(entry)
            }
          })
          longTaskObserver.observe({ entryTypes: ['longtask'] })
          this.observers.push(longTaskObserver)
        }
      }

      // 监听页面可见性变化
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
          this.recordPageHide()
        }
      })

    } catch (error) {
      console.warn('性能监控初始化失败:', error)
    }
  }

  /**
   * 记录导航时间
   */
  private recordNavigationTiming(entry: PerformanceNavigationTiming) {
    const metrics = [
      { name: 'page_load_time', value: entry.loadEventEnd - entry.navigationStart },
      { name: 'dom_content_loaded', value: entry.domContentLoadedEventEnd - entry.navigationStart },
      { name: 'dom_interactive', value: entry.domInteractive - entry.navigationStart },
      { name: 'dns_lookup', value: entry.domainLookupEnd - entry.domainLookupStart },
      { name: 'tcp_connect', value: entry.connectEnd - entry.connectStart },
      { name: 'request_response', value: entry.responseEnd - entry.requestStart },
      { name: 'dom_processing', value: entry.domComplete - entry.domLoading }
    ]

    metrics.forEach(metric => {
      if (metric.value > 0) {
        this.addMetric(metric.name, metric.value, 'timing')
      }
    })
  }

  /**
   * 记录资源加载时间
   */
  private recordResourceTiming(entry: PerformanceResourceTiming) {
    const duration = entry.responseEnd - entry.startTime
    const size = entry.transferSize || 0

    this.addMetric('resource_load_time', duration, 'timing', {
      resource_type: entry.initiatorType,
      resource_name: entry.name.split('/').pop() || 'unknown'
    })

    if (size > 0) {
      this.addMetric('resource_size', size, 'gauge', {
        resource_type: entry.initiatorType
      })
    }
  }

  /**
   * 记录自定义测量
   */
  private recordMeasure(entry: PerformanceMeasure) {
    this.addMetric(entry.name, entry.duration, 'timing')
  }

  /**
   * 记录长任务
   */
  private recordLongTask(entry: PerformanceEntry) {
    this.addMetric('long_task', entry.duration, 'timing', {
      task_type: entry.entryType
    })
  }

  /**
   * 记录页面隐藏
   */
  private recordPageHide() {
    const now = performance.now()
    this.addMetric('page_session_duration', now, 'timing')
  }

  /**
   * 添加性能指标
   */
  addMetric(name: string, value: number, type: 'timing' | 'counter' | 'gauge', tags?: Record<string, string>) {
    if (!this.isEnabled) return

    const metric: PerformanceMetric = {
      name,
      value,
      timestamp: Date.now(),
      type,
      tags
    }

    this.metrics.push(metric)

    // 限制指标数量，避免内存泄漏
    if (this.metrics.length > 1000) {
      this.metrics = this.metrics.slice(-500)
    }
  }

  /**
   * 开始计时
   */
  startTiming(name: string): () => void {
    const startTime = performance.now()
    
    return () => {
      const duration = performance.now() - startTime
      this.addMetric(name, duration, 'timing')
      return duration
    }
  }

  /**
   * 测量函数执行时间
   */
  measureFunction<T>(name: string, fn: () => T): T {
    const endTiming = this.startTiming(name)
    try {
      const result = fn()
      endTiming()
      return result
    } catch (error) {
      endTiming()
      throw error
    }
  }

  /**
   * 测量异步函数执行时间
   */
  async measureAsyncFunction<T>(name: string, fn: () => Promise<T>): Promise<T> {
    const endTiming = this.startTiming(name)
    try {
      const result = await fn()
      endTiming()
      return result
    } catch (error) {
      endTiming()
      throw error
    }
  }

  /**
   * 记录组件性能
   */
  recordComponentPerformance(name: string, type: 'mount' | 'update', duration: number) {
    const existing = this.componentMetrics.get(name) || {
      name,
      mountTime: 0,
      updateTime: 0,
      renderCount: 0,
      lastRenderTime: 0
    }

    if (type === 'mount') {
      existing.mountTime = duration
    } else {
      existing.updateTime = duration
    }

    existing.renderCount++
    existing.lastRenderTime = Date.now()

    this.componentMetrics.set(name, existing)
    this.addMetric(`component_${type}_time`, duration, 'timing', { component: name })
  }

  /**
   * 记录API性能
   */
  recordApiPerformance(metric: ApiPerformance) {
    this.apiMetrics.push(metric)
    
    // 限制API指标数量
    if (this.apiMetrics.length > 500) {
      this.apiMetrics = this.apiMetrics.slice(-250)
    }

    this.addMetric('api_request_duration', metric.duration, 'timing', {
      method: metric.method,
      status: metric.status.toString(),
      cached: metric.cached.toString()
    })

    if (metric.size > 0) {
      this.addMetric('api_response_size', metric.size, 'gauge', {
        method: metric.method
      })
    }
  }

  /**
   * 获取页面性能指标
   */
  getPagePerformance(): PagePerformance | null {
    if (typeof window === 'undefined' || !window.performance) return null

    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming
    if (!navigation) return null

    return {
      loadTime: navigation.loadEventEnd - navigation.navigationStart,
      domContentLoaded: navigation.domContentLoadedEventEnd - navigation.navigationStart,
      firstPaint: this.getFirstPaint(),
      firstContentfulPaint: this.getFirstContentfulPaint(),
      largestContentfulPaint: this.getLargestContentfulPaint(),
      firstInputDelay: this.getFirstInputDelay(),
      cumulativeLayoutShift: this.getCumulativeLayoutShift(),
      timeToInteractive: this.getTimeToInteractive()
    }
  }

  /**
   * 获取组件性能指标
   */
  getComponentPerformance(): ComponentPerformance[] {
    return Array.from(this.componentMetrics.values())
  }

  /**
   * 获取API性能指标
   */
  getApiPerformance(): ApiPerformance[] {
    return [...this.apiMetrics]
  }

  /**
   * 获取所有性能指标
   */
  getAllMetrics(): PerformanceMetric[] {
    return [...this.metrics]
  }

  /**
   * 获取性能统计
   */
  getPerformanceStats() {
    const pagePerf = this.getPagePerformance()
    const componentPerf = this.getComponentPerformance()
    const apiPerf = this.getApiPerformance()

    return {
      page: pagePerf,
      components: componentPerf,
      api: {
        totalRequests: apiPerf.length,
        averageDuration: apiPerf.length > 0 
          ? apiPerf.reduce((sum, metric) => sum + metric.duration, 0) / apiPerf.length 
          : 0,
        cacheHitRate: apiPerf.length > 0 
          ? apiPerf.filter(metric => metric.cached).length / apiPerf.length 
          : 0
      },
      memory: this.getMemoryUsage(),
      timestamp: Date.now()
    }
  }

  /**
   * 清除性能数据
   */
  clearMetrics() {
    this.metrics.length = 0
    this.componentMetrics.clear()
    this.apiMetrics.length = 0
  }

  /**
   * 启用/禁用性能监控
   */
  setEnabled(enabled: boolean) {
    this.isEnabled = enabled
    
    if (!enabled) {
      this.observers.forEach(observer => observer.disconnect())
      this.observers.length = 0
    } else if (this.observers.length === 0) {
      this.initializeObservers()
    }
  }

  /**
   * 获取First Paint时间
   */
  private getFirstPaint(): number {
    const paintEntries = performance.getEntriesByType('paint')
    const fpEntry = paintEntries.find(entry => entry.name === 'first-paint')
    return fpEntry ? fpEntry.startTime : 0
  }

  /**
   * 获取First Contentful Paint时间
   */
  private getFirstContentfulPaint(): number {
    const paintEntries = performance.getEntriesByType('paint')
    const fcpEntry = paintEntries.find(entry => entry.name === 'first-contentful-paint')
    return fcpEntry ? fcpEntry.startTime : 0
  }

  /**
   * 获取Largest Contentful Paint时间
   */
  private getLargestContentfulPaint(): number {
    // 这里需要使用Web Vitals库或自定义实现
    return 0
  }

  /**
   * 获取First Input Delay时间
   */
  private getFirstInputDelay(): number {
    // 这里需要使用Web Vitals库或自定义实现
    return 0
  }

  /**
   * 获取Cumulative Layout Shift分数
   */
  private getCumulativeLayoutShift(): number {
    // 这里需要使用Web Vitals库或自定义实现
    return 0
  }

  /**
   * 获取Time to Interactive时间
   */
  private getTimeToInteractive(): number {
    // 这里需要使用Web Vitals库或自定义实现
    return 0
  }

  /**
   * 获取内存使用情况
   */
  private getMemoryUsage() {
    if ('memory' in performance) {
      const memory = (performance as any).memory
      return {
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit
      }
    }
    return null
  }

  /**
   * 销毁监控器
   */
  destroy() {
    this.observers.forEach(observer => observer.disconnect())
    this.observers.length = 0
    this.clearMetrics()
  }
}

// 导出全局实例
export const performanceMonitor = PerformanceMonitor.getInstance()

// Vue组件性能监控装饰器
export function withPerformanceMonitoring(componentName: string) {
  return function(target: any) {
    const originalMounted = target.mounted
    const originalUpdated = target.updated

    target.mounted = function() {
      const endTiming = performanceMonitor.startTiming(`${componentName}_mount`)
      if (originalMounted) {
        originalMounted.call(this)
      }
      const duration = endTiming()
      performanceMonitor.recordComponentPerformance(componentName, 'mount', duration)
    }

    target.updated = function() {
      const endTiming = performanceMonitor.startTiming(`${componentName}_update`)
      if (originalUpdated) {
        originalUpdated.call(this)
      }
      const duration = endTiming()
      performanceMonitor.recordComponentPerformance(componentName, 'update', duration)
    }

    return target
  }
}

// 性能报告生成器
export function generatePerformanceReport() {
  const stats = performanceMonitor.getPerformanceStats()
  
  return {
    summary: {
      pageLoadTime: stats.page?.loadTime || 0,
      apiAverageDuration: stats.api.averageDuration,
      cacheHitRate: stats.api.cacheHitRate,
      componentCount: stats.components.length
    },
    details: stats,
    recommendations: generateRecommendations(stats)
  }
}

// 性能优化建议生成器
function generateRecommendations(stats: any): string[] {
  const recommendations: string[] = []

  if (stats.page?.loadTime > 3000) {
    recommendations.push('页面加载时间过长，建议优化资源加载')
  }

  if (stats.api.averageDuration > 1000) {
    recommendations.push('API响应时间较慢，建议优化后端性能或增加缓存')
  }

  if (stats.api.cacheHitRate < 0.5) {
    recommendations.push('缓存命中率较低，建议优化缓存策略')
  }

  if (stats.memory?.usedJSHeapSize > 50 * 1024 * 1024) {
    recommendations.push('内存使用量较高，建议检查内存泄漏')
  }

  return recommendations
}
