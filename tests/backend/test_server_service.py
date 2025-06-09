"""
服务器服务测试
测试服务器管理功能
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src'))

from services.server_service import ServerService
from utils.exceptions import (
    ErrorCode, ValidationError, ResourceNotFoundError, 
    ResourceConflictError, AuthorizationError
)


class TestServerService:
    """服务器服务测试类"""
    
    @pytest.fixture
    def server_service(self, mock_db):
        """创建服务器服务实例"""
        with patch('services.server_service.db', mock_db):
            service = ServerService()
            return service
    
    def test_create_server_success(self, server_service, sample_server_data):
        """测试创建服务器成功"""
        user_id = 1
        server_data = {
            'name': 'test-server',
            'ip': '192.168.1.100',
            'description': '测试服务器'
        }
        
        with patch('models.Server') as mock_server_model:
            # 模拟服务器不存在
            mock_server_model.get_by_name.return_value = None
            
            # 模拟创建成功
            mock_server = Mock()
            mock_server.id = 1
            mock_server.name = server_data['name']
            mock_server.token = 'generated_token'
            mock_server.to_dict.return_value = sample_server_data
            mock_server_model.create.return_value = mock_server
            
            # 执行测试
            result = server_service.create_server(user_id, server_data)
            
            # 验证结果
            assert result['success'] is True
            assert result['server']['name'] == server_data['name']
            assert 'token' in result['server']
            
            # 验证创建方法被调用
            mock_server_model.create.assert_called_once()
    
    def test_create_server_name_conflict(self, server_service):
        """测试创建服务器名称冲突"""
        user_id = 1
        server_data = {
            'name': 'existing-server',
            'ip': '192.168.1.100'
        }
        
        with patch('models.Server') as mock_server_model:
            # 模拟服务器已存在
            existing_server = Mock()
            existing_server.name = server_data['name']
            mock_server_model.get_by_name.return_value = existing_server
            
            # 执行测试并验证异常
            with pytest.raises(ResourceConflictError) as exc_info:
                server_service.create_server(user_id, server_data)
            
            assert exc_info.value.error_code == ErrorCode.CONFLICT
            assert 'name' in exc_info.value.details['conflict_field']
    
    def test_create_server_validation_error(self, server_service):
        """测试创建服务器验证错误"""
        user_id = 1
        
        # 测试缺少必需字段
        with pytest.raises(ValidationError):
            server_service.create_server(user_id, {})
        
        # 测试无效IP地址
        with pytest.raises(ValidationError) as exc_info:
            server_service.create_server(user_id, {
                'name': 'test-server',
                'ip': 'invalid-ip'
            })
        
        assert 'IP地址' in exc_info.value.message
    
    def test_update_server_success(self, server_service, sample_server_data):
        """测试更新服务器成功"""
        server_id = 1
        user_id = 1
        update_data = {
            'description': '更新后的描述',
            'auto_renew': False
        }
        
        # 模拟现有服务器
        mock_server = Mock()
        mock_server.id = server_id
        mock_server.user_id = user_id
        mock_server.name = 'test-server'
        mock_server.save = Mock()
        mock_server.to_dict.return_value = sample_server_data
        
        with patch('models.Server.get_by_id', return_value=mock_server):
            # 执行测试
            result = server_service.update_server(server_id, user_id, update_data)
            
            # 验证结果
            assert result['success'] is True
            assert result['server']['id'] == server_id
            
            # 验证服务器属性被更新
            assert mock_server.description == update_data['description']
            assert mock_server.auto_renew == update_data['auto_renew']
            mock_server.save.assert_called_once()
    
    def test_update_server_not_found(self, server_service):
        """测试更新不存在的服务器"""
        server_id = 999
        user_id = 1
        update_data = {'description': '新描述'}
        
        with patch('models.Server.get_by_id', return_value=None):
            # 执行测试并验证异常
            with pytest.raises(ResourceNotFoundError) as exc_info:
                server_service.update_server(server_id, user_id, update_data)
            
            assert exc_info.value.error_code == ErrorCode.NOT_FOUND
            assert '服务器' in exc_info.value.message
    
    def test_update_server_permission_denied(self, server_service):
        """测试更新服务器权限不足"""
        server_id = 1
        user_id = 1
        other_user_id = 2
        update_data = {'description': '新描述'}
        
        # 模拟属于其他用户的服务器
        mock_server = Mock()
        mock_server.id = server_id
        mock_server.user_id = other_user_id
        
        with patch('models.Server.get_by_id', return_value=mock_server):
            # 执行测试并验证异常
            with pytest.raises(AuthorizationError) as exc_info:
                server_service.update_server(server_id, user_id, update_data)
            
            assert exc_info.value.error_code == ErrorCode.PERMISSION_DENIED
    
    def test_delete_server_success(self, server_service):
        """测试删除服务器成功"""
        server_id = 1
        user_id = 1
        
        # 模拟服务器对象
        mock_server = Mock()
        mock_server.id = server_id
        mock_server.user_id = user_id
        mock_server.delete = Mock()
        
        with patch('models.Server.get_by_id', return_value=mock_server), \
             patch('models.Certificate.get_by_server', return_value=[]):  # 无关联证书
            
            # 执行测试
            result = server_service.delete_server(server_id, user_id)
            
            # 验证结果
            assert result['success'] is True
            assert result['server_id'] == server_id
            
            # 验证删除方法被调用
            mock_server.delete.assert_called_once()
    
    def test_delete_server_with_certificates(self, server_service):
        """测试删除有关联证书的服务器"""
        server_id = 1
        user_id = 1
        
        # 模拟服务器对象
        mock_server = Mock()
        mock_server.id = server_id
        mock_server.user_id = user_id
        
        # 模拟关联的证书
        mock_certificates = [Mock(), Mock()]
        
        with patch('models.Server.get_by_id', return_value=mock_server), \
             patch('models.Certificate.get_by_server', return_value=mock_certificates):
            
            # 执行测试并验证异常
            with pytest.raises(ValidationError) as exc_info:
                server_service.delete_server(server_id, user_id)
            
            assert '关联证书' in exc_info.value.message
    
    def test_get_server_success(self, server_service, sample_server_data):
        """测试获取服务器成功"""
        server_id = 1
        user_id = 1
        
        # 模拟服务器对象
        mock_server = Mock()
        mock_server.id = server_id
        mock_server.user_id = user_id
        mock_server.to_dict.return_value = sample_server_data
        
        with patch('models.Server.get_by_id', return_value=mock_server):
            # 执行测试
            result = server_service.get_server(server_id, user_id)
            
            # 验证结果
            assert result['id'] == server_id
            assert result['name'] == sample_server_data['name']
    
    def test_list_servers(self, server_service, sample_server_data):
        """测试服务器列表查询"""
        user_id = 1
        page = 1
        limit = 10
        
        # 模拟服务器列表
        mock_servers = [
            Mock(to_dict=lambda: {'id': 1, 'name': 'server1'}),
            Mock(to_dict=lambda: {'id': 2, 'name': 'server2'})
        ]
        
        with patch('models.Server.get_by_user', return_value=(mock_servers, 2)):
            # 执行测试
            result = server_service.list_servers(user_id, page, limit)
            
            # 验证结果
            assert result['total'] == 2
            assert result['page'] == page
            assert result['limit'] == limit
            assert len(result['items']) == 2
            assert result['items'][0]['name'] == 'server1'
    
    def test_check_server_status_online(self, server_service):
        """测试检查服务器状态在线"""
        server_id = 1
        
        # 模拟服务器对象
        mock_server = Mock()
        mock_server.id = server_id
        mock_server.ip = '192.168.1.100'
        mock_server.update_status = Mock()
        
        with patch('models.Server.get_by_id', return_value=mock_server), \
             patch('services.server_service.ping_server', return_value=True):
            
            # 执行测试
            result = server_service.check_server_status(server_id)
            
            # 验证结果
            assert result['server_id'] == server_id
            assert result['status'] == 'online'
            assert result['reachable'] is True
            
            # 验证状态更新被调用
            mock_server.update_status.assert_called_with('online')
    
    def test_check_server_status_offline(self, server_service):
        """测试检查服务器状态离线"""
        server_id = 1
        
        # 模拟服务器对象
        mock_server = Mock()
        mock_server.id = server_id
        mock_server.ip = '192.168.1.100'
        mock_server.update_status = Mock()
        
        with patch('models.Server.get_by_id', return_value=mock_server), \
             patch('services.server_service.ping_server', return_value=False):
            
            # 执行测试
            result = server_service.check_server_status(server_id)
            
            # 验证结果
            assert result['server_id'] == server_id
            assert result['status'] == 'offline'
            assert result['reachable'] is False
            
            # 验证状态更新被调用
            mock_server.update_status.assert_called_with('offline')
    
    def test_regenerate_server_token(self, server_service):
        """测试重新生成服务器令牌"""
        server_id = 1
        user_id = 1
        
        # 模拟服务器对象
        mock_server = Mock()
        mock_server.id = server_id
        mock_server.user_id = user_id
        mock_server.regenerate_token = Mock(return_value='new_token')
        
        with patch('models.Server.get_by_id', return_value=mock_server):
            # 执行测试
            result = server_service.regenerate_server_token(server_id, user_id)
            
            # 验证结果
            assert result['success'] is True
            assert result['server_id'] == server_id
            assert result['new_token'] == 'new_token'
            
            # 验证令牌重新生成被调用
            mock_server.regenerate_token.assert_called_once()
    
    def test_get_server_statistics(self, server_service):
        """测试获取服务器统计信息"""
        server_id = 1
        
        # 模拟服务器对象
        mock_server = Mock()
        mock_server.id = server_id
        mock_server.name = 'test-server'
        
        # 模拟统计数据
        mock_certificates = [Mock(), Mock(), Mock()]  # 3个证书
        mock_expiring_certs = [Mock()]  # 1个即将过期
        
        with patch('models.Server.get_by_id', return_value=mock_server), \
             patch('models.Certificate.get_by_server', return_value=mock_certificates), \
             patch('models.Certificate.get_expiring_by_server', return_value=mock_expiring_certs):
            
            # 执行测试
            result = server_service.get_server_statistics(server_id)
            
            # 验证结果
            assert result['server_id'] == server_id
            assert result['server_name'] == 'test-server'
            assert result['total_certificates'] == 3
            assert result['expiring_certificates'] == 1
            assert result['certificate_health_score'] > 0
    
    def test_batch_check_server_status(self, server_service):
        """测试批量检查服务器状态"""
        server_ids = [1, 2, 3]
        
        # 模拟服务器对象
        mock_servers = []
        for i, server_id in enumerate(server_ids):
            mock_server = Mock()
            mock_server.id = server_id
            mock_server.ip = f'192.168.1.{100 + i}'
            mock_server.update_status = Mock()
            mock_servers.append(mock_server)
        
        with patch('models.Server.get_by_id', side_effect=mock_servers), \
             patch('services.server_service.ping_server', side_effect=[True, False, True]):
            
            # 执行测试
            result = server_service.batch_check_server_status(server_ids)
            
            # 验证结果
            assert result['total'] == 3
            assert result['online'] == 2
            assert result['offline'] == 1
            assert len(result['results']) == 3
    
    def test_validate_server_data(self, server_service):
        """测试服务器数据验证"""
        # 测试有效数据
        valid_data = {
            'name': 'test-server',
            'ip': '192.168.1.100',
            'description': '测试服务器'
        }
        
        # 应该不抛出异常
        server_service._validate_server_data(valid_data)
        
        # 测试无效数据
        invalid_data_cases = [
            {'name': '', 'ip': '192.168.1.100'},  # 空名称
            {'name': 'test', 'ip': 'invalid-ip'},  # 无效IP
            {'name': 'a' * 101, 'ip': '192.168.1.100'},  # 名称过长
        ]
        
        for invalid_data in invalid_data_cases:
            with pytest.raises(ValidationError):
                server_service._validate_server_data(invalid_data)
    
    def test_server_health_check(self, server_service):
        """测试服务器健康检查"""
        server_id = 1
        
        # 模拟服务器对象
        mock_server = Mock()
        mock_server.id = server_id
        mock_server.ip = '192.168.1.100'
        mock_server.name = 'test-server'
        mock_server.status = 'online'
        
        with patch('models.Server.get_by_id', return_value=mock_server), \
             patch('services.server_service.check_server_health') as mock_health_check:
            
            mock_health_check.return_value = {
                'reachable': True,
                'response_time': 50,
                'ssl_enabled': True,
                'certificate_valid': True,
                'disk_usage': 75,
                'memory_usage': 60,
                'cpu_usage': 30
            }
            
            # 执行测试
            result = server_service.server_health_check(server_id)
            
            # 验证结果
            assert result['server_id'] == server_id
            assert result['server_name'] == 'test-server'
            assert result['health_status']['reachable'] is True
            assert result['health_status']['response_time'] == 50
            assert result['overall_health'] in ['healthy', 'warning', 'critical']
