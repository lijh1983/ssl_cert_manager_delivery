"""
证书服务测试模块
测试证书服务的各种功能
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend/src'))

from services.certificate_service import CertificateService


class TestCertificateService:
    """证书服务测试类"""
    
    @pytest.fixture
    def certificate_service(self):
        """创建证书服务实例"""
        with patch('services.certificate_service.ACMEManager'):
            service = CertificateService()
            return service
    
    @pytest.fixture
    def mock_user(self):
        """模拟用户"""
        user = MagicMock()
        user.id = 1
        user.role = 'user'
        return user
    
    @pytest.fixture
    def mock_admin(self):
        """模拟管理员"""
        admin = MagicMock()
        admin.id = 2
        admin.role = 'admin'
        return admin
    
    @pytest.fixture
    def mock_server(self):
        """模拟服务器"""
        server = MagicMock()
        server.id = 1
        server.user_id = 1
        server.name = 'test-server'
        return server
    
    @pytest.fixture
    def mock_certificate(self):
        """模拟证书"""
        cert = MagicMock()
        cert.id = 1
        cert.domain = 'example.com'
        cert.domains = 'example.com,www.example.com'
        cert.user_id = 1
        cert.server_id = 1
        cert.ca_type = 'letsencrypt'
        cert.validation_method = 'http'
        cert.status = 'valid'
        cert.expires_at = datetime.now() + timedelta(days=60)
        return cert
    
    def test_certificate_service_initialization(self, certificate_service):
        """测试证书服务初始化"""
        assert certificate_service.acme_email is not None
        assert isinstance(certificate_service.staging, bool)
        assert certificate_service.acme_manager is not None
    
    @patch('services.certificate_service.User')
    @patch('services.certificate_service.Server')
    @patch('services.certificate_service.Certificate')
    def test_request_certificate_success(self, mock_cert_class, mock_server_class, 
                                       mock_user_class, certificate_service, 
                                       mock_user, mock_server):
        """测试成功申请证书"""
        # 设置模拟对象
        mock_user_class.get_by_id.return_value = mock_user
        mock_server_class.get_by_id.return_value = mock_server
        mock_cert_class.get_by_domain.return_value = None
        
        # 模拟证书创建
        mock_certificate = MagicMock()
        mock_certificate.id = 1
        mock_cert_class.create.return_value = mock_certificate
        
        # 模拟ACME管理器
        certificate_service.acme_manager.request_certificate.return_value = {
            'success': True,
            'cert_info': {
                'not_valid_after': datetime.now() + timedelta(days=90)
            }
        }
        
        # 执行测试
        result = certificate_service.request_certificate(
            user_id=1,
            domains=['example.com'],
            server_id=1
        )
        
        # 验证结果
        assert result['success'] == True
        assert 'certificate_id' in result
        assert result['domains'] == ['example.com']
        
        # 验证调用
        mock_user_class.get_by_id.assert_called_with(1)
        mock_server_class.get_by_id.assert_called_with(1)
        certificate_service.acme_manager.request_certificate.assert_called_once()
    
    @patch('services.certificate_service.User')
    def test_request_certificate_user_not_found(self, mock_user_class, certificate_service):
        """测试用户不存在的情况"""
        mock_user_class.get_by_id.return_value = None
        
        result = certificate_service.request_certificate(
            user_id=999,
            domains=['example.com'],
            server_id=1
        )
        
        assert result['success'] == False
        assert '用户不存在' in result['error']
    
    @patch('services.certificate_service.User')
    @patch('services.certificate_service.Server')
    def test_request_certificate_server_permission_denied(self, mock_server_class, 
                                                         mock_user_class, certificate_service,
                                                         mock_user):
        """测试服务器权限不足的情况"""
        mock_user_class.get_by_id.return_value = mock_user
        
        # 模拟不属于用户的服务器
        mock_server = MagicMock()
        mock_server.user_id = 999  # 不同的用户ID
        mock_server_class.get_by_id.return_value = mock_server
        
        result = certificate_service.request_certificate(
            user_id=1,
            domains=['example.com'],
            server_id=1
        )
        
        assert result['success'] == False
        assert '服务器不存在或无权限' in result['error']
    
    @patch('services.certificate_service.User')
    @patch('services.certificate_service.Server')
    @patch('services.certificate_service.Certificate')
    def test_request_certificate_domain_exists(self, mock_cert_class, mock_server_class,
                                             mock_user_class, certificate_service,
                                             mock_user, mock_server, mock_certificate):
        """测试域名已存在证书的情况"""
        mock_user_class.get_by_id.return_value = mock_user
        mock_server_class.get_by_id.return_value = mock_server
        mock_cert_class.get_by_domain.return_value = mock_certificate
        
        result = certificate_service.request_certificate(
            user_id=1,
            domains=['example.com'],
            server_id=1
        )
        
        assert result['success'] == False
        assert '已存在有效证书' in result['error']
    
    @patch('services.certificate_service.Certificate')
    @patch('services.certificate_service.User')
    def test_renew_certificate_success(self, mock_user_class, mock_cert_class,
                                     certificate_service, mock_user, mock_certificate):
        """测试成功续期证书"""
        mock_cert_class.get_by_id.return_value = mock_certificate
        mock_user_class.get_by_id.return_value = mock_user
        
        # 模拟ACME管理器
        certificate_service.acme_manager.renew_certificate.return_value = {
            'success': True,
            'renewed': True,
            'cert_info': {
                'not_valid_after': datetime.now() + timedelta(days=90)
            }
        }
        
        result = certificate_service.renew_certificate(1, 1)
        
        assert result['success'] == True
        assert result['renewed'] == True
        
        # 验证证书更新被调用
        mock_certificate.update.assert_called_once()
    
    @patch('services.certificate_service.Certificate')
    def test_renew_certificate_not_found(self, mock_cert_class, certificate_service):
        """测试证书不存在的情况"""
        mock_cert_class.get_by_id.return_value = None
        
        result = certificate_service.renew_certificate(999, 1)
        
        assert result['success'] == False
        assert '证书不存在' in result['error']
    
    @patch('services.certificate_service.Certificate')
    @patch('services.certificate_service.User')
    def test_renew_certificate_permission_denied(self, mock_user_class, mock_cert_class,
                                                certificate_service, mock_user, mock_certificate):
        """测试续期证书权限不足的情况"""
        # 设置证书属于不同用户
        mock_certificate.user_id = 999
        mock_cert_class.get_by_id.return_value = mock_certificate
        mock_user_class.get_by_id.return_value = mock_user
        
        result = certificate_service.renew_certificate(1, 1)
        
        assert result['success'] == False
        assert '无权限操作此证书' in result['error']
    
    @patch('services.certificate_service.Certificate')
    @patch('services.certificate_service.User')
    def test_revoke_certificate_success(self, mock_user_class, mock_cert_class,
                                      certificate_service, mock_user, mock_certificate):
        """测试成功撤销证书"""
        mock_cert_class.get_by_id.return_value = mock_certificate
        mock_user_class.get_by_id.return_value = mock_user
        
        # 模拟ACME客户端
        mock_client = MagicMock()
        mock_client.revoke_certificate.return_value = {'success': True}
        certificate_service.acme_manager.get_client.return_value = mock_client
        
        result = certificate_service.revoke_certificate(1, 1)
        
        assert result['success'] == True
        
        # 验证证书状态更新
        mock_certificate.update.assert_called_once()
        mock_client.revoke_certificate.assert_called_once()
    
    @patch('services.certificate_service.Certificate')
    def test_revoke_certificate_not_found(self, mock_cert_class, certificate_service):
        """测试撤销不存在的证书"""
        mock_cert_class.get_by_id.return_value = None
        
        result = certificate_service.revoke_certificate(999, 1)
        
        assert result['success'] == False
        assert '证书不存在' in result['error']
    
    @patch('services.certificate_service.Certificate')
    def test_auto_renew_certificates(self, mock_cert_class, certificate_service):
        """测试自动续期证书"""
        # 模拟需要续期的证书列表
        mock_certificates = [
            MagicMock(id=1, domain='example.com', auto_renew=True, user_id=1),
            MagicMock(id=2, domain='test.com', auto_renew=False, user_id=1),
            MagicMock(id=3, domain='demo.com', auto_renew=True, user_id=2)
        ]
        mock_cert_class.get_expiring_certificates.return_value = mock_certificates
        
        # 模拟续期结果
        def mock_renew_side_effect(cert_id, user_id):
            if cert_id == 1:
                return {'success': True, 'renewed': True}
            elif cert_id == 3:
                return {'success': False, 'error': '续期失败'}
            else:
                return {'success': True, 'renewed': False}
        
        with patch.object(certificate_service, 'renew_certificate', side_effect=mock_renew_side_effect):
            result = certificate_service.auto_renew_certificates()
        
        assert result['success'] == True
        assert result['total'] == 3
        assert len(result['renewed']) == 1
        assert len(result['skipped']) == 1
        assert len(result['failed']) == 1
    
    @patch('services.certificate_service.Certificate')
    def test_get_certificate_status_success(self, mock_cert_class, certificate_service, mock_certificate):
        """测试获取证书状态成功"""
        mock_cert_class.get_by_id.return_value = mock_certificate
        
        # 模拟ACME客户端状态
        mock_client = MagicMock()
        mock_client.get_certificate_status.return_value = {'exists': True, 'status': 'valid'}
        certificate_service.acme_manager.get_client.return_value = mock_client
        
        result = certificate_service.get_certificate_status(1)
        
        assert result['success'] == True
        assert 'certificate' in result
        assert 'acme_status' in result
        assert result['certificate']['status'] == 'valid'
    
    @patch('services.certificate_service.Certificate')
    def test_get_certificate_status_not_found(self, mock_cert_class, certificate_service):
        """测试获取不存在证书的状态"""
        mock_cert_class.get_by_id.return_value = None
        
        result = certificate_service.get_certificate_status(999)
        
        assert result['success'] == False
        assert '证书不存在' in result['error']
    
    def test_get_supported_cas(self, certificate_service):
        """测试获取支持的CA列表"""
        # 模拟ACME管理器返回的CA列表
        mock_cas = [
            {'name': 'letsencrypt', 'display_name': 'Let\'s Encrypt'},
            {'name': 'zerossl', 'display_name': 'ZeroSSL'}
        ]
        certificate_service.acme_manager.get_supported_cas.return_value = mock_cas
        
        result = certificate_service.get_supported_cas()
        
        assert result == mock_cas
        certificate_service.acme_manager.get_supported_cas.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
