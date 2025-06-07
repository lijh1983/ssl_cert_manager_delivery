"""
服务器模型模块，处理服务器相关的数据操作
"""
import datetime
import secrets
import string
from typing import Dict, List, Any, Optional, Tuple
from .database import db

class Server:
    """服务器模型类"""
    
    def __init__(self, id: int = None, name: str = None, ip: str = None, 
                 os_type: str = None, version: str = None, token: str = None,
                 auto_renew: bool = True, user_id: int = None,
                 created_at: str = None, updated_at: str = None):
        """初始化服务器对象"""
        self.id = id
        self.name = name
        self.ip = ip
        self.os_type = os_type
        self.version = version
        self.token = token
        self.auto_renew = auto_renew
        self.user_id = user_id
        self.created_at = created_at
        self.updated_at = updated_at
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """生成随机令牌"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @classmethod
    def get_by_id(cls, server_id: int) -> Optional['Server']:
        """根据ID获取服务器"""
        db.connect()
        server_data = db.fetchone("SELECT * FROM servers WHERE id = ?", (server_id,))
        db.close()
        
        if not server_data:
            return None
        
        return cls(**server_data)
    
    @classmethod
    def get_by_token(cls, token: str) -> Optional['Server']:
        """根据令牌获取服务器"""
        db.connect()
        server_data = db.fetchone("SELECT * FROM servers WHERE token = ?", (token,))
        db.close()
        
        if not server_data:
            return None
        
        return cls(**server_data)
    
    @classmethod
    def get_all(cls, page: int = 1, limit: int = 20, keyword: str = None, 
                user_id: int = None) -> Tuple[List['Server'], int]:
        """获取所有服务器"""
        db.connect()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if keyword:
            conditions.append("(name LIKE ? OR ip LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 计算总数
        count_sql = f"SELECT COUNT(*) as total FROM servers{where_clause}"
        count_result = db.fetchone(count_sql, tuple(params))
        total = count_result['total'] if count_result else 0
        
        # 分页查询
        offset = (page - 1) * limit
        sql = f"SELECT * FROM servers{where_clause} ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        servers_data = db.fetchall(sql, tuple(params))
        db.close()
        
        servers = [cls(**server_data) for server_data in servers_data]
        return servers, total
    
    def save(self) -> int:
        """保存服务器信息"""
        db.connect()
        now = datetime.datetime.now().isoformat()
        
        if self.id:
            # 更新现有服务器
            data = {
                'name': self.name,
                'ip': self.ip if self.ip else '',
                'os_type': self.os_type if self.os_type else '',
                'version': self.version if self.version else '',
                'auto_renew': self.auto_renew,
                'updated_at': now
            }
            
            db.update('servers', data, 'id = ?', (self.id,))
            server_id = self.id
        else:
            # 创建新服务器
            if not self.token:
                self.token = self.generate_token()
                
            data = {
                'name': self.name,
                'ip': self.ip if self.ip else '',
                'os_type': self.os_type if self.os_type else '',
                'version': self.version if self.version else '',
                'token': self.token,
                'auto_renew': self.auto_renew,
                'user_id': self.user_id,
                'created_at': now,
                'updated_at': now
            }
            server_id = db.insert('servers', data)
            self.id = server_id
        
        db.commit()
        db.close()
        return server_id
    
    def delete(self) -> bool:
        """删除服务器"""
        if not self.id:
            return False
        
        db.connect()
        result = db.delete('servers', 'id = ?', (self.id,))
        db.commit()
        db.close()
        
        return result > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """将服务器对象转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'ip': self.ip,
            'os_type': self.os_type,
            'version': self.version,
            'token': self.token,
            'auto_renew': self.auto_renew,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def get_certificates(self) -> List[Dict[str, Any]]:
        """获取服务器上的证书"""
        if not self.id:
            return []
        
        db.connect()
        certificates = db.fetchall(
            "SELECT * FROM certificates WHERE server_id = ? ORDER BY expires_at ASC",
            (self.id,)
        )
        db.close()
        
        return certificates
    
    def get_certificates_count(self) -> int:
        """获取服务器上的证书数量"""
        if not self.id:
            return 0
        
        db.connect()
        result = db.fetchone(
            "SELECT COUNT(*) as count FROM certificates WHERE server_id = ?",
            (self.id,)
        )
        db.close()
        
        return result['count'] if result else 0
    
    def update_heartbeat(self) -> None:
        """更新服务器心跳时间"""
        if not self.id:
            return
        
        db.connect()
        now = datetime.datetime.now().isoformat()
        db.update('servers', {'updated_at': now}, 'id = ?', (self.id,))
        db.commit()
        db.close()
        
        self.updated_at = now
    
    def is_online(self) -> bool:
        """检查服务器是否在线"""
        if not self.updated_at:
            return False
        
        last_update = datetime.datetime.fromisoformat(self.updated_at)
        now = datetime.datetime.now()
        
        # 如果5分钟内有心跳，认为在线
        return (now - last_update).total_seconds() < 300
    
    @classmethod
    def create(cls, name: str, user_id: int, auto_renew: bool = True) -> 'Server':
        """创建新服务器"""
        token = cls.generate_token()
        server = cls(
            name=name,
            token=token,
            auto_renew=auto_renew,
            user_id=user_id
        )
        server.save()
        
        return server
    
    def register(self, ip: str, os_type: str, version: str, hostname: str = None) -> None:
        """注册服务器信息"""
        self.ip = ip
        self.os_type = os_type
        self.version = version
        
        # 如果没有名称或提供了主机名，使用主机名作为名称
        if not self.name and hostname:
            self.name = hostname
        
        self.save()
    
    def get_install_command(self) -> str:
        """获取安装命令"""
        return f"curl -s https://example.com/install.sh | bash -s {self.token}"
