export interface Alert {
  id: number
  type: 'expiry' | 'error' | 'revoke'
  message: string
  status: 'pending' | 'sent' | 'resolved'
  certificate_id: number
  certificate?: {
    domain: string
    expires_at: string
  }
  created_at: string
  updated_at: string
}

export interface UpdateAlertRequest {
  status: 'pending' | 'sent' | 'resolved'
}

export interface AlertListResponse {
  total: number
  page: number
  limit: number
  items: Alert[]
}
