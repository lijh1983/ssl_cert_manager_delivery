import request from './request'
import type {
  Certificate,
  CreateCertificateRequest,
  UpdateCertificateRequest,
  CertificateListResponse,
  CertificateDeployment,
  MonitoringConfig,
  UpdateMonitoringConfigRequest,
  BatchUpdateMonitoringRequest,
  MonitoringStatistics,
  DomainStatus,
  DomainCheckResult,
  BatchDomainCheckRequest,
  BatchDomainCheckResult,
  DomainMonitoringStatistics,
  DomainMonitoringHistory,
  PortStatus,
  PortCheckResult,
  ConfigurePortsRequest,
  BatchPortCheckRequest,
  BatchPortCheckResult,
  PortMonitoringStatistics,
  PortMonitoringHistory,
  SecurityReport,
  ManualCheckRequest,
  ManualCheckResult,
  RenewCertificateRequest,
  RenewCertificateResult,
  ImportCertificatesResult,
  ExportFilters,
  DiscoveryScanRequest,
  DiscoveryScanResult,
  BatchOperationsRequest,
  BatchOperationsResult,
  TaskInfo,
  OperationHistoryResponse,
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
  },

  // 监控配置相关API
  // 获取证书监控配置
  getMonitoringConfig: (id: number): Promise<ApiResponse<MonitoringConfig>> => {
    return request.get(`/certificates/${id}/monitoring`)
  },

  // 更新证书监控配置
  updateMonitoringConfig: (id: number, config: UpdateMonitoringConfigRequest): Promise<ApiResponse<MonitoringConfig>> => {
    return request.put(`/certificates/${id}/monitoring`, config)
  },

  // 批量更新监控配置
  batchUpdateMonitoring: (data: BatchUpdateMonitoringRequest): Promise<ApiResponse> => {
    return request.put('/certificates/monitoring/batch', data)
  },

  // 获取监控统计信息
  getMonitoringStatistics: (): Promise<ApiResponse<MonitoringStatistics>> => {
    return request.get('/monitoring/statistics')
  },

  // 获取启用监控的证书列表
  getMonitoringEnabledCertificates: (enabled: boolean = true): Promise<ApiResponse<{certificates: Certificate[], count: number}>> => {
    return request.get('/certificates/monitoring/enabled', {
      params: { enabled: enabled.toString() }
    })
  },

  // 域名监控相关API
  // 获取证书域名状态
  getDomainStatus: (id: number): Promise<ApiResponse<DomainStatus>> => {
    return request.get(`/certificates/${id}/domain-status`)
  },

  // 手动触发域名检查
  checkDomain: (id: number): Promise<ApiResponse<DomainCheckResult>> => {
    return request.post(`/certificates/${id}/check-domain`)
  },

  // 批量检查域名
  batchCheckDomains: (data: BatchDomainCheckRequest): Promise<ApiResponse<BatchDomainCheckResult>> => {
    return request.post('/certificates/batch-check-domains', data)
  },

  // 获取域名监控统计信息
  getDomainMonitoringStatistics: (): Promise<ApiResponse<DomainMonitoringStatistics>> => {
    return request.get('/domain-monitoring/statistics')
  },

  // 获取域名监控历史
  getDomainHistory: (id: number, params?: {
    page?: number
    per_page?: number
    check_type?: string
  }): Promise<ApiResponse<{
    history: DomainMonitoringHistory[]
    pagination: {
      page: number
      per_page: number
      total: number
      pages: number
    }
  }>> => {
    return request.get(`/certificates/${id}/domain-history`, { params })
  },

  // 端口监控相关API
  // 获取证书端口状态
  getPortStatus: (id: number): Promise<ApiResponse<PortStatus>> => {
    return request.get(`/certificates/${id}/port-status`)
  },

  // 手动触发端口检查
  checkPorts: (id: number): Promise<ApiResponse<PortCheckResult>> => {
    return request.post(`/certificates/${id}/check-ports`)
  },

  // 配置监控端口
  configurePorts: (id: number, data: ConfigurePortsRequest): Promise<ApiResponse<{monitored_ports: number[]}>> => {
    return request.post(`/certificates/${id}/configure-ports`, data)
  },

  // 批量检查端口
  batchCheckPorts: (data: BatchPortCheckRequest): Promise<ApiResponse<BatchPortCheckResult>> => {
    return request.post('/certificates/batch-check-ports', data)
  },

  // 获取端口监控统计信息
  getPortMonitoringStatistics: (): Promise<ApiResponse<PortMonitoringStatistics>> => {
    return request.get('/port-monitoring/statistics')
  },

  // 生成安全评估报告
  getSecurityReport: (certificateId?: number): Promise<ApiResponse<SecurityReport>> => {
    return request.get('/port-monitoring/security-report', {
      params: certificateId ? { certificate_id: certificateId } : undefined
    })
  },

  // 获取端口监控历史
  getPortHistory: (id: number, params?: {
    page?: number
    per_page?: number
    port?: number
    check_type?: string
  }): Promise<ApiResponse<{
    history: PortMonitoringHistory[]
    pagination: {
      page: number
      per_page: number
      total: number
      pages: number
    }
  }>> => {
    return request.get(`/certificates/${id}/port-history`, { params })
  },

  // 证书操作相关API
  // 手动触发证书检测
  manualCheck: (id: number, data?: ManualCheckRequest): Promise<ApiResponse<ManualCheckResult>> => {
    return request.post(`/certificates/${id}/manual-check`, data)
  },

  // 手动续期证书
  renewCertificate: (id: number, data?: RenewCertificateRequest): Promise<ApiResponse<RenewCertificateResult>> => {
    return request.post(`/certificates/${id}/renew`, data)
  },

  // 批量导入证书
  importCertificates: (file: File): Promise<ApiResponse<ImportCertificatesResult>> => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/certificates/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 导出证书数据
  exportCertificates: (filters?: ExportFilters): Promise<Blob> => {
    return request.get('/certificates/export', {
      params: filters,
      responseType: 'blob'
    })
  },

  // 网络发现扫描
  discoveryScan: (data: DiscoveryScanRequest): Promise<ApiResponse<DiscoveryScanResult>> => {
    return request.post('/certificates/discovery-scan', data)
  },

  // 获取证书操作历史
  getOperationHistory: (id: number, params?: {
    page?: number
    per_page?: number
  }): Promise<ApiResponse<OperationHistoryResponse>> => {
    return request.get(`/certificates/${id}/operation-history`, { params })
  },

  // 批量操作
  batchOperations: (data: BatchOperationsRequest): Promise<ApiResponse<BatchOperationsResult>> => {
    return request.post('/certificates/batch-operations', data)
  },

  // 获取任务状态
  getTaskStatus: (taskId: string): Promise<ApiResponse<TaskInfo>> => {
    return request.get(`/tasks/${taskId}/status`)
  },

  // 取消任务
  cancelTask: (taskId: string): Promise<ApiResponse<null>> => {
    return request.post(`/tasks/${taskId}/cancel`)
  }
}
