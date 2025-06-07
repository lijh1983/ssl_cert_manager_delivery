import request from './request'
import type { 
  Server, 
  CreateServerRequest, 
  UpdateServerRequest, 
  ServerListResponse,
  ApiResponse 
} from '@/types/server'

export const serverApi = {
  // 获取服务器列表
  getList: (params?: {
    page?: number
    limit?: number
    keyword?: string
  }): Promise<ApiResponse<ServerListResponse>> => {
    return request.get('/servers', { params })
  },

  // 获取服务器详情
  getDetail: (id: number): Promise<ApiResponse<Server>> => {
    return request.get(`/servers/${id}`)
  },

  // 创建服务器
  create: (data: CreateServerRequest): Promise<ApiResponse<Server>> => {
    return request.post('/servers', data)
  },

  // 更新服务器
  update: (id: number, data: UpdateServerRequest): Promise<ApiResponse<Server>> => {
    return request.put(`/servers/${id}`, data)
  },

  // 删除服务器
  delete: (id: number): Promise<ApiResponse> => {
    return request.delete(`/servers/${id}`)
  },

  // 重新生成服务器令牌
  regenerateToken: (id: number): Promise<ApiResponse<{ token: string; install_command: string }>> => {
    return request.post(`/servers/${id}/regenerate-token`)
  }
}
