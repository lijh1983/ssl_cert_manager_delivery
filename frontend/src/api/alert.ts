/**
 * 告警管理API
 */

import { request } from '@/utils/request'

export interface AlertRule {
  id: string
  name: string
  alert_type: string
  severity: string
  enabled: boolean
  conditions: Record<string, any>
  notification_providers: string[]
  notification_template: string
  cooldown_minutes: number
  created_at?: string
  updated_at?: string
}

export interface Alert {
  id: string
  rule_id: string
  alert_type: string
  severity: string
  title: string
  description: string
  context: Record<string, any>
  status: string
  created_at?: string
  resolved_at?: string
  last_sent_at?: string
}

export interface CreateAlertRuleRequest {
  name: string
  alert_type: string
  severity: string
  enabled?: boolean
  conditions: Record<string, any>
  notification_providers: string[]
  notification_template: string
  cooldown_minutes?: number
}

export interface UpdateAlertRuleRequest {
  name?: string
  enabled?: boolean
  conditions?: Record<string, any>
  notification_providers?: string[]
  cooldown_minutes?: number
}

export interface TestNotificationRequest {
  provider: string
  recipient: string
  message?: string
}

export const alertApi = {
  /**
   * 获取告警规则列表
   */
  getRules(): Promise<ApiResponse<{ rules: AlertRule[] }>> {
    return request.get('/api/v1/alerts/rules')
  },

  /**
   * 创建告警规则
   */
  createRule(data: CreateAlertRuleRequest): Promise<ApiResponse<{ rule_id: string; message: string }>> {
    return request.post('/api/v1/alerts/rules', data)
  },

  /**
   * 更新告警规则
   */
  updateRule(ruleId: string, data: UpdateAlertRuleRequest): Promise<ApiResponse<{ message: string }>> {
    return request.put(`/api/v1/alerts/rules/${ruleId}`, data)
  },

  /**
   * 删除告警规则
   */
  deleteRule(ruleId: string): Promise<ApiResponse<{ message: string }>> {
    return request.delete(`/api/v1/alerts/rules/${ruleId}`)
  },

  /**
   * 获取活跃告警
   */
  getActiveAlerts(): Promise<ApiResponse<{ alerts: Alert[] }>> {
    return request.get('/api/v1/alerts/active')
  },

  /**
   * 解决告警
   */
  resolveAlert(alertId: string): Promise<ApiResponse<{ message: string }>> {
    return request.post(`/api/v1/alerts/${alertId}/resolve`)
  },

  /**
   * 获取告警历史
   */
  getAlertHistory(limit?: number): Promise<ApiResponse<{ alerts: Alert[] }>> {
    const params = limit ? { limit } : {}
    return request.get('/api/v1/alerts/history', { params })
  },

  /**
   * 获取可用的通知提供商
   */
  getNotificationProviders(): Promise<ApiResponse<{ providers: string[] }>> {
    return request.get('/api/v1/notifications/providers')
  },

  /**
   * 测试通知发送
   */
  testNotification(data: TestNotificationRequest): Promise<ApiResponse<{ message: string; result: any }>> {
    return request.post('/api/v1/notifications/test', data)
  }
}
