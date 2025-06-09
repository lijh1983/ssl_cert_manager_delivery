"""
输入验证和数据清理模块
提供统一的数据验证和清理功能
"""
import re
import html
import ipaddress
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from flask import request, jsonify

from .exceptions import ValidationError


class InputValidator:
    """输入验证器"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        if not isinstance(email, str):
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_domain(domain: str, allow_wildcard: bool = False) -> bool:
        """验证域名格式"""
        if not isinstance(domain, str):
            return False
        
        # 长度检查
        if len(domain) > 253 or len(domain) == 0:
            return False
        
        # 通配符域名检查
        if domain.startswith('*.'):
            if not allow_wildcard:
                return False
            # 通配符只能在最前面
            if domain.count('*') > 1:
                return False
            # 验证通配符后的域名部分
            domain = domain[2:]
        
        # 基本域名格式验证
        pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        return bool(re.match(pattern, domain))
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """验证用户名格式"""
        if not isinstance(username, str):
            return False
        
        if len(username) < 3 or len(username) > 50:
            return False
        
        # 用户名只能包含字母、数字、下划线和连字符
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, username))
    
    @staticmethod
    def validate_password(password: str) -> bool:
        """验证密码强度"""
        if not isinstance(password, str):
            return False
        
        if len(password) < 8 or len(password) > 128:
            return False
        
        # 密码强度检查
        has_lower = bool(re.search(r'[a-z]', password))
        has_upper = bool(re.search(r'[A-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        
        return has_lower and has_upper and has_digit
    
    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """验证IP地址格式"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_port(port: Any) -> bool:
        """验证端口号"""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """验证URL格式"""
        if not isinstance(url, str):
            return False
        
        pattern = r'^https?://(?:[-\w.])+(?::[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$'
        return bool(re.match(pattern, url))


class DataSanitizer:
    """数据清理器"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """清理字符串"""
        if not isinstance(value, str):
            return str(value)
        
        # HTML转义
        sanitized = html.escape(value)
        
        # 移除控制字符
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
        
        # 限制长度
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    @staticmethod
    def sanitize_email(email: str) -> str:
        """清理邮箱地址"""
        if not isinstance(email, str):
            return ''
        
        # 转换为小写并去除空格
        email = email.lower().strip()
        
        # 基本格式检查
        if not InputValidator.validate_email(email):
            return ''
        
        return email
    
    @staticmethod
    def sanitize_domain(domain: str) -> str:
        """清理域名"""
        if not isinstance(domain, str):
            return ''
        
        # 转换为小写并去除空格
        domain = domain.lower().strip()
        
        # 移除协议前缀
        domain = re.sub(r'^https?://', '', domain)
        
        # 移除路径
        domain = domain.split('/')[0]
        
        # 移除端口
        domain = domain.split(':')[0]
        
        return domain
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """清理文件名"""
        if not isinstance(filename, str):
            return ''
        
        # 移除危险字符
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        
        # 移除控制字符
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
        
        # 限制长度
        if len(filename) > 255:
            filename = filename[:255]
        
        return filename.strip()


def validate_request_data(validation_rules: Dict[str, Dict[str, Any]]):
    """请求数据验证装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                raise ValidationError("请求必须是JSON格式")
            
            try:
                data = request.get_json()
                if data is None:
                    raise ValidationError("请求体不能为空")
            except Exception:
                raise ValidationError("JSON格式错误")
            
            # 验证字段
            field_errors = {}
            
            for field_name, rules in validation_rules.items():
                value = data.get(field_name)
                
                # 检查必需字段
                if rules.get('required', False) and (value is None or value == ''):
                    field_errors[field_name] = '此字段为必需'
                    continue
                
                # 如果字段为空且非必需，跳过验证
                if value is None or value == '':
                    continue
                
                # 类型检查
                expected_type = rules.get('type')
                if expected_type and not isinstance(value, expected_type):
                    field_errors[field_name] = f'字段类型必须是{expected_type.__name__}'
                    continue
                
                # 长度检查
                if isinstance(value, str):
                    min_length = rules.get('min_length')
                    max_length = rules.get('max_length')
                    
                    if min_length and len(value) < min_length:
                        field_errors[field_name] = f'长度不能少于{min_length}个字符'
                        continue
                    
                    if max_length and len(value) > max_length:
                        field_errors[field_name] = f'长度不能超过{max_length}个字符'
                        continue
                
                # 模式匹配
                pattern = rules.get('pattern')
                if pattern and isinstance(value, str):
                    if not re.match(pattern, value):
                        field_errors[field_name] = '格式不正确'
                        continue
                
                # 自定义验证器
                validator = rules.get('validator')
                if validator and callable(validator):
                    if not validator(value):
                        field_errors[field_name] = '验证失败'
                        continue
            
            if field_errors:
                raise ValidationError("字段验证失败", field_errors=field_errors)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def sanitize_request_data():
    """请求数据清理装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if request.is_json:
                data = request.get_json()
                if data:
                    # 清理字符串字段
                    for key, value in data.items():
                        if isinstance(value, str):
                            data[key] = DataSanitizer.sanitize_string(value)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# 常用验证规则
COMMON_VALIDATION_RULES = {
    'email': {
        'required': True,
        'type': str,
        'max_length': 254,
        'validator': InputValidator.validate_email
    },
    'username': {
        'required': True,
        'type': str,
        'min_length': 3,
        'max_length': 50,
        'validator': InputValidator.validate_username
    },
    'password': {
        'required': True,
        'type': str,
        'min_length': 8,
        'max_length': 128,
        'validator': InputValidator.validate_password
    },
    'domain': {
        'required': True,
        'type': str,
        'max_length': 253,
        'validator': lambda x: InputValidator.validate_domain(x, allow_wildcard=True)
    },
    'ip_address': {
        'required': True,
        'type': str,
        'validator': InputValidator.validate_ip_address
    },
    'port': {
        'required': False,
        'type': int,
        'validator': InputValidator.validate_port
    },
    'url': {
        'required': False,
        'type': str,
        'max_length': 2048,
        'validator': InputValidator.validate_url
    }
}
