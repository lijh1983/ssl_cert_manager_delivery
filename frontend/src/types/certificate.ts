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
}

export interface CreateCertificateRequest {
  domain: string
  server_id: number
  type?: 'single' | 'wildcard' | 'multi'
  ca_type?: string
  validation_method?: 'dns' | 'http'
}

export interface UpdateCertificateRequest {
  auto_renew?: boolean
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
