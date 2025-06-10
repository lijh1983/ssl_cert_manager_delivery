"""
证书模型模块，处理证书相关的数据操作
"""
import datetime
import json
from typing import Dict, List, Any, Optional, Tuple
from .database import db

class Certificate:
    """证书模型类"""
    
    def __init__(self, id: int = None, domain: str = None, type: str = None,
                 status: str = None, created_at: str = None, expires_at: str = None,
                 server_id: int = None, ca_type: str = None,
                 private_key: str = None, certificate: str = None,
                 updated_at: str = None, monitoring_enabled: bool = True,
                 monitoring_frequency: int = 3600, alert_enabled: bool = True,
                 notes: str = None, tags: str = None, owner: str = None,
                 business_unit: str = None, dns_status: str = None,
                 dns_response_time: int = None, domain_reachable: bool = None,
                 http_status_code: int = None, last_dns_check: str = None,
                 last_reachability_check: str = None, monitored_ports: str = None,
                 ssl_handshake_time: int = None, tls_version: str = None,
                 cipher_suite: str = None, certificate_chain_valid: bool = None,
                 http_redirect_status: str = None, last_port_check: str = None,
                 last_manual_check: str = None, check_in_progress: bool = None,
                 renewal_status: str = None, auto_renewal_enabled: bool = None,
                 renewal_days_before: int = None, import_source: str = None,
                 last_renewal_attempt: str = None):
        """初始化证书对象"""
        self.id = id
        self.domain = domain
        self.type = type  # single/wildcard/multi
        self.status = status  # valid/expired/revoked/pending
        self.created_at = created_at
        self.expires_at = expires_at
        self.server_id = server_id
        self.ca_type = ca_type
        self.private_key = private_key
        self.certificate = certificate
        self.updated_at = updated_at
        # 监控控制字段
        self.monitoring_enabled = monitoring_enabled
        self.monitoring_frequency = monitoring_frequency  # 监控频率(秒)
        self.alert_enabled = alert_enabled
        # 备注信息字段
        self.notes = notes
        self.tags = tags  # JSON格式存储标签
        self.owner = owner
        self.business_unit = business_unit
        # 域名监控字段
        self.dns_status = dns_status
        self.dns_response_time = dns_response_time
        self.domain_reachable = domain_reachable
        self.http_status_code = http_status_code
        self.last_dns_check = last_dns_check
        self.last_reachability_check = last_reachability_check
        # 端口监控字段
        self.monitored_ports = monitored_ports
        self.ssl_handshake_time = ssl_handshake_time
        self.tls_version = tls_version
        self.cipher_suite = cipher_suite
        self.certificate_chain_valid = certificate_chain_valid
        self.http_redirect_status = http_redirect_status
        self.last_port_check = last_port_check
        # 证书操作字段
        self.last_manual_check = last_manual_check
        self.check_in_progress = check_in_progress
        self.renewal_status = renewal_status
        self.auto_renewal_enabled = auto_renewal_enabled
        self.renewal_days_before = renewal_days_before
        self.import_source = import_source
        self.last_renewal_attempt = last_renewal_attempt
    
    @classmethod
    def get_by_id(cls, cert_id: int) -> Optional['Certificate']:
        """根据ID获取证书"""
        db.connect()
        cert_data = db.fetchone("SELECT * FROM certificates WHERE id = ?", (cert_id,))
        db.close()
        
        if not cert_data:
            return None
        
        return cls(**cert_data)
    
    @classmethod
    def get_by_domain(cls, domain: str, server_id: int = None) -> Optional['Certificate']:
        """根据域名获取证书"""
        db.connect()
        
        if server_id:
            cert_data = db.fetchone(
                "SELECT * FROM certificates WHERE domain = ? AND server_id = ?", 
                (domain, server_id)
            )
        else:
            cert_data = db.fetchone(
                "SELECT * FROM certificates WHERE domain = ? ORDER BY expires_at DESC LIMIT 1", 
                (domain,)
            )
        
        db.close()
        
        if not cert_data:
            return None
        
        return cls(**cert_data)
    
    @classmethod
    def get_all(cls, page: int = 1, limit: int = 20, keyword: str = None, 
                status: str = None, server_id: int = None) -> Tuple[List['Certificate'], int]:
        """获取所有证书"""
        db.connect()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if keyword:
            conditions.append("domain LIKE ?")
            params.append(f"%{keyword}%")
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        if server_id:
            conditions.append("server_id = ?")
            params.append(server_id)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 计算总数
        count_sql = f"SELECT COUNT(*) as total FROM certificates{where_clause}"
        count_result = db.fetchone(count_sql, tuple(params))
        total = count_result['total'] if count_result else 0
        
        # 分页查询
        offset = (page - 1) * limit
        sql = f"""
            SELECT c.*, s.name as server_name 
            FROM certificates c
            LEFT JOIN servers s ON c.server_id = s.id
            {where_clause} 
            ORDER BY c.expires_at ASC 
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        certs_data = db.fetchall(sql, tuple(params))
        db.close()
        
        certificates = []
        for cert_data in certs_data:
            # 提取服务器名称
            server_name = cert_data.pop('server_name', None)
            cert = cls(**cert_data)
            cert.server_name = server_name
            certificates.append(cert)
        
        return certificates, total
    
    @classmethod
    def get_expiring(cls, days: int = 15, limit: int = 10) -> List['Certificate']:
        """获取即将过期的证书"""
        db.connect()
        
        # 计算截止日期
        now = datetime.datetime.now()
        expiry_date = (now + datetime.timedelta(days=days)).isoformat()
        
        sql = """
            SELECT c.*, s.name as server_name 
            FROM certificates c
            LEFT JOIN servers s ON c.server_id = s.id
            WHERE c.status = 'valid' AND c.expires_at <= ? 
            ORDER BY c.expires_at ASC 
            LIMIT ?
        """
        
        certs_data = db.fetchall(sql, (expiry_date, limit))
        db.close()
        
        certificates = []
        for cert_data in certs_data:
            # 提取服务器名称
            server_name = cert_data.pop('server_name', None)
            cert = cls(**cert_data)
            cert.server_name = server_name
            certificates.append(cert)
        
        return certificates
    
    def save(self) -> int:
        """保存证书信息"""
        db.connect()
        now = datetime.datetime.now().isoformat()
        
        if self.id:
            # 更新现有证书
            data = {
                'domain': self.domain,
                'type': self.type,
                'status': self.status,
                'expires_at': self.expires_at,
                'server_id': self.server_id,
                'ca_type': self.ca_type,
                'updated_at': now,
                # 监控控制字段
                'monitoring_enabled': getattr(self, 'monitoring_enabled', True),
                'monitoring_frequency': getattr(self, 'monitoring_frequency', 3600),
                'alert_enabled': getattr(self, 'alert_enabled', True),
                # 备注信息字段
                'notes': getattr(self, 'notes', None),
                'tags': getattr(self, 'tags', None),
                'owner': getattr(self, 'owner', None),
                'business_unit': getattr(self, 'business_unit', None),
                # 域名监控字段
                'dns_status': getattr(self, 'dns_status', None),
                'dns_response_time': getattr(self, 'dns_response_time', None),
                'domain_reachable': getattr(self, 'domain_reachable', None),
                'http_status_code': getattr(self, 'http_status_code', None),
                'last_dns_check': getattr(self, 'last_dns_check', None),
                'last_reachability_check': getattr(self, 'last_reachability_check', None),
                # 端口监控字段
                'monitored_ports': getattr(self, 'monitored_ports', None),
                'ssl_handshake_time': getattr(self, 'ssl_handshake_time', None),
                'tls_version': getattr(self, 'tls_version', None),
                'cipher_suite': getattr(self, 'cipher_suite', None),
                'certificate_chain_valid': getattr(self, 'certificate_chain_valid', None),
                'http_redirect_status': getattr(self, 'http_redirect_status', None),
                'last_port_check': getattr(self, 'last_port_check', None),
                # 证书操作字段
                'last_manual_check': getattr(self, 'last_manual_check', None),
                'check_in_progress': getattr(self, 'check_in_progress', None),
                'renewal_status': getattr(self, 'renewal_status', None),
                'auto_renewal_enabled': getattr(self, 'auto_renewal_enabled', None),
                'renewal_days_before': getattr(self, 'renewal_days_before', None),
                'import_source': getattr(self, 'import_source', None),
                'last_renewal_attempt': getattr(self, 'last_renewal_attempt', None)
            }

            # 如果有私钥和证书内容，也更新
            if self.private_key:
                data['private_key'] = self.private_key
            if self.certificate:
                data['certificate'] = self.certificate
            
            db.update('certificates', data, 'id = ?', (self.id,))
            cert_id = self.id
        else:
            # 创建新证书
            data = {
                'domain': self.domain,
                'type': self.type,
                'status': self.status,
                'created_at': now,
                'expires_at': self.expires_at,
                'server_id': self.server_id,
                'ca_type': self.ca_type,
                'private_key': self.private_key,
                'certificate': self.certificate,
                'updated_at': now,
                # 监控控制字段
                'monitoring_enabled': getattr(self, 'monitoring_enabled', True),
                'monitoring_frequency': getattr(self, 'monitoring_frequency', 3600),
                'alert_enabled': getattr(self, 'alert_enabled', True),
                # 备注信息字段
                'notes': getattr(self, 'notes', None),
                'tags': getattr(self, 'tags', None),
                'owner': getattr(self, 'owner', None),
                'business_unit': getattr(self, 'business_unit', None),
                # 域名监控字段
                'dns_status': getattr(self, 'dns_status', None),
                'dns_response_time': getattr(self, 'dns_response_time', None),
                'domain_reachable': getattr(self, 'domain_reachable', None),
                'http_status_code': getattr(self, 'http_status_code', None),
                'last_dns_check': getattr(self, 'last_dns_check', None),
                'last_reachability_check': getattr(self, 'last_reachability_check', None),
                # 端口监控字段
                'monitored_ports': getattr(self, 'monitored_ports', '["80", "443"]'),
                'ssl_handshake_time': getattr(self, 'ssl_handshake_time', None),
                'tls_version': getattr(self, 'tls_version', None),
                'cipher_suite': getattr(self, 'cipher_suite', None),
                'certificate_chain_valid': getattr(self, 'certificate_chain_valid', None),
                'http_redirect_status': getattr(self, 'http_redirect_status', None),
                'last_port_check': getattr(self, 'last_port_check', None),
                # 证书操作字段
                'last_manual_check': getattr(self, 'last_manual_check', None),
                'check_in_progress': getattr(self, 'check_in_progress', 0),
                'renewal_status': getattr(self, 'renewal_status', 'pending'),
                'auto_renewal_enabled': getattr(self, 'auto_renewal_enabled', 0),
                'renewal_days_before': getattr(self, 'renewal_days_before', 30),
                'import_source': getattr(self, 'import_source', 'manual'),
                'last_renewal_attempt': getattr(self, 'last_renewal_attempt', None)
            }
            cert_id = db.insert('certificates', data)
            self.id = cert_id
        
        db.commit()
        db.close()
        return cert_id
    
    def delete(self) -> bool:
        """删除证书"""
        if not self.id:
            return False
        
        db.connect()
        result = db.delete('certificates', 'id = ?', (self.id,))
        db.commit()
        db.close()
        
        return result > 0
    
    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        """将证书对象转换为字典"""
        cert_dict = {
            'id': self.id,
            'domain': self.domain,
            'type': self.type,
            'status': self.status,
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'server_id': self.server_id,
            'ca_type': self.ca_type,
            'updated_at': self.updated_at,
            # 监控控制字段
            'monitoring_enabled': getattr(self, 'monitoring_enabled', True),
            'monitoring_frequency': getattr(self, 'monitoring_frequency', 3600),
            'alert_enabled': getattr(self, 'alert_enabled', True),
            # 备注信息字段
            'notes': getattr(self, 'notes', None),
            'tags': getattr(self, 'tags', None),
            'owner': getattr(self, 'owner', None),
            'business_unit': getattr(self, 'business_unit', None),
            # 域名监控字段
            'dns_status': getattr(self, 'dns_status', None),
            'dns_response_time': getattr(self, 'dns_response_time', None),
            'domain_reachable': getattr(self, 'domain_reachable', None),
            'http_status_code': getattr(self, 'http_status_code', None),
            'last_dns_check': getattr(self, 'last_dns_check', None),
            'last_reachability_check': getattr(self, 'last_reachability_check', None),
            # 端口监控字段
            'monitored_ports': getattr(self, 'monitored_ports', None),
            'ssl_handshake_time': getattr(self, 'ssl_handshake_time', None),
            'tls_version': getattr(self, 'tls_version', None),
            'cipher_suite': getattr(self, 'cipher_suite', None),
            'certificate_chain_valid': getattr(self, 'certificate_chain_valid', None),
            'http_redirect_status': getattr(self, 'http_redirect_status', None),
            'last_port_check': getattr(self, 'last_port_check', None),
            # 证书操作字段
            'last_manual_check': getattr(self, 'last_manual_check', None),
            'check_in_progress': getattr(self, 'check_in_progress', None),
            'renewal_status': getattr(self, 'renewal_status', None),
            'auto_renewal_enabled': getattr(self, 'auto_renewal_enabled', None),
            'renewal_days_before': getattr(self, 'renewal_days_before', None),
            'import_source': getattr(self, 'import_source', None),
            'last_renewal_attempt': getattr(self, 'last_renewal_attempt', None)
        }
        
        # 添加服务器名称（如果有）
        if hasattr(self, 'server_name'):
            cert_dict['server_name'] = self.server_name
        
        # 计算剩余天数
        if self.expires_at:
            try:
                expires_at = datetime.datetime.fromisoformat(self.expires_at)
                now = datetime.datetime.now()
                days_left = (expires_at - now).days
                cert_dict['days_left'] = max(0, days_left)
            except (ValueError, TypeError):
                cert_dict['days_left'] = None
        
        # 如果需要包含证书内容
        if include_content:
            cert_dict['private_key'] = self.private_key
            cert_dict['certificate'] = self.certificate
        
        return cert_dict
    
    def get_deployments(self) -> List[Dict[str, Any]]:
        """获取证书部署记录"""
        if not self.id:
            return []
        
        db.connect()
        deployments = db.fetchall(
            "SELECT * FROM certificate_deployments WHERE certificate_id = ? ORDER BY created_at DESC",
            (self.id,)
        )
        db.close()
        
        return deployments
    
    def add_deployment(self, deploy_type: str, deploy_target: str, status: str = 'success') -> int:
        """添加证书部署记录"""
        if not self.id:
            return 0
        
        db.connect()
        now = datetime.datetime.now().isoformat()
        
        data = {
            'certificate_id': self.id,
            'deploy_type': deploy_type,
            'deploy_target': deploy_target,
            'status': status,
            'created_at': now,
            'updated_at': now
        }
        
        deployment_id = db.insert('certificate_deployments', data)
        db.commit()
        db.close()
        
        return deployment_id
    
    def is_expired(self) -> bool:
        """检查证书是否已过期"""
        if not self.expires_at:
            return True
        
        try:
            expires_at = datetime.datetime.fromisoformat(self.expires_at)
            now = datetime.datetime.now()
            return now >= expires_at
        except (ValueError, TypeError):
            return True
    
    def is_expiring(self, days: int = 15) -> bool:
        """检查证书是否即将过期"""
        if not self.expires_at:
            return False
        
        try:
            expires_at = datetime.datetime.fromisoformat(self.expires_at)
            now = datetime.datetime.now()
            threshold = now + datetime.timedelta(days=days)
            return now < expires_at <= threshold
        except (ValueError, TypeError):
            return False
    
    def update_status(self) -> None:
        """更新证书状态"""
        if self.is_expired() and self.status == 'valid':
            self.status = 'expired'
            self.save()
    
    def renew(self) -> None:
        """将证书状态设置为续期中"""
        self.status = 'renewing'
        self.save()
    
    @classmethod
    def create(cls, domain: str, type: str, server_id: int, ca_type: str, 
               status: str = 'pending', expires_at: str = None) -> 'Certificate':
        """创建新证书"""
        cert = cls(
            domain=domain,
            type=type,
            status=status,
            server_id=server_id,
            ca_type=ca_type,
            expires_at=expires_at or (datetime.datetime.now() + datetime.timedelta(days=90)).isoformat(),
            private_key='',
            certificate=''
        )
        cert.save()
        
        return cert
    
    @classmethod
    def get_statistics(cls) -> Dict[str, int]:
        """获取证书统计信息"""
        db.connect()
        
        # 总数
        total_result = db.fetchone("SELECT COUNT(*) as count FROM certificates")
        total = total_result['count'] if total_result else 0
        
        # 有效证书
        valid_result = db.fetchone("SELECT COUNT(*) as count FROM certificates WHERE status = 'valid'")
        valid = valid_result['count'] if valid_result else 0
        
        # 即将过期证书
        now = datetime.datetime.now()
        expiry_date = (now + datetime.timedelta(days=15)).isoformat()
        expiring_result = db.fetchone(
            "SELECT COUNT(*) as count FROM certificates WHERE status = 'valid' AND expires_at <= ?",
            (expiry_date,)
        )
        expiring = expiring_result['count'] if expiring_result else 0
        
        # 已过期证书
        expired_result = db.fetchone("SELECT COUNT(*) as count FROM certificates WHERE status = 'expired'")
        expired = expired_result['count'] if expired_result else 0
        
        # 证书类型分布
        type_distribution = db.fetchall("SELECT type, COUNT(*) as count FROM certificates GROUP BY type")
        
        db.close()
        
        return {
            'total': total,
            'valid': valid,
            'expiring': expiring,
            'expired': expired,
            'type_distribution': type_distribution
        }
