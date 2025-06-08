"""
认证API测试模块
测试用户登录、注册、令牌刷新等认证相关功能
"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend/src'))

from app import app
from models.database import db
from models.user import User


class TestAuthAPI:
    """认证API测试类"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret_key'
        
        with app.test_client() as client:
            with app.app_context():
                # 初始化测试数据库
                db.connect()
                db.create_tables()
                
                # 创建测试用户
                test_user = User.create(
                    username='testuser',
                    email='test@example.com',
                    password='testpass123',
                    role='user'
                )
                
                test_admin = User.create(
                    username='admin',
                    email='admin@example.com',
                    password='adminpass123',
                    role='admin'
                )
                
                db.close()
                
                yield client
                
                # 清理测试数据
                db.connect()
                db.execute("DELETE FROM users")
                db.commit()
                db.close()
    
    def test_login_success(self, client):
        """测试成功登录"""
        response = client.post('/api/v1/auth/login', 
                             json={
                                 'username': 'testuser',
                                 'password': 'testpass123'
                             })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 200
        assert 'token' in data['data']
        assert 'user' in data['data']
        assert data['data']['user']['username'] == 'testuser'
    
    def test_login_invalid_credentials(self, client):
        """测试无效凭据登录"""
        response = client.post('/api/v1/auth/login',
                             json={
                                 'username': 'testuser',
                                 'password': 'wrongpassword'
                             })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['code'] == 401
        assert '用户名或密码错误' in data['message']
    
    def test_login_missing_parameters(self, client):
        """测试缺少参数的登录请求"""
        # 缺少密码
        response = client.post('/api/v1/auth/login',
                             json={'username': 'testuser'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 400
    
    def test_login_invalid_username_format(self, client):
        """测试无效用户名格式"""
        response = client.post('/api/v1/auth/login',
                             json={
                                 'username': 'a',  # 太短
                                 'password': 'testpass123'
                             })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 400
    
    def test_refresh_token_success(self, client):
        """测试成功刷新令牌"""
        # 先登录获取令牌
        login_response = client.post('/api/v1/auth/login',
                                   json={
                                       'username': 'testuser',
                                       'password': 'testpass123'
                                   })
        
        login_data = json.loads(login_response.data)
        token = login_data['data']['token']
        
        # 刷新令牌
        response = client.post('/api/v1/auth/refresh',
                             headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 200
        assert 'token' in data['data']
    
    def test_logout_success(self, client):
        """测试成功登出"""
        # 先登录获取令牌
        login_response = client.post('/api/v1/auth/login',
                                   json={
                                       'username': 'testuser',
                                       'password': 'testpass123'
                                   })
        
        login_data = json.loads(login_response.data)
        token = login_data['data']['token']
        
        # 登出
        response = client.post('/api/v1/auth/logout',
                             headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 200
    
    def test_input_sanitization(self, client):
        """测试输入数据清理"""
        # 测试包含HTML标签的输入
        response = client.post('/api/v1/auth/login',
                             json={
                                 'username': '<script>alert("xss")</script>testuser',
                                 'password': 'testpass123'
                             })
        
        # 应该返回400错误，因为用户名格式不正确
        assert response.status_code == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
