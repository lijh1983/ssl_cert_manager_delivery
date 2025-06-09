"""
证书部署测试
测试证书自动部署到不同Web服务器的功能
"""
import pytest
import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src'))

from services.certificate_service import CertificateService
from utils.exceptions import CertificateError, ErrorCode
from utils.logging_config import get_logger

logger = get_logger(__name__)


class TestCertificateDeployment:
    """证书部署测试类"""
    
    @pytest.fixture
    def certificate_service(self):
        """创建证书服务实例"""
        return CertificateService()
    
    @pytest.fixture
    def mock_certificate(self):
        """模拟证书对象"""
        return Mock(
            id=1,
            domain='test.example.com',
            certificate='-----BEGIN CERTIFICATE-----\nMOCK_CERTIFICATE_CONTENT\n-----END CERTIFICATE-----',
            private_key='-----BEGIN PRIVATE KEY-----\nMOCK_PRIVATE_KEY_CONTENT\n-----END PRIVATE KEY-----',
            ca_type='letsencrypt',
            expires_at=(datetime.now() + timedelta(days=90)).isoformat()
        )
    
    @pytest.fixture
    def deployment_configs(self):
        """部署配置"""
        return {
            'nginx': {
                'server_type': 'nginx',
                'config_path': '/etc/nginx/ssl/',
                'cert_file': 'cert.pem',
                'key_file': 'privkey.pem',
                'reload_command': 'systemctl reload nginx',
                'config_template': '''
server {
    listen 443 ssl;
    server_name {domain};
    ssl_certificate {cert_path};
    ssl_certificate_key {key_path};
}'''
            },
            'apache': {
                'server_type': 'apache',
                'config_path': '/etc/apache2/ssl/',
                'cert_file': 'cert.pem',
                'key_file': 'privkey.pem',
                'reload_command': 'systemctl reload apache2',
                'config_template': '''
<VirtualHost *:443>
    ServerName {domain}
    SSLEngine on
    SSLCertificateFile {cert_path}
    SSLCertificateKeyFile {key_path}
</VirtualHost>'''
            },
            'iis': {
                'server_type': 'iis',
                'config_path': 'C:\\inetpub\\ssl\\',
                'cert_file': 'cert.pfx',
                'key_file': None,  # IIS使用PFX格式
                'reload_command': 'iisreset',
                'config_template': None  # IIS通过管理界面配置
            }
        }
    
    @pytest.fixture
    def temp_ssl_dir(self):
        """创建临时SSL目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    # ==================== Nginx部署测试 ====================
    
    def test_nginx_deployment_success(self, certificate_service, mock_certificate, deployment_configs, temp_ssl_dir):
        """测试Nginx证书部署成功"""
        config = deployment_configs['nginx']
        config['config_path'] = temp_ssl_dir + '/'
        
        with patch('models.certificate.Certificate.get_by_id', return_value=mock_certificate), \
             patch('subprocess.run') as mock_subprocess, \
             patch('os.path.exists', return_value=True), \
             patch('os.makedirs'), \
             patch('builtins.open', mock_open()) as mock_file:
            
            # 模拟成功的服务重载
            mock_subprocess.return_value = Mock(returncode=0, stdout='', stderr='')
            
            # 执行部署
            result = certificate_service.deploy_certificate(mock_certificate.id, config)
            
            # 验证结果
            assert result['success'] is True
            assert 'deployed_files' in result
            assert len(result['deployed_files']) == 2  # cert.pem 和 privkey.pem
            
            # 验证文件写入
            assert mock_file.call_count >= 2  # 至少写入证书和私钥文件
            
            # 验证服务重载
            mock_subprocess.assert_called_with(
                ['systemctl', 'reload', 'nginx'],
                capture_output=True,
                text=True,
                timeout=30
            )
    
    def test_nginx_deployment_permission_denied(self, certificate_service, mock_certificate, deployment_configs):
        """测试Nginx部署权限不足"""
        config = deployment_configs['nginx']
        
        with patch('models.certificate.Certificate.get_by_id', return_value=mock_certificate), \
             patch('builtins.open', side_effect=PermissionError("Permission denied")):
            
            # 执行部署并验证异常
            with pytest.raises(CertificateError) as exc_info:
                certificate_service.deploy_certificate(mock_certificate.id, config)
            
            assert exc_info.value.error_code == ErrorCode.CERTIFICATE_DEPLOYMENT_FAILED
            assert '权限' in exc_info.value.message
    
    def test_nginx_deployment_service_reload_failure(self, certificate_service, mock_certificate, deployment_configs, temp_ssl_dir):
        """测试Nginx服务重载失败"""
        config = deployment_configs['nginx']
        config['config_path'] = temp_ssl_dir + '/'
        
        with patch('models.certificate.Certificate.get_by_id', return_value=mock_certificate), \
             patch('subprocess.run') as mock_subprocess, \
             patch('os.path.exists', return_value=True), \
             patch('os.makedirs'), \
             patch('builtins.open', mock_open()):
            
            # 模拟服务重载失败
            mock_subprocess.return_value = Mock(
                returncode=1, 
                stdout='', 
                stderr='nginx: configuration file test failed'
            )
            
            # 执行部署并验证异常
            with pytest.raises(CertificateError) as exc_info:
                certificate_service.deploy_certificate(mock_certificate.id, config)
            
            assert exc_info.value.error_code == ErrorCode.CERTIFICATE_DEPLOYMENT_FAILED
            assert 'nginx' in exc_info.value.message.lower()

    # ==================== Apache部署测试 ====================
    
    def test_apache_deployment_success(self, certificate_service, mock_certificate, deployment_configs, temp_ssl_dir):
        """测试Apache证书部署成功"""
        config = deployment_configs['apache']
        config['config_path'] = temp_ssl_dir + '/'
        
        with patch('models.certificate.Certificate.get_by_id', return_value=mock_certificate), \
             patch('subprocess.run') as mock_subprocess, \
             patch('os.path.exists', return_value=True), \
             patch('os.makedirs'), \
             patch('builtins.open', mock_open()) as mock_file:
            
            # 模拟成功的服务重载
            mock_subprocess.return_value = Mock(returncode=0, stdout='', stderr='')
            
            # 执行部署
            result = certificate_service.deploy_certificate(mock_certificate.id, config)
            
            # 验证结果
            assert result['success'] is True
            assert 'deployed_files' in result
            
            # 验证Apache重载命令
            mock_subprocess.assert_called_with(
                ['systemctl', 'reload', 'apache2'],
                capture_output=True,
                text=True,
                timeout=30
            )
    
    def test_apache_deployment_config_test_failure(self, certificate_service, mock_certificate, deployment_configs, temp_ssl_dir):
        """测试Apache配置测试失败"""
        config = deployment_configs['apache']
        config['config_path'] = temp_ssl_dir + '/'
        
        with patch('models.certificate.Certificate.get_by_id', return_value=mock_certificate), \
             patch('subprocess.run') as mock_subprocess, \
             patch('os.path.exists', return_value=True), \
             patch('os.makedirs'), \
             patch('builtins.open', mock_open()):
            
            # 模拟配置测试失败
            mock_subprocess.side_effect = [
                Mock(returncode=1, stdout='', stderr='Syntax error on line 10'),  # 配置测试
                Mock(returncode=0, stdout='', stderr='')  # 可能的回滚操作
            ]
            
            # 执行部署并验证异常
            with pytest.raises(CertificateError) as exc_info:
                certificate_service.deploy_certificate(mock_certificate.id, config)
            
            assert exc_info.value.error_code == ErrorCode.CERTIFICATE_DEPLOYMENT_FAILED

    # ==================== IIS部署测试 ====================
    
    def test_iis_deployment_success(self, certificate_service, mock_certificate, deployment_configs, temp_ssl_dir):
        """测试IIS证书部署成功"""
        config = deployment_configs['iis']
        config['config_path'] = temp_ssl_dir + '\\'
        
        with patch('models.certificate.Certificate.get_by_id', return_value=mock_certificate), \
             patch('subprocess.run') as mock_subprocess, \
             patch('os.path.exists', return_value=True), \
             patch('os.makedirs'), \
             patch('builtins.open', mock_open()), \
             patch('services.certificate_service.convert_to_pfx') as mock_convert:
            
            # 模拟PFX转换成功
            mock_convert.return_value = b'mock_pfx_content'
            
            # 模拟IIS重启成功
            mock_subprocess.return_value = Mock(returncode=0, stdout='', stderr='')
            
            # 执行部署
            result = certificate_service.deploy_certificate(mock_certificate.id, config)
            
            # 验证结果
            assert result['success'] is True
            assert 'deployed_files' in result
            
            # 验证PFX转换被调用
            mock_convert.assert_called_once()
            
            # 验证IIS重启命令
            mock_subprocess.assert_called_with(
                ['iisreset'],
                capture_output=True,
                text=True,
                timeout=60
            )

    # ==================== 证书链完整性测试 ====================
    
    def test_certificate_chain_validation(self, certificate_service, deployment_configs, temp_ssl_dir):
        """测试证书链完整性检查"""
        # 创建包含完整证书链的证书
        full_chain_cert = Mock(
            id=2,
            domain='chain.example.com',
            certificate='''-----BEGIN CERTIFICATE-----
MOCK_LEAF_CERTIFICATE_CONTENT
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MOCK_INTERMEDIATE_CERTIFICATE_CONTENT
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MOCK_ROOT_CERTIFICATE_CONTENT
-----END CERTIFICATE-----''',
            private_key='-----BEGIN PRIVATE KEY-----\nMOCK_PRIVATE_KEY_CONTENT\n-----END PRIVATE KEY-----'
        )
        
        config = deployment_configs['nginx']
        config['config_path'] = temp_ssl_dir + '/'
        config['validate_chain'] = True
        
        with patch('models.certificate.Certificate.get_by_id', return_value=full_chain_cert), \
             patch('subprocess.run') as mock_subprocess, \
             patch('os.path.exists', return_value=True), \
             patch('os.makedirs'), \
             patch('builtins.open', mock_open()), \
             patch('services.certificate_service.validate_certificate_chain') as mock_validate:
            
            # 模拟证书链验证成功
            mock_validate.return_value = True
            mock_subprocess.return_value = Mock(returncode=0, stdout='', stderr='')
            
            # 执行部署
            result = certificate_service.deploy_certificate(full_chain_cert.id, config)
            
            # 验证结果
            assert result['success'] is True
            
            # 验证证书链验证被调用
            mock_validate.assert_called_once()
    
    def test_certificate_chain_validation_failure(self, certificate_service, deployment_configs, temp_ssl_dir):
        """测试证书链验证失败"""
        # 创建不完整证书链的证书
        incomplete_chain_cert = Mock(
            id=3,
            domain='incomplete.example.com',
            certificate='-----BEGIN CERTIFICATE-----\nMOCK_LEAF_ONLY_CONTENT\n-----END CERTIFICATE-----',
            private_key='-----BEGIN PRIVATE KEY-----\nMOCK_PRIVATE_KEY_CONTENT\n-----END PRIVATE KEY-----'
        )
        
        config = deployment_configs['nginx']
        config['config_path'] = temp_ssl_dir + '/'
        config['validate_chain'] = True
        
        with patch('models.certificate.Certificate.get_by_id', return_value=incomplete_chain_cert), \
             patch('services.certificate_service.validate_certificate_chain') as mock_validate:
            
            # 模拟证书链验证失败
            mock_validate.return_value = False
            
            # 执行部署并验证异常
            with pytest.raises(CertificateError) as exc_info:
                certificate_service.deploy_certificate(incomplete_chain_cert.id, config)
            
            assert exc_info.value.error_code == ErrorCode.CERTIFICATE_DEPLOYMENT_FAILED
            assert '证书链' in exc_info.value.message

    # ==================== SSL/TLS配置安全性测试 ====================
    
    def test_ssl_security_configuration_validation(self, certificate_service, mock_certificate, deployment_configs, temp_ssl_dir):
        """测试SSL/TLS配置安全性验证"""
        config = deployment_configs['nginx']
        config['config_path'] = temp_ssl_dir + '/'
        config['security_check'] = True
        config['min_tls_version'] = '1.2'
        config['allowed_ciphers'] = [
            'ECDHE-RSA-AES256-GCM-SHA384',
            'ECDHE-RSA-AES128-GCM-SHA256'
        ]
        
        with patch('models.certificate.Certificate.get_by_id', return_value=mock_certificate), \
             patch('subprocess.run') as mock_subprocess, \
             patch('os.path.exists', return_value=True), \
             patch('os.makedirs'), \
             patch('builtins.open', mock_open()), \
             patch('services.certificate_service.validate_ssl_config') as mock_validate_ssl:
            
            # 模拟SSL配置验证成功
            mock_validate_ssl.return_value = {
                'valid': True,
                'tls_version': '1.2',
                'cipher_suites': ['ECDHE-RSA-AES256-GCM-SHA384'],
                'security_score': 95
            }
            mock_subprocess.return_value = Mock(returncode=0, stdout='', stderr='')
            
            # 执行部署
            result = certificate_service.deploy_certificate(mock_certificate.id, config)
            
            # 验证结果
            assert result['success'] is True
            assert 'security_validation' in result
            assert result['security_validation']['valid'] is True
            
            # 验证SSL配置验证被调用
            mock_validate_ssl.assert_called_once()
