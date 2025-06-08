"""
服务器API测试模块
测试服务器管理相关的API功能
"""

import pytest
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend/src'))

from app import app
from models.database import db
from models.user import User
from models.server import Server


class TestServerAPI:
    """服务器API测试类"""
    
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
                self.test_user = User.create(
                    username='testuser',
                    email='test@example.com',
                    password='testpass123',
                    role='user'
                )
                
                self.test_admin = User.create(
                    username='admin',
                    email='admin@example.com',
                    password='adminpass123',
                    role='admin'
                )
                
                db.close()
                
                yield client
                
                # 清理测试数据
                db.connect()
                db.execute("DELETE FROM servers")
                db.execute("DELETE FROM users")
                db.commit()
                db.close()
    
    def get_auth_token(self, client, username='testuser', password='testpass123'):
        """获取认证令牌"""
        response = client.post('/api/v1/auth/login',
                             json={
                                 'username': username,
                                 'password': password
                             })
        data = json.loads(response.data)
        return data['data']['token']
    
    def test_create_server_success(self, client):
        """测试成功创建服务器"""
        token = self.get_auth_token(client)
        
        response = client.post('/api/v1/servers',
                             json={
                                 'name': 'test-server-01',
                                 'auto_renew': True
                             },
                             headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data']['name'] == 'test-server-01'
        assert 'token' in data['data']
        assert 'install_command' in data['data']
    
    def test_create_server_invalid_name(self, client):
        """测试无效服务器名称"""
        token = self.get_auth_token(client)
        
        # 测试太短的名称
        response = client.post('/api/v1/servers',
                             json={'name': 'a'},
                             headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['code'] == 400
    
    def test_create_server_without_auth(self, client):
        """测试未认证的服务器创建"""
        response = client.post('/api/v1/servers',
                             json={'name': 'test-server'})
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['code'] == 401
    
    def test_get_servers_list(self, client):
        """测试获取服务器列表"""
        token = self.get_auth_token(client)
        
        # 先创建一个服务器
        client.post('/api/v1/servers',
                   json={'name': 'test-server-01'},
                   headers={'Authorization': f'Bearer {token}'})
        
        # 获取服务器列表
        response = client.get('/api/v1/servers',
                            headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 200
        assert 'items' in data['data']
        assert len(data['data']['items']) >= 1
    
    def test_get_server_detail(self, client):
        """测试获取服务器详情"""
        token = self.get_auth_token(client)
        
        # 先创建一个服务器
        create_response = client.post('/api/v1/servers',
                                    json={'name': 'test-server-01'},
                                    headers={'Authorization': f'Bearer {token}'})
        
        create_data = json.loads(create_response.data)
        server_id = create_data['data']['id']
        
        # 获取服务器详情
        response = client.get(f'/api/v1/servers/{server_id}',
                            headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data']['name'] == 'test-server-01'
    
    def test_update_server(self, client):
        """测试更新服务器信息"""
        token = self.get_auth_token(client)
        
        # 先创建一个服务器
        create_response = client.post('/api/v1/servers',
                                    json={'name': 'test-server-01'},
                                    headers={'Authorization': f'Bearer {token}'})
        
        create_data = json.loads(create_response.data)
        server_id = create_data['data']['id']
        
        # 更新服务器信息
        response = client.put(f'/api/v1/servers/{server_id}',
                            json={
                                'name': 'updated-server',
                                'auto_renew': False
                            },
                            headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 200
        assert data['data']['name'] == 'updated-server'
        assert data['data']['auto_renew'] == False
    
    def test_delete_server(self, client):
        """测试删除服务器"""
        token = self.get_auth_token(client)
        
        # 先创建一个服务器
        create_response = client.post('/api/v1/servers',
                                    json={'name': 'test-server-01'},
                                    headers={'Authorization': f'Bearer {token}'})
        
        create_data = json.loads(create_response.data)
        server_id = create_data['data']['id']
        
        # 删除服务器
        response = client.delete(f'/api/v1/servers/{server_id}',
                               headers={'Authorization': f'Bearer {token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 200
        
        # 验证服务器已被删除
        get_response = client.get(f'/api/v1/servers/{server_id}',
                                headers={'Authorization': f'Bearer {token}'})
        assert get_response.status_code == 404
    
    def test_server_permission_control(self, client):
        """测试服务器权限控制"""
        # 用户A创建服务器
        token_a = self.get_auth_token(client, 'testuser', 'testpass123')
        
        create_response = client.post('/api/v1/servers',
                                    json={'name': 'user-a-server'},
                                    headers={'Authorization': f'Bearer {token_a}'})
        
        create_data = json.loads(create_response.data)
        server_id = create_data['data']['id']
        
        # 创建另一个用户B
        admin_token = self.get_auth_token(client, 'admin', 'adminpass123')
        
        client.post('/api/v1/users',
                   json={
                       'username': 'userb',
                       'email': 'userb@example.com',
                       'password': 'userpass123'
                   },
                   headers={'Authorization': f'Bearer {admin_token}'})
        
        # 用户B尝试访问用户A的服务器
        token_b = self.get_auth_token(client, 'userb', 'userpass123')
        
        response = client.get(f'/api/v1/servers/{server_id}',
                            headers={'Authorization': f'Bearer {token_b}'})
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['code'] == 403
        assert '权限不足' in data['message']
    
    def test_admin_can_view_all_servers(self, client):
        """测试管理员可以查看所有服务器"""
        # 普通用户创建服务器
        user_token = self.get_auth_token(client, 'testuser', 'testpass123')
        
        client.post('/api/v1/servers',
                   json={'name': 'user-server'},
                   headers={'Authorization': f'Bearer {user_token}'})
        
        # 管理员查看服务器列表
        admin_token = self.get_auth_token(client, 'admin', 'adminpass123')
        
        response = client.get('/api/v1/servers',
                            headers={'Authorization': f'Bearer {admin_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['code'] == 200
        assert len(data['data']['items']) >= 1
    
    def test_server_name_validation(self, client):
        """测试服务器名称验证"""
        token = self.get_auth_token(client)
        
        invalid_names = [
            '',  # 空名称
            'a',  # 太短
            'a' * 51,  # 太长
            'server with spaces',  # 包含空格
            'server@#$%',  # 包含特殊字符
        ]
        
        for invalid_name in invalid_names:
            response = client.post('/api/v1/servers',
                                 json={'name': invalid_name},
                                 headers={'Authorization': f'Bearer {token}'})
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['code'] == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
