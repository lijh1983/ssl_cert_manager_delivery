"""
pytest配置文件
提供测试夹具和通用测试工具
"""
import os
import sys
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

# 设置测试环境变量
os.environ['ENVIRONMENT'] = 'test'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test_secret_key'
os.environ['LOG_LEVEL'] = 'DEBUG'


@pytest.fixture(scope='session')
def test_app():
    """创建测试Flask应用"""
    from app import app
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['DATABASE_URL'] = 'sqlite:///:memory:'
    
    with app.app_context():
        yield app


@pytest.fixture
def client(test_app):
    """创建测试客户端"""
    return test_app.test_client()


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_db():
    """模拟数据库"""
    with patch('models.db') as mock:
        mock.connect.return_value = None
        mock.close.return_value = None
        mock.commit.return_value = None
        mock.fetchone.return_value = None
        mock.fetchall.return_value = []
        mock.insert.return_value = 1
        mock.update.return_value = True
        mock.delete.return_value = True
        yield mock


@pytest.fixture
def mock_acme_client():
    """模拟ACME客户端"""
    with patch('services.acme_client.ACMEManager') as mock:
        instance = Mock()
        instance.initialize.return_value = True
        instance.request_certificate.return_value = {
            'success': True,
            'certificate': 'test_cert',
            'private_key': 'test_key',
            'domains': ['test.example.com']
        }
        instance.revoke_certificate.return_value = {'success': True}
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_notification_manager():
    """模拟通知管理器"""
    with patch('services.notification.NotificationManager') as mock:
        instance = Mock()
        instance.send_notification.return_value = {
            'success': True,
            'sent': ['email'],
            'failed': []
        }
        mock.return_value = instance
        yield instance


@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        'id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
        'password_hash': 'hashed_password',
        'is_admin': False,
        'created_at': '2024-01-01T00:00:00',
        'updated_at': '2024-01-01T00:00:00'
    }


@pytest.fixture
def sample_server_data():
    """示例服务器数据"""
    return {
        'id': 1,
        'name': 'test-server',
        'ip': '192.168.1.100',
        'token': 'test_token',
        'user_id': 1,
        'status': 'online',
        'auto_renew': True,
        'created_at': '2024-01-01T00:00:00',
        'updated_at': '2024-01-01T00:00:00'
    }


@pytest.fixture
def sample_certificate_data():
    """示例证书数据"""
    return {
        'id': 1,
        'domain': 'test.example.com',
        'type': 'single',
        'server_id': 1,
        'ca_type': 'letsencrypt',
        'status': 'valid',
        'certificate': 'test_certificate_content',
        'private_key': 'test_private_key',
        'expires_at': '2024-12-31T23:59:59',
        'created_at': '2024-01-01T00:00:00',
        'updated_at': '2024-01-01T00:00:00'
    }


@pytest.fixture
def auth_headers():
    """认证头部"""
    return {
        'Authorization': 'Bearer test_token',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def mock_jwt_token():
    """模拟JWT令牌"""
    with patch('utils.auth.verify_token') as mock:
        mock.return_value = {'user_id': 1, 'username': 'testuser'}
        yield mock


@pytest.fixture
def mock_logger():
    """模拟日志记录器"""
    with patch('utils.logging_config.get_logger') as mock:
        logger_instance = Mock()
        logger_instance.info.return_value = None
        logger_instance.warning.return_value = None
        logger_instance.error.return_value = None
        logger_instance.debug.return_value = None
        logger_instance.audit.return_value = None
        logger_instance.performance.return_value = None
        logger_instance.security.return_value = None
        mock.return_value = logger_instance
        yield logger_instance


@pytest.fixture
def mock_config():
    """模拟配置"""
    with patch('utils.config_manager.get_config') as mock:
        config = Mock()
        config.app_name = 'SSL Certificate Manager Test'
        config.version = '1.0.0'
        config.environment = 'test'
        config.debug = True
        config.host = '127.0.0.1'
        config.port = 8000
        
        # 数据库配置
        config.database.url = 'sqlite:///:memory:'
        config.database.echo = False
        
        # 安全配置
        config.security.secret_key = 'test_secret_key'
        config.security.jwt_expiration = 3600
        config.security.password_min_length = 8
        
        # ACME配置
        config.acme.default_ca = 'letsencrypt'
        config.acme.account_email = 'test@example.com'
        config.acme.key_size = 2048
        
        # 日志配置
        config.logging.level = 'DEBUG'
        config.logging.file_path = '/tmp/test.log'
        config.logging.console_enabled = True
        
        mock.return_value = config
        yield config


class TestDataFactory:
    """测试数据工厂"""
    
    @staticmethod
    def create_user(**kwargs):
        """创建用户数据"""
        default_data = {
            'id': 1,
            'username': 'testuser',
            'email': 'test@example.com',
            'password_hash': 'hashed_password',
            'is_admin': False,
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00'
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_server(**kwargs):
        """创建服务器数据"""
        default_data = {
            'id': 1,
            'name': 'test-server',
            'ip': '192.168.1.100',
            'token': 'test_token',
            'user_id': 1,
            'status': 'online',
            'auto_renew': True,
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00'
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_certificate(**kwargs):
        """创建证书数据"""
        default_data = {
            'id': 1,
            'domain': 'test.example.com',
            'type': 'single',
            'server_id': 1,
            'ca_type': 'letsencrypt',
            'status': 'valid',
            'certificate': 'test_certificate_content',
            'private_key': 'test_private_key',
            'expires_at': '2024-12-31T23:59:59',
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00'
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_alert(**kwargs):
        """创建告警数据"""
        default_data = {
            'id': 1,
            'type': 'certificate_expiring',
            'severity': 'warning',
            'title': '证书即将过期',
            'message': '证书test.example.com将在7天后过期',
            'status': 'active',
            'certificate_id': 1,
            'server_id': 1,
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00'
        }
        default_data.update(kwargs)
        return default_data


@pytest.fixture
def test_data_factory():
    """测试数据工厂夹具"""
    return TestDataFactory


# 测试工具函数
def assert_response_success(response, expected_code=200):
    """断言响应成功"""
    assert response.status_code == expected_code
    data = response.get_json()
    assert data['code'] == expected_code
    assert 'message' in data
    assert 'data' in data
    return data


def assert_response_error(response, expected_code=400):
    """断言响应错误"""
    assert response.status_code == expected_code
    data = response.get_json()
    assert data['code'] == expected_code
    assert 'message' in data
    return data


def assert_validation_error(response, field_name=None):
    """断言验证错误"""
    data = assert_response_error(response, 422)
    if field_name:
        assert 'details' in data
        assert 'field_errors' in data['details']
        assert field_name in data['details']['field_errors']
    return data


# ==================== 稳定性测试专用夹具 ====================

@pytest.fixture
def performance_monitor():
    """性能监控器"""
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.response_times = []
            self.memory_samples = []

        def start(self):
            import time
            import psutil
            self.start_time = time.time()
            self.initial_memory = psutil.Process().memory_info().rss / 1024 / 1024

        def end(self):
            import time
            import psutil
            self.end_time = time.time()
            self.final_memory = psutil.Process().memory_info().rss / 1024 / 1024

        def add_response_time(self, response_time):
            self.response_times.append(response_time)

        def get_stats(self):
            if not self.response_times:
                return {}

            import statistics
            return {
                'duration': self.end_time - self.start_time if self.end_time else 0,
                'memory_growth': self.final_memory - self.initial_memory if hasattr(self, 'final_memory') else 0,
                'avg_response_time': statistics.mean(self.response_times),
                'max_response_time': max(self.response_times),
                'min_response_time': min(self.response_times)
            }

    return PerformanceMonitor()


@pytest.fixture
def stability_test_config():
    """稳定性测试配置"""
    return {
        'performance': {
            'max_response_time': 5.0,
            'max_memory_growth': 100,  # MB
            'concurrent_users': 10,
            'requests_per_user': 5
        },
        'load_test': {
            'duration': 30,  # 秒
            'ramp_up_time': 5,  # 秒
            'acceptable_error_rate': 0.01  # 1%
        },
        'timeouts': {
            'acme_request': 30,
            'database_query': 5,
            'api_call': 10
        }
    }


@pytest.fixture
def mock_expiring_certificates():
    """模拟即将过期的证书"""
    from datetime import datetime, timedelta

    certificates = []
    expiry_days = [30, 15, 7, 3, 1, -1]  # 包括已过期的证书

    for i, days in enumerate(expiry_days):
        cert = Mock()
        cert.id = i + 1
        cert.domain = f'cert{i+1}.example.com'
        cert.expires_at = (datetime.now() + timedelta(days=days)).isoformat()
        cert.auto_renew = True
        cert.ca_type = 'letsencrypt'
        cert.server = Mock(name=f'server{i+1}', id=i+1)
        cert.status = 'expired' if days < 0 else 'valid'
        certificates.append(cert)

    return certificates


@pytest.fixture
def mock_deployment_configs():
    """模拟部署配置"""
    return {
        'nginx': {
            'server_type': 'nginx',
            'config_path': '/etc/nginx/ssl/',
            'cert_file': 'cert.pem',
            'key_file': 'privkey.pem',
            'reload_command': 'systemctl reload nginx'
        },
        'apache': {
            'server_type': 'apache',
            'config_path': '/etc/apache2/ssl/',
            'cert_file': 'cert.pem',
            'key_file': 'privkey.pem',
            'reload_command': 'systemctl reload apache2'
        },
        'iis': {
            'server_type': 'iis',
            'config_path': 'C:\\inetpub\\ssl\\',
            'cert_file': 'cert.pfx',
            'key_file': None,
            'reload_command': 'iisreset'
        }
    }


# ==================== 测试标记定义 ====================

# 定义自定义pytest标记
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow
pytest.mark.stability = pytest.mark.stability


# ==================== 测试跳过条件 ====================

def skip_if_no_network():
    """如果没有网络连接则跳过测试"""
    import socket
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return False
    except OSError:
        return True


def skip_if_no_docker():
    """如果没有Docker则跳过测试"""
    import subprocess
    try:
        subprocess.run(['docker', '--version'], capture_output=True, check=True)
        return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        return True


# ==================== 自动清理 ====================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """测试后自动清理"""
    yield
    # 清理临时文件、重置全局状态等
    import gc
    gc.collect()
