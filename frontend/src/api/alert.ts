import request from './request'
import type { Alert, UpdateAlertRequest, AlertListResponse, ApiResponse } from '@/types/alert'

export const alertApi = {
  // 获取告警列表
  getList: (params?: {
    page?: number
    limit?: number
    type?: string
    status?: string
  }): Promise<ApiResponse<AlertListResponse>> => {
    return request.get('/alerts', { params })
  },

  // 获取告警详情
  getDetail: (id: number): Promise<ApiResponse<Alert>> => {
    return request.get(`/alerts/${id}`)
  },

  // 更新告警状态
  update: (id: number, data: UpdateAlertRequest): Promise<ApiResponse<Alert>> => {
    return request.put(`/alerts/${id}`, data)
  },

  // 删除告警
  delete: (id: number): Promise<ApiResponse> => {
    return request.delete(`/alerts/${id}`)
  },

  // 批量处理告警
  batchResolve: (ids: number[]): Promise<ApiResponse> => {
    return request.post('/alerts/batch-resolve', { ids })
  }
}
