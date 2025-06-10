export interface Certificate {
  id: number
  domain: string
  type: 'single' | 'wildcard' | 'multi'
  status: 'valid' | 'expired' | 'revoked' | 'pending'
  server_id: number
  server_name?: string
  ca_type: string
  created_at: string
  expires_at: string
  updated_at: string
  auto_renew?: boolean
  validation_method?: 'dns' | 'http'
  private_key?: string
  certificate?: string
  days_left?: number
  // 监控控制字段
  monitoring_enabled: boolean
  monitoring_frequency: number
  alert_enabled: boolean
  // 备注信息字段
  notes?: string
  tags?: string
  owner?: string
  business_unit?: string
  // 域名监控字段
  dns_status?: string
  dns_response_time?: number
  domain_reachable?: boolean
  http_status_code?: number
  last_dns_check?: string
  last_reachability_check?: string
  // 端口监控字段
  monitored_ports?: string
  ssl_handshake_time?: number
  tls_version?: string
  cipher_suite?: string
  certificate_chain_valid?: boolean
  http_redirect_status?: string
  last_port_check?: string
  // 证书操作字段
  last_manual_check?: string
  check_in_progress?: boolean
  renewal_status?: string
  auto_renewal_enabled?: boolean
  renewal_days_before?: number
  import_source?: string
  last_renewal_attempt?: string
}

export interface CreateCertificateRequest {
  domain: string
  server_id: number
  type: 'single' | 'wildcard' | 'multi'
  ca_type: string
  validation_method: 'dns' | 'http'
  auto_renew?: boolean
  email?: string
}

export interface UpdateCertificateRequest {
  auto_renew?: boolean
  notes?: string
  tags?: string
  owner?: string
  business_unit?: string
}

// 监控配置相关类型
export interface MonitoringConfig {
  monitoring_enabled: boolean
  monitoring_frequency: number
  alert_enabled: boolean
}

export interface UpdateMonitoringConfigRequest {
  monitoring_enabled?: boolean
  monitoring_frequency?: number
  alert_enabled?: boolean
}

export interface BatchUpdateMonitoringRequest {
  certificate_ids: number[]
  monitoring_enabled?: boolean
  monitoring_frequency?: number
  alert_enabled?: boolean
}

export interface MonitoringStatistics {
  total_certificates: number
  monitoring_enabled_count: number
  alert_enabled_count: number
  average_frequency: number
  frequency_distribution: {
    frequency: number
    count: number
  }[]
}

// 域名监控相关类型
export interface DomainStatus {
  certificate_id: number
  domain: string
  dns_status?: string
  dns_response_time?: number
  domain_reachable?: boolean
  http_status_code?: number
  last_dns_check?: string
  last_reachability_check?: string
}

export interface DomainCheckResult {
  success: boolean
  certificate_id: number
  domain: string
  dns_check: {
    domain: string
    status: string
    response_time: number
    records: Record<string, string[]>
    errors: string[]
    dns_server_used?: string
    timestamp: string
  }
  dns_validation: {
    domain: string
    valid: boolean
    issues: string[]
    recommendations: string[]
    details: any
    timestamp: string
  }
  reachability_check: {
    domain: string
    reachable: boolean
    response_time: number
    http_checks: Record<string, any>
    port_checks: Record<string, any>
    ssl_info: Record<string, any>
    errors: string[]
    timestamp: string
  }
  overall_status: string
  timestamp: string
}

export interface BatchDomainCheckRequest {
  certificate_ids: number[]
  max_concurrent?: number
}

export interface BatchDomainCheckResult {
  success: boolean
  total_count: number
  success_count: number
  failed_count: number
  results: DomainCheckResult[]
  errors: string[]
  timestamp: string
}

export interface DomainMonitoringStatistics {
  dns_status_distribution: Record<string, number>
  reachability_distribution: {
    reachable: number
    unreachable: number
  }
  average_dns_response_time: number
  average_success_response_time: number
  recent_checks: {
    dns_checks_last_hour: number
    reachability_checks_last_hour: number
  }
}

export interface DomainMonitoringHistory {
  id: number
  certificate_id: number
  check_type: string
  status: string
  response_time?: number
  details?: string
  error_message?: string
  created_at: string
}

// 端口监控相关类型
export interface PortStatus {
  certificate_id: number
  domain: string
  monitored_ports?: string
  ssl_handshake_time?: number
  tls_version?: string
  cipher_suite?: string
  certificate_chain_valid?: boolean
  http_redirect_status?: string
  last_port_check?: string
}

export interface PortCheckResult {
  success: boolean
  certificate_id: number
  domain: string
  ssl_checks: Record<number, {
    domain: string
    port: number
    ssl_enabled: boolean
    handshake_time: number
    tls_version?: string
    cipher_suite?: string
    certificate_details: any
    certificate_chain_valid: boolean
    security_grade: string
    errors: string[]
    timestamp: string
  }>
  http_redirect_check: {
    domain: string
    port: number
    redirect_enabled: boolean
    redirect_target?: string
    redirect_status_code?: number
    redirect_type?: string
    hsts_enabled: boolean
    hsts_max_age?: number
    errors: string[]
    timestamp: string
  }
  monitored_ports: number[]
  overall_security_grade: string
  timestamp: string
}

export interface ConfigurePortsRequest {
  ports: number[]
}

export interface BatchPortCheckRequest {
  certificate_ids: number[]
  max_concurrent?: number
}

export interface BatchPortCheckResult {
  success: boolean
  total_count: number
  success_count: number
  failed_count: number
  results: PortCheckResult[]
  errors: string[]
  timestamp: string
}

export interface PortMonitoringStatistics {
  tls_version_distribution: Record<string, number>
  certificate_chain_valid_count: number
  certificate_chain_invalid_count: number
  average_handshake_time: number
  slow_handshakes_count: number
  http_redirect_distribution: Record<string, number>
}

export interface PortMonitoringHistory {
  id: number
  certificate_id: number
  port: number
  check_type: string
  status: string
  handshake_time?: number
  tls_version?: string
  cipher_suite?: string
  security_grade?: string
  details?: string
  error_message?: string
  created_at: string
}

export interface SecurityReport {
  certificate_id?: number
  generated_at: string
  total_certificates: number
  security_issues: {
    certificate_id: number
    domain: string
    issue: string
    severity: string
    recommendation: string
  }[]
  issues_count: number
  recommendations: string[]
}

// 证书操作相关类型
export interface ManualCheckRequest {
  check_types?: string[]
}

export interface ManualCheckResult {
  task_id: string
  estimated_duration?: number
}

export interface RenewCertificateRequest {
  force?: boolean
}

export interface RenewCertificateResult {
  new_expires_at?: string
  renewal_details?: any
}

export interface ImportCertificatesResult {
  total_rows: number
  success_count: number
  failed_count: number
  duplicate_count: number
  imported_certificates: {
    id: number
    domain: string
  }[]
  errors: string[]
}

export interface ExportFilters {
  status?: string
  expires_before?: string
  domain_pattern?: string
}

export interface DiscoveryScanRequest {
  ip_ranges: string[]
  ports?: number[]
}

export interface DiscoveryScanResult {
  task_id: string
  total_targets: number
}

export interface BatchOperationsRequest {
  operation_type: 'check' | 'renew' | 'delete'
  certificate_ids: number[]
  options?: Record<string, any>
}

export interface BatchOperationsResult {
  task_id: string
  total_count: number
}

export interface TaskInfo {
  task_id: string
  type?: string
  status: string
  progress: number
  total_items?: number
  processed_items?: number
  success_count?: number
  failed_count?: number
  results?: any[]
  errors?: string[]
  start_time?: string
  end_time?: string
  // 特定任务类型的字段
  certificate_id?: number
  domain?: string
  check_types?: string[]
  total_targets?: number
  scanned_count?: number
  discovered_certificates?: any[]
  total_count?: number
}

export interface CertificateOperation {
  id: number
  certificate_id?: number
  operation_type: string
  status: string
  details?: string
  user_id?: number
  created_at: string
  completed_at?: string
  error_message?: string
}

export interface OperationHistoryResponse {
  operations: CertificateOperation[]
  pagination: {
    page: number
    per_page: number
    total: number
    pages: number
  }
}

export interface DiscoveredCertificate {
  ip: string
  port: number
  has_certificate: boolean
  domain?: string
  san_domains?: string[]
  expires?: string
  issuer?: Record<string, any>
  discovered_at: string
  error?: string
}

export interface CertificateListResponse {
  total: number
  page: number
  limit: number
  items: Certificate[]
}

export interface CertificateDeployment {
  id: number
  certificate_id: number
  service_type: string
  config_path: string
  status: 'success' | 'failed' | 'pending'
  created_at: string
  updated_at: string
}

export interface SyncCertificateRequest {
  certificates: {
    domain: string
    path: string
    key_path: string
    expires_at: string
    type: string
  }[]
}
