export interface Server {
  id: number
  name: string
  ip?: string
  os_type?: string
  hostname?: string
  version?: string
  status: 'online' | 'offline' | 'unknown'
  last_seen?: string
  auto_renew: boolean
  user_id: number
  created_at: string
  updated_at: string
  certificates_count?: number
  certificates?: any[]
  token?: string
  install_command?: string
}

export interface CreateServerRequest {
  name: string
  auto_renew?: boolean
}

export interface UpdateServerRequest {
  name?: string
  auto_renew?: boolean
}

export interface RegisterServerRequest {
  hostname: string
  ip: string
  os_type: string
  version: string
}

export interface HeartbeatRequest {
  version: string
  timestamp: number
}

export interface ServerListResponse {
  total: number
  page: number
  limit: number
  items: Server[]
}
