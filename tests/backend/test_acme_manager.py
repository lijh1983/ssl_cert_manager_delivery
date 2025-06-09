"""
ACME管理器测试
测试ACME协议处理和CA交互功能
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src'))

from services.acme_client import ACMEManager
from utils.exceptions import (
    ErrorCode, ACMEError, ValidationError, CertificateError
)


class TestACMEManager:
    """ACME管理器测试类"""
    
    @pytest.fixture
    def acme_manager(self):
        """创建ACME管理器实例"""
        return ACMEManager(email='test@example.com', ca_type='letsencrypt')
    
    def test_initialization_success(self, acme_manager):
        """测试ACME管理器初始化成功"""
        with patch('services.acme_client.client.ClientNetwork') as mock_network, \
             patch('services.acme_client.client.ClientV2') as mock_client:
            
            # 模拟成功初始化
            mock_client.get_directory.return_value = Mock()
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance
            
            # 执行初始化
            result = acme_manager.initialize()
            
            # 验证结果
            assert result is True
            assert acme_manager.client is not None
    
    def test_initialization_network_error(self, acme_manager):
        """测试ACME初始化网络错误"""
        with patch('services.acme_client.client.ClientV2.get_directory') as mock_get_dir:
            import requests
            mock_get_dir.side_effect = requests.exceptions.ConnectionError("连接失败")
            
            # 执行测试并验证异常
            with pytest.raises(ACMEError) as exc_info:
                acme_manager.initialize()
            
            assert exc_info.value.error_code == ErrorCode.ACME_NETWORK_ERROR
            assert '连接' in exc_info.value.message
    
    def test_initialization_timeout_error(self, acme_manager):
        """测试ACME初始化超时错误"""
        with patch('services.acme_client.client.ClientV2.get_directory') as mock_get_dir:
            import requests
            mock_get_dir.side_effect = requests.exceptions.Timeout("请求超时")
            
            # 执行测试并验证异常
            with pytest.raises(ACMEError) as exc_info:
                acme_manager.initialize()
            
            assert exc_info.value.error_code == ErrorCode.ACME_TIMEOUT
            assert '超时' in exc_info.value.message
    
    def test_domain_validation_valid_domains(self, acme_manager):
        """测试有效域名验证"""
        valid_domains = [
            'example.com',
            'sub.example.com',
            'test-domain.com',
            'a.b.c.example.com',
            '*.example.com',  # 通配符域名
            'xn--fsq.xn--0zwm56d'  # 国际化域名
        ]
        
        for domain in valid_domains:
            assert acme_manager._validate_domain_format(domain), f"域名验证失败: {domain}"
    
    def test_domain_validation_invalid_domains(self, acme_manager):
        """测试无效域名验证"""
        invalid_domains = [
            '',
            'invalid..domain.com',
            '.example.com',
            'example.com.',
            'too-long-' + 'a' * 250 + '.com',
            '*.*.example.com',  # 多个通配符
            'example.com/path',  # 包含路径
            'localhost',  # 本地域名
            '192.168.1.1'  # IP地址
        ]
        
        for domain in invalid_domains:
            assert not acme_manager._validate_domain_format(domain), f"域名验证应该失败: {domain}"
    
    def test_request_certificate_success(self, acme_manager):
        """测试证书申请成功"""
        domains = ['test.example.com']
        validation_method = 'http'
        
        # 模拟ACME客户端和相关组件
        with patch.object(acme_manager, 'client') as mock_client, \
             patch.object(acme_manager, 'account') as mock_account, \
             patch.object(acme_manager, 'generate_csr') as mock_generate_csr, \
             patch.object(acme_manager, '_process_authorization') as mock_process_auth, \
             patch.object(acme_manager, '_wait_for_order_ready') as mock_wait_order, \
             patch.object(acme_manager, '_cleanup_challenge') as mock_cleanup, \
             patch.object(acme_manager, '_save_certificate') as mock_save:
            
            # 设置模拟返回值
            mock_generate_csr.return_value = (b'csr_pem', b'key_pem')
            
            mock_order = Mock()
            mock_order.uri = 'test_order_uri'
            mock_order.authorizations = [Mock()]
            mock_order.fullchain_pem = 'test_certificate_pem'
            
            mock_client.new_order.return_value = mock_order
            mock_client.finalize_order.return_value = mock_order
            mock_wait_order.return_value = mock_order
            
            mock_save.return_value = {
                'expires_at': '2024-12-31T23:59:59',
                'issuer': 'Let\'s Encrypt'
            }
            
            # 执行测试
            result = acme_manager.request_certificate(domains, validation_method)
            
            # 验证结果
            assert result['success'] is True
            assert result['certificate'] == 'test_certificate_pem'
            assert result['domains'] == domains
            assert 'cert_info' in result
            
            # 验证方法调用
            mock_client.new_order.assert_called_once()
            mock_process_auth.assert_called()
            mock_wait_order.assert_called_once()
            mock_cleanup.assert_called()
    
    def test_request_certificate_validation_error(self, acme_manager):
        """测试证书申请验证错误"""
        # 测试空域名列表
        with pytest.raises(ValidationError):
            acme_manager.request_certificate([])
        
        # 测试无效域名
        with pytest.raises(ACMEError) as exc_info:
            acme_manager.request_certificate(['invalid..domain'])
        
        assert exc_info.value.error_code == ErrorCode.ACME_INVALID_DOMAIN
    
    def test_request_certificate_rate_limit_error(self, acme_manager):
        """测试证书申请频率限制错误"""
        domains = ['test.example.com']
        
        with patch.object(acme_manager, 'client') as mock_client, \
             patch.object(acme_manager, 'account'), \
             patch.object(acme_manager, 'generate_csr') as mock_generate_csr:
            
            mock_generate_csr.return_value = (b'csr_pem', b'key_pem')
            
            # 模拟频率限制错误
            from acme import messages
            rate_limit_error = messages.Error(detail='rate limit exceeded')
            mock_client.new_order.side_effect = rate_limit_error
            
            # 执行测试并验证异常
            with pytest.raises(ACMEError) as exc_info:
                acme_manager.request_certificate(domains)
            
            assert exc_info.value.error_code == ErrorCode.ACME_RATE_LIMIT
    
    def test_request_certificate_order_failed(self, acme_manager):
        """测试证书申请订单失败"""
        domains = ['test.example.com']
        
        with patch.object(acme_manager, 'client') as mock_client, \
             patch.object(acme_manager, 'account'), \
             patch.object(acme_manager, 'generate_csr') as mock_generate_csr:
            
            mock_generate_csr.return_value = (b'csr_pem', b'key_pem')
            
            # 模拟订单失败
            from acme import messages
            order_error = messages.Error(detail='order failed')
            mock_client.new_order.side_effect = order_error
            
            # 执行测试并验证异常
            with pytest.raises(ACMEError) as exc_info:
                acme_manager.request_certificate(domains)
            
            assert exc_info.value.error_code == ErrorCode.ACME_ORDER_FAILED
    
    def test_process_authorization_http_challenge(self, acme_manager):
        """测试HTTP验证处理"""
        # 模拟授权对象
        mock_authorization = Mock()
        mock_authorization.body.identifier.value = 'test.example.com'
        
        # 模拟HTTP挑战
        mock_http_challenge = Mock()
        mock_http_challenge.chall.typ = 'http-01'
        mock_http_challenge.token = 'test_token'
        mock_authorization.body.challenges = [mock_http_challenge]
        
        with patch.object(acme_manager, '_setup_http_challenge') as mock_setup, \
             patch.object(acme_manager, '_wait_for_challenge_completion') as mock_wait:
            
            mock_setup.return_value = True
            
            # 执行测试
            acme_manager._process_authorization(mock_authorization, 'http')
            
            # 验证方法调用
            mock_setup.assert_called_once()
            mock_wait.assert_called_once()
    
    def test_process_authorization_dns_challenge(self, acme_manager):
        """测试DNS验证处理"""
        # 模拟授权对象
        mock_authorization = Mock()
        mock_authorization.body.identifier.value = 'test.example.com'
        
        # 模拟DNS挑战
        mock_dns_challenge = Mock()
        mock_dns_challenge.chall.typ = 'dns-01'
        mock_dns_challenge.token = 'test_token'
        mock_authorization.body.challenges = [mock_dns_challenge]
        
        with patch.object(acme_manager, '_setup_dns_challenge') as mock_setup, \
             patch.object(acme_manager, '_wait_for_challenge_completion') as mock_wait:
            
            mock_setup.return_value = True
            
            # 执行测试
            acme_manager._process_authorization(mock_authorization, 'dns')
            
            # 验证方法调用
            mock_setup.assert_called_once()
            mock_wait.assert_called_once()
    
    def test_wait_for_challenge_completion_success(self, acme_manager):
        """测试等待验证完成成功"""
        mock_challenge = Mock()
        
        with patch.object(acme_manager, 'client') as mock_client:
            # 模拟验证成功
            from acme import messages
            mock_challenge.status = messages.STATUS_VALID
            mock_client.poll.return_value = mock_challenge
            
            # 执行测试（应该正常完成）
            acme_manager._wait_for_challenge_completion(mock_challenge)
            
            # 验证轮询被调用
            mock_client.poll.assert_called()
    
    def test_wait_for_challenge_completion_failed(self, acme_manager):
        """测试等待验证完成失败"""
        mock_challenge = Mock()
        
        with patch.object(acme_manager, 'client') as mock_client:
            # 模拟验证失败
            from acme import messages
            mock_challenge.status = messages.STATUS_INVALID
            mock_challenge.error = 'validation failed'
            mock_client.poll.return_value = mock_challenge
            
            # 执行测试并验证异常
            with pytest.raises(ACMEError) as exc_info:
                acme_manager._wait_for_challenge_completion(mock_challenge)
            
            assert exc_info.value.error_code == ErrorCode.ACME_CHALLENGE_FAILED
    
    def test_wait_for_challenge_completion_timeout(self, acme_manager):
        """测试等待验证完成超时"""
        mock_challenge = Mock()
        
        with patch.object(acme_manager, 'client') as mock_client, \
             patch('time.sleep'):  # 加速测试
            
            # 模拟一直处于待处理状态
            from acme import messages
            mock_challenge.status = messages.STATUS_PENDING
            mock_client.poll.return_value = mock_challenge
            
            # 执行测试并验证超时异常
            with pytest.raises(ACMEError) as exc_info:
                acme_manager._wait_for_challenge_completion(mock_challenge, timeout=1)
            
            assert exc_info.value.error_code == ErrorCode.ACME_TIMEOUT
    
    def test_revoke_certificate_success(self, acme_manager):
        """测试证书撤销成功"""
        certificate_pem = 'test_certificate_pem'
        
        with patch.object(acme_manager, 'client') as mock_client, \
             patch.object(acme_manager, 'account'):
            
            # 模拟撤销成功
            mock_client.revoke.return_value = None
            
            # 执行测试
            result = acme_manager.revoke_certificate(certificate_pem)
            
            # 验证结果
            assert result['success'] is True
            
            # 验证撤销方法被调用
            mock_client.revoke.assert_called_once()
    
    def test_revoke_certificate_error(self, acme_manager):
        """测试证书撤销错误"""
        certificate_pem = 'test_certificate_pem'
        
        with patch.object(acme_manager, 'client') as mock_client, \
             patch.object(acme_manager, 'account'):
            
            # 模拟撤销失败
            mock_client.revoke.side_effect = Exception("撤销失败")
            
            # 执行测试并验证异常
            with pytest.raises(CertificateError) as exc_info:
                acme_manager.revoke_certificate(certificate_pem)
            
            assert exc_info.value.error_code == ErrorCode.CERTIFICATE_REVOCATION_FAILED
    
    def test_generate_csr(self, acme_manager):
        """测试CSR生成"""
        domains = ['test.example.com', 'www.test.example.com']
        
        # 执行测试
        csr_pem, key_pem = acme_manager.generate_csr(domains)
        
        # 验证结果
        assert isinstance(csr_pem, bytes)
        assert isinstance(key_pem, bytes)
        assert b'BEGIN CERTIFICATE REQUEST' in csr_pem
        assert b'BEGIN PRIVATE KEY' in key_pem
    
    def test_get_ca_directory_url(self, acme_manager):
        """测试获取CA目录URL"""
        # 测试不同CA类型
        test_cases = [
            ('letsencrypt', 'https://acme-v02.api.letsencrypt.org/directory'),
            ('zerossl', 'https://acme.zerossl.com/v2/DV90'),
            ('buypass', 'https://api.buypass.com/acme/directory')
        ]
        
        for ca_type, expected_url in test_cases:
            acme_manager.ca_type = ca_type
            url = acme_manager._get_ca_directory_url()
            assert url == expected_url
    
    def test_account_registration_success(self, acme_manager):
        """测试账户注册成功"""
        with patch('services.acme_client.client.ClientV2') as mock_client_class, \
             patch('services.acme_client.messages.NewRegistration') as mock_new_reg:
            
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            mock_account = Mock()
            mock_client.new_account.return_value = mock_account
            
            # 执行账户注册
            acme_manager.client = mock_client
            result = acme_manager._register_or_get_account()
            
            # 验证结果
            assert result == mock_account
            mock_client.new_account.assert_called_once()
    
    def test_account_registration_rate_limit(self, acme_manager):
        """测试账户注册频率限制"""
        with patch('services.acme_client.client.ClientV2') as mock_client_class:
            
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # 模拟频率限制错误
            from acme import messages
            rate_limit_error = messages.Error(detail='rate limit exceeded')
            mock_client.new_account.side_effect = rate_limit_error
            
            acme_manager.client = mock_client
            
            # 执行测试并验证异常
            with pytest.raises(ACMEError) as exc_info:
                acme_manager._register_or_get_account()
            
            assert exc_info.value.error_code == ErrorCode.ACME_RATE_LIMIT
