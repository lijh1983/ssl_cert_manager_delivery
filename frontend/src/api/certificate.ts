import request from './request'
import type { 
  Certificate, 
  CreateCertificateRequest, 
  UpdateCertificateRequest, 
  CertificateListResponse,
  CertificateDeployment,
  ApiResponse 
} from '@/types/certificate'

export const certificateApi = {
  // 获取证书列表
  getList: (params?: {
    page?: number
    limit?: number
    keyword?: string
    status?: string
    server_id?: number
  }): Promise<ApiResponse<CertificateListResponse>> => {
    return request.get('/certificates', { params })
  },

  // 获取证书详情
  getDetail: (id: number): Promise<ApiResponse<Certificate>> => {
    return request.get(`/certificates/${id}`)
  },

  // 创建证书
  create: (data: CreateCertificateRequest): Promise<ApiResponse<Certificate>> => {
    return request.post('/certificates', data)
  },

  // 更新证书
  update: (id: number, data: UpdateCertificateRequest): Promise<ApiResponse<Certificate>> => {
    return request.put(`/certificates/${id}`, data)
  },

  // 删除证书
  delete: (id: number): Promise<ApiResponse> => {
    return request.delete(`/certificates/${id}`)
  },

  // 续期证书
  renew: (id: number): Promise<ApiResponse> => {
    return request.post(`/certificates/${id}/renew`)
  },

  // 获取证书部署记录
  getDeployments: (id: number): Promise<ApiResponse<CertificateDeployment[]>> => {
    return request.get(`/certificates/${id}/deployments`)
  },

  // 下载证书
  download: (id: number, type: 'cert' | 'key' | 'fullchain'): Promise<Blob> => {
    return request.get(`/certificates/${id}/download/${type}`, {
      responseType: 'blob'
    })
  },

  // 获取即将过期的证书
  getExpiring: (days?: number): Promise<ApiResponse<Certificate[]>> => {
    return request.get('/certificates/expiring', { 
      params: { days: days || 30 } 
    })
  }
}
