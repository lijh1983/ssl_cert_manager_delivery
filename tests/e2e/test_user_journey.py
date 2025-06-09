"""
端到端用户流程测试
测试完整的用户旅程：注册/登录 → 添加服务器 → 配置域名 → 申请证书 → 查看状态 → 设置自动续期
"""
import pytest
import sys
import os
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src'))

from services.user_service import UserService
from services.server_service import ServerService
from services.certificate_service import CertificateService
from utils.exceptions import ValidationError, AuthenticationError, AuthorizationError
from utils.logging_config import get_logger

logger = get_logger(__name__)


class TestUserJourney:
    """端到端用户流程测试类"""
    
    @pytest.fixture
    def user_service(self):
        """创建用户服务实例"""
        return UserService()
    
    @pytest.fixture
    def server_service(self):
        """创建服务器服务实例"""
        return ServerService()
    
    @pytest.fixture
    def certificate_service(self):
        """创建证书服务实例"""
        with patch('services.certificate_service.ACMEManager') as mock_manager:
            service = CertificateService()
            service.acme_manager = mock_manager.return_value
            return service
    
    @pytest.fixture
    def test_user_data(self):
        """测试用户数据"""
        return {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'SecurePassword123!',
            'full_name': '测试用户'
        }
    
    @pytest.fixture
    def test_server_data(self):
        """测试服务器数据"""
        return {
            'name': 'web-server-01',
            'ip': '192.168.1.100',
            'description': '主要Web服务器',
            'server_type': 'nginx'
        }
    
    @pytest.fixture
    def test_domain_data(self):
        """测试域名数据"""
        return {
            'domains': ['example.com', 'www.example.com'],
            'validation_method': 'http',
            'ca_type': 'letsencrypt',
            'auto_renew': True
        }

    # ==================== 完整用户旅程测试 ====================
    
    def test_complete_user_journey_success(self, user_service, server_service, certificate_service, 
                                         test_user_data, test_server_data, test_domain_data):
        """测试完整用户旅程成功流程"""
        
        # ========== 步骤1: 用户注册 ==========
        with patch('models.user.User.get_by_username', return_value=None), \
             patch('models.user.User.get_by_email', return_value=None), \
             patch('models.user.User.create') as mock_user_create:
            
            mock_user = Mock(
                id=1,
                username=test_user_data['username'],
                email=test_user_data['email'],
                is_active=True
            )
            mock_user_create.return_value = mock_user
            
            # 执行用户注册
            register_result = user_service.register_user(test_user_data)
            
            # 验证注册结果
            assert register_result['success'] is True
            assert register_result['user_id'] == 1
            assert 'token' in register_result
            
            user_id = register_result['user_id']
            auth_token = register_result['token']
        
        # ========== 步骤2: 用户登录 ==========
        with patch('models.user.User.authenticate') as mock_authenticate:
            mock_authenticate.return_value = mock_user
            
            # 执行用户登录
            login_result = user_service.login_user(
                test_user_data['username'],
                test_user_data['password']
            )
            
            # 验证登录结果
            assert login_result['success'] is True
            assert login_result['user_id'] == user_id
            assert 'token' in login_result
        
        # ========== 步骤3: 添加服务器 ==========
        with patch('models.user.User.get_by_id', return_value=mock_user), \
             patch('models.server.Server.get_by_name', return_value=None), \
             patch('models.server.Server.create') as mock_server_create:
            
            mock_server = Mock(
                id=1,
                name=test_server_data['name'],
                ip=test_server_data['ip'],
                user_id=user_id,
                token='server_token_123'
            )
            mock_server_create.return_value = mock_server
            
            # 执行添加服务器
            server_result = server_service.create_server(user_id, test_server_data)
            
            # 验证服务器添加结果
            assert server_result['success'] is True
            assert server_result['server']['id'] == 1
            assert server_result['server']['name'] == test_server_data['name']
            
            server_id = server_result['server']['id']
        
        # ========== 步骤4: 申请SSL证书 ==========
        mock_cert_result = {
            'success': True,
            'certificate': 'mock_certificate_content',
            'private_key': 'mock_private_key',
            'domains': test_domain_data['domains'],
            'cert_info': {
                'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat(),
                'issuer': 'Let\'s Encrypt'
            }
        }
        
        with patch('models.user.User.get_by_id', return_value=mock_user), \
             patch('models.server.Server.get_by_id', return_value=mock_server), \
             patch('models.certificate.Certificate.get_by_domain', return_value=None), \
             patch('models.certificate.Certificate.create') as mock_cert_create:
            
            mock_certificate = Mock(
                id=1,
                domain=test_domain_data['domains'][0],
                status='valid',
                expires_at=(datetime.now() + timedelta(days=90)).isoformat()
            )
            mock_cert_create.return_value = mock_certificate
            certificate_service.acme_manager.request_certificate.return_value = mock_cert_result
            
            # 执行证书申请
            cert_result = certificate_service.request_certificate(
                user_id=user_id,
                domains=test_domain_data['domains'],
                server_id=server_id,
                ca_type=test_domain_data['ca_type'],
                validation_method=test_domain_data['validation_method'],
                auto_renew=test_domain_data['auto_renew']
            )
            
            # 验证证书申请结果
            assert cert_result['success'] is True
            assert cert_result['certificate_id'] == 1
            assert cert_result['domains'] == test_domain_data['domains']
            
            certificate_id = cert_result['certificate_id']
        
        # ========== 步骤5: 查看证书状态 ==========
        with patch('models.certificate.Certificate.get_by_id', return_value=mock_certificate):
            
            # 执行证书状态查询
            status_result = certificate_service.get_certificate_status(certificate_id)
            
            # 验证状态查询结果
            assert status_result['id'] == certificate_id
            assert status_result['status'] == 'valid'
            assert 'expires_at' in status_result
        
        # ========== 步骤6: 查看用户的所有证书 ==========
        with patch('models.certificate.Certificate.get_by_user') as mock_get_user_certs:
            mock_get_user_certs.return_value = ([mock_certificate], 1)
            
            # 执行证书列表查询
            list_result = certificate_service.list_certificates(user_id, page=1, limit=10)
            
            # 验证列表查询结果
            assert list_result['total'] == 1
            assert len(list_result['items']) == 1
            assert list_result['items'][0]['id'] == certificate_id
        
        # ========== 步骤7: 设置自动续期 ==========
        with patch('models.certificate.Certificate.get_by_id', return_value=mock_certificate):
            mock_certificate.save = Mock()
            
            # 执行自动续期设置
            auto_renew_result = certificate_service.update_auto_renew_setting(
                certificate_id, user_id, auto_renew=True
            )
            
            # 验证自动续期设置结果
            assert auto_renew_result['success'] is True
            assert mock_certificate.auto_renew is True
            mock_certificate.save.assert_called_once()
        
        logger.info("完整用户旅程测试成功完成")
    
    def test_user_journey_with_errors_and_recovery(self, user_service, server_service, certificate_service,
                                                  test_user_data, test_server_data, test_domain_data):
        """测试用户旅程中的错误处理和恢复"""
        
        # ========== 步骤1: 用户注册失败（邮箱已存在）==========
        with patch('models.user.User.get_by_email') as mock_get_by_email:
            mock_get_by_email.return_value = Mock(email=test_user_data['email'])
            
            # 执行用户注册（应该失败）
            register_result = user_service.register_user(test_user_data)
            
            # 验证注册失败
            assert register_result['success'] is False
            assert '邮箱已存在' in register_result['error']
        
        # ========== 步骤2: 修改邮箱后成功注册 ==========
        test_user_data['email'] = 'newemail@example.com'
        
        with patch('models.user.User.get_by_username', return_value=None), \
             patch('models.user.User.get_by_email', return_value=None), \
             patch('models.user.User.create') as mock_user_create:
            
            mock_user = Mock(
                id=1,
                username=test_user_data['username'],
                email=test_user_data['email']
            )
            mock_user_create.return_value = mock_user
            
            # 执行用户注册
            register_result = user_service.register_user(test_user_data)
            
            # 验证注册成功
            assert register_result['success'] is True
            user_id = register_result['user_id']
        
        # ========== 步骤3: 添加服务器失败（IP地址无效）==========
        invalid_server_data = test_server_data.copy()
        invalid_server_data['ip'] = 'invalid-ip-address'
        
        with patch('models.user.User.get_by_id', return_value=mock_user):
            
            # 执行添加服务器（应该失败）
            server_result = server_service.create_server(user_id, invalid_server_data)
            
            # 验证服务器添加失败
            assert server_result['success'] is False
            assert 'IP地址' in server_result['error']
        
        # ========== 步骤4: 修正IP地址后成功添加服务器 ==========
        with patch('models.user.User.get_by_id', return_value=mock_user), \
             patch('models.server.Server.get_by_name', return_value=None), \
             patch('models.server.Server.create') as mock_server_create:
            
            mock_server = Mock(
                id=1,
                name=test_server_data['name'],
                ip=test_server_data['ip'],
                user_id=user_id
            )
            mock_server_create.return_value = mock_server
            
            # 执行添加服务器
            server_result = server_service.create_server(user_id, test_server_data)
            
            # 验证服务器添加成功
            assert server_result['success'] is True
            server_id = server_result['server']['id']
        
        # ========== 步骤5: 证书申请失败（域名验证失败）==========
        with patch('models.user.User.get_by_id', return_value=mock_user), \
             patch('models.server.Server.get_by_id', return_value=mock_server), \
             patch('models.certificate.Certificate.get_by_domain', return_value=None):
            
            # 模拟ACME验证失败
            from utils.exceptions import ACMEError, ErrorCode
            mock_error = ACMEError(
                ErrorCode.ACME_CHALLENGE_FAILED,
                "HTTP验证失败：无法访问验证文件"
            )
            certificate_service.acme_manager.request_certificate.side_effect = mock_error
            
            # 执行证书申请（应该失败）
            cert_result = certificate_service.request_certificate(
                user_id=user_id,
                domains=test_domain_data['domains'],
                server_id=server_id,
                ca_type=test_domain_data['ca_type'],
                validation_method=test_domain_data['validation_method']
            )
            
            # 验证证书申请失败
            assert cert_result['success'] is False
            assert 'HTTP验证失败' in cert_result['error']
        
        # ========== 步骤6: 切换到DNS验证后成功申请证书 ==========
        mock_cert_result = {
            'success': True,
            'certificate': 'mock_certificate_content',
            'private_key': 'mock_private_key',
            'domains': test_domain_data['domains'],
            'cert_info': {
                'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat(),
                'issuer': 'Let\'s Encrypt'
            }
        }
        
        with patch('models.user.User.get_by_id', return_value=mock_user), \
             patch('models.server.Server.get_by_id', return_value=mock_server), \
             patch('models.certificate.Certificate.get_by_domain', return_value=None), \
             patch('models.certificate.Certificate.create') as mock_cert_create:
            
            mock_certificate = Mock(
                id=1,
                domain=test_domain_data['domains'][0],
                status='valid'
            )
            mock_cert_create.return_value = mock_certificate
            certificate_service.acme_manager.request_certificate.side_effect = None
            certificate_service.acme_manager.request_certificate.return_value = mock_cert_result
            
            # 执行证书申请（使用DNS验证）
            cert_result = certificate_service.request_certificate(
                user_id=user_id,
                domains=test_domain_data['domains'],
                server_id=server_id,
                ca_type=test_domain_data['ca_type'],
                validation_method='dns'  # 切换到DNS验证
            )
            
            # 验证证书申请成功
            assert cert_result['success'] is True
            assert cert_result['certificate_id'] == 1
        
        logger.info("用户旅程错误处理和恢复测试成功完成")
    
    def test_multi_user_concurrent_journey(self, user_service, server_service, certificate_service):
        """测试多用户并发操作"""
        import concurrent.futures
        
        def user_journey_worker(user_index):
            """单个用户的完整旅程"""
            user_data = {
                'username': f'user{user_index}',
                'email': f'user{user_index}@example.com',
                'password': 'SecurePassword123!'
            }
            
            server_data = {
                'name': f'server-{user_index}',
                'ip': f'192.168.1.{100 + user_index}',
                'description': f'用户{user_index}的服务器'
            }
            
            domain_data = {
                'domains': [f'user{user_index}.example.com'],
                'validation_method': 'http',
                'ca_type': 'letsencrypt'
            }
            
            try:
                # 模拟用户注册
                with patch('models.user.User.get_by_username', return_value=None), \
                     patch('models.user.User.get_by_email', return_value=None), \
                     patch('models.user.User.create') as mock_user_create:
                    
                    mock_user = Mock(id=user_index, username=user_data['username'])
                    mock_user_create.return_value = mock_user
                    
                    register_result = user_service.register_user(user_data)
                    if not register_result['success']:
                        return {'user_index': user_index, 'success': False, 'step': 'register'}
                    
                    user_id = register_result['user_id']
                
                # 模拟添加服务器
                with patch('models.user.User.get_by_id', return_value=mock_user), \
                     patch('models.server.Server.get_by_name', return_value=None), \
                     patch('models.server.Server.create') as mock_server_create:
                    
                    mock_server = Mock(id=user_index, name=server_data['name'], user_id=user_id)
                    mock_server_create.return_value = mock_server
                    
                    server_result = server_service.create_server(user_id, server_data)
                    if not server_result['success']:
                        return {'user_index': user_index, 'success': False, 'step': 'server'}
                    
                    server_id = server_result['server']['id']
                
                # 模拟申请证书
                mock_cert_result = {
                    'success': True,
                    'certificate': f'cert_content_{user_index}',
                    'private_key': f'key_content_{user_index}',
                    'domains': domain_data['domains']
                }
                
                with patch('models.user.User.get_by_id', return_value=mock_user), \
                     patch('models.server.Server.get_by_id', return_value=mock_server), \
                     patch('models.certificate.Certificate.get_by_domain', return_value=None), \
                     patch('models.certificate.Certificate.create') as mock_cert_create:
                    
                    mock_certificate = Mock(id=user_index, domain=domain_data['domains'][0])
                    mock_cert_create.return_value = mock_certificate
                    certificate_service.acme_manager.request_certificate.return_value = mock_cert_result
                    
                    cert_result = certificate_service.request_certificate(
                        user_id=user_id,
                        domains=domain_data['domains'],
                        server_id=server_id,
                        ca_type=domain_data['ca_type'],
                        validation_method=domain_data['validation_method']
                    )
                    
                    if not cert_result['success']:
                        return {'user_index': user_index, 'success': False, 'step': 'certificate'}
                
                return {'user_index': user_index, 'success': True, 'step': 'completed'}
                
            except Exception as e:
                return {'user_index': user_index, 'success': False, 'error': str(e)}
        
        # 并发执行多个用户旅程
        concurrent_users = 5
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_journey_worker, i) for i in range(1, concurrent_users + 1)]
            
            results = []
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
        
        # 验证所有用户旅程都成功完成
        successful_journeys = [r for r in results if r['success']]
        failed_journeys = [r for r in results if not r['success']]
        
        assert len(successful_journeys) == concurrent_users, f"部分用户旅程失败: {failed_journeys}"
        
        logger.info(f"多用户并发旅程测试完成: {len(successful_journeys)}/{concurrent_users} 成功")
