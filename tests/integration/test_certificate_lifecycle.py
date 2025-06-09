"""
证书申请流程完整测试用例
测试从域名验证到证书部署的完整生命周期
"""
import pytest
import sys
import os
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src'))

from services.certificate_service import CertificateService
from services.acme_client import ACMEManager, ACMEClient
from utils.exceptions import ACMEError, ValidationError, ErrorCode
from utils.logging_config import get_logger

logger = get_logger(__name__)


class TestCertificateLifecycle:
    """证书生命周期完整测试"""
    
    @pytest.fixture
    def mock_acme_server(self):
        """模拟ACME服务器"""
        class MockACMEServer:
            def __init__(self):
                self.rate_limit_count = 0
                self.network_failure_count = 0
                self.dns_failure_domains = set()
                self.http_failure_domains = set()
                
            def reset(self):
                self.rate_limit_count = 0
                self.network_failure_count = 0
                self.dns_failure_domains.clear()
                self.http_failure_domains.clear()
                
            def set_rate_limit(self, count: int):
                self.rate_limit_count = count
                
            def set_network_failure(self, count: int):
                self.network_failure_count = count
                
            def set_dns_failure(self, domains: List[str]):
                self.dns_failure_domains.update(domains)
                
            def set_http_failure(self, domains: List[str]):
                self.http_failure_domains.update(domains)
        
        return MockACMEServer()
    
    @pytest.fixture
    def certificate_service(self, mock_acme_server):
        """创建证书服务实例"""
        with patch('services.certificate_service.ACMEManager') as mock_manager:
            service = CertificateService()
            service.acme_manager = mock_manager.return_value
            service.mock_server = mock_acme_server
            return service
    
    @pytest.fixture
    def test_domains(self):
        """测试域名"""
        return {
            'single': ['test.example.com'],
            'multi': ['test1.example.com', 'test2.example.com', 'test3.example.com'],
            'wildcard': ['*.example.com'],
            'mixed': ['example.com', '*.example.com', 'api.example.com']
        }
    
    @pytest.fixture
    def test_users_and_servers(self):
        """测试用户和服务器数据"""
        return {
            'user_id': 1,
            'server_id': 1,
            'admin_user_id': 2,
            'invalid_user_id': 999,
            'invalid_server_id': 999
        }

    # ==================== 正常流程测试 ====================
    
    def test_single_domain_http_validation_success(self, certificate_service, test_domains, test_users_and_servers):
        """测试单域名HTTP验证成功流程"""
        domains = test_domains['single']
        user_id = test_users_and_servers['user_id']
        server_id = test_users_and_servers['server_id']
        
        # 模拟成功的证书申请
        mock_result = {
            'success': True,
            'certificate': 'mock_certificate_content',
            'private_key': 'mock_private_key',
            'domains': domains,
            'cert_info': {
                'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat(),
                'issuer': 'Let\'s Encrypt',
                'serial_number': '123456789'
            }
        }
        
        with patch('models.user.User.get_by_id') as mock_user, \
             patch('models.server.Server.get_by_id') as mock_server, \
             patch('models.certificate.Certificate.get_by_domain') as mock_cert_check, \
             patch('models.certificate.Certificate.create') as mock_cert_create:
            
            # 设置模拟对象
            mock_user.return_value = Mock(id=user_id, role='user')
            mock_server.return_value = Mock(id=server_id, user_id=user_id)
            mock_cert_check.return_value = None  # 无现有证书
            mock_cert_create.return_value = Mock(id=1)
            
            certificate_service.acme_manager.request_certificate.return_value = mock_result
            
            # 执行测试
            result = certificate_service.request_certificate(
                user_id=user_id,
                domains=domains,
                server_id=server_id,
                ca_type='letsencrypt',
                validation_method='http',
                auto_renew=True
            )
            
            # 验证结果
            assert result['success'] is True
            assert result['certificate_id'] == 1
            assert result['domains'] == domains
            assert 'expires_at' in result
            assert 'message' in result
            
            # 验证ACME管理器被正确调用
            certificate_service.acme_manager.request_certificate.assert_called_once_with(
                domains, 'letsencrypt', 'http'
            )
            
            # 验证证书创建
            mock_cert_create.assert_called_once()
    
    def test_multi_domain_http_validation_success(self, certificate_service, test_domains, test_users_and_servers):
        """测试多域名HTTP验证成功流程"""
        domains = test_domains['multi']
        user_id = test_users_and_servers['user_id']
        server_id = test_users_and_servers['server_id']
        
        mock_result = {
            'success': True,
            'certificate': 'mock_multi_domain_certificate',
            'private_key': 'mock_private_key',
            'domains': domains,
            'cert_info': {
                'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat(),
                'issuer': 'Let\'s Encrypt',
                'subject_alt_names': domains
            }
        }
        
        with patch('models.user.User.get_by_id') as mock_user, \
             patch('models.server.Server.get_by_id') as mock_server, \
             patch('models.certificate.Certificate.get_by_domain') as mock_cert_check, \
             patch('models.certificate.Certificate.create') as mock_cert_create:
            
            mock_user.return_value = Mock(id=user_id, role='user')
            mock_server.return_value = Mock(id=server_id, user_id=user_id)
            mock_cert_check.return_value = None
            mock_cert_create.return_value = Mock(id=2)
            
            certificate_service.acme_manager.request_certificate.return_value = mock_result
            
            # 执行测试
            result = certificate_service.request_certificate(
                user_id=user_id,
                domains=domains,
                server_id=server_id,
                ca_type='letsencrypt',
                validation_method='http'
            )
            
            # 验证结果
            assert result['success'] is True
            assert result['domains'] == domains
            assert len(result['domains']) == 3
    
    def test_wildcard_domain_dns_validation_success(self, certificate_service, test_domains, test_users_and_servers):
        """测试通配符域名DNS验证成功流程"""
        domains = test_domains['wildcard']
        user_id = test_users_and_servers['user_id']
        server_id = test_users_and_servers['server_id']
        
        mock_result = {
            'success': True,
            'certificate': 'mock_wildcard_certificate',
            'private_key': 'mock_private_key',
            'domains': domains,
            'cert_info': {
                'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat(),
                'issuer': 'Let\'s Encrypt',
                'is_wildcard': True
            }
        }
        
        with patch('models.user.User.get_by_id') as mock_user, \
             patch('models.server.Server.get_by_id') as mock_server, \
             patch('models.certificate.Certificate.get_by_domain') as mock_cert_check, \
             patch('models.certificate.Certificate.create') as mock_cert_create:
            
            mock_user.return_value = Mock(id=user_id, role='user')
            mock_server.return_value = Mock(id=server_id, user_id=user_id)
            mock_cert_check.return_value = None
            mock_cert_create.return_value = Mock(id=3)
            
            certificate_service.acme_manager.request_certificate.return_value = mock_result
            
            # 执行测试
            result = certificate_service.request_certificate(
                user_id=user_id,
                domains=domains,
                server_id=server_id,
                ca_type='letsencrypt',
                validation_method='dns'
            )
            
            # 验证结果
            assert result['success'] is True
            assert domains[0].startswith('*.')
            
            # 验证DNS验证方式被使用
            certificate_service.acme_manager.request_certificate.assert_called_with(
                domains, 'letsencrypt', 'dns'
            )
    
    def test_different_ca_providers_success(self, certificate_service, test_domains, test_users_and_servers):
        """测试不同CA提供商的证书申请"""
        domains = test_domains['single']
        user_id = test_users_and_servers['user_id']
        server_id = test_users_and_servers['server_id']
        
        ca_providers = ['letsencrypt', 'zerossl', 'buypass']
        
        for ca_type in ca_providers:
            mock_result = {
                'success': True,
                'certificate': f'mock_{ca_type}_certificate',
                'private_key': 'mock_private_key',
                'domains': domains,
                'cert_info': {
                    'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat(),
                    'issuer': ca_type.title(),
                    'ca_type': ca_type
                }
            }
            
            with patch('models.user.User.get_by_id') as mock_user, \
                 patch('models.server.Server.get_by_id') as mock_server, \
                 patch('models.certificate.Certificate.get_by_domain') as mock_cert_check, \
                 patch('models.certificate.Certificate.create') as mock_cert_create:
                
                mock_user.return_value = Mock(id=user_id, role='user')
                mock_server.return_value = Mock(id=server_id, user_id=user_id)
                mock_cert_check.return_value = None
                mock_cert_create.return_value = Mock(id=4)
                
                certificate_service.acme_manager.request_certificate.return_value = mock_result
                
                # 执行测试
                result = certificate_service.request_certificate(
                    user_id=user_id,
                    domains=domains,
                    server_id=server_id,
                    ca_type=ca_type,
                    validation_method='http'
                )
                
                # 验证结果
                assert result['success'] is True
                
                # 验证CA类型被正确传递
                certificate_service.acme_manager.request_certificate.assert_called_with(
                    domains, ca_type, 'http'
                )

    # ==================== 异常处理测试 ====================

    def test_domain_validation_failure_dns_error(self, certificate_service, test_domains, test_users_and_servers):
        """测试域名验证失败 - DNS解析错误"""
        domains = ['invalid-dns.example.com']
        user_id = test_users_and_servers['user_id']
        server_id = test_users_and_servers['server_id']

        # 模拟DNS解析错误
        mock_error = ACMEError(
            error_code=ErrorCode.ACME_DNS_ERROR,
            message="DNS解析失败",
            acme_details={'domain': domains[0], 'error_type': 'dns_resolution_failed'}
        )

        with patch('models.user.User.get_by_id') as mock_user, \
             patch('models.server.Server.get_by_id') as mock_server, \
             patch('models.certificate.Certificate.get_by_domain') as mock_cert_check:

            mock_user.return_value = Mock(id=user_id, role='user')
            mock_server.return_value = Mock(id=server_id, user_id=user_id)
            mock_cert_check.return_value = None

            certificate_service.acme_manager.request_certificate.side_effect = mock_error

            # 执行测试
            result = certificate_service.request_certificate(
                user_id=user_id,
                domains=domains,
                server_id=server_id,
                ca_type='letsencrypt',
                validation_method='dns'
            )

            # 验证结果
            assert result['success'] is False
            assert 'DNS解析失败' in result['error']

    def test_http_validation_file_access_failure(self, certificate_service, test_domains, test_users_and_servers):
        """测试HTTP验证文件无法访问"""
        domains = ['unreachable.example.com']
        user_id = test_users_and_servers['user_id']
        server_id = test_users_and_servers['server_id']

        # 模拟HTTP验证文件无法访问
        mock_error = ACMEError(
            error_code=ErrorCode.ACME_CHALLENGE_FAILED,
            message="HTTP验证失败：无法访问验证文件",
            acme_details={'domain': domains[0], 'challenge_type': 'http-01', 'status': 'invalid'}
        )

        with patch('models.user.User.get_by_id') as mock_user, \
             patch('models.server.Server.get_by_id') as mock_server, \
             patch('models.certificate.Certificate.get_by_domain') as mock_cert_check:

            mock_user.return_value = Mock(id=user_id, role='user')
            mock_server.return_value = Mock(id=server_id, user_id=user_id)
            mock_cert_check.return_value = None

            certificate_service.acme_manager.request_certificate.side_effect = mock_error

            # 执行测试
            result = certificate_service.request_certificate(
                user_id=user_id,
                domains=domains,
                server_id=server_id,
                ca_type='letsencrypt',
                validation_method='http'
            )

            # 验证结果
            assert result['success'] is False
            assert 'HTTP验证失败' in result['error']

    def test_ca_server_unavailable(self, certificate_service, test_domains, test_users_and_servers):
        """测试CA服务器不可用"""
        domains = test_domains['single']
        user_id = test_users_and_servers['user_id']
        server_id = test_users_and_servers['server_id']

        # 模拟CA服务器不可用
        mock_error = ACMEError(
            error_code=ErrorCode.ACME_NETWORK_ERROR,
            message="无法连接到ACME服务器",
            acme_details={'directory_url': 'https://acme-v02.api.letsencrypt.org/directory'}
        )

        with patch('models.user.User.get_by_id') as mock_user, \
             patch('models.server.Server.get_by_id') as mock_server, \
             patch('models.certificate.Certificate.get_by_domain') as mock_cert_check:

            mock_user.return_value = Mock(id=user_id, role='user')
            mock_server.return_value = Mock(id=server_id, user_id=user_id)
            mock_cert_check.return_value = None

            certificate_service.acme_manager.request_certificate.side_effect = mock_error

            # 执行测试
            result = certificate_service.request_certificate(
                user_id=user_id,
                domains=domains,
                server_id=server_id,
                ca_type='letsencrypt',
                validation_method='http'
            )

            # 验证结果
            assert result['success'] is False
            assert '无法连接到ACME服务器' in result['error']

    def test_rate_limit_exceeded(self, certificate_service, test_domains, test_users_and_servers):
        """测试频率限制超限"""
        domains = test_domains['single']
        user_id = test_users_and_servers['user_id']
        server_id = test_users_and_servers['server_id']

        # 模拟频率限制错误
        mock_error = ACMEError(
            error_code=ErrorCode.ACME_RATE_LIMIT,
            message="证书申请频率超限",
            acme_details={'domains': domains, 'retry_after': 3600}
        )

        with patch('models.user.User.get_by_id') as mock_user, \
             patch('models.server.Server.get_by_id') as mock_server, \
             patch('models.certificate.Certificate.get_by_domain') as mock_cert_check:

            mock_user.return_value = Mock(id=user_id, role='user')
            mock_server.return_value = Mock(id=server_id, user_id=user_id)
            mock_cert_check.return_value = None

            certificate_service.acme_manager.request_certificate.side_effect = mock_error

            # 执行测试
            result = certificate_service.request_certificate(
                user_id=user_id,
                domains=domains,
                server_id=server_id,
                ca_type='letsencrypt',
                validation_method='http'
            )

            # 验证结果
            assert result['success'] is False
            assert '频率超限' in result['error']

    def test_network_timeout_and_interruption(self, certificate_service, test_domains, test_users_and_servers):
        """测试网络超时和连接中断"""
        domains = test_domains['single']
        user_id = test_users_and_servers['user_id']
        server_id = test_users_and_servers['server_id']

        # 模拟网络超时
        mock_error = ACMEError(
            error_code=ErrorCode.ACME_TIMEOUT,
            message="连接ACME服务器超时",
            acme_details={'timeout': True, 'duration': 30}
        )

        with patch('models.user.User.get_by_id') as mock_user, \
             patch('models.server.Server.get_by_id') as mock_server, \
             patch('models.certificate.Certificate.get_by_domain') as mock_cert_check:

            mock_user.return_value = Mock(id=user_id, role='user')
            mock_server.return_value = Mock(id=server_id, user_id=user_id)
            mock_cert_check.return_value = None

            certificate_service.acme_manager.request_certificate.side_effect = mock_error

            # 执行测试
            result = certificate_service.request_certificate(
                user_id=user_id,
                domains=domains,
                server_id=server_id,
                ca_type='letsencrypt',
                validation_method='http'
            )

            # 验证结果
            assert result['success'] is False
            assert '超时' in result['error']

    # ==================== 边界条件测试 ====================

    def test_maximum_domain_count_limit(self, certificate_service, test_users_and_servers):
        """测试最大域名数量限制"""
        # 创建超过限制的域名列表（假设限制为100个）
        max_domains = [f'test{i}.example.com' for i in range(101)]
        user_id = test_users_and_servers['user_id']
        server_id = test_users_and_servers['server_id']

        with patch('models.user.User.get_by_id') as mock_user, \
             patch('models.server.Server.get_by_id') as mock_server, \
             patch('models.certificate.Certificate.get_by_domain') as mock_cert_check:

            mock_user.return_value = Mock(id=user_id, role='user')
            mock_server.return_value = Mock(id=server_id, user_id=user_id)
            mock_cert_check.return_value = None

            # 模拟ACME客户端拒绝过多域名
            mock_error = ValidationError("域名数量超过限制（最大100个）")
            certificate_service.acme_manager.request_certificate.side_effect = mock_error

            # 执行测试
            result = certificate_service.request_certificate(
                user_id=user_id,
                domains=max_domains,
                server_id=server_id,
                ca_type='letsencrypt',
                validation_method='http'
            )

            # 验证结果
            assert result['success'] is False
            assert '域名数量' in result['error'] or '限制' in result['error']

    def test_certificate_validity_period_boundary(self, certificate_service, test_domains, test_users_and_servers):
        """测试证书有效期边界"""
        domains = test_domains['single']
        user_id = test_users_and_servers['user_id']
        server_id = test_users_and_servers['server_id']

        # 测试最短有效期（1天）
        short_validity = datetime.now() + timedelta(days=1)
        mock_result_short = {
            'success': True,
            'certificate': 'mock_short_validity_cert',
            'private_key': 'mock_private_key',
            'domains': domains,
            'cert_info': {
                'not_valid_after': short_validity.isoformat(),
                'issuer': 'Let\'s Encrypt'
            }
        }

        # 测试最长有效期（90天）
        long_validity = datetime.now() + timedelta(days=90)
        mock_result_long = {
            'success': True,
            'certificate': 'mock_long_validity_cert',
            'private_key': 'mock_private_key',
            'domains': domains,
            'cert_info': {
                'not_valid_after': long_validity.isoformat(),
                'issuer': 'Let\'s Encrypt'
            }
        }

        with patch('models.user.User.get_by_id') as mock_user, \
             patch('models.server.Server.get_by_id') as mock_server, \
             patch('models.certificate.Certificate.get_by_domain') as mock_cert_check, \
             patch('models.certificate.Certificate.create') as mock_cert_create:

            mock_user.return_value = Mock(id=user_id, role='user')
            mock_server.return_value = Mock(id=server_id, user_id=user_id)
            mock_cert_check.return_value = None
            mock_cert_create.return_value = Mock(id=5)

            # 测试短有效期
            certificate_service.acme_manager.request_certificate.return_value = mock_result_short
            result_short = certificate_service.request_certificate(
                user_id=user_id,
                domains=domains,
                server_id=server_id,
                ca_type='letsencrypt',
                validation_method='http'
            )
            assert result_short['success'] is True

            # 测试长有效期
            certificate_service.acme_manager.request_certificate.return_value = mock_result_long
            result_long = certificate_service.request_certificate(
                user_id=user_id,
                domains=domains,
                server_id=server_id,
                ca_type='letsencrypt',
                validation_method='http'
            )
            assert result_long['success'] is True

    def test_concurrent_same_domain_requests(self, certificate_service, test_domains, test_users_and_servers):
        """测试并发申请相同域名的冲突处理"""
        domains = test_domains['single']
        user_id = test_users_and_servers['user_id']
        server_id = test_users_and_servers['server_id']

        with patch('models.user.User.get_by_id') as mock_user, \
             patch('models.server.Server.get_by_id') as mock_server, \
             patch('models.certificate.Certificate.get_by_domain') as mock_cert_check:

            mock_user.return_value = Mock(id=user_id, role='user')
            mock_server.return_value = Mock(id=server_id, user_id=user_id)

            # 第一次请求时无现有证书
            # 第二次请求时已有有效证书
            existing_cert = Mock(status='valid', domain=domains[0])
            mock_cert_check.side_effect = [None, existing_cert]

            # 第一次请求成功
            mock_result = {
                'success': True,
                'certificate': 'mock_certificate',
                'private_key': 'mock_private_key',
                'domains': domains,
                'cert_info': {'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat()}
            }

            with patch('models.certificate.Certificate.create') as mock_cert_create:
                mock_cert_create.return_value = Mock(id=6)
                certificate_service.acme_manager.request_certificate.return_value = mock_result

                # 第一次请求
                result1 = certificate_service.request_certificate(
                    user_id=user_id,
                    domains=domains,
                    server_id=server_id,
                    ca_type='letsencrypt',
                    validation_method='http'
                )
                assert result1['success'] is True

                # 第二次请求（应该失败，因为已存在有效证书）
                result2 = certificate_service.request_certificate(
                    user_id=user_id,
                    domains=domains,
                    server_id=server_id,
                    ca_type='letsencrypt',
                    validation_method='http'
                )
                assert result2['success'] is False
                assert '已存在有效证书' in result2['error']

    # ==================== 权限和验证测试 ====================

    def test_user_permission_validation(self, certificate_service, test_domains):
        """测试用户权限验证"""
        domains = test_domains['single']

        # 测试用户不存在
        with patch('models.user.User.get_by_id') as mock_user:
            mock_user.return_value = None

            result = certificate_service.request_certificate(
                user_id=999,
                domains=domains,
                server_id=1,
                ca_type='letsencrypt',
                validation_method='http'
            )

            assert result['success'] is False
            assert '用户不存在' in result['error']

    def test_server_permission_validation(self, certificate_service, test_domains):
        """测试服务器权限验证"""
        domains = test_domains['single']
        user_id = 1

        with patch('models.user.User.get_by_id') as mock_user:
            mock_user.return_value = Mock(id=user_id, role='user')

            # 测试服务器不存在
            with patch('models.server.Server.get_by_id') as mock_server:
                mock_server.return_value = None

                result = certificate_service.request_certificate(
                    user_id=user_id,
                    domains=domains,
                    server_id=999,
                    ca_type='letsencrypt',
                    validation_method='http'
                )

                assert result['success'] is False
                assert '服务器不存在或无权限' in result['error']

            # 测试用户无权限访问服务器
            with patch('models.server.Server.get_by_id') as mock_server:
                mock_server.return_value = Mock(id=1, user_id=2)  # 不同用户的服务器

                result = certificate_service.request_certificate(
                    user_id=user_id,
                    domains=domains,
                    server_id=1,
                    ca_type='letsencrypt',
                    validation_method='http'
                )

                assert result['success'] is False
                assert '服务器不存在或无权限' in result['error']

    def test_admin_user_access_all_servers(self, certificate_service, test_domains):
        """测试管理员用户可以访问所有服务器"""
        domains = test_domains['single']
        admin_user_id = 2
        other_user_server_id = 1

        mock_result = {
            'success': True,
            'certificate': 'mock_admin_certificate',
            'private_key': 'mock_private_key',
            'domains': domains,
            'cert_info': {
                'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat(),
                'issuer': 'Let\'s Encrypt'
            }
        }

        with patch('models.user.User.get_by_id') as mock_user, \
             patch('models.server.Server.get_by_id') as mock_server, \
             patch('models.certificate.Certificate.get_by_domain') as mock_cert_check, \
             patch('models.certificate.Certificate.create') as mock_cert_create:

            # 管理员用户
            mock_user.return_value = Mock(id=admin_user_id, role='admin')
            # 其他用户的服务器
            mock_server.return_value = Mock(id=other_user_server_id, user_id=1)
            mock_cert_check.return_value = None
            mock_cert_create.return_value = Mock(id=7)

            certificate_service.acme_manager.request_certificate.return_value = mock_result

            # 执行测试
            result = certificate_service.request_certificate(
                user_id=admin_user_id,
                domains=domains,
                server_id=other_user_server_id,
                ca_type='letsencrypt',
                validation_method='http'
            )

            # 验证管理员可以成功申请证书
            assert result['success'] is True
