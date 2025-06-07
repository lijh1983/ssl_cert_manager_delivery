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
from models.database import db, init_db
from models.user import User
from models.server import Server
from models.certificate import Certificate
from models.alert import Alert

# 初始化Flask应用
app = Flask(__name__)

# 配置
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')
app.config['JWT_EXPIRATION'] = 3600  # Token有效期1小时

# 初始化数据库
init_db()

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
def login():
    """用户登录"""
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'data': None
        }), 400
    
    user = User.authenticate(data['username'], data['password'])
    if not user:
        return jsonify({
            'code': 401,
            'message': '用户名或密码错误',
            'data': None
        }), 401
    
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
def create_user():
    """创建用户"""
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data or 'email' not in data:
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
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
def create_server():
    """创建服务器"""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'data': None
        }), 400
    
    server = Server.create(
        name=data['name'],
        user_id=g.user.id,
        auto_renew=data.get('auto_renew', True)
    )
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'id': server.id,
            'name': server.name,
            'token': server.token,
            'auto_renew': server.auto_renew,
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
    
    server.save()
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'id': server.id,
            'name': server.name,
            'auto_renew': server.auto_renew,
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
def create_certificate():
    """手动申请证书"""
    data = request.get_json()
    if not data or 'domain' not in data or 'server_id' not in data:
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'data': None
        }), 400
    
    server_id = data['server_id']
    server = Server.get_by_id(server_id)
    if not server:
        return jsonify({
            'code': 404,
            'message': '服务器不存在',
            'data': None
        }), 404
    
    # 普通用户只能为自己的服务器申请证书
    if not g.user.is_admin() and server.user_id != g.user.id:
        return jsonify({
            'code': 403,
            'message': '权限不足',
            'data': None
        }), 403
    
    # 创建证书记录
    cert = Certificate.create(
        domain=data['domain'],
        type=data.get('type', 'single'),
        server_id=server_id,
        ca_type=data.get('ca_type', 'letsencrypt')
    )
    
    # 返回验证信息
    validation_method = data.get('validation_method', 'dns')
    validation_info = {
        'type': validation_method,
        'record': '_acme-challenge',
        'value': f'randomvalue{secrets.randbelow(1000)}',
        'instructions': f"请添加以下DNS记录：_acme-challenge.{data['domain']} TXT {validation_info['value']}"
    }
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'id': cert.id,
            'domain': cert.domain,
            'type': cert.type,
            'status': cert.status,
            'server_id': cert.server_id,
            'ca_type': cert.ca_type,
            'validation': validation_info
        }
    })

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
def renew_certificate(cert_id):
    """手动续期证书"""
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
    
    # 普通用户只能续期自己的服务器上的证书
    if not g.user.is_admin() and server.user_id != g.user.id:
        return jsonify({
            'code': 403,
            'message': '权限不足',
            'data': None
        }), 403
    
    # 设置证书状态为续期中
    cert.renew()
    
    return jsonify({
        'code': 200,
        'message': 'success',
        'data': {
            'id': cert.id,
            'domain': cert.domain,
            'status': cert.status,
            'message': '证书续期任务已提交'
        }
    })

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

# 启动应用
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
