"""
CSRF保护模块
提供跨站请求伪造(CSRF)攻击防护功能
"""
import secrets
import hashlib
import hmac
from functools import wraps
from typing import Optional, Dict, Any
from flask import Flask, request, session, jsonify, g
from utils.exceptions import ValidationError, ErrorCode
from utils.logging_config import get_logger

logger = get_logger(__name__)


class CSRFProtection:
    """CSRF保护类"""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.secret_key = None
        self.token_field = 'csrf_token'
        self.header_name = 'X-CSRF-Token'
        self.time_limit = 3600  # 1小时
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """初始化应用"""
        self.app = app
        self.secret_key = app.config.get('SECRET_KEY', 'default-secret-key')
        
        # 配置CSRF设置
        app.config.setdefault('CSRF_TOKEN_FIELD', self.token_field)
        app.config.setdefault('CSRF_HEADER_NAME', self.header_name)
        app.config.setdefault('CSRF_TIME_LIMIT', self.time_limit)
        
        # 注册请求处理器
        app.before_request(self._before_request)
        
        logger.info("CSRF保护已初始化")
    
    def _before_request(self):
        """请求前处理"""
        # 为每个请求生成CSRF令牌
        if 'csrf_token' not in session:
            session['csrf_token'] = self.generate_token()
    
    def generate_token(self) -> str:
        """生成CSRF令牌"""
        # 生成随机字符串
        random_string = secrets.token_urlsafe(32)
        
        # 使用HMAC签名
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            random_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        token = f"{random_string}.{signature}"
        logger.debug(f"生成CSRF令牌: {token[:16]}...")
        
        return token
    
    def validate_token(self, token: str) -> bool:
        """验证CSRF令牌"""
        if not token:
            return False
        
        try:
            # 分离随机字符串和签名
            parts = token.split('.')
            if len(parts) != 2:
                return False
            
            random_string, signature = parts
            
            # 重新计算签名
            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                random_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # 使用安全比较
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if is_valid:
                logger.debug(f"CSRF令牌验证成功: {token[:16]}...")
            else:
                logger.warning(f"CSRF令牌验证失败: {token[:16]}...")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"CSRF令牌验证异常: {e}")
            return False
    
    def get_token(self) -> str:
        """获取当前会话的CSRF令牌"""
        return session.get('csrf_token', '')
    
    def protect(self, f):
        """CSRF保护装饰器"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
                # 获取令牌
                token = None
                
                # 首先从表单数据中获取
                if request.form:
                    token = request.form.get(self.token_field)
                
                # 然后从JSON数据中获取
                if not token and request.is_json:
                    json_data = request.get_json(silent=True)
                    if json_data:
                        token = json_data.get(self.token_field)
                
                # 最后从请求头中获取
                if not token:
                    token = request.headers.get(self.header_name)
                
                # 验证令牌
                if not token:
                    logger.warning(f"CSRF令牌缺失 - {request.method} {request.path}")
                    raise ValidationError(
                        error_code=ErrorCode.CSRF_TOKEN_MISSING,
                        message="CSRF令牌缺失"
                    )
                
                session_token = session.get('csrf_token')
                if not session_token:
                    logger.warning(f"会话中无CSRF令牌 - {request.method} {request.path}")
                    raise ValidationError(
                        error_code=ErrorCode.CSRF_TOKEN_INVALID,
                        message="会话已过期，请刷新页面"
                    )
                
                if not self.validate_token(token) or token != session_token:
                    logger.warning(f"CSRF令牌无效 - {request.method} {request.path}")
                    raise ValidationError(
                        error_code=ErrorCode.CSRF_TOKEN_INVALID,
                        message="CSRF令牌无效"
                    )
                
                logger.debug(f"CSRF验证通过 - {request.method} {request.path}")
            
            return f(*args, **kwargs)
        
        return decorated_function


# 全局CSRF保护实例
csrf = CSRFProtection()


def init_csrf_protection(app: Flask):
    """初始化CSRF保护"""
    csrf.init_app(app)
    
    # 添加模板全局变量
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=csrf.get_token)
    
    # 添加API端点获取CSRF令牌
    @app.route('/api/v1/csrf-token', methods=['GET'])
    def get_csrf_token():
        """获取CSRF令牌"""
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'csrf_token': csrf.get_token(),
                'field_name': csrf.token_field,
                'header_name': csrf.header_name
            }
        })


def csrf_protect(f):
    """CSRF保护装饰器"""
    return csrf.protect(f)


def require_csrf_token(f):
    """要求CSRF令牌的装饰器（别名）"""
    return csrf_protect(f)


def get_csrf_token() -> str:
    """获取当前CSRF令牌"""
    return csrf.get_token()


def validate_csrf_token(token: str) -> bool:
    """验证CSRF令牌"""
    return csrf.validate_token(token)
