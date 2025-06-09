"""
证书服务全面测试
测试证书申请、续期、部署等核心功能
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src'))

from services.certificate_service import CertificateService
from utils.exceptions import (
    ErrorCode, ValidationError, CertificateError, 
    ACMEError, ResourceNotFoundError
)


class TestCertificateService:
    """证书服务测试类"""
    
    @pytest.fixture
    def certificate_service(self, mock_db, mock_acme_client, mock_notification_manager):
        """创建证书服务实例"""
        with patch('services.certificate_service.db', mock_db), \
             patch('services.certificate_service.ACMEManager', return_value=mock_acme_client), \
             patch('services.certificate_service.NotificationManager', return_value=mock_notification_manager):
            service = CertificateService()
            return service
    
    def test_request_certificate_success(self, certificate_service, mock_acme_client, sample_certificate_data):
        """测试证书申请成功"""
        # 准备测试数据
        user_id = 1
        domains = ['test.example.com']
        server_id = 1
        
        # 模拟ACME客户端返回成功结果
        mock_acme_client.request_certificate.return_value = {
            'success': True,
            'certificate': 'test_certificate_content',
            'private_key': 'test_private_key',
            'domains': domains,
            'cert_info': {
                'expires_at': '2024-12-31T23:59:59',
                'issuer': 'Let\'s Encrypt'
            }
        }
        
        # 模拟数据库操作
        with patch('models.Certificate') as mock_cert_model:
            mock_cert_model.create.return_value = Mock(id=1, domain=domains[0])
            
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
            
            # 验证ACME客户端被正确调用
            mock_acme_client.request_certificate.assert_called_once_with(
                domains, 'http'
            )
            
            # 验证数据库创建操作
            mock_cert_model.create.assert_called_once()
    
    def test_request_certificate_validation_error(self, certificate_service):
        """测试证书申请参数验证错误"""
        # 测试空域名列表
        with pytest.raises(ValidationError) as exc_info:
            certificate_service.request_certificate(
                user_id=1,
                domains=[],
                server_id=1
            )
        assert exc_info.value.error_code == ErrorCode.VALIDATION_ERROR
        
        # 测试无效域名格式
        with pytest.raises(ValidationError) as exc_info:
            certificate_service.request_certificate(
                user_id=1,
                domains=['invalid..domain'],
                server_id=1
            )
        assert 'domain' in str(exc_info.value.message).lower()
    
    def test_request_certificate_acme_error(self, certificate_service, mock_acme_client):
        """测试ACME错误处理"""
        # 模拟ACME客户端抛出异常
        mock_acme_client.request_certificate.side_effect = ACMEError(
            ErrorCode.ACME_DNS_ERROR,
            "DNS解析失败",
            acme_details={'domain': 'test.example.com'}
        )
        
        # 执行测试并验证异常
        with pytest.raises(ACMEError) as exc_info:
            certificate_service.request_certificate(
                user_id=1,
                domains=['test.example.com'],
                server_id=1
            )
        
        assert exc_info.value.error_code == ErrorCode.ACME_DNS_ERROR
        assert 'DNS' in exc_info.value.message
    
    def test_renew_certificate_success(self, certificate_service, mock_acme_client):
        """测试证书续期成功"""
        certificate_id = 1
        
        # 模拟现有证书
        mock_certificate = Mock()
        mock_certificate.id = certificate_id
        mock_certificate.domain = 'test.example.com'
        mock_certificate.ca_type = 'letsencrypt'
        mock_certificate.server_id = 1
        mock_certificate.status = 'valid'
        mock_certificate.save = Mock()
        
        # 模拟ACME续期成功
        mock_acme_client.request_certificate.return_value = {
            'success': True,
            'certificate': 'renewed_certificate_content',
            'private_key': 'renewed_private_key',
            'domains': ['test.example.com'],
            'cert_info': {
                'expires_at': '2025-12-31T23:59:59',
                'issuer': 'Let\'s Encrypt'
            }
        }
        
        with patch('models.Certificate.get_by_id', return_value=mock_certificate):
            # 执行测试
            result = certificate_service.renew_certificate(certificate_id)
            
            # 验证结果
            assert result['success'] is True
            assert result['certificate_id'] == certificate_id
            assert 'expires_at' in result
            
            # 验证证书对象被更新
            mock_certificate.save.assert_called_once()
    
    def test_renew_certificate_not_found(self, certificate_service):
        """测试续期不存在的证书"""
        with patch('models.Certificate.get_by_id', return_value=None):
            with pytest.raises(ResourceNotFoundError) as exc_info:
                certificate_service.renew_certificate(999)
            
            assert exc_info.value.error_code == ErrorCode.NOT_FOUND
            assert '证书' in exc_info.value.message
    
    def test_deploy_certificate_success(self, certificate_service):
        """测试证书部署成功"""
        certificate_id = 1
        deployment_config = {
            'server_type': 'nginx',
            'config_path': '/etc/nginx/ssl/',
            'reload_command': 'systemctl reload nginx'
        }
        
        # 模拟证书对象
        mock_certificate = Mock()
        mock_certificate.id = certificate_id
        mock_certificate.certificate = 'test_certificate_content'
        mock_certificate.private_key = 'test_private_key'
        mock_certificate.domain = 'test.example.com'
        mock_certificate.add_deployment = Mock()
        
        with patch('models.Certificate.get_by_id', return_value=mock_certificate), \
             patch('services.certificate_service.deploy_to_server') as mock_deploy:
            
            mock_deploy.return_value = {
                'success': True,
                'deployed_files': [
                    '/etc/nginx/ssl/test.example.com.crt',
                    '/etc/nginx/ssl/test.example.com.key'
                ]
            }
            
            # 执行测试
            result = certificate_service.deploy_certificate(
                certificate_id, deployment_config
            )
            
            # 验证结果
            assert result['success'] is True
            assert 'deployed_files' in result
            
            # 验证部署函数被调用
            mock_deploy.assert_called_once()
            
            # 验证部署记录被添加
            mock_certificate.add_deployment.assert_called_once()
    
    def test_deploy_certificate_failure(self, certificate_service):
        """测试证书部署失败"""
        certificate_id = 1
        deployment_config = {'server_type': 'nginx'}
        
        mock_certificate = Mock()
        mock_certificate.id = certificate_id
        
        with patch('models.Certificate.get_by_id', return_value=mock_certificate), \
             patch('services.certificate_service.deploy_to_server') as mock_deploy:
            
            mock_deploy.side_effect = Exception("部署失败")
            
            # 执行测试并验证异常
            with pytest.raises(CertificateError) as exc_info:
                certificate_service.deploy_certificate(
                    certificate_id, deployment_config
                )
            
            assert exc_info.value.error_code == ErrorCode.CERTIFICATE_DEPLOYMENT_FAILED
    
    def test_revoke_certificate_success(self, certificate_service, mock_acme_client):
        """测试证书撤销成功"""
        certificate_id = 1
        
        # 模拟证书对象
        mock_certificate = Mock()
        mock_certificate.id = certificate_id
        mock_certificate.certificate = 'test_certificate_content'
        mock_certificate.status = 'valid'
        mock_certificate.save = Mock()
        
        # 模拟ACME撤销成功
        mock_acme_client.revoke_certificate.return_value = {'success': True}
        
        with patch('models.Certificate.get_by_id', return_value=mock_certificate):
            # 执行测试
            result = certificate_service.revoke_certificate(certificate_id)
            
            # 验证结果
            assert result['success'] is True
            assert result['certificate_id'] == certificate_id
            
            # 验证证书状态被更新
            assert mock_certificate.status == 'revoked'
            mock_certificate.save.assert_called_once()
    
    def test_get_certificate_status(self, certificate_service):
        """测试获取证书状态"""
        certificate_id = 1
        
        # 模拟证书对象
        mock_certificate = Mock()
        mock_certificate.id = certificate_id
        mock_certificate.domain = 'test.example.com'
        mock_certificate.status = 'valid'
        mock_certificate.expires_at = datetime.now() + timedelta(days=30)
        mock_certificate.to_dict.return_value = {
            'id': certificate_id,
            'domain': 'test.example.com',
            'status': 'valid',
            'expires_at': '2024-12-31T23:59:59'
        }
        
        with patch('models.Certificate.get_by_id', return_value=mock_certificate):
            # 执行测试
            result = certificate_service.get_certificate_status(certificate_id)
            
            # 验证结果
            assert result['id'] == certificate_id
            assert result['domain'] == 'test.example.com'
            assert result['status'] == 'valid'
    
    def test_list_certificates(self, certificate_service, mock_db):
        """测试证书列表查询"""
        user_id = 1
        page = 1
        limit = 10
        
        # 模拟数据库查询结果
        mock_certificates = [
            Mock(to_dict=lambda: {'id': 1, 'domain': 'test1.example.com'}),
            Mock(to_dict=lambda: {'id': 2, 'domain': 'test2.example.com'})
        ]
        
        with patch('models.Certificate.get_by_user', return_value=(mock_certificates, 2)):
            # 执行测试
            result = certificate_service.list_certificates(
                user_id=user_id,
                page=page,
                limit=limit
            )
            
            # 验证结果
            assert result['total'] == 2
            assert result['page'] == page
            assert result['limit'] == limit
            assert len(result['items']) == 2
            assert result['items'][0]['domain'] == 'test1.example.com'
    
    def test_check_expiring_certificates(self, certificate_service, mock_notification_manager):
        """测试检查即将过期的证书"""
        days_before = 30
        
        # 模拟即将过期的证书
        expiring_cert = Mock()
        expiring_cert.id = 1
        expiring_cert.domain = 'expiring.example.com'
        expiring_cert.expires_at = datetime.now() + timedelta(days=7)
        expiring_cert.server.name = 'test-server'
        
        with patch('models.Certificate.get_expiring', return_value=[expiring_cert]):
            # 执行测试
            result = certificate_service.check_expiring_certificates(days_before)
            
            # 验证结果
            assert result['checked'] == 1
            assert result['expiring'] == 1
            assert len(result['certificates']) == 1
            
            # 验证通知被发送
            mock_notification_manager.send_notification.assert_called()
    
    def test_get_supported_cas(self, certificate_service):
        """测试获取支持的CA列表"""
        result = certificate_service.get_supported_cas()
        
        # 验证结果
        assert isinstance(result, list)
        assert len(result) > 0
        
        # 验证CA信息结构
        ca = result[0]
        assert 'name' in ca
        assert 'display_name' in ca
        assert 'description' in ca
        assert 'directory_url' in ca
    
    def test_validate_domain_ownership(self, certificate_service):
        """测试域名所有权验证"""
        domain = 'test.example.com'
        validation_method = 'http'
        
        with patch('services.certificate_service.validate_domain_http') as mock_validate:
            mock_validate.return_value = True
            
            # 执行测试
            result = certificate_service.validate_domain_ownership(
                domain, validation_method
            )
            
            # 验证结果
            assert result is True
            mock_validate.assert_called_once_with(domain)
    
    def test_certificate_health_check(self, certificate_service):
        """测试证书健康检查"""
        certificate_id = 1
        
        # 模拟证书对象
        mock_certificate = Mock()
        mock_certificate.id = certificate_id
        mock_certificate.domain = 'test.example.com'
        mock_certificate.certificate = 'test_certificate_content'
        mock_certificate.expires_at = datetime.now() + timedelta(days=30)
        
        with patch('models.Certificate.get_by_id', return_value=mock_certificate), \
             patch('services.certificate_service.check_certificate_validity') as mock_check:
            
            mock_check.return_value = {
                'valid': True,
                'days_remaining': 30,
                'issuer': 'Let\'s Encrypt',
                'signature_algorithm': 'SHA256withRSA'
            }
            
            # 执行测试
            result = certificate_service.certificate_health_check(certificate_id)
            
            # 验证结果
            assert result['certificate_id'] == certificate_id
            assert result['domain'] == 'test.example.com'
            assert result['health_status']['valid'] is True
            assert result['health_status']['days_remaining'] == 30
    
    def test_batch_renew_certificates(self, certificate_service, mock_acme_client):
        """测试批量续期证书"""
        certificate_ids = [1, 2, 3]
        
        # 模拟证书对象
        mock_certificates = []
        for cert_id in certificate_ids:
            mock_cert = Mock()
            mock_cert.id = cert_id
            mock_cert.domain = f'test{cert_id}.example.com'
            mock_cert.ca_type = 'letsencrypt'
            mock_cert.save = Mock()
            mock_certificates.append(mock_cert)
        
        # 模拟ACME续期成功
        mock_acme_client.request_certificate.return_value = {
            'success': True,
            'certificate': 'renewed_certificate',
            'private_key': 'renewed_key',
            'domains': ['test.example.com']
        }
        
        with patch('models.Certificate.get_by_id', side_effect=mock_certificates):
            # 执行测试
            result = certificate_service.batch_renew_certificates(certificate_ids)
            
            # 验证结果
            assert result['total'] == 3
            assert result['successful'] == 3
            assert result['failed'] == 0
            assert len(result['results']) == 3
