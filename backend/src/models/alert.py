"""
告警模型模块，处理告警相关的数据操作
"""
import datetime
from typing import Dict, List, Any, Optional, Tuple
from .database import db

class Alert:
    """告警模型类"""
    
    def __init__(self, id: int = None, type: str = None, message: str = None, 
                 status: str = None, certificate_id: int = None,
                 created_at: str = None, updated_at: str = None):
        """初始化告警对象"""
        self.id = id
        self.type = type  # expiry/error/revoke
        self.message = message
        self.status = status  # pending/sent/resolved
        self.certificate_id = certificate_id
        self.created_at = created_at
        self.updated_at = updated_at
    
    @classmethod
    def get_by_id(cls, alert_id: int) -> Optional['Alert']:
        """根据ID获取告警"""
        db.connect()
        alert_data = db.fetchone("SELECT * FROM alerts WHERE id = ?", (alert_id,))
        db.close()
        
        if not alert_data:
            return None
        
        return cls(**alert_data)
    
    @classmethod
    def get_all(cls, page: int = 1, limit: int = 20, status: str = None, 
                type: str = None) -> Tuple[List['Alert'], int]:
        """获取所有告警"""
        db.connect()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if status:
            conditions.append("a.status = ?")
            params.append(status)
        
        if type:
            conditions.append("a.type = ?")
            params.append(type)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 计算总数
        count_sql = f"SELECT COUNT(*) as total FROM alerts a{where_clause}"
        count_result = db.fetchone(count_sql, tuple(params))
        total = count_result['total'] if count_result else 0
        
        # 分页查询
        offset = (page - 1) * limit
        sql = f"""
            SELECT a.*, c.domain as certificate_domain, c.expires_at as certificate_expires_at 
            FROM alerts a
            LEFT JOIN certificates c ON a.certificate_id = c.id
            {where_clause} 
            ORDER BY a.created_at DESC 
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        alerts_data = db.fetchall(sql, tuple(params))
        db.close()
        
        alerts = []
        for alert_data in alerts_data:
            # 提取证书信息
            certificate_domain = alert_data.pop('certificate_domain', None)
            certificate_expires_at = alert_data.pop('certificate_expires_at', None)
            
            alert = cls(**alert_data)
            alert.certificate_domain = certificate_domain
            alert.certificate_expires_at = certificate_expires_at
            alerts.append(alert)
        
        return alerts, total
    
    @classmethod
    def get_recent(cls, limit: int = 10) -> List['Alert']:
        """获取最近的告警"""
        db.connect()
        
        sql = """
            SELECT a.*, c.domain as certificate_domain, c.expires_at as certificate_expires_at 
            FROM alerts a
            LEFT JOIN certificates c ON a.certificate_id = c.id
            WHERE a.status != 'resolved'
            ORDER BY a.created_at DESC 
            LIMIT ?
        """
        
        alerts_data = db.fetchall(sql, (limit,))
        db.close()
        
        alerts = []
        for alert_data in alerts_data:
            # 提取证书信息
            certificate_domain = alert_data.pop('certificate_domain', None)
            certificate_expires_at = alert_data.pop('certificate_expires_at', None)
            
            alert = cls(**alert_data)
            alert.certificate_domain = certificate_domain
            alert.certificate_expires_at = certificate_expires_at
            alerts.append(alert)
        
        return alerts
    
    def save(self) -> int:
        """保存告警信息"""
        db.connect()
        now = datetime.datetime.now().isoformat()
        
        if self.id:
            # 更新现有告警
            data = {
                'type': self.type,
                'message': self.message,
                'status': self.status,
                'updated_at': now
            }
            
            db.update('alerts', data, 'id = ?', (self.id,))
            alert_id = self.id
        else:
            # 创建新告警
            data = {
                'type': self.type,
                'message': self.message,
                'status': self.status,
                'certificate_id': self.certificate_id,
                'created_at': now,
                'updated_at': now
            }
            alert_id = db.insert('alerts', data)
            self.id = alert_id
        
        db.commit()
        db.close()
        return alert_id
    
    def delete(self) -> bool:
        """删除告警"""
        if not self.id:
            return False
        
        db.connect()
        result = db.delete('alerts', 'id = ?', (self.id,))
        db.commit()
        db.close()
        
        return result > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """将告警对象转换为字典"""
        alert_dict = {
            'id': self.id,
            'type': self.type,
            'message': self.message,
            'status': self.status,
            'certificate_id': self.certificate_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        
        # 添加证书信息（如果有）
        if hasattr(self, 'certificate_domain'):
            alert_dict['certificate'] = {
                'domain': self.certificate_domain,
                'expires_at': self.certificate_expires_at
            }
        
        return alert_dict
    
    def resolve(self) -> None:
        """解决告警"""
        self.status = 'resolved'
        self.save()
    
    @classmethod
    def create_expiry_alert(cls, certificate_id: int, domain: str, days_left: int) -> 'Alert':
        """创建证书过期告警"""
        message = f"证书 {domain} 将在 {days_left} 天后过期"
        alert = cls(
            type='expiry',
            message=message,
            status='pending',
            certificate_id=certificate_id
        )
        alert.save()
        
        return alert
    
    @classmethod
    def create_error_alert(cls, certificate_id: int, domain: str, error_message: str) -> 'Alert':
        """创建证书错误告警"""
        message = f"证书 {domain} 出现错误: {error_message}"
        alert = cls(
            type='error',
            message=message,
            status='pending',
            certificate_id=certificate_id
        )
        alert.save()
        
        return alert
    
    @classmethod
    def create_revoke_alert(cls, certificate_id: int, domain: str) -> 'Alert':
        """创建证书吊销告警"""
        message = f"证书 {domain} 已被吊销"
        alert = cls(
            type='revoke',
            message=message,
            status='pending',
            certificate_id=certificate_id
        )
        alert.save()
        
        return alert
    
    @classmethod
    def get_pending_count(cls) -> int:
        """获取未处理告警数量"""
        db.connect()
        result = db.fetchone("SELECT COUNT(*) as count FROM alerts WHERE status = 'pending'")
        db.close()
        
        return result['count'] if result else 0
    
    @classmethod
    def check_certificate_expiry(cls) -> int:
        """检查证书过期情况并创建告警"""
        db.connect()
        
        # 获取告警天数设置
        setting = db.fetchone("SELECT value FROM settings WHERE key = 'alert_before_days'")
        alert_days = int(setting['value']) if setting else 30
        
        # 计算告警日期
        now = datetime.datetime.now()
        alert_date = (now + datetime.timedelta(days=alert_days)).isoformat()
        
        # 查找即将过期但尚未创建告警的证书
        sql = """
            SELECT c.id, c.domain, c.expires_at
            FROM certificates c
            LEFT JOIN alerts a ON c.id = a.certificate_id AND a.type = 'expiry' AND a.status != 'resolved'
            WHERE c.status = 'valid' AND c.expires_at <= ? AND a.id IS NULL
        """
        
        certificates = db.fetchall(sql, (alert_date,))
        db.close()
        
        # 创建告警
        count = 0
        for cert in certificates:
            try:
                expires_at = datetime.datetime.fromisoformat(cert['expires_at'])
                days_left = (expires_at - now).days
                if days_left >= 0:
                    cls.create_expiry_alert(cert['id'], cert['domain'], days_left)
                    count += 1
            except (ValueError, TypeError):
                continue
        
        return count
