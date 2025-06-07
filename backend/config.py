import os
from datetime import timedelta
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """基础配置类"""
    
    # Flask基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # 数据库配置
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///ssl_cert_manager.db'
    
    # JWT配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)))
    JWT_ALGORITHM = 'HS256'
    
    # CORS配置
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # SSL证书配置
    DEFAULT_CA = os.environ.get('DEFAULT_CA', 'letsencrypt')
    ACME_DIRECTORY_URL = os.environ.get('ACME_DIRECTORY_URL', 'https://acme-v02.api.letsencrypt.org/directory')
    ACME_STAGING_URL = os.environ.get('ACME_STAGING_URL', 'https://acme-staging-v02.api.letsencrypt.org/directory')
    
    # 邮件配置
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'True').lower() == 'true'
    
    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    
    # 速率限制配置
    RATE_LIMIT_STORAGE_URL = os.environ.get('RATE_LIMIT_STORAGE_URL', 'memory://')
    RATE_LIMIT_DEFAULT = os.environ.get('RATE_LIMIT_DEFAULT', '100 per hour')
    
    # 安全配置
    BCRYPT_LOG_ROUNDS = int(os.environ.get('BCRYPT_LOG_ROUNDS', 12))
    PASSWORD_MIN_LENGTH = int(os.environ.get('PASSWORD_MIN_LENGTH', 6))
    
    # 客户端配置
    CLIENT_HEARTBEAT_INTERVAL = int(os.environ.get('CLIENT_HEARTBEAT_INTERVAL', 300))
    CLIENT_OFFLINE_THRESHOLD = int(os.environ.get('CLIENT_OFFLINE_THRESHOLD', 900))
    
    # 证书配置
    CERT_RENEWAL_DAYS = int(os.environ.get('CERT_RENEWAL_DAYS', 30))
    CERT_CLEANUP_DAYS = int(os.environ.get('CERT_CLEANUP_DAYS', 90))
    
    # Webhook配置
    WEBHOOK_TIMEOUT = int(os.environ.get('WEBHOOK_TIMEOUT', 30))
    WEBHOOK_RETRY_COUNT = int(os.environ.get('WEBHOOK_RETRY_COUNT', 3))


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False
    
    # 开发环境使用较低的加密轮数
    BCRYPT_LOG_ROUNDS = 4
    
    # 开发环境使用测试CA
    ACME_DIRECTORY_URL = Config.ACME_STAGING_URL


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    
    # 生产环境必须设置的环境变量
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # 检查必需的环境变量
        required_vars = [
            'SECRET_KEY',
            'JWT_SECRET_KEY',
            'DATABASE_URL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")


class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TESTING = True
    
    # 测试环境使用内存数据库
    DATABASE_URL = 'sqlite:///:memory:'
    
    # 测试环境使用较低的加密轮数
    BCRYPT_LOG_ROUNDS = 4
    
    # 测试环境禁用CSRF保护
    WTF_CSRF_ENABLED = False


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """获取当前配置"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
