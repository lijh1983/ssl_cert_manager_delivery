/**
 * 用户相关类型定义
 */

// 用户角色类型
export type UserRole = 'admin' | 'user' | 'viewer'

// 用户权限类型
export type UserPermission = 
  // 证书管理权限
  | 'certificate:view'
  | 'certificate:create'
  | 'certificate:update'
  | 'certificate:delete'
  
  // 服务器管理权限
  | 'server:view'
  | 'server:create'
  | 'server:update'
  | 'server:delete'
  
  // 告警管理权限
  | 'alert:view'
  | 'alert:create'
  | 'alert:update'
  | 'alert:delete'
  | 'alert:acknowledge'
  
  // 日志查看权限
  | 'log:view'
  | 'log:export'
  
  // 用户管理权限
  | 'user:view'
  | 'user:create'
  | 'user:update'
  | 'user:delete'
  
  // 系统设置权限
  | 'system:view'
  | 'system:update'
  
  // 监控权限
  | 'monitoring:view'
  | 'monitoring:config'

// 用户基本信息接口
export interface User {
  id: string
  username: string
  name: string
  displayName?: string
  email: string
  avatar?: string
  role: UserRole
  permissions: UserPermission[]
  status: 'active' | 'inactive' | 'suspended'
  createdAt: string
  updatedAt: string
  lastLoginAt?: string
  lastLoginIp?: string
  emailVerified: boolean
  twoFactorEnabled: boolean
  department?: string
  position?: string
  phone?: string
  timezone?: string
  language?: string
}

// 用户创建请求接口
export interface CreateUserRequest {
  username: string
  name: string
  email: string
  password: string
  role: UserRole
  department?: string
  position?: string
  phone?: string
}

// 用户更新请求接口
export interface UpdateUserRequest {
  name?: string
  email?: string
  avatar?: string
  department?: string
  position?: string
  phone?: string
  timezone?: string
  language?: string
}

// 用户密码更改请求接口
export interface ChangePasswordRequest {
  currentPassword: string
  newPassword: string
  confirmPassword: string
}

// 用户偏好设置接口
export interface UserPreferences {
  theme: 'light' | 'dark' | 'auto'
  language: string
  timezone: string
  dateFormat: string
  pageSize: number
  autoRefresh: boolean
  refreshInterval: number
  notifications: {
    email: boolean
    browser: boolean
    sound: boolean
  }
  dashboard: {
    showWelcome: boolean
    defaultView: string
    widgets: string[]
  }
}

// 用户会话信息接口
export interface UserSession {
  id: string
  userId: string
  deviceInfo: string
  ipAddress: string
  userAgent: string
  createdAt: string
  lastActiveAt: string
  expiresAt: string
  isActive: boolean
}

// 用户活动日志接口
export interface UserActivity {
  id: string
  userId: string
  action: string
  resource: string
  resourceId?: string
  details?: Record<string, any>
  ipAddress: string
  userAgent: string
  createdAt: string
}

// 用户统计信息接口
export interface UserStats {
  totalUsers: number
  activeUsers: number
  newUsersToday: number
  newUsersThisWeek: number
  newUsersThisMonth: number
  usersByRole: Record<UserRole, number>
  usersByStatus: Record<string, number>
  loginStats: {
    todayLogins: number
    weeklyLogins: number
    monthlyLogins: number
  }
}

// 用户查询参数接口
export interface UserQueryParams {
  page?: number
  pageSize?: number
  search?: string
  role?: UserRole
  status?: string
  department?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  createdAfter?: string
  createdBefore?: string
  lastLoginAfter?: string
  lastLoginBefore?: string
}

// 用户列表响应接口
export interface UserListResponse {
  users: User[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

// 用户角色信息接口
export interface RoleInfo {
  role: UserRole
  name: string
  description: string
  permissions: UserPermission[]
  color: string
  icon: string
}

// 用户权限信息接口
export interface PermissionInfo {
  permission: UserPermission
  name: string
  description: string
  category: string
  level: 'read' | 'write' | 'admin'
}

// 用户邀请接口
export interface UserInvitation {
  id: string
  email: string
  role: UserRole
  invitedBy: string
  invitedAt: string
  expiresAt: string
  status: 'pending' | 'accepted' | 'expired' | 'cancelled'
  token: string
}

// 用户邀请请求接口
export interface InviteUserRequest {
  email: string
  role: UserRole
  message?: string
}

// 用户个人资料更新接口
export interface ProfileUpdateRequest {
  name?: string
  displayName?: string
  avatar?: string
  phone?: string
  department?: string
  position?: string
  timezone?: string
  language?: string
}

// 用户安全设置接口
export interface UserSecuritySettings {
  twoFactorEnabled: boolean
  backupCodes: string[]
  trustedDevices: Array<{
    id: string
    name: string
    lastUsed: string
    isActive: boolean
  }>
  loginHistory: Array<{
    timestamp: string
    ipAddress: string
    userAgent: string
    location?: string
    success: boolean
  }>
}

// 用户通知设置接口
export interface UserNotificationSettings {
  email: {
    enabled: boolean
    certificateExpiry: boolean
    alertNotifications: boolean
    systemUpdates: boolean
    securityAlerts: boolean
  }
  browser: {
    enabled: boolean
    certificateExpiry: boolean
    alertNotifications: boolean
  }
  mobile: {
    enabled: boolean
    certificateExpiry: boolean
    alertNotifications: boolean
  }
}

// 导出所有类型
export type {
  User,
  UserRole,
  UserPermission,
  CreateUserRequest,
  UpdateUserRequest,
  ChangePasswordRequest,
  UserPreferences,
  UserSession,
  UserActivity,
  UserStats,
  UserQueryParams,
  UserListResponse,
  RoleInfo,
  PermissionInfo,
  UserInvitation,
  InviteUserRequest,
  ProfileUpdateRequest,
  UserSecuritySettings,
  UserNotificationSettings
}
