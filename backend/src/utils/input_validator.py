"""
输入验证工具类
"""

import re
import ipaddress
from typing import Any, Dict, List, Optional, Union


class InputValidator:
    """输入验证器"""
    
    @staticmethod
    def validate_domain(domain: str, allow_wildcard: bool = False) -> bool:
        """验证域名格式"""
        if not domain or len(domain) > 253:
            return False

        # 如果允许通配符域名
        if allow_wildcard and domain.startswith('*.'):
            domain = domain[2:]  # 移除通配符前缀

        # 域名正则表达式
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(pattern, domain))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        if not email or len(email) > 254:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """验证IP地址格式"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_port(port: Union[str, int]) -> bool:
        """验证端口号"""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_server_name(name: str) -> bool:
        """验证服务器名称"""
        if not name or len(name) > 100:
            return False
        
        # 服务器名称只能包含字母、数字、中文、下划线、连字符和空格
        pattern = r'^[\w\u4e00-\u9fa5\-\s]+$'
        return bool(re.match(pattern, name))
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """验证用户名"""
        if not username or len(username) < 3 or len(username) > 50:
            return False
        
        # 用户名只能包含字母、数字和下划线
        pattern = r'^[a-zA-Z0-9_]+$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def validate_password(password: str) -> bool:
        """验证密码强度"""
        if not password or len(password) < 6 or len(password) > 128:
            return False
        
        # 密码必须包含至少一个字母和一个数字
        has_letter = bool(re.search(r'[a-zA-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        
        return has_letter and has_digit
    
    @staticmethod
    def validate_certificate_type(cert_type: str) -> bool:
        """验证证书类型"""
        valid_types = ['DV', 'OV', 'EV']
        return cert_type in valid_types
    
    @staticmethod
    def validate_ca_type(ca_type: str) -> bool:
        """验证CA类型"""
        valid_cas = ['letsencrypt', 'zerossl', 'buypass', 'google']
        return ca_type in valid_cas
    
    @staticmethod
    def validate_encryption_algorithm(algorithm: str) -> bool:
        """验证加密算法"""
        valid_algorithms = ['rsa', 'ecc']
        return algorithm.lower() in valid_algorithms
    
    @staticmethod
    def validate_server_type(server_type: str) -> bool:
        """验证服务器类型"""
        valid_types = ['nginx', 'apache', 'iis', 'other']
        return server_type in valid_types
    
    @staticmethod
    def validate_monitoring_status(status: str) -> bool:
        """验证监控状态"""
        valid_statuses = ['normal', 'warning', 'error', 'unknown']
        return status in valid_statuses
    
    @staticmethod
    def validate_ip_type(ip_type: str) -> bool:
        """验证IP类型"""
        valid_types = ['ipv4', 'ipv6']
        return ip_type.lower() in valid_types
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """清理字符串输入"""
        if not isinstance(value, str):
            return ""
        
        # 移除危险字符
        value = re.sub(r'[<>"\']', '', value)
        
        # 限制长度
        if len(value) > max_length:
            value = value[:max_length]
        
        return value.strip()
    
    @staticmethod
    def validate_pagination(page: Union[str, int], limit: Union[str, int]) -> Dict[str, int]:
        """验证分页参数"""
        try:
            page_num = max(1, int(page))
        except (ValueError, TypeError):
            page_num = 1
        
        try:
            limit_num = max(1, min(100, int(limit)))
        except (ValueError, TypeError):
            limit_num = 20
        
        return {'page': page_num, 'limit': limit_num}
    
    @staticmethod
    def validate_sort_field(field: str, allowed_fields: List[str]) -> str:
        """验证排序字段"""
        if field in allowed_fields:
            return field
        return allowed_fields[0] if allowed_fields else 'id'
    
    @staticmethod
    def validate_sort_order(order: str) -> str:
        """验证排序顺序"""
        return 'desc' if order.lower() == 'desc' else 'asc'
    
    @classmethod
    def validate_certificate_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证证书数据"""
        errors = {}
        
        # 验证域名
        domain = data.get('domain', '').strip()
        if not domain:
            errors['domain'] = '域名不能为空'
        elif not cls.validate_domain(domain):
            errors['domain'] = '域名格式不正确'
        
        # 验证CA类型
        ca_type = data.get('ca_type', '').strip()
        if ca_type and not cls.validate_ca_type(ca_type):
            errors['ca_type'] = 'CA类型不正确'
        
        # 验证加密算法
        algorithm = data.get('encryption_algorithm', '').strip()
        if algorithm and not cls.validate_encryption_algorithm(algorithm):
            errors['encryption_algorithm'] = '加密算法不正确'
        
        return errors
    
    @classmethod
    def validate_server_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证服务器数据"""
        errors = {}
        
        # 验证服务器名称
        name = data.get('name', '').strip()
        if not name:
            errors['name'] = '服务器名称不能为空'
        elif not cls.validate_server_name(name):
            errors['name'] = '服务器名称格式不正确'
        
        # 验证IP地址（可选）
        ip = data.get('ip', '').strip()
        if ip and not cls.validate_ip_address(ip):
            errors['ip'] = 'IP地址格式不正确'
        
        # 验证服务器类型
        server_type = data.get('server_type', '').strip()
        if server_type and not cls.validate_server_type(server_type):
            errors['server_type'] = '服务器类型不正确'
        
        return errors
    
    @classmethod
    def validate_monitoring_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证监控数据"""
        errors = {}
        
        # 验证域名
        domain = data.get('domain', '').strip()
        if not domain:
            errors['domain'] = '域名不能为空'
        elif not cls.validate_domain(domain):
            errors['domain'] = '域名格式不正确'
        
        # 验证端口
        port = data.get('port', 443)
        if not cls.validate_port(port):
            errors['port'] = '端口号不正确'
        
        # 验证IP类型
        ip_type = data.get('ip_type', '').strip()
        if ip_type and not cls.validate_ip_type(ip_type):
            errors['ip_type'] = 'IP类型不正确'
        
        # 验证IP地址（可选）
        ip_address = data.get('ip_address', '').strip()
        if ip_address and not cls.validate_ip_address(ip_address):
            errors['ip_address'] = 'IP地址格式不正确'
        
        return errors
    
    @classmethod
    def validate_user_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证用户数据"""
        errors = {}
        
        # 验证用户名
        username = data.get('username', '').strip()
        if not username:
            errors['username'] = '用户名不能为空'
        elif not cls.validate_username(username):
            errors['username'] = '用户名格式不正确'
        
        # 验证邮箱
        email = data.get('email', '').strip()
        if not email:
            errors['email'] = '邮箱不能为空'
        elif not cls.validate_email(email):
            errors['email'] = '邮箱格式不正确'
        
        # 验证密码（如果提供）
        password = data.get('password', '').strip()
        if password and not cls.validate_password(password):
            errors['password'] = '密码强度不够'
        
        return errors
