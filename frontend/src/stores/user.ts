/**
 * 用户状态管理
 * 管理用户信息、权限、偏好设置等
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, UserRole, UserPermission, UserPreferences } from '@/types/user'

// 用户角色枚举
export enum UserRoleEnum {
  ADMIN = 'admin',
  USER = 'user',
  VIEWER = 'viewer'
}

// 用户权限枚举
export enum UserPermissionEnum {
  // 证书管理权限
  CERTIFICATE_VIEW = 'certificate:view',
  CERTIFICATE_CREATE = 'certificate:create',
  CERTIFICATE_UPDATE = 'certificate:update',
  CERTIFICATE_DELETE = 'certificate:delete',
  
  // 服务器管理权限
  SERVER_VIEW = 'server:view',
  SERVER_CREATE = 'server:create',
  SERVER_UPDATE = 'server:update',
  SERVER_DELETE = 'server:delete',
  
  // 告警管理权限
  ALERT_VIEW = 'alert:view',
  ALERT_CREATE = 'alert:create',
  ALERT_UPDATE = 'alert:update',
  ALERT_DELETE = 'alert:delete',
  ALERT_ACKNOWLEDGE = 'alert:acknowledge',
  
  // 日志查看权限
  LOG_VIEW = 'log:view',
  LOG_EXPORT = 'log:export',
  
  // 用户管理权限
  USER_VIEW = 'user:view',
  USER_CREATE = 'user:create',
  USER_UPDATE = 'user:update',
  USER_DELETE = 'user:delete',
  
  // 系统设置权限
  SYSTEM_VIEW = 'system:view',
  SYSTEM_UPDATE = 'system:update',
  
  // 监控权限
  MONITORING_VIEW = 'monitoring:view',
  MONITORING_CONFIG = 'monitoring:config'
}

// 默认用户偏好设置
const defaultPreferences: UserPreferences = {
  theme: 'light',
  language: 'zh-CN',
  timezone: 'Asia/Shanghai',
  dateFormat: 'YYYY-MM-DD HH:mm:ss',
  pageSize: 20,
  autoRefresh: true,
  refreshInterval: 30000, // 30秒
  notifications: {
    email: true,
    browser: true,
    sound: false
  },
  dashboard: {
    showWelcome: true,
    defaultView: 'overview',
    widgets: ['certificates', 'alerts', 'servers']
  }
}

// 角色权限映射
const rolePermissions: Record<UserRoleEnum, UserPermissionEnum[]> = {
  [UserRoleEnum.ADMIN]: [
    // 管理员拥有所有权限
    UserPermissionEnum.CERTIFICATE_VIEW,
    UserPermissionEnum.CERTIFICATE_CREATE,
    UserPermissionEnum.CERTIFICATE_UPDATE,
    UserPermissionEnum.CERTIFICATE_DELETE,
    UserPermissionEnum.SERVER_VIEW,
    UserPermissionEnum.SERVER_CREATE,
    UserPermissionEnum.SERVER_UPDATE,
    UserPermissionEnum.SERVER_DELETE,
    UserPermissionEnum.ALERT_VIEW,
    UserPermissionEnum.ALERT_CREATE,
    UserPermissionEnum.ALERT_UPDATE,
    UserPermissionEnum.ALERT_DELETE,
    UserPermissionEnum.ALERT_ACKNOWLEDGE,
    UserPermissionEnum.LOG_VIEW,
    UserPermissionEnum.LOG_EXPORT,
    UserPermissionEnum.USER_VIEW,
    UserPermissionEnum.USER_CREATE,
    UserPermissionEnum.USER_UPDATE,
    UserPermissionEnum.USER_DELETE,
    UserPermissionEnum.SYSTEM_VIEW,
    UserPermissionEnum.SYSTEM_UPDATE,
    UserPermissionEnum.MONITORING_VIEW,
    UserPermissionEnum.MONITORING_CONFIG
  ],
  [UserRoleEnum.USER]: [
    // 普通用户权限
    UserPermissionEnum.CERTIFICATE_VIEW,
    UserPermissionEnum.CERTIFICATE_CREATE,
    UserPermissionEnum.CERTIFICATE_UPDATE,
    UserPermissionEnum.SERVER_VIEW,
    UserPermissionEnum.SERVER_CREATE,
    UserPermissionEnum.SERVER_UPDATE,
    UserPermissionEnum.ALERT_VIEW,
    UserPermissionEnum.ALERT_ACKNOWLEDGE,
    UserPermissionEnum.LOG_VIEW,
    UserPermissionEnum.MONITORING_VIEW
  ],
  [UserRoleEnum.VIEWER]: [
    // 只读用户权限
    UserPermissionEnum.CERTIFICATE_VIEW,
    UserPermissionEnum.SERVER_VIEW,
    UserPermissionEnum.ALERT_VIEW,
    UserPermissionEnum.LOG_VIEW,
    UserPermissionEnum.MONITORING_VIEW
  ]
}

export const useUserStore = defineStore('user', () => {
  // 状态
  const currentUser = ref<User | null>(null)
  const preferences = ref<UserPreferences>({ ...defaultPreferences })
  const isLoading = ref(false)
  const lastActivity = ref<Date>(new Date())

  // 计算属性
  const isLoggedIn = computed(() => !!currentUser.value)
  
  const userRole = computed(() => currentUser.value?.role || UserRoleEnum.VIEWER)
  
  const isAdmin = computed(() => userRole.value === UserRoleEnum.ADMIN)
  
  const isUser = computed(() => userRole.value === UserRoleEnum.USER)
  
  const isViewer = computed(() => userRole.value === UserRoleEnum.VIEWER)
  
  const userPermissions = computed(() => {
    if (!currentUser.value) return []
    return rolePermissions[userRole.value] || []
  })
  
  const userName = computed(() => currentUser.value?.name || '未知用户')
  
  const userEmail = computed(() => currentUser.value?.email || '')
  
  const userAvatar = computed(() => currentUser.value?.avatar || '')

  // 权限检查方法
  const hasPermission = (permission: UserPermissionEnum): boolean => {
    return userPermissions.value.includes(permission)
  }

  const hasAnyPermission = (permissions: UserPermissionEnum[]): boolean => {
    return permissions.some(permission => hasPermission(permission))
  }

  const hasAllPermissions = (permissions: UserPermissionEnum[]): boolean => {
    return permissions.every(permission => hasPermission(permission))
  }

  // 角色检查方法
  const hasRole = (role: UserRoleEnum): boolean => {
    return userRole.value === role
  }

  const hasAnyRole = (roles: UserRoleEnum[]): boolean => {
    return roles.includes(userRole.value)
  }

  // 用户操作方法
  const setUser = (user: User) => {
    currentUser.value = user
    updateLastActivity()
  }

  const clearUser = () => {
    currentUser.value = null
    preferences.value = { ...defaultPreferences }
  }

  const updateUser = (updates: Partial<User>) => {
    if (currentUser.value) {
      currentUser.value = { ...currentUser.value, ...updates }
    }
  }

  const updatePreferences = (newPreferences: Partial<UserPreferences>) => {
    preferences.value = { ...preferences.value, ...newPreferences }
    // 这里可以添加保存到后端的逻辑
  }

  const updateLastActivity = () => {
    lastActivity.value = new Date()
  }

  // 主题相关方法
  const setTheme = (theme: 'light' | 'dark' | 'auto') => {
    updatePreferences({ theme })
  }

  const setLanguage = (language: string) => {
    updatePreferences({ language })
  }

  // 通知设置方法
  const updateNotificationSettings = (notifications: Partial<UserPreferences['notifications']>) => {
    updatePreferences({
      notifications: { ...preferences.value.notifications, ...notifications }
    })
  }

  // 仪表板设置方法
  const updateDashboardSettings = (dashboard: Partial<UserPreferences['dashboard']>) => {
    updatePreferences({
      dashboard: { ...preferences.value.dashboard, ...dashboard }
    })
  }

  // 获取用户显示名称
  const getDisplayName = (): string => {
    if (!currentUser.value) return '游客'
    return currentUser.value.displayName || currentUser.value.name || currentUser.value.email
  }

  // 检查用户是否在线（基于最后活动时间）
  const isOnline = computed(() => {
    const now = new Date()
    const diff = now.getTime() - lastActivity.value.getTime()
    return diff < 5 * 60 * 1000 // 5分钟内有活动认为在线
  })

  // 获取用户状态文本
  const getStatusText = (): string => {
    if (!isLoggedIn.value) return '未登录'
    if (isOnline.value) return '在线'
    return '离线'
  }

  return {
    // 状态
    currentUser,
    preferences,
    isLoading,
    lastActivity,

    // 计算属性
    isLoggedIn,
    userRole,
    isAdmin,
    isUser,
    isViewer,
    userPermissions,
    userName,
    userEmail,
    userAvatar,
    isOnline,

    // 方法
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    hasRole,
    hasAnyRole,
    setUser,
    clearUser,
    updateUser,
    updatePreferences,
    updateLastActivity,
    setTheme,
    setLanguage,
    updateNotificationSettings,
    updateDashboardSettings,
    getDisplayName,
    getStatusText
  }
})
