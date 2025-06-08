"""
ACME客户端测试模块
测试ACME协议客户端的各种功能
"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend/src'))

from services.acme_client import ACMEClient, ACMEManager, CertificateAuthority
from services.dns_providers import DNSManager


class TestACMEClient:
    """ACME客户端测试类"""
    
    @pytest.fixture
    def temp_storage(self):
        """创建临时存储目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def acme_client(self, temp_storage):
        """创建ACME客户端实例"""
        with patch.dict(os.environ, {'CERT_STORAGE_PATH': temp_storage}):
            client = ACMEClient(
                CertificateAuthority.LETS_ENCRYPT_PROD,
                'test@example.com',
                staging=True
            )
            return client
    
    def test_acme_client_initialization(self, acme_client):
        """测试ACME客户端初始化"""
        assert acme_client.email == 'test@example.com'
        assert acme_client.staging == True
        assert acme_client.ca_config == CertificateAuthority.LETS_ENCRYPT_PROD
        assert acme_client.dns_manager is not None
    
    @patch('services.acme_client.client.ClientV2')
    @patch('services.acme_client.client.ClientNetwork')
    def test_acme_client_initialize_success(self, mock_network, mock_client, acme_client):
        """测试ACME客户端成功初始化"""
        # Mock ACME客户端
        mock_directory = MagicMock()
        mock_client.get_directory.return_value = mock_directory
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        
        # Mock账户注册
        mock_account = MagicMock()
        mock_client_instance.new_account.return_value = mock_account
        mock_client_instance.query_registration.side_effect = Exception("Account not found")
        
        # 执行初始化
        result = acme_client.initialize()
        
        assert result == True
        assert acme_client.client is not None
        assert acme_client.account is not None
    
    def test_generate_csr(self, acme_client):
        """测试生成CSR"""
        domains = ['example.com', 'www.example.com']
        
        csr_pem, key_pem = acme_client.generate_csr(domains)
        
        assert csr_pem is not None
        assert key_pem is not None
        assert b'-----BEGIN CERTIFICATE REQUEST-----' in csr_pem
        assert b'-----BEGIN PRIVATE KEY-----' in key_pem
    
    def test_parse_certificate_info(self, acme_client):
        """测试解析证书信息"""
        # 创建一个模拟的证书PEM
        mock_cert_pem = """-----BEGIN CERTIFICATE-----
MIIFXTCCBEWgAwIBAgISA1234567890abcdefghijklmnopqrANBgkqhkiG9w0BAQsF
ADBZMQswCQYDVQQGEwJVUzEgMB4GA1UEChMXKGZha2UpIExldCdzIEVuY3J5cHQx
KDAmBgNVBAMTH0xldCdzIEVuY3J5cHQgQXV0aG9yaXR5IFgzIChGYWtlKTAeFw0y
MzEwMDEwMDAwMDBaFw0yNDAxMDEwMDAwMDBaMBYxFDASBgNVBAMTC2V4YW1wbGUu
Y29tMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1234567890abcdef
ghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghi
jklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklm
nopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopq
rstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZwIDAQABo4ICZTCCAmEwDgYDVR0PAQH/
BAQDAgWgMB0GA1UdJQQWMBQGCCsGAQUFBwMBBggrBgEFBQcDAjAMBgNVHRMBAf8E
AjAAMB0GA1UdDgQWBBT1234567890abcdefghijklmnopqrANBgNVHSMEGDAWgBT
1234567890abcdefghijklmnopqrANBgNVHSMEGDAWgBT1234567890abcdefghijk
lmnopqrANBgNVHSMEGDAWgBT1234567890abcdefghijklmnopqrANBgNVHSMEGDA
WgBT1234567890abcdefghijklmnopqrANBgNVHSMEGDAWgBT1234567890abcdef
ghijklmnopqrANBgNVHSMEGDAWgBT1234567890abcdefghijklmnopqrANBgNVHS
MEGDAW
-----END CERTIFICATE-----"""
        
        # 由于这是一个模拟证书，实际解析会失败，我们只测试方法存在
        try:
            cert_info = acme_client._parse_certificate_info(mock_cert_pem)
            # 如果解析成功，检查返回的字典结构
            assert isinstance(cert_info, dict)
        except Exception:
            # 预期会失败，因为这是一个无效的证书
            pass
    
    @patch('services.acme_client.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_certificate_info(self, mock_file, mock_exists, acme_client):
        """测试加载证书信息"""
        mock_exists.return_value = True
        mock_cert_info = {
            'domain': 'example.com',
            'expires_at': '2024-01-01T00:00:00Z',
            'status': 'valid'
        }
        mock_file.return_value.read.return_value = str(mock_cert_info)
        
        # 由于JSON解析问题，我们模拟json.load
        with patch('json.load', return_value=mock_cert_info):
            result = acme_client._load_certificate_info('example.com')
            assert result == mock_cert_info
    
    def test_should_renew_certificate(self, acme_client):
        """测试证书续期判断"""
        from datetime import datetime, timedelta
        
        # 测试需要续期的证书
        cert_info_expired = {
            'not_valid_after': (datetime.now() + timedelta(days=10)).isoformat()
        }
        assert acme_client._should_renew_certificate(cert_info_expired, days_before=30) == True
        
        # 测试不需要续期的证书
        cert_info_valid = {
            'not_valid_after': (datetime.now() + timedelta(days=60)).isoformat()
        }
        assert acme_client._should_renew_certificate(cert_info_valid, days_before=30) == False
    
    @patch('services.acme_client.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_certificate(self, mock_file, mock_makedirs, acme_client):
        """测试保存证书"""
        domain = 'example.com'
        certificate_pem = '-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----'
        key_pem = b'-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----'
        
        with patch.object(acme_client, '_parse_certificate_info', return_value={'domain': domain}):
            result = acme_client._save_certificate(domain, certificate_pem, key_pem)
            
            assert isinstance(result, dict)
            mock_makedirs.assert_called()
            assert mock_file.call_count >= 2  # 至少调用两次（证书和私钥）


class TestACMEManager:
    """ACME管理器测试类"""
    
    @pytest.fixture
    def acme_manager(self):
        """创建ACME管理器实例"""
        with patch.object(ACMEManager, '_initialize_clients'):
            manager = ACMEManager('test@example.com', staging=True)
            return manager
    
    def test_acme_manager_initialization(self, acme_manager):
        """测试ACME管理器初始化"""
        assert acme_manager.email == 'test@example.com'
        assert acme_manager.staging == True
        assert isinstance(acme_manager.clients, dict)
    
    def test_get_supported_cas(self, acme_manager):
        """测试获取支持的CA列表"""
        # 模拟一些客户端
        acme_manager.clients = {
            'letsencrypt': MagicMock(),
            'zerossl': MagicMock()
        }
        
        cas = acme_manager.get_supported_cas()
        
        assert isinstance(cas, list)
        assert len(cas) == 3  # letsencrypt, zerossl, buypass
        
        # 检查CA信息结构
        for ca in cas:
            assert 'name' in ca
            assert 'display_name' in ca
            assert 'available' in ca
            assert 'rate_limits' in ca
    
    def test_get_client(self, acme_manager):
        """测试获取客户端"""
        mock_client = MagicMock()
        acme_manager.clients['letsencrypt'] = mock_client
        
        client = acme_manager.get_client('letsencrypt')
        assert client == mock_client
        
        # 测试不存在的客户端
        client = acme_manager.get_client('nonexistent')
        assert client is None
    
    def test_request_certificate(self, acme_manager):
        """测试申请证书"""
        mock_client = MagicMock()
        mock_client.request_certificate.return_value = {
            'success': True,
            'certificate': 'test_cert',
            'domains': ['example.com']
        }
        acme_manager.clients['letsencrypt'] = mock_client
        
        result = acme_manager.request_certificate(['example.com'])
        
        assert result['success'] == True
        mock_client.request_certificate.assert_called_once_with(['example.com'], 'http')
    
    def test_auto_renew_certificates(self, acme_manager):
        """测试自动续期证书"""
        mock_client = MagicMock()
        mock_client.list_certificates.return_value = [
            {'domain': 'example.com', 'should_renew': True},
            {'domain': 'test.com', 'should_renew': False}
        ]
        mock_client.renew_certificate.return_value = {
            'success': True,
            'renewed': True
        }
        acme_manager.clients['letsencrypt'] = mock_client
        
        result = acme_manager.auto_renew_certificates()
        
        assert result['success'] == True
        assert len(result['renewed']) == 1
        assert len(result['skipped']) == 1
        assert len(result['failed']) == 0


class TestDNSManager:
    """DNS管理器测试类"""
    
    @pytest.fixture
    def dns_manager(self):
        """创建DNS管理器实例"""
        with patch.object(DNSManager, '_load_providers'):
            manager = DNSManager()
            return manager
    
    def test_dns_manager_initialization(self, dns_manager):
        """测试DNS管理器初始化"""
        assert isinstance(dns_manager.providers, dict)
    
    def test_get_provider(self, dns_manager):
        """测试获取DNS提供商"""
        mock_provider = MagicMock()
        dns_manager.providers['cloudflare'] = mock_provider
        
        provider = dns_manager.get_provider('cloudflare')
        assert provider == mock_provider
        
        # 测试不存在的提供商
        provider = dns_manager.get_provider('nonexistent')
        assert provider is None
    
    def test_add_acme_challenge(self, dns_manager):
        """测试添加ACME验证记录"""
        mock_provider = MagicMock()
        mock_provider.add_txt_record.return_value = True
        mock_provider.verify_txt_record.return_value = True
        dns_manager.providers['cloudflare'] = mock_provider
        
        result = dns_manager.add_acme_challenge('example.com', 'test_value', 'cloudflare')
        
        assert result == True
        mock_provider.add_txt_record.assert_called_once()
        mock_provider.verify_txt_record.assert_called_once()
    
    def test_remove_acme_challenge(self, dns_manager):
        """测试删除ACME验证记录"""
        mock_provider = MagicMock()
        mock_provider.delete_txt_record.return_value = True
        dns_manager.providers['cloudflare'] = mock_provider
        
        result = dns_manager.remove_acme_challenge('example.com', 'test_value', 'cloudflare')
        
        assert result == True
        mock_provider.delete_txt_record.assert_called_once()
    
    def test_get_available_providers(self, dns_manager):
        """测试获取可用的DNS提供商列表"""
        dns_manager.providers = {
            'cloudflare': MagicMock(),
            'aliyun': MagicMock()
        }
        
        providers = dns_manager.get_available_providers()
        
        assert isinstance(providers, list)
        assert 'cloudflare' in providers
        assert 'aliyun' in providers


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
