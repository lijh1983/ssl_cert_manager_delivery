"""
服务器服务模块
提供服务器管理功能
"""
import subprocess
import socket
import time
import secrets
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from utils.logging_config import get_logger
from utils.exceptions import (
    ValidationError, ResourceNotFoundError, ResourceConflictError,
    AuthorizationError, ErrorCode
)
from utils.validators import InputValidator

logger = get_logger(__name__)


class ServerService:
    """服务器服务"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def create_server(self, user_id: int, server_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建服务器"""
        # 验证输入数据
        self._validate_server_data(server_data)
        
        # 检查服务器名称是否已存在
        from models import Server
        existing_server = Server.get_by_name(server_data['name'])
        if existing_server:
            raise ResourceConflictError("服务器", "name")
        
        # 生成服务器令牌
        token = self._generate_server_token()
        
        # 创建服务器记录
        server = Server.create(
            name=server_data['name'],
            ip=server_data['ip'],
            description=server_data.get('description', ''),
            user_id=user_id,
            token=token,
            auto_renew=server_data.get('auto_renew', True),
            status='offline'  # 初始状态为离线
        )
        
        self.logger.audit(
            action="create",
            resource_type="server",
            resource_id=server.id,
            result="success",
            user_id=user_id
        )
        
        return {
            'success': True,
            'server': server.to_dict(),
            'message': '服务器创建成功'
        }
    
    def update_server(self, server_id: int, user_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新服务器"""
        # 获取服务器
        from models import Server
        server = Server.get_by_id(server_id)
        if not server:
            raise ResourceNotFoundError("服务器", server_id)
        
        # 检查权限
        if server.user_id != user_id:
            raise AuthorizationError("无权限修改此服务器")
        
        # 验证更新数据
        if 'name' in update_data or 'ip' in update_data:
            self._validate_server_data(update_data, partial=True)
        
        # 更新服务器属性
        for key, value in update_data.items():
            if hasattr(server, key) and key not in ['id', 'user_id', 'token', 'created_at']:
                setattr(server, key, value)
        
        server.updated_at = datetime.now()
        server.save()
        
        self.logger.audit(
            action="update",
            resource_type="server",
            resource_id=server_id,
            result="success",
            user_id=user_id
        )
        
        return {
            'success': True,
            'server': server.to_dict(),
            'message': '服务器更新成功'
        }
    
    def delete_server(self, server_id: int, user_id: int) -> Dict[str, Any]:
        """删除服务器"""
        # 获取服务器
        from models import Server, Certificate
        server = Server.get_by_id(server_id)
        if not server:
            raise ResourceNotFoundError("服务器", server_id)
        
        # 检查权限
        if server.user_id != user_id:
            raise AuthorizationError("无权限删除此服务器")
        
        # 检查是否有关联的证书
        certificates = Certificate.get_by_server(server_id)
        if certificates:
            raise ValidationError(f"无法删除服务器，存在{len(certificates)}个关联证书")
        
        # 删除服务器
        server.delete()
        
        self.logger.audit(
            action="delete",
            resource_type="server",
            resource_id=server_id,
            result="success",
            user_id=user_id
        )
        
        return {
            'success': True,
            'server_id': server_id,
            'message': '服务器删除成功'
        }
    
    def get_server(self, server_id: int, user_id: int) -> Dict[str, Any]:
        """获取服务器详情"""
        from models import Server
        server = Server.get_by_id(server_id)
        if not server:
            raise ResourceNotFoundError("服务器", server_id)
        
        # 检查权限
        if server.user_id != user_id:
            raise AuthorizationError("无权限查看此服务器")
        
        return server.to_dict()
    
    def list_servers(self, user_id: int, page: int = 1, limit: int = 10, 
                    filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """获取服务器列表"""
        from models import Server
        
        servers, total = Server.get_by_user(user_id, page, limit, filters)
        
        return {
            'items': [server.to_dict() for server in servers],
            'total': total,
            'page': page,
            'limit': limit,
            'pages': (total + limit - 1) // limit
        }
    
    def check_server_status(self, server_id: int) -> Dict[str, Any]:
        """检查服务器状态"""
        from models import Server
        server = Server.get_by_id(server_id)
        if not server:
            raise ResourceNotFoundError("服务器", server_id)
        
        # 检查服务器连通性
        reachable = ping_server(server.ip)
        status = 'online' if reachable else 'offline'
        
        # 更新服务器状态
        server.update_status(status)
        
        return {
            'server_id': server_id,
            'ip': server.ip,
            'status': status,
            'reachable': reachable,
            'checked_at': datetime.now().isoformat()
        }
    
    def batch_check_server_status(self, server_ids: List[int]) -> Dict[str, Any]:
        """批量检查服务器状态"""
        results = []
        online_count = 0
        offline_count = 0
        
        for server_id in server_ids:
            try:
                result = self.check_server_status(server_id)
                results.append(result)
                
                if result['status'] == 'online':
                    online_count += 1
                else:
                    offline_count += 1
                    
            except Exception as e:
                self.logger.error(f"检查服务器{server_id}状态失败: {e}")
                results.append({
                    'server_id': server_id,
                    'status': 'error',
                    'error': str(e)
                })
                offline_count += 1
        
        return {
            'total': len(server_ids),
            'online': online_count,
            'offline': offline_count,
            'results': results
        }
    
    def regenerate_server_token(self, server_id: int, user_id: int) -> Dict[str, Any]:
        """重新生成服务器令牌"""
        from models import Server
        server = Server.get_by_id(server_id)
        if not server:
            raise ResourceNotFoundError("服务器", server_id)
        
        # 检查权限
        if server.user_id != user_id:
            raise AuthorizationError("无权限操作此服务器")
        
        # 生成新令牌
        new_token = server.regenerate_token()
        
        self.logger.audit(
            action="regenerate_token",
            resource_type="server",
            resource_id=server_id,
            result="success",
            user_id=user_id
        )
        
        return {
            'success': True,
            'server_id': server_id,
            'new_token': new_token,
            'message': '服务器令牌重新生成成功'
        }
    
    def get_server_statistics(self, server_id: int) -> Dict[str, Any]:
        """获取服务器统计信息"""
        from models import Server, Certificate
        
        server = Server.get_by_id(server_id)
        if not server:
            raise ResourceNotFoundError("服务器", server_id)
        
        # 获取证书统计
        certificates = Certificate.get_by_server(server_id)
        expiring_certificates = Certificate.get_expiring_by_server(server_id, days=30)
        
        # 计算健康分数
        total_certs = len(certificates)
        expiring_certs = len(expiring_certificates)
        
        if total_certs == 0:
            health_score = 100
        else:
            health_score = max(0, 100 - (expiring_certs * 100 // total_certs))
        
        return {
            'server_id': server_id,
            'server_name': server.name,
            'total_certificates': total_certs,
            'expiring_certificates': expiring_certs,
            'certificate_health_score': health_score,
            'last_check': server.last_check_at.isoformat() if server.last_check_at else None,
            'status': server.status
        }
    
    def server_health_check(self, server_id: int) -> Dict[str, Any]:
        """服务器健康检查"""
        from models import Server
        
        server = Server.get_by_id(server_id)
        if not server:
            raise ResourceNotFoundError("服务器", server_id)
        
        # 执行健康检查
        health_status = check_server_health(server.ip)
        
        # 计算总体健康状态
        if health_status['reachable']:
            if health_status.get('response_time', 0) < 100:
                overall_health = 'healthy'
            elif health_status.get('response_time', 0) < 500:
                overall_health = 'warning'
            else:
                overall_health = 'critical'
        else:
            overall_health = 'critical'
        
        return {
            'server_id': server_id,
            'server_name': server.name,
            'health_status': health_status,
            'overall_health': overall_health,
            'checked_at': datetime.now().isoformat()
        }
    
    def _validate_server_data(self, data: Dict[str, Any], partial: bool = False):
        """验证服务器数据"""
        if not partial:
            # 完整验证
            if not data.get('name'):
                raise ValidationError("服务器名称不能为空")
            
            if not data.get('ip'):
                raise ValidationError("服务器IP地址不能为空")
        
        # 验证名称
        if 'name' in data:
            name = data['name']
            if not isinstance(name, str) or len(name.strip()) == 0:
                raise ValidationError("服务器名称不能为空")
            
            if len(name) > 100:
                raise ValidationError("服务器名称长度不能超过100个字符")
        
        # 验证IP地址
        if 'ip' in data:
            ip = data['ip']
            if not InputValidator.validate_ip_address(ip):
                raise ValidationError("IP地址格式不正确")
        
        # 验证描述
        if 'description' in data:
            description = data['description']
            if description and len(description) > 500:
                raise ValidationError("描述长度不能超过500个字符")
    
    def _generate_server_token(self) -> str:
        """生成服务器令牌"""
        return secrets.token_urlsafe(32)


def ping_server(ip: str, timeout: int = 5) -> bool:
    """检查服务器连通性"""
    try:
        # 使用socket检查连通性
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, 22))  # 尝试连接SSH端口
        sock.close()
        return result == 0
    except Exception:
        return False


def check_server_health(ip: str) -> Dict[str, Any]:
    """检查服务器健康状态"""
    health_status = {
        'reachable': False,
        'response_time': None,
        'ssl_enabled': False,
        'certificate_valid': False,
        'disk_usage': None,
        'memory_usage': None,
        'cpu_usage': None
    }
    
    try:
        # 检查连通性和响应时间
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, 22))
        end_time = time.time()
        sock.close()
        
        if result == 0:
            health_status['reachable'] = True
            health_status['response_time'] = int((end_time - start_time) * 1000)  # 毫秒
        
        # 检查HTTPS端口
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((ip, 443))
            sock.close()
            health_status['ssl_enabled'] = (result == 0)
        except:
            pass
        
        # 模拟系统资源使用情况（实际实现需要通过agent获取）
        if health_status['reachable']:
            import random
            health_status['disk_usage'] = random.randint(20, 90)
            health_status['memory_usage'] = random.randint(30, 80)
            health_status['cpu_usage'] = random.randint(10, 70)
    
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
    
    return health_status
