"""
API应用主模块，提供RESTful API服务
"""
import os
import json
import datetime
import secrets
import jwt
from typing import Dict, List, Any, Optional
from flask import Flask, request, jsonify, g
from functools import wraps

# 导入模型
from models.database import db, init_db, DatabaseConfig
from models.user import User
from models.server import Server
from models.certificate import Certificate
from models.alert import Alert

# 导入安全模块
from utils.validators import InputValidator, DataSanitizer, validate_request_data, sanitize_request_data
from utils.csrf import init_csrf_protection, csrf_protect, require_csrf_token
from utils.rate_limiter import init_rate_limiter, rate_limit, strict_rate_limit, moderate_rate_limit

# 导入错误处理模块
from utils.exceptions import (
    ErrorCode, BaseAPIException, ValidationError,
    AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ResourceConflictError,
    ACMEError, CertificateError
)
from utils.error_handler import (
    handle_api_errors, api_error_handler,
    validate_json_request, create_error_response
)

# 导入配置和日志模块
from utils.config_manager import get_config, get_security_config, get_logging_config
from utils.logging_config import setup_logging, init_logging_middleware, get_logger

# 导入服务模块
from services.certificate_service import certificate_service
from services.alert_manager import alert_manager, AlertRule, AlertType, AlertSeverity
from services.notification import notification_manager
from services.monitoring_service import MonitoringService
from services.domain_monitoring_service import DomainMonitoringService
from services.domain_monitoring_scheduler import domain_monitoring_scheduler
from services.port_monitoring_service import PortMonitoringService
from services.certificate_operations_service import CertificateOperationsService

# 获取应用配置
app_config = get_config()
security_config = get_security_config()
logging_config = get_logging_config()

# 设置日志
setup_logging(
    app_name=app_config.app_name.lower().replace(' ', '_'),
    log_level=logging_config.level,
    log_file=logging_config.file_path,
    enable_console=logging_config.console_enabled
)

# 获取应用日志记录器
logger = get_logger('app')

# 初始化服务实例
monitoring_service = MonitoringService()
domain_monitoring_service = DomainMonitoringService()
port_monitoring_service = PortMonitoringService()
certificate_operations_service = CertificateOperationsService()

# 初始化Flask应用
app = Flask(__name__)

# 配置
app.config['SECRET_KEY'] = security_config.secret_key
app.config['JWT_EXPIRATION'] = security_config.jwt_expiration
app.config['DEBUG'] = app_config.debug

# 注册错误处理器
handle_api_errors(app)

# 初始化日志中间件
init_logging_middleware(app)

# 初始化MySQL数据库
try:
    logger.info("初始化MySQL数据库连接...")
    init_db()
    logger.info("MySQL数据库初始化完成")
except Exception as e:
    logger.error(f"MySQL数据库初始化失败: {e}")
    raise

# 初始化安全模块
init_csrf_protection(app)
init_rate_limiter(app)

# 辅助函数
def generate_token(user_id: int) -> str:
    """生成JWT令牌"""
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=app.config['JWT_EXPIRATION']),
        'iat': datetime.datetime.utcnow()
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# 装饰器
def login_required(f):
    """用户认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'code': 401,
                'message': '未认证或认证失败',
                'data': None
            }), 401
        
        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({
                'code': 401,
                'message': '令牌已过期或无效',
                'data': None
            }), 401
        
        user = User.get_by_id(payload['user_id'])
        if not user:
            return jsonify({
                'code': 401,
                'message': '用户不存在',
                'data': None
            }), 401
        
        g.user = user
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user') or not g.user.is_admin():
            return jsonify({
                'code': 403,
                'message': '权限不足',
                'data': None
            }), 403
        return f(*args, **kwargs)
    return decorated_function

def server_token_required(f):
    """服务器令牌认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('X-Server-Token')
        if not token:
            return jsonify({
                'code': 401,
                'message': '未提供服务器令牌',
                'data': None
            }), 401
        
        server = Server.get_by_token(token)
        if not server:
            return jsonify({
                'code': 401,
                'message': '无效的服务器令牌',
                'data': None
            }), 401
        
        g.server = server
        return f(*args, **kwargs)
    return decorated_function

# 路由
@app.route('/api/v1/auth/login', methods=['POST'])
@strict_rate_limit  # 严格限流：每分钟5次，每小时20次
@api_error_handler
@validate_json_request(required_fields=['username', 'password'])
def login():
    """用户登录"""
    data = request.get_json()

    username = data['username']
    password = data['password']

    # 验证用户名格式
    if not InputValidator.validate_username(username):
        raise ValidationError(
            "用户名格式不正确",
            field_errors={'username': '用户名只能包含字母、数字、下划线和连字符，长度3-30个字符'}
        )

    user = User.authenticate(username, password)
    if not user:
        raise AuthenticationError(
            error_code=ErrorCode.INVALID_CREDENTIALS,
            message="用户名或密码错误"
        )

    token = generate_token(user.id)

    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'token': token,
            'expires_in': app.config['JWT_EXPIRATION'],
            'user': user.to_dict()
        }
    })

@app.route('/api/v1/auth/refresh', methods=['POST'])
@login_required
def refresh_token():
    """刷新令牌"""
    token = generate_token(g.user.id)
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'token': token,
            'expires_in': app.config['JWT_EXPIRATION']
        }
    })

@app.route('/api/v1/auth/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    # JWT无状态，客户端丢弃令牌即可
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': None
    })

@app.route('/api/v1/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    """获取用户列表"""
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    keyword = request.args.get('keyword')
    
    users, total = User.get_all(page, limit, keyword)
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'total': total,
            'page': page,
            'limit': limit,
            'items': [user.to_dict() for user in users]
        }
    })

@app.route('/api/v1/users', methods=['POST'])
@login_required
@admin_required
@moderate_rate_limit  # 中等限流
@csrf_protect  # CSRF保护
@validate_request_data({
    'username': {
        'required': True,
        'type': str,
        'min_length': 3,
        'max_length': 30,
        'validator': InputValidator.validate_username
    },
    'email': {
        'required': True,
        'type': str,
        'max_length': 100,
        'validator': InputValidator.validate_email
    },
    'password': {
        'required': True,
        'type': str,
        'min_length': 8,
        'max_length': 128
    },
    'role': {
        'required': False,
        'type': str,
        'pattern': r'^(admin|user)$'
    }
})
@sanitize_request_data()
def create_user():
    """创建用户"""
    data = request.get_json()

    # 验证密码强度
    password_valid, password_message = InputValidator.validate_password(data['password'])
    if not password_valid:
        return jsonify({
            'code': 400,
            'message': password_message,
            'data': None
        }), 400

    try:
        user = User.create(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            role=data.get('role', 'user')
        )

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': user.to_dict()
        })
    except ValueError as e:
        return jsonify({
            'code': 409,
            'message': str(e),
            'data': None
        }), 409

@app.route('/api/v1/users/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """获取用户详情"""
    # 普通用户只能查看自己的信息
    if not g.user.is_admin() and g.user.id != user_id:
        return jsonify({
            'code': 403,
            'message': '权限不足',
            'data': None
        }), 403
    
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({
            'code': 404,
            'message': '用户不存在',
            'data': None
        }), 404
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': user.to_dict()
    })

@app.route('/api/v1/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """更新用户信息"""
    # 普通用户只能更新自己的信息
    if not g.user.is_admin() and g.user.id != user_id:
        return jsonify({
            'code': 403,
            'message': '权限不足',
            'data': None
        }), 403
    
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({
            'code': 404,
            'message': '用户不存在',
            'data': None
        }), 404
    
    data = request.get_json()
    if not data:
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'data': None
        }), 400
    
    # 只允许更新特定字段
    if 'email' in data:
        user.email = data['email']
    
    # 只有管理员可以更改角色
    if g.user.is_admin() and 'role' in data:
        user.role = data['role']
    
    # 更新密码
    if 'password' in data:
        user.password = data['password']
    
    user.save()
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': user.to_dict()
    })

@app.route('/api/v1/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """删除用户"""
    user = User.get_by_id(user_id)
    if not user:
        return jsonify({
            'code': 404,
            'message': '用户不存在',
            'data': None
        }), 404
    
    # 不能删除自己
    if user.id == g.user.id:
        return jsonify({
            'code': 400,
            'message': '不能删除当前登录用户',
            'data': None
        }), 400
    
    user.delete()
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': None
    })

@app.route('/api/v1/servers', methods=['GET'])
@login_required
def get_servers():
    """获取服务器列表"""
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    keyword = request.args.get('keyword')
    
    # 管理员可以查看所有服务器，普通用户只能查看自己的服务器
    user_id = None if g.user.is_admin() else g.user.id
    
    servers, total = Server.get_all(page, limit, keyword, user_id)
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'total': total,
            'page': page,
            'limit': limit,
            'items': [server.to_dict() for server in servers]
        }
    })

@app.route('/api/v1/servers', methods=['POST'])
@login_required
@moderate_rate_limit  # 中等限流
@csrf_protect  # CSRF保护
@validate_request_data({
    'name': {
        'required': True,
        'type': str,
        'min_length': 2,
        'max_length': 50,
        'validator': InputValidator.validate_server_name
    },
    'type': {
        'required': False,
        'type': str,
        'pattern': r'^(nginx|apache|iis|other)$'
    },
    'os_type': {
        'required': False,
        'type': str,
        'max_length': 100
    },
    'ip': {
        'required': False,
        'type': str,
        'validator': InputValidator.validate_ip_address
    },
    'version': {
        'required': False,
        'type': str,
        'max_length': 50
    },
    'auto_renew': {
        'required': False,
        'type': bool
    },
    'description': {
        'required': False,
        'type': str,
        'max_length': 500
    }
})
@sanitize_request_data()
def create_server():
    """创建服务器"""
    data = request.get_json()

    server = Server.create(
        name=data['name'],
        user_id=g.user.id,
        server_type=data.get('type', 'nginx'),
        os_type=data.get('os_type', ''),
        ip=data.get('ip', ''),
        version=data.get('version', ''),
        auto_renew=data.get('auto_renew', True),
        description=data.get('description', '')
    )

    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'id': server.id,
            'name': server.name,
            'type': server.server_type,
            'os_type': server.os_type,
            'ip': server.ip,
            'version': server.version,
            'token': server.token,
            'auto_renew': server.auto_renew,
            'description': server.description,
            'created_at': server.created_at,
            'install_command': server.get_install_command()
        }
    })

@app.route('/api/v1/servers/<int:server_id>', methods=['GET'])
@login_required
def get_server(server_id):
    """获取服务器详情"""
    server = Server.get_by_id(server_id)
    if not server:
        return jsonify({
            'code': 404,
            'message': '服务器不存在',
            'data': None
        }), 404
    
    # 普通用户只能查看自己的服务器
    if not g.user.is_admin() and server.user_id != g.user.id:
        return jsonify({
            'code': 403,
            'message': '权限不足',
            'data': None
        }), 403
    
    # 获取服务器上的证书
    certificates = server.get_certificates()
    certificates_count = len(certificates)
    
    server_dict = server.to_dict()
    server_dict['certificates_count'] = certificates_count
    server_dict['certificates'] = certificates[:5]  # 只返回前5个证书
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': server_dict
    })

@app.route('/api/v1/servers/<int:server_id>', methods=['PUT'])
@login_required
def update_server(server_id):
    """更新服务器信息"""
    server = Server.get_by_id(server_id)
    if not server:
        return jsonify({
            'code': 404,
            'message': '服务器不存在',
            'data': None
        }), 404
    
    # 普通用户只能更新自己的服务器
    if not g.user.is_admin() and server.user_id != g.user.id:
        return jsonify({
            'code': 403,
            'message': '权限不足',
            'data': None
        }), 403
    
    data = request.get_json()
    if not data:
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'data': None
        }), 400
    
    # 只允许更新特定字段
    if 'name' in data:
        server.name = data['name']

    if 'auto_renew' in data:
        server.auto_renew = data['auto_renew']

    if 'description' in data:
        server.description = data['description']

    server.save()

    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'id': server.id,
            'name': server.name,
            'auto_renew': server.auto_renew,
            'description': server.description,
            'updated_at': server.updated_at
        }
    })

@app.route('/api/v1/servers/<int:server_id>', methods=['DELETE'])
@login_required
def delete_server(server_id):
    """删除服务器"""
    server = Server.get_by_id(server_id)
    if not server:
        return jsonify({
            'code': 404,
            'message': '服务器不存在',
            'data': None
        }), 404
    
    # 普通用户只能删除自己的服务器
    if not g.user.is_admin() and server.user_id != g.user.id:
        return jsonify({
            'code': 403,
            'message': '权限不足',
            'data': None
        }), 403
    
    server.delete()
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': None
    })

@app.route('/api/v1/servers/register', methods=['POST'])
@server_token_required
def register_server():
    """客户端注册服务器信息"""
    data = request.get_json()
    if not data:
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'data': None
        }), 400
    
    server = g.server
    server.register(
        ip=data.get('ip', ''),
        os_type=data.get('os_type', ''),
        version=data.get('version', ''),
        hostname=data.get('hostname')
    )
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'id': server.id,
            'name': server.name,
            'auto_renew': server.auto_renew
        }
    })

@app.route('/api/v1/servers/heartbeat', methods=['POST'])
@server_token_required
def server_heartbeat():
    """客户端发送心跳"""
    server = g.server
    server.update_heartbeat()
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'server_time': int(datetime.datetime.now().timestamp()),
            'commands': []  # 可能包含需要执行的命令
        }
    })

@app.route('/api/v1/certificates', methods=['GET'])
@login_required
def get_certificates():
    """获取证书列表"""
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    keyword = request.args.get('keyword')
    status = request.args.get('status')
    server_id = request.args.get('server_id')
    
    if server_id:
        server_id = int(server_id)
        # 普通用户只能查看自己的服务器上的证书
        if not g.user.is_admin():
            server = Server.get_by_id(server_id)
            if not server or server.user_id != g.user.id:
                return jsonify({
                    'code': 403,
                    'message': '权限不足',
                    'data': None
                }), 403
    
    certificates, total = Certificate.get_all(page, limit, keyword, status, server_id)
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'total': total,
            'page': page,
            'limit': limit,
            'items': [cert.to_dict() for cert in certificates]
        }
    })

@app.route('/api/v1/certificates', methods=['POST'])
@login_required
@moderate_rate_limit
@csrf_protect
@api_error_handler
@validate_json_request(
    required_fields=['domain', 'server_id'],
    optional_fields=['type', 'ca_type', 'validation_method', 'auto_renew']
)
def create_certificate():
    """申请证书"""
    data = request.get_json()

    # 验证服务器权限
    server = Server.get_by_id(data['server_id'])
    if not server:
        raise ResourceNotFoundError("服务器", data['server_id'])

    if not g.user.is_admin() and server.user_id != g.user.id:
        raise AuthorizationError("无权限在此服务器上申请证书")

    # 处理域名列表
    domains = []
    cert_type = data.get('type', 'single')

    if cert_type == 'multi':
        # 多域名证书，域名用逗号分隔
        domains = [d.strip() for d in data['domain'].split(',')]
        if len(domains) > 100:  # 限制域名数量
            raise ValidationError("多域名证书最多支持100个域名")
    else:
        domains = [data['domain']]

    # 验证所有域名格式
    for domain in domains:
        if not InputValidator.validate_domain(domain, allow_wildcard=cert_type == 'wildcard'):
            raise ValidationError(
                f'域名格式不正确: {domain}',
                field_errors={'domain': f'域名 {domain} 格式不正确'}
            )

    # 使用证书服务申请证书
    result = certificate_service.request_certificate(
        user_id=g.user.id,
        domains=domains,
        server_id=data['server_id'],
        ca_type=data.get('ca_type', 'letsencrypt'),
        validation_method=data.get('validation_method', 'http'),
        auto_renew=data.get('auto_renew', True)
    )

    if result['success']:
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'certificate_id': result['certificate_id'],
                'domains': result['domains'],
                'expires_at': result['expires_at'],
                'message': result['message']
            }
        })
    else:
        raise CertificateError(
            error_code=ErrorCode.CERTIFICATE_REQUEST_FAILED,
            message=result['error'],
            domain=domains[0] if domains else None
        )

@app.route('/api/v1/certificates/<int:cert_id>', methods=['GET'])
@login_required
def get_certificate(cert_id):
    """获取证书详情"""
    cert = Certificate.get_by_id(cert_id)
    if not cert:
        return jsonify({
            'code': 404,
            'message': '证书不存在',
            'data': None
        }), 404
    
    # 获取服务器信息
    server = Server.get_by_id(cert.server_id)
    if not server:
        return jsonify({
            'code': 404,
            'message': '服务器不存在',
            'data': None
        }), 404
    
    # 普通用户只能查看自己的服务器上的证书
    if not g.user.is_admin() and server.user_id != g.user.id:
        return jsonify({
            'code': 403,
            'message': '权限不足',
            'data': None
        }), 403
    
    # 获取证书部署记录
    deployments = cert.get_deployments()
    
    cert_dict = cert.to_dict()
    cert_dict['server'] = {
        'id': server.id,
        'name': server.name
    }
    cert_dict['deployments'] = deployments
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': cert_dict
    })

@app.route('/api/v1/certificates/<int:cert_id>', methods=['PUT'])
@login_required
def update_certificate(cert_id):
    """更新证书信息"""
    cert = Certificate.get_by_id(cert_id)
    if not cert:
        return jsonify({
            'code': 404,
            'message': '证书不存在',
            'data': None
        }), 404
    
    # 获取服务器信息
    server = Server.get_by_id(cert.server_id)
    if not server:
        return jsonify({
            'code': 404,
            'message': '服务器不存在',
            'data': None
        }), 404
    
    # 普通用户只能更新自己的服务器上的证书
    if not g.user.is_admin() and server.user_id != g.user.id:
        return jsonify({
            'code': 403,
            'message': '权限不足',
            'data': None
        }), 403
    
    data = request.get_json()
    if not data:
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'data': None
        }), 400
    
    # 只允许更新特定字段
    if 'auto_renew' in data:
        # 这里假设证书表中有auto_renew字段，实际可能需要修改数据库设计
        cert.auto_renew = data['auto_renew']
    
    cert.save()
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'id': cert.id,
            'domain': cert.domain,
            'auto_renew': getattr(cert, 'auto_renew', None),
            'updated_at': cert.updated_at
        }
    })

@app.route('/api/v1/certificates/<int:cert_id>', methods=['DELETE'])
@login_required
def delete_certificate(cert_id):
    """删除证书"""
    cert = Certificate.get_by_id(cert_id)
    if not cert:
        return jsonify({
            'code': 404,
            'message': '证书不存在',
            'data': None
        }), 404
    
    # 获取服务器信息
    server = Server.get_by_id(cert.server_id)
    if not server:
        return jsonify({
            'code': 404,
            'message': '服务器不存在',
            'data': None
        }), 404
    
    # 普通用户只能删除自己的服务器上的证书
    if not g.user.is_admin() and server.user_id != g.user.id:
        return jsonify({
            'code': 403,
            'message': '权限不足',
            'data': None
        }), 403
    
    cert.delete()
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': None
    })

@app.route('/api/v1/certificates/<int:cert_id>/renew', methods=['POST'])
@login_required
@moderate_rate_limit
@csrf_protect
def renew_certificate(cert_id):
    """续期证书"""
    try:
        # 使用证书服务续期证书
        result = certificate_service.renew_certificate(cert_id, g.user.id)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'certificate_id': cert_id,
                    'renewed': result.get('renewed', False),
                    'expires_at': result.get('expires_at'),
                    'message': result['message']
                }
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"证书续期异常: {e}")
        return jsonify({
            'code': 500,
            'message': '证书续期失败',
            'data': None
        }), 500

@app.route('/api/v1/certificates/<int:cert_id>/revoke', methods=['POST'])
@login_required
@moderate_rate_limit
@csrf_protect
@validate_request_data({
    'reason': {
        'required': False,
        'type': int,
        'pattern': r'^[0-9]$'
    }
})
def revoke_certificate(cert_id):
    """撤销证书"""
    data = request.get_json() or {}
    reason = data.get('reason', 0)

    try:
        # 使用证书服务撤销证书
        result = certificate_service.revoke_certificate(cert_id, g.user.id, reason)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'certificate_id': cert_id,
                    'message': result['message']
                }
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"证书撤销异常: {e}")
        return jsonify({
            'code': 500,
            'message': '证书撤销失败',
            'data': None
        }), 500

@app.route('/api/v1/certificates/<int:cert_id>/status', methods=['GET'])
@login_required
def get_certificate_status(cert_id):
    """获取证书状态"""
    try:
        # 使用证书服务获取证书状态
        result = certificate_service.get_certificate_status(cert_id)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result
            })
        else:
            return jsonify({
                'code': 404,
                'message': result['error'],
                'data': None
            }), 404

    except Exception as e:
        logger.error(f"获取证书状态异常: {e}")
        return jsonify({
            'code': 500,
            'message': '获取证书状态失败',
            'data': None
        }), 500

@app.route('/api/v1/certificates/apply', methods=['POST'])
@login_required
@moderate_rate_limit
@csrf_protect
@api_error_handler
@validate_json_request(
    required_fields=['domain', 'ca_type', 'encryption_algorithm'],
    optional_fields=['description']
)
def apply_free_certificate():
    """免费申请证书"""
    data = request.get_json()

    domain = data['domain']
    ca_type = data['ca_type']  # google, letsencrypt, zerossl
    encryption_algorithm = data['encryption_algorithm']  # ecc, rsa
    description = data.get('description', '')

    try:
        # 生成DNS验证记录
        verification_info = certificate_service.generate_dns_verification(
            domain=domain,
            ca_type=ca_type
        )

        # 创建证书申请记录
        cert = Certificate.create(
            domain=domain,
            ca_type=ca_type,
            type='single' if not domain.startswith('*.') else 'wildcard',
            validation_method='dns',
            user_id=g.user.id,
            status='pending_verification',
            description=description
        )

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'certificate_id': cert.id,
                'domain': domain,
                'verification_info': verification_info,
                'status': 'pending_verification'
            }
        })

    except Exception as e:
        logger.error(f"证书申请失败: {e}")
        return jsonify({
            'code': 500,
            'message': '证书申请失败',
            'data': None
        }), 500

@app.route('/api/v1/certificates/<int:cert_id>/verify-domain', methods=['POST'])
@login_required
@moderate_rate_limit
@csrf_protect
def verify_domain(cert_id):
    """验证域名所有权"""
    cert = Certificate.get_by_id(cert_id)
    if not cert:
        return jsonify({
            'code': 404,
            'message': '证书不存在',
            'data': None
        }), 404

    # 权限检查
    if not g.user.is_admin() and cert.user_id != g.user.id:
        return jsonify({
            'code': 403,
            'message': '权限不足',
            'data': None
        }), 403

    try:
        # 执行域名验证
        result = certificate_service.verify_domain_ownership(cert_id)

        if result['success']:
            # 验证成功，开始申请证书
            cert_result = certificate_service.issue_certificate(cert_id)

            if cert_result['success']:
                return jsonify({
                    'code': 200,
                    'message': '域名验证通过，证书申请成功',
                    'data': {
                        'certificate_id': cert_id,
                        'status': 'issued',
                        'expires_at': cert_result.get('expires_at')
                    }
                })
            else:
                return jsonify({
                    'code': 400,
                    'message': f'证书申请失败: {cert_result["error"]}',
                    'data': None
                }), 400
        else:
            return jsonify({
                'code': 400,
                'message': '域名验证未通过，请检查配置或稍后再试',
                'data': {
                    'error': result.get('error'),
                    'details': result.get('details')
                }
            }), 400

    except Exception as e:
        logger.error(f"域名验证失败: {e}")
        return jsonify({
            'code': 500,
            'message': '域名验证失败',
            'data': None
        }), 500

@app.route('/api/v1/certificates/<int:cert_id>/download', methods=['GET'])
@login_required
def download_certificate(cert_id):
    """下载证书文件"""
    cert = Certificate.get_by_id(cert_id)
    if not cert:
        return jsonify({
            'code': 404,
            'message': '证书不存在',
            'data': None
        }), 404

    # 权限检查
    if not g.user.is_admin() and cert.user_id != g.user.id:
        return jsonify({
            'code': 403,
            'message': '权限不足',
            'data': None
        }), 403

    format_type = request.args.get('format', 'pem')

    try:
        # 生成下载文件
        download_data = certificate_service.generate_download_files(cert_id, format_type)

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'download_url': download_data['download_url'],
                'filename': download_data['filename'],
                'format': format_type,
                'size': download_data['size'],
                'expires_at': download_data['expires_at']
            }
        })

    except Exception as e:
        logger.error(f"证书下载失败: {e}")
        return jsonify({
            'code': 500,
            'message': '证书下载失败',
            'data': None
        }), 500

@app.route('/api/v1/certificates/expired', methods=['DELETE'])
@login_required
@csrf_protect
def delete_expired_certificates():
    """删除失效证书"""
    try:
        # 获取用户的失效证书
        user_id = None if g.user.is_admin() else g.user.id
        result = certificate_service.delete_expired_certificates(user_id)

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'deleted_count': result['deleted_count'],
                'deleted_certificates': result['deleted_certificates']
            }
        })

    except Exception as e:
        logger.error(f"删除失效证书失败: {e}")
        return jsonify({
            'code': 500,
            'message': '删除失效证书失败',
            'data': None
        }), 500

@app.route('/api/v1/certificates/auto-renew', methods=['POST'])
@login_required
@admin_required
@strict_rate_limit
@csrf_protect
def auto_renew_certificates():
    """自动续期所有证书"""
    try:
        # 使用证书服务自动续期证书
        result = certificate_service.auto_renew_certificates()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': result
        })

    except Exception as e:
        logger.error(f"自动续期异常: {e}")
        return jsonify({
            'code': 500,
            'message': '自动续期失败',
            'data': None
        }), 500

# ==========================================
# 证书监控API
# ==========================================

@app.route('/api/v1/monitoring', methods=['GET'])
@login_required
def get_monitoring_list():
    """获取证书监控列表"""
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    keyword = request.args.get('keyword')
    status = request.args.get('status')

    try:
        # 获取用户的监控配置
        user_id = None if g.user.is_admin() else g.user.id
        result = domain_monitoring_service.get_monitoring_list(
            page=page,
            limit=limit,
            keyword=keyword,
            status=status,
            user_id=user_id
        )

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total': result['total'],
                'page': page,
                'limit': limit,
                'items': result['items']
            }
        })

    except Exception as e:
        logger.error(f"获取监控列表失败: {e}")
        return jsonify({
            'code': 500,
            'message': '获取监控列表失败',
            'data': None
        }), 500

@app.route('/api/v1/monitoring', methods=['POST'])
@login_required
@moderate_rate_limit
@csrf_protect
@validate_request_data({
    'domain': {
        'required': True,
        'type': str,
        'validator': InputValidator.validate_domain
    },
    'port': {
        'required': False,
        'type': int,
        'min_value': 1,
        'max_value': 65535
    },
    'ip_type': {
        'required': False,
        'type': str,
        'pattern': r'^(ipv4|ipv6)$'
    },
    'ip_address': {
        'required': False,
        'type': str
    },
    'monitoring_enabled': {
        'required': False,
        'type': bool
    },
    'description': {
        'required': False,
        'type': str,
        'max_length': 500
    }
})
def create_monitoring():
    """创建监控配置"""
    data = request.get_json()

    try:
        result = domain_monitoring_service.create_monitoring_config(
            domain=data['domain'],
            port=data.get('port', 443),
            ip_type=data.get('ip_type', 'ipv4'),
            ip_address=data.get('ip_address'),
            monitoring_enabled=data.get('monitoring_enabled', True),
            description=data.get('description', ''),
            user_id=g.user.id
        )

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result['monitoring_config']
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"创建监控配置失败: {e}")
        return jsonify({
            'code': 500,
            'message': '创建监控配置失败',
            'data': None
        }), 500

@app.route('/api/v1/monitoring/<int:monitoring_id>', methods=['GET'])
@login_required
def get_monitoring_detail(monitoring_id):
    """获取监控详情"""
    try:
        result = domain_monitoring_service.get_monitoring_detail(monitoring_id)

        if result['success']:
            # 权限检查
            monitoring_config = result['monitoring_config']
            if not g.user.is_admin() and monitoring_config.get('user_id') != g.user.id:
                return jsonify({
                    'code': 403,
                    'message': '权限不足',
                    'data': None
                }), 403

            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result['monitoring_config']
            })
        else:
            return jsonify({
                'code': 404,
                'message': '监控配置不存在',
                'data': None
            }), 404

    except Exception as e:
        logger.error(f"获取监控详情失败: {e}")
        return jsonify({
            'code': 500,
            'message': '获取监控详情失败',
            'data': None
        }), 500

@app.route('/api/v1/monitoring/<int:monitoring_id>', methods=['PUT'])
@login_required
@csrf_protect
@validate_request_data({
    'monitoring_enabled': {
        'required': False,
        'type': bool
    },
    'description': {
        'required': False,
        'type': str,
        'max_length': 500
    }
})
def update_monitoring(monitoring_id):
    """更新监控配置"""
    data = request.get_json()

    try:
        # 权限检查
        monitoring_detail = domain_monitoring_service.get_monitoring_detail(monitoring_id)
        if not monitoring_detail['success']:
            return jsonify({
                'code': 404,
                'message': '监控配置不存在',
                'data': None
            }), 404

        monitoring_config = monitoring_detail['monitoring_config']
        if not g.user.is_admin() and monitoring_config.get('user_id') != g.user.id:
            return jsonify({
                'code': 403,
                'message': '权限不足',
                'data': None
            }), 403

        # 更新监控配置
        result = domain_monitoring_service.update_monitoring_config(monitoring_id, data)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result['monitoring_config']
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"更新监控配置失败: {e}")
        return jsonify({
            'code': 500,
            'message': '更新监控配置失败',
            'data': None
        }), 500

@app.route('/api/v1/monitoring/<int:monitoring_id>', methods=['DELETE'])
@login_required
@csrf_protect
def delete_monitoring(monitoring_id):
    """删除监控配置"""
    try:
        # 权限检查
        monitoring_detail = domain_monitoring_service.get_monitoring_detail(monitoring_id)
        if not monitoring_detail['success']:
            return jsonify({
                'code': 404,
                'message': '监控配置不存在',
                'data': None
            }), 404

        monitoring_config = monitoring_detail['monitoring_config']
        if not g.user.is_admin() and monitoring_config.get('user_id') != g.user.id:
            return jsonify({
                'code': 403,
                'message': '权限不足',
                'data': None
            }), 403

        # 删除监控配置
        result = domain_monitoring_service.delete_monitoring_config(monitoring_id)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': None
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"删除监控配置失败: {e}")
        return jsonify({
            'code': 500,
            'message': '删除监控配置失败',
            'data': None
        }), 500

@app.route('/api/v1/monitoring/<int:monitoring_id>/check', methods=['POST'])
@login_required
@moderate_rate_limit
@csrf_protect
def check_monitoring(monitoring_id):
    """立即检测证书"""
    try:
        # 权限检查
        monitoring_detail = domain_monitoring_service.get_monitoring_detail(monitoring_id)
        if not monitoring_detail['success']:
            return jsonify({
                'code': 404,
                'message': '监控配置不存在',
                'data': None
            }), 404

        monitoring_config = monitoring_detail['monitoring_config']
        if not g.user.is_admin() and monitoring_config.get('user_id') != g.user.id:
            return jsonify({
                'code': 403,
                'message': '权限不足',
                'data': None
            }), 403

        # 执行检测
        result = domain_monitoring_service.perform_immediate_check(monitoring_id)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': '证书检测完成',
                'data': result['check_result']
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"证书检测失败: {e}")
        return jsonify({
            'code': 500,
            'message': '证书检测失败',
            'data': None
        }), 500

@app.route('/api/v1/monitoring/<int:monitoring_id>/history', methods=['GET'])
@login_required
def get_monitoring_history(monitoring_id):
    """获取监控历史"""
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))

    try:
        # 权限检查
        monitoring_detail = domain_monitoring_service.get_monitoring_detail(monitoring_id)
        if not monitoring_detail['success']:
            return jsonify({
                'code': 404,
                'message': '监控配置不存在',
                'data': None
            }), 404

        monitoring_config = monitoring_detail['monitoring_config']
        if not g.user.is_admin() and monitoring_config.get('user_id') != g.user.id:
            return jsonify({
                'code': 403,
                'message': '权限不足',
                'data': None
            }), 403

        # 获取监控历史
        result = domain_monitoring_service.get_monitoring_history(
            monitoring_id, page, limit
        )

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'total': result['total'],
                    'page': page,
                    'limit': limit,
                    'items': result['history']
                }
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"获取监控历史失败: {e}")
        return jsonify({
            'code': 500,
            'message': '获取监控历史失败',
            'data': None
        }), 500

# ==========================================
# 告警管理API
# ==========================================

@app.route('/api/v1/alerts/rules', methods=['GET'])
@login_required
@admin_required
def get_alert_rules():
    """获取告警规则列表"""
    try:
        rules = alert_manager.get_rules()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'rules': [
                    {
                        'id': rule.id,
                        'name': rule.name,
                        'alert_type': rule.alert_type.value,
                        'severity': rule.severity.value,
                        'enabled': rule.enabled,
                        'conditions': rule.conditions,
                        'notification_providers': rule.notification_providers,
                        'notification_template': rule.notification_template,
                        'cooldown_minutes': rule.cooldown_minutes,
                        'created_at': rule.created_at.isoformat() if rule.created_at else None,
                        'updated_at': rule.updated_at.isoformat() if rule.updated_at else None
                    }
                    for rule in rules
                ]
            }
        })

    except Exception as e:
        logger.error(f"获取告警规则失败: {e}")
        return jsonify({
            'code': 500,
            'message': '获取告警规则失败',
            'data': None
        }), 500

@app.route('/api/v1/alerts/rules', methods=['POST'])
@login_required
@admin_required
@moderate_rate_limit
@csrf_protect
@validate_request_data({
    'name': {
        'required': True,
        'type': str,
        'min_length': 2,
        'max_length': 100
    },
    'alert_type': {
        'required': True,
        'type': str,
        'pattern': r'^(certificate_expiring|certificate_expired|certificate_renewal_failed|server_offline|system_error|quota_exceeded)$'
    },
    'severity': {
        'required': True,
        'type': str,
        'pattern': r'^(low|medium|high|critical)$'
    },
    'enabled': {
        'required': False,
        'type': bool
    },
    'conditions': {
        'required': True,
        'type': dict
    },
    'notification_providers': {
        'required': True,
        'type': list
    },
    'notification_template': {
        'required': True,
        'type': str,
        'max_length': 50
    },
    'cooldown_minutes': {
        'required': False,
        'type': int,
        'min_value': 1,
        'max_value': 10080  # 一周
    }
})
@sanitize_request_data()
def create_alert_rule():
    """创建告警规则"""
    data = request.get_json()

    try:
        # 生成规则ID
        import uuid
        rule_id = str(uuid.uuid4())

        # 创建告警规则
        rule = AlertRule(
            id=rule_id,
            name=data['name'],
            alert_type=AlertType(data['alert_type']),
            severity=AlertSeverity(data['severity']),
            enabled=data.get('enabled', True),
            conditions=data['conditions'],
            notification_providers=data['notification_providers'],
            notification_template=data['notification_template'],
            cooldown_minutes=data.get('cooldown_minutes', 60)
        )

        # 添加规则
        if alert_manager.add_rule(rule):
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'rule_id': rule_id,
                    'message': '告警规则创建成功'
                }
            })
        else:
            return jsonify({
                'code': 400,
                'message': '告警规则创建失败',
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"创建告警规则异常: {e}")
        return jsonify({
            'code': 500,
            'message': '创建告警规则失败',
            'data': None
        }), 500

@app.route('/api/v1/alerts/rules/<rule_id>', methods=['PUT'])
@login_required
@admin_required
@moderate_rate_limit
@csrf_protect
@validate_request_data({
    'name': {
        'required': False,
        'type': str,
        'min_length': 2,
        'max_length': 100
    },
    'enabled': {
        'required': False,
        'type': bool
    },
    'conditions': {
        'required': False,
        'type': dict
    },
    'notification_providers': {
        'required': False,
        'type': list
    },
    'cooldown_minutes': {
        'required': False,
        'type': int,
        'min_value': 1,
        'max_value': 10080
    }
})
@sanitize_request_data()
def update_alert_rule(rule_id):
    """更新告警规则"""
    data = request.get_json()

    try:
        if alert_manager.update_rule(rule_id, data):
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'message': '告警规则更新成功'
                }
            })
        else:
            return jsonify({
                'code': 404,
                'message': '告警规则不存在',
                'data': None
            }), 404

    except Exception as e:
        logger.error(f"更新告警规则异常: {e}")
        return jsonify({
            'code': 500,
            'message': '更新告警规则失败',
            'data': None
        }), 500

@app.route('/api/v1/alerts/rules/<rule_id>', methods=['DELETE'])
@login_required
@admin_required
@moderate_rate_limit
@csrf_protect
def delete_alert_rule(rule_id):
    """删除告警规则"""
    try:
        if alert_manager.delete_rule(rule_id):
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'message': '告警规则删除成功'
                }
            })
        else:
            return jsonify({
                'code': 404,
                'message': '告警规则不存在',
                'data': None
            }), 404

    except Exception as e:
        logger.error(f"删除告警规则异常: {e}")
        return jsonify({
            'code': 500,
            'message': '删除告警规则失败',
            'data': None
        }), 500

@app.route('/api/v1/alerts/active', methods=['GET'])
@login_required
def get_active_alerts():
    """获取活跃告警"""
    try:
        alerts = alert_manager.get_active_alerts()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'alerts': [
                    {
                        'id': alert.id,
                        'rule_id': alert.rule_id,
                        'alert_type': alert.alert_type.value,
                        'severity': alert.severity.value,
                        'title': alert.title,
                        'description': alert.description,
                        'context': alert.context,
                        'status': alert.status,
                        'created_at': alert.created_at.isoformat() if alert.created_at else None,
                        'last_sent_at': alert.last_sent_at.isoformat() if alert.last_sent_at else None
                    }
                    for alert in alerts
                ]
            }
        })

    except Exception as e:
        logger.error(f"获取活跃告警失败: {e}")
        return jsonify({
            'code': 500,
            'message': '获取活跃告警失败',
            'data': None
        }), 500

@app.route('/api/v1/alerts/<alert_id>/resolve', methods=['POST'])
@login_required
@admin_required
@csrf_protect
def resolve_alert(alert_id):
    """解决告警"""
    try:
        if alert_manager.resolve_alert(alert_id):
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'message': '告警已解决'
                }
            })
        else:
            return jsonify({
                'code': 404,
                'message': '告警不存在',
                'data': None
            }), 404

    except Exception as e:
        logger.error(f"解决告警异常: {e}")
        return jsonify({
            'code': 500,
            'message': '解决告警失败',
            'data': None
        }), 500

@app.route('/api/v1/alerts/history', methods=['GET'])
@login_required
@admin_required
def get_alert_history():
    """获取告警历史"""
    try:
        limit = request.args.get('limit', 100, type=int)
        alerts = alert_manager.get_alert_history(limit)

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'alerts': [
                    {
                        'id': alert.id,
                        'rule_id': alert.rule_id,
                        'alert_type': alert.alert_type.value,
                        'severity': alert.severity.value,
                        'title': alert.title,
                        'description': alert.description,
                        'status': alert.status,
                        'created_at': alert.created_at.isoformat() if alert.created_at else None,
                        'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
                    }
                    for alert in alerts
                ]
            }
        })

    except Exception as e:
        logger.error(f"获取告警历史失败: {e}")
        return jsonify({
            'code': 500,
            'message': '获取告警历史失败',
            'data': None
        }), 500

@app.route('/api/v1/notifications/providers', methods=['GET'])
@login_required
@admin_required
def get_notification_providers():
    """获取可用的通知提供商"""
    try:
        providers = notification_manager.get_available_providers()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'providers': providers
            }
        })

    except Exception as e:
        logger.error(f"获取通知提供商失败: {e}")
        return jsonify({
            'code': 500,
            'message': '获取通知提供商失败',
            'data': None
        }), 500

@app.route('/api/v1/notifications/test', methods=['POST'])
@login_required
@admin_required
@strict_rate_limit
@csrf_protect
@validate_request_data({
    'provider': {
        'required': True,
        'type': str,
        'max_length': 50
    },
    'recipient': {
        'required': True,
        'type': str,
        'max_length': 200
    },
    'message': {
        'required': False,
        'type': str,
        'max_length': 1000
    }
})
@sanitize_request_data()
def test_notification():
    """测试通知发送"""
    data = request.get_json()

    try:
        # 准备测试消息
        test_context = {
            'domain': 'test.example.com',
            'expires_at': '2024-01-01 00:00:00',
            'days_remaining': 7,
            'server_name': '测试服务器',
            'ca_type': 'Let\'s Encrypt'
        }

        # 如果指定了自定义消息，使用系统告警模板
        if data.get('message'):
            test_context.update({
                'alert_type': 'system_test',
                'severity': 'low',
                'alert_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'description': data['message']
            })
            template_name = 'system_alert'
        else:
            template_name = 'certificate_expiring'

        # 发送测试通知
        result = notification_manager.send_notification(
            template_name=template_name,
            context=test_context,
            providers=[data['provider']]
        )

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'message': '测试通知发送成功',
                    'result': result
                }
            })
        else:
            return jsonify({
                'code': 400,
                'message': '测试通知发送失败',
                'data': {
                    'errors': result.get('failed', [])
                }
            }), 400

    except Exception as e:
        logger.error(f"测试通知发送异常: {e}")
        return jsonify({
            'code': 500,
            'message': '测试通知发送失败',
            'data': None
        }), 500

@app.route('/api/v1/certificates/supported-cas', methods=['GET'])
@login_required
def get_supported_cas():
    """获取支持的CA列表"""
    try:
        cas = certificate_service.get_supported_cas()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'cas': cas
            }
        })

    except Exception as e:
        logger.error(f"获取CA列表异常: {e}")
        return jsonify({
            'code': 500,
            'message': '获取CA列表失败',
            'data': None
        }), 500

@app.route('/api/v1/certificates/sync', methods=['POST'])
@server_token_required
def sync_certificates():
    """客户端同步证书信息"""
    data = request.get_json()
    if not data or 'certificates' not in data:
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'data': None
        }), 400
    
    server = g.server
    certificates = data['certificates']
    
    synced = 0
    new_certs = 0
    updated_certs = 0
    
    for cert_data in certificates:
        domain = cert_data.get('domain')
        if not domain:
            continue
        
        # 查找现有证书
        cert = Certificate.get_by_domain(domain, server.id)
        
        if cert:
            # 更新现有证书
            cert.type = cert_data.get('type', cert.type)
            cert.expires_at = cert_data.get('expires_at', cert.expires_at)
            
            # 如果提供了证书内容，也更新
            if 'certificate' in cert_data:
                cert.certificate = cert_data['certificate']
            if 'private_key' in cert_data:
                cert.private_key = cert_data['private_key']
            
            # 更新状态
            if cert.is_expired():
                cert.status = 'expired'
            else:
                cert.status = 'valid'
            
            cert.save()
            updated_certs += 1
        else:
            # 创建新证书
            cert = Certificate.create(
                domain=domain,
                type=cert_data.get('type', 'single'),
                server_id=server.id,
                ca_type=cert_data.get('ca_type', 'letsencrypt'),
                status='valid',
                expires_at=cert_data.get('expires_at')
            )
            
            # 如果提供了证书内容，也更新
            if 'certificate' in cert_data:
                cert.certificate = cert_data['certificate']
            if 'private_key' in cert_data:
                cert.private_key = cert_data['private_key']
            
            cert.save()
            new_certs += 1
        
        # 添加部署记录
        if 'path' in cert_data:
            cert.add_deployment('nginx', cert_data['path'])
        
        synced += 1
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'synced': synced,
            'new': new_certs,
            'updated': updated_certs
        }
    })

@app.route('/api/v1/alerts', methods=['GET'])
@login_required
def get_alerts():
    """获取告警列表"""
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    status = request.args.get('status')
    alert_type = request.args.get('type')
    
    alerts, total = Alert.get_all(page, limit, status, alert_type)
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'total': total,
            'page': page,
            'limit': limit,
            'items': [alert.to_dict() for alert in alerts]
        }
    })

@app.route('/api/v1/alerts/<int:alert_id>', methods=['PUT'])
@login_required
def update_alert(alert_id):
    """更新告警状态"""
    alert = Alert.get_by_id(alert_id)
    if not alert:
        return jsonify({
            'code': 404,
            'message': '告警不存在',
            'data': None
        }), 404
    
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'data': None
        }), 400
    
    alert.status = data['status']
    alert.save()
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'id': alert.id,
            'status': alert.status,
            'updated_at': alert.updated_at
        }
    })

@app.route('/api/v1/settings', methods=['GET'])
@login_required
@admin_required
def get_settings():
    """获取系统设置"""
    db.connect()
    settings = db.fetchall("SELECT key, value FROM settings")
    db.close()
    
    settings_dict = {item['key']: item['value'] for item in settings}
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': settings_dict
    })

@app.route('/api/v1/settings', methods=['PUT'])
@login_required
@admin_required
def update_settings():
    """更新系统设置"""
    data = request.get_json()
    if not data:
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'data': None
        }), 400
    
    db.connect()
    now = datetime.datetime.now().isoformat()
    
    for key, value in data.items():
        # 检查设置是否存在
        setting = db.fetchone("SELECT * FROM settings WHERE key = ?", (key,))
        
        if setting:
            # 更新现有设置
            db.update('settings', {
                'value': str(value),
                'updated_at': now
            }, 'key = ?', (key,))
        else:
            # 创建新设置
            db.insert('settings', {
                'key': key,
                'value': str(value),
                'created_at': now,
                'updated_at': now
            })
    
    db.commit()
    
    # 获取更新后的设置
    settings = db.fetchall("SELECT key, value FROM settings")
    db.close()
    
    settings_dict = {item['key']: item['value'] for item in settings}
    settings_dict['updated_at'] = now
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': settings_dict
    })

@app.route('/api/v1/client/register', methods=['POST'])
@server_token_required
def client_register():
    """客户端首次注册"""
    data = request.get_json()
    if not data:
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'data': None
        }), 400
    
    server = g.server
    server.register(
        ip=data.get('ip', ''),
        os_type=data.get('os_type', ''),
        version=data.get('version', ''),
        hostname=data.get('hostname')
    )
    
    # 获取系统设置
    db.connect()
    settings = db.fetchall("SELECT key, value FROM settings")
    db.close()
    
    settings_dict = {item['key']: item['value'] for item in settings}
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'server_id': server.id,
            'name': server.name,
            'auto_renew': server.auto_renew,
            'settings': {
                'default_ca': settings_dict.get('default_ca', 'letsencrypt'),
                'renew_before_days': int(settings_dict.get('renew_before_days', 15))
            }
        }
    })

@app.route('/api/v1/client/tasks', methods=['GET'])
@server_token_required
def get_client_tasks():
    """获取客户端任务"""
    server = g.server
    
    # 查找需要续期的证书
    db.connect()
    
    # 获取续期天数设置
    setting = db.fetchone("SELECT value FROM settings WHERE key = 'renew_before_days'")
    renew_days = int(setting['value']) if setting else 15
    
    # 计算续期日期
    now = datetime.datetime.now()
    renew_date = (now + datetime.timedelta(days=renew_days)).isoformat()
    
    # 查找需要续期的证书
    sql = """
        SELECT id, domain, ca_type
        FROM certificates
        WHERE server_id = ? AND status = 'valid' AND expires_at <= ?
    """
    
    certificates = db.fetchall(sql, (server.id, renew_date))
    db.close()
    
    tasks = []
    for cert in certificates:
        tasks.append({
            'id': len(tasks) + 1,
            'type': 'renew',
            'certificate_id': cert['id'],
            'domain': cert['domain'],
            'params': {
                'ca_type': cert['ca_type'],
                'validation_method': 'dns'
            }
        })
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'tasks': tasks
        }
    })

@app.route('/api/v1/client/tasks/<int:task_id>', methods=['PUT'])
@server_token_required
def update_client_task(task_id):
    """更新客户端任务状态"""
    data = request.get_json()
    if not data or 'status' not in data:
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'data': None
        }), 400
    
    status = data['status']
    result = data.get('result', {})
    
    # 如果任务完成并成功，更新证书信息
    if status == 'completed' and result.get('success') and 'certificate' in result:
        cert_data = result['certificate']
        cert_id = cert_data.get('id')
        
        if cert_id:
            cert = Certificate.get_by_id(cert_id)
            if cert and cert.server_id == g.server.id:
                cert.status = 'valid'
                cert.expires_at = cert_data.get('expires_at', cert.expires_at)
                
                # 如果提供了证书内容，也更新
                if 'certificate' in cert_data:
                    cert.certificate = cert_data['certificate']
                if 'private_key' in cert_data:
                    cert.private_key = cert_data['private_key']
                
                cert.save()
                
                # 添加部署记录
                if 'path' in cert_data:
                    cert.add_deployment('nginx', cert_data['path'])
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': None
    })

# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'code': 404,
        'message': '请求的资源不存在',
        'data': None
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'code': 500,
        'message': '服务器内部错误',
        'data': None
    }), 500

# 健康检查和监控端点
@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    try:
        # 检查数据库连接
        db.connect()
        db.fetchone('SELECT 1')
        db_status = 'healthy'
        db.close()
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'

    # 检查系统资源
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        system_status = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent
        }
    except ImportError:
        system_status = 'psutil not available'
    except Exception as e:
        system_status = f'error: {str(e)}'

    # 检查服务状态
    try:
        # 检查告警管理器
        alert_status = 'healthy' if alert_manager else 'not initialized'

        # 检查通知管理器
        notification_status = 'healthy' if notification_manager else 'not initialized'

        # 检查证书服务
        cert_service_status = 'healthy' if certificate_service else 'not initialized'

    except Exception as e:
        alert_status = notification_status = cert_service_status = f'error: {str(e)}'

    health_data = {
        'status': 'healthy' if db_status == 'healthy' else 'unhealthy',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'services': {
            'database': db_status,
            'alert_manager': alert_status,
            'notification_manager': notification_status,
            'certificate_service': cert_service_status
        },
        'system': system_status
    }

    status_code = 200 if health_data['status'] == 'healthy' else 503

    return jsonify({
        'code': status_code,
        'message': health_data['status'],
        'data': health_data
    }), status_code

@app.route('/ready', methods=['GET'])
def readiness_check():
    """就绪检查端点"""
    try:
        # 检查数据库是否就绪
        db.connect()
        db.fetchone('SELECT COUNT(*) FROM users')
        db.close()

        # 检查关键服务是否就绪
        ready = (
            alert_manager is not None and
            notification_manager is not None and
            certificate_service is not None
        )

        if ready:
            return jsonify({
                'code': 200,
                'message': 'ready',
                'data': {
                    'status': 'ready',
                    'timestamp': datetime.datetime.utcnow().isoformat()
                }
            }), 200
        else:
            return jsonify({
                'code': 503,
                'message': 'not ready',
                'data': {
                    'status': 'not ready',
                    'timestamp': datetime.datetime.utcnow().isoformat()
                }
            }), 503

    except Exception as e:
        return jsonify({
            'code': 503,
            'message': 'not ready',
            'data': {
                'status': 'not ready',
                'error': str(e),
                'timestamp': datetime.datetime.utcnow().isoformat()
            }
        }), 503

# SSL证书监控配置API端点
@app.route('/api/v1/certificates/<int:certificate_id>/monitoring', methods=['GET'])
@login_required
def get_certificate_monitoring_config(certificate_id):
    """获取证书监控配置"""
    try:
        result = monitoring_service.get_monitoring_config(certificate_id)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result['config']
            })
        else:
            return jsonify({
                'code': 404,
                'message': result['error'],
                'data': None
            }), 404

    except Exception as e:
        logger.error(f"获取监控配置失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/<int:certificate_id>/monitoring', methods=['PUT'])
@login_required
@moderate_rate_limit
@csrf_protect
@validate_request_data({
    'monitoring_enabled': {
        'required': False,
        'type': bool
    },
    'monitoring_frequency': {
        'required': False,
        'type': int,
        'min_value': 300,
        'max_value': 86400
    },
    'alert_enabled': {
        'required': False,
        'type': bool
    }
})
def update_certificate_monitoring_config(certificate_id):
    """更新证书监控配置"""
    try:
        data = request.get_json()
        result = monitoring_service.update_monitoring_config(certificate_id, data)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': result['message'],
                'data': result['config']
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"更新监控配置失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/monitoring/batch', methods=['PUT'])
@login_required
@admin_required
@moderate_rate_limit
@csrf_protect
@validate_request_data({
    'certificate_ids': {
        'required': True,
        'type': list,
        'min_length': 1,
        'max_length': 100
    },
    'monitoring_enabled': {
        'required': False,
        'type': bool
    },
    'monitoring_frequency': {
        'required': False,
        'type': int,
        'min_value': 300,
        'max_value': 86400
    },
    'alert_enabled': {
        'required': False,
        'type': bool
    }
})
def batch_update_monitoring_config():
    """批量更新证书监控配置"""
    try:
        data = request.get_json()
        certificate_ids = data['certificate_ids']
        config = {k: v for k, v in data.items() if k != 'certificate_ids'}

        result = monitoring_service.batch_update_monitoring(certificate_ids, config)

        return jsonify({
            'code': 200,
            'message': result['message'],
            'data': result['details']
        })

    except Exception as e:
        logger.error(f"批量更新监控配置失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/monitoring/statistics', methods=['GET'])
@login_required
def get_monitoring_statistics():
    """获取监控统计信息"""
    try:
        result = monitoring_service.get_monitoring_statistics()

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result['statistics']
            })
        else:
            return jsonify({
                'code': 500,
                'message': result['error'],
                'data': None
            }), 500

    except Exception as e:
        logger.error(f"获取监控统计失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/monitoring/enabled', methods=['GET'])
@login_required
def get_monitoring_enabled_certificates():
    """获取启用监控的证书列表"""
    try:
        enabled = request.args.get('enabled', 'true').lower() == 'true'
        result = monitoring_service.get_certificates_by_monitoring_status(enabled)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'certificates': result['certificates'],
                    'count': result['count']
                }
            })
        else:
            return jsonify({
                'code': 500,
                'message': result['error'],
                'data': None
            }), 500

    except Exception as e:
        logger.error(f"获取监控证书列表失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

# SSL证书域名监控API端点
@app.route('/api/v1/certificates/<int:certificate_id>/domain-status', methods=['GET'])
@login_required
def get_certificate_domain_status(certificate_id):
    """获取证书域名监控状态"""
    try:
        # 获取证书信息
        certificate = Certificate.get_by_id(certificate_id)
        if not certificate:
            return jsonify({
                'code': 404,
                'message': '证书不存在',
                'data': None
            }), 404

        # 构建域名状态信息
        domain_status = {
            'certificate_id': certificate_id,
            'domain': certificate.domain,
            'dns_status': getattr(certificate, 'dns_status', None),
            'dns_response_time': getattr(certificate, 'dns_response_time', None),
            'domain_reachable': getattr(certificate, 'domain_reachable', None),
            'http_status_code': getattr(certificate, 'http_status_code', None),
            'last_dns_check': getattr(certificate, 'last_dns_check', None),
            'last_reachability_check': getattr(certificate, 'last_reachability_check', None)
        }

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': domain_status
        })

    except Exception as e:
        logger.error(f"获取域名状态失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/<int:certificate_id>/check-domain', methods=['POST'])
@login_required
@moderate_rate_limit
@csrf_protect
def check_certificate_domain(certificate_id):
    """手动触发证书域名检查"""
    try:
        result = domain_monitoring_service.perform_comprehensive_domain_check(certificate_id)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': '域名检查完成',
                'data': result
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"域名检查失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/batch-check-domains', methods=['POST'])
@login_required
@admin_required
@moderate_rate_limit
@csrf_protect
@validate_request_data({
    'certificate_ids': {
        'required': True,
        'type': list,
        'min_length': 1,
        'max_length': 50
    },
    'max_concurrent': {
        'required': False,
        'type': int,
        'min_value': 1,
        'max_value': 10
    }
})
def batch_check_certificate_domains():
    """批量检查证书域名"""
    try:
        data = request.get_json()
        certificate_ids = data['certificate_ids']
        max_concurrent = data.get('max_concurrent', 5)

        result = domain_monitoring_service.batch_check_domains(certificate_ids, max_concurrent)

        return jsonify({
            'code': 200,
            'message': '批量域名检查完成',
            'data': result
        })

    except Exception as e:
        logger.error(f"批量域名检查失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/domain-monitoring/statistics', methods=['GET'])
@login_required
def get_domain_monitoring_statistics():
    """获取域名监控统计信息"""
    try:
        result = domain_monitoring_service.get_domain_monitoring_statistics()

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result['statistics']
            })
        else:
            return jsonify({
                'code': 500,
                'message': result['error'],
                'data': None
            }), 500

    except Exception as e:
        logger.error(f"获取域名监控统计失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/<int:certificate_id>/domain-history', methods=['GET'])
@login_required
def get_certificate_domain_history(certificate_id):
    """获取证书域名监控历史"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        check_type = request.args.get('check_type', None)

        # 构建查询条件
        where_conditions = ['certificate_id = ?']
        params = [certificate_id]

        if check_type:
            where_conditions.append('check_type = ?')
            params.append(check_type)

        where_clause = ' AND '.join(where_conditions)

        # 获取总数
        count_query = f"SELECT COUNT(*) as count FROM domain_monitoring_history WHERE {where_clause}"
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        # 获取分页数据
        offset = (page - 1) * per_page
        data_query = f"""
            SELECT * FROM domain_monitoring_history
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([per_page, offset])

        cursor.execute(data_query, params)
        history_records = []

        for row in cursor.fetchall():
            history_records.append({
                'id': row[0],
                'certificate_id': row[1],
                'check_type': row[2],
                'status': row[3],
                'response_time': row[4],
                'details': row[5],
                'error_message': row[6],
                'created_at': row[7]
            })

        conn.close()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'history': history_records,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }
        })

    except Exception as e:
        logger.error(f"获取域名监控历史失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

# SSL证书端口监控API端点
@app.route('/api/v1/certificates/<int:certificate_id>/port-status', methods=['GET'])
@login_required
def get_certificate_port_status(certificate_id):
    """获取证书端口监控状态"""
    try:
        # 获取证书信息
        certificate = Certificate.get_by_id(certificate_id)
        if not certificate:
            return jsonify({
                'code': 404,
                'message': '证书不存在',
                'data': None
            }), 404

        # 构建端口状态信息
        port_status = {
            'certificate_id': certificate_id,
            'domain': certificate.domain,
            'monitored_ports': getattr(certificate, 'monitored_ports', None),
            'ssl_handshake_time': getattr(certificate, 'ssl_handshake_time', None),
            'tls_version': getattr(certificate, 'tls_version', None),
            'cipher_suite': getattr(certificate, 'cipher_suite', None),
            'certificate_chain_valid': getattr(certificate, 'certificate_chain_valid', None),
            'http_redirect_status': getattr(certificate, 'http_redirect_status', None),
            'last_port_check': getattr(certificate, 'last_port_check', None)
        }

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': port_status
        })

    except Exception as e:
        logger.error(f"获取端口状态失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/<int:certificate_id>/check-ports', methods=['POST'])
@login_required
@moderate_rate_limit
@csrf_protect
def check_certificate_ports(certificate_id):
    """手动触发证书端口检查"""
    try:
        result = port_monitoring_service.perform_comprehensive_port_check(certificate_id)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': '端口检查完成',
                'data': result
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"端口检查失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/<int:certificate_id>/configure-ports', methods=['POST'])
@login_required
@moderate_rate_limit
@csrf_protect
@validate_request_data({
    'ports': {
        'required': True,
        'type': list,
        'min_length': 1,
        'max_length': 20
    }
})
def configure_certificate_ports(certificate_id):
    """配置证书监控端口"""
    try:
        data = request.get_json()
        ports = data['ports']

        # 验证端口格式
        try:
            ports = [int(port) for port in ports]
        except (ValueError, TypeError):
            return jsonify({
                'code': 400,
                'message': '端口必须为数字',
                'data': None
            }), 400

        result = port_monitoring_service.configure_monitored_ports(certificate_id, ports)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': result['message'],
                'data': {'monitored_ports': result['monitored_ports']}
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"配置监控端口失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/port-monitoring/security-report', methods=['GET'])
@login_required
def get_port_security_report():
    """生成端口安全评估报告"""
    try:
        certificate_id = request.args.get('certificate_id', type=int)
        result = port_monitoring_service.generate_security_report(certificate_id)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result['report']
            })
        else:
            return jsonify({
                'code': 500,
                'message': result['error'],
                'data': None
            }), 500

    except Exception as e:
        logger.error(f"生成安全报告失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/batch-check-ports', methods=['POST'])
@login_required
@admin_required
@moderate_rate_limit
@csrf_protect
@validate_request_data({
    'certificate_ids': {
        'required': True,
        'type': list,
        'min_length': 1,
        'max_length': 30
    },
    'max_concurrent': {
        'required': False,
        'type': int,
        'min_value': 1,
        'max_value': 5
    }
})
def batch_check_certificate_ports():
    """批量检查证书端口"""
    try:
        data = request.get_json()
        certificate_ids = data['certificate_ids']
        max_concurrent = data.get('max_concurrent', 3)

        result = port_monitoring_service.batch_check_ports(certificate_ids, max_concurrent)

        return jsonify({
            'code': 200,
            'message': '批量端口检查完成',
            'data': result
        })

    except Exception as e:
        logger.error(f"批量端口检查失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/port-monitoring/statistics', methods=['GET'])
@login_required
def get_port_monitoring_statistics():
    """获取端口监控统计信息"""
    try:
        result = port_monitoring_service.get_port_monitoring_statistics()

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result['statistics']
            })
        else:
            return jsonify({
                'code': 500,
                'message': result['error'],
                'data': None
            }), 500

    except Exception as e:
        logger.error(f"获取端口监控统计失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/<int:certificate_id>/port-history', methods=['GET'])
@login_required
def get_certificate_port_history(certificate_id):
    """获取证书端口监控历史"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        port = request.args.get('port', type=int)
        check_type = request.args.get('check_type', None)

        # 构建查询条件
        where_conditions = ['certificate_id = ?']
        params = [certificate_id]

        if port:
            where_conditions.append('port = ?')
            params.append(port)

        if check_type:
            where_conditions.append('check_type = ?')
            params.append(check_type)

        where_clause = ' AND '.join(where_conditions)

        # 获取总数
        count_query = f"SELECT COUNT(*) as count FROM port_monitoring_history WHERE {where_clause}"
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        # 获取分页数据
        offset = (page - 1) * per_page
        data_query = f"""
            SELECT * FROM port_monitoring_history
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([per_page, offset])

        cursor.execute(data_query, params)
        history_records = []

        for row in cursor.fetchall():
            history_records.append({
                'id': row[0],
                'certificate_id': row[1],
                'port': row[2],
                'check_type': row[3],
                'status': row[4],
                'handshake_time': row[5],
                'tls_version': row[6],
                'cipher_suite': row[7],
                'security_grade': row[8],
                'details': row[9],
                'error_message': row[10],
                'created_at': row[11]
            })

        conn.close()

        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'history': history_records,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }
        })

    except Exception as e:
        logger.error(f"获取端口监控历史失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

# SSL证书操作API端点
@app.route('/api/v1/certificates/<int:certificate_id>/manual-check', methods=['POST'])
@login_required
@moderate_rate_limit
@csrf_protect
@validate_request_data({
    'check_types': {
        'required': False,
        'type': list,
        'allowed_values': ['domain', 'port', 'ssl']
    }
})
def manual_check_certificate(certificate_id):
    """手动触发证书检测"""
    try:
        data = request.get_json() or {}
        check_types = data.get('check_types', ['domain', 'port', 'ssl'])

        result = certificate_operations_service.manual_certificate_check(certificate_id, check_types)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': result['message'],
                'data': {
                    'task_id': result['task_id'],
                    'estimated_duration': result.get('estimated_duration')
                }
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"手动检测失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/<int:certificate_id>/manual-renew', methods=['POST'])
@login_required
@admin_required
@moderate_rate_limit
@csrf_protect
@validate_request_data({
    'force': {
        'required': False,
        'type': bool
    }
})
def manual_renew_certificate(certificate_id):
    """手动续期证书"""
    try:
        data = request.get_json() or {}
        force = data.get('force', False)

        result = certificate_operations_service.renew_certificate(certificate_id, force)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': result['message'],
                'data': {
                    'new_expires_at': result.get('new_expires_at'),
                    'renewal_details': result.get('renewal_details')
                }
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': result.get('details')
            }), 400

    except Exception as e:
        logger.error(f"证书续期失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/import', methods=['POST'])
@login_required
@admin_required
@strict_rate_limit
@csrf_protect
def import_certificates():
    """批量导入证书"""
    try:
        # 检查文件上传
        if 'file' not in request.files:
            return jsonify({
                'code': 400,
                'message': '请上传CSV文件',
                'data': None
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'code': 400,
                'message': '请选择文件',
                'data': None
            }), 400

        if not file.filename.lower().endswith('.csv'):
            return jsonify({
                'code': 400,
                'message': '只支持CSV文件格式',
                'data': None
            }), 400

        # 读取文件内容
        csv_content = file.read().decode('utf-8-sig')
        user_id = session.get('user_id', 1)  # 获取当前用户ID

        result = certificate_operations_service.import_certificates_from_csv(csv_content, user_id)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': '证书导入完成',
                'data': result['import_results']
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': result.get('invalid_rows')
            }), 400

    except Exception as e:
        logger.error(f"证书导入失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/export', methods=['GET'])
@login_required
def export_certificates():
    """导出证书数据"""
    try:
        # 获取过滤参数
        filters = {}
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        if request.args.get('expires_before'):
            filters['expires_before'] = request.args.get('expires_before')
        if request.args.get('domain_pattern'):
            filters['domain_pattern'] = request.args.get('domain_pattern')

        result = certificate_operations_service.export_certificates_to_csv(filters)

        if result['success']:
            # 创建响应
            response = make_response(result['csv_content'])
            response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
            response.headers['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'

            return response
        else:
            return jsonify({
                'code': 500,
                'message': result['error'],
                'data': None
            }), 500

    except Exception as e:
        logger.error(f"证书导出失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/discovery-scan', methods=['POST'])
@login_required
@admin_required
@strict_rate_limit
@csrf_protect
@validate_request_data({
    'ip_ranges': {
        'required': True,
        'type': list,
        'min_length': 1,
        'max_length': 10
    },
    'ports': {
        'required': False,
        'type': list,
        'max_length': 10
    }
})
def discovery_scan():
    """网络发现扫描"""
    try:
        data = request.get_json()
        ip_ranges = data['ip_ranges']
        ports = data.get('ports', [443, 8443, 9443])

        result = certificate_operations_service.import_from_discovery(ip_ranges, ports)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': result['message'],
                'data': {
                    'task_id': result['task_id'],
                    'total_targets': result['total_targets']
                }
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"发现扫描失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/<int:certificate_id>/operation-history', methods=['GET'])
@login_required
def get_certificate_operation_history(certificate_id):
    """获取证书操作历史"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)

        result = certificate_operations_service.get_operation_history(certificate_id, page, per_page)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'operations': result['operations'],
                    'pagination': result['pagination']
                }
            })
        else:
            return jsonify({
                'code': 500,
                'message': result['error'],
                'data': None
            }), 500

    except Exception as e:
        logger.error(f"获取操作历史失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/certificates/batch-operations', methods=['POST'])
@login_required
@admin_required
@strict_rate_limit
@csrf_protect
@validate_request_data({
    'operation_type': {
        'required': True,
        'type': str,
        'allowed_values': ['check', 'renew', 'delete']
    },
    'certificate_ids': {
        'required': True,
        'type': list,
        'min_length': 1,
        'max_length': 50
    },
    'options': {
        'required': False,
        'type': dict
    }
})
def batch_operations():
    """批量操作"""
    try:
        data = request.get_json()
        operation_type = data['operation_type']
        certificate_ids = data['certificate_ids']
        options = data.get('options', {})

        result = certificate_operations_service.batch_operations(operation_type, certificate_ids, options)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': result['message'],
                'data': {
                    'task_id': result['task_id'],
                    'total_count': result['total_count']
                }
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"批量操作失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/tasks/<task_id>/status', methods=['GET'])
@login_required
def get_task_status(task_id):
    """获取任务状态"""
    try:
        result = certificate_operations_service.get_task_status(task_id)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': result['task_info']
            })
        else:
            return jsonify({
                'code': 404,
                'message': result['error'],
                'data': None
            }), 404

    except Exception as e:
        logger.error(f"获取任务状态失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/api/v1/tasks/<task_id>/cancel', methods=['POST'])
@login_required
@csrf_protect
def cancel_task(task_id):
    """取消任务"""
    try:
        result = certificate_operations_service.cancel_task(task_id)

        if result['success']:
            return jsonify({
                'code': 200,
                'message': result['message'],
                'data': None
            })
        else:
            return jsonify({
                'code': 400,
                'message': result['error'],
                'data': None
            }), 400

    except Exception as e:
        logger.error(f"取消任务失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus监控指标端点"""
    try:
        # 获取基本统计信息
        total_users = User.count()
        total_servers = Server.count()
        total_certificates = Certificate.count()
        active_certificates = Certificate.count_by_status('valid')
        expired_certificates = Certificate.count_by_status('expired')

        # 获取系统指标
        try:
            import psutil
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
        except ImportError:
            cpu_percent = memory = disk = None

        # 生成Prometheus格式的指标
        metrics_data = []

        # 应用指标
        metrics_data.append(f'ssl_manager_users_total {total_users}')
        metrics_data.append(f'ssl_manager_servers_total {total_servers}')
        metrics_data.append(f'ssl_manager_certificates_total {total_certificates}')
        metrics_data.append(f'ssl_manager_certificates_active {active_certificates}')
        metrics_data.append(f'ssl_manager_certificates_expired {expired_certificates}')

        # 系统指标
        if cpu_percent is not None:
            metrics_data.append(f'ssl_manager_cpu_percent {cpu_percent}')
        if memory is not None:
            metrics_data.append(f'ssl_manager_memory_percent {memory.percent}')
            metrics_data.append(f'ssl_manager_memory_used_bytes {memory.used}')
            metrics_data.append(f'ssl_manager_memory_total_bytes {memory.total}')
        if disk is not None:
            metrics_data.append(f'ssl_manager_disk_percent {disk.percent}')
            metrics_data.append(f'ssl_manager_disk_used_bytes {disk.used}')
            metrics_data.append(f'ssl_manager_disk_total_bytes {disk.total}')

        # 添加时间戳
        import time
        timestamp = int(time.time() * 1000)
        metrics_data = [f'{metric} {timestamp}' for metric in metrics_data]

        return '\n'.join(metrics_data) + '\n', 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        return f'# Error generating metrics: {str(e)}\n', 500, {'Content-Type': 'text/plain; charset=utf-8'}

# 启动应用
if __name__ == '__main__':
    # 启动域名监控调度器
    try:
        domain_monitoring_scheduler.start()
        logger.info("域名监控调度器启动成功")
    except Exception as e:
        logger.error(f"域名监控调度器启动失败: {str(e)}")

    # 启动应用
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'

    logger.info(f"启动SSL证书管理器后端服务，端口: {port}, 调试模式: {debug}")

    try:
        app.run(host='0.0.0.0', port=port, debug=debug)
    finally:
        # 应用关闭时停止调度器
        try:
            domain_monitoring_scheduler.stop()
            logger.info("域名监控调度器已停止")
        except Exception as e:
            logger.error(f"停止域名监控调度器失败: {str(e)}")
