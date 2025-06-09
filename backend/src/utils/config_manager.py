"""
统一配置管理模块
支持从环境变量、配置文件读取配置
"""
import os
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str = 'sqlite:///ssl_cert_manager.db'
    echo: bool = False


@dataclass
class SecurityConfig:
    """安全配置"""
    secret_key: str = 'dev_secret_key_change_in_production'
    jwt_expiration: int = 3600
    password_min_length: int = 8


@dataclass
class ACMEConfig:
    """ACME配置"""
    default_ca: str = 'letsencrypt'
    account_email: str = ''
    key_size: int = 2048
    challenge_timeout: int = 300


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = 'INFO'
    file_path: str = '/tmp/logs/ssl_cert_manager.log'
    console_enabled: bool = True


@dataclass
class AppConfig:
    """应用配置"""
    app_name: str = 'SSL Certificate Manager'
    version: str = '1.0.0'
    environment: str = 'development'
    debug: bool = False
    host: str = '0.0.0.0'
    port: int = 8000
    
    # 子配置
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    acme: ACMEConfig = field(default_factory=ACMEConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config = AppConfig()
        self._load_from_env()
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        env_mappings = {
            'SECRET_KEY': ('security.secret_key', str),
            'JWT_EXPIRATION': ('security.jwt_expiration', int),
            'DATABASE_URL': ('database.url', str),
            'LOG_LEVEL': ('logging.level', str),
            'ACME_ACCOUNT_EMAIL': ('acme.account_email', str),
            'DEBUG': ('debug', bool),
            'HOST': ('host', str),
            'PORT': ('port', int),
        }
        
        for env_key, (config_path, value_type) in env_mappings.items():
            env_value = os.environ.get(env_key)
            if env_value is not None:
                try:
                    # 类型转换
                    if value_type == bool:
                        value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif value_type == int:
                        value = int(env_value)
                    else:
                        value = env_value
                    
                    # 设置配置值
                    self._set_nested_value(self.config, config_path, value)
                    
                except (ValueError, TypeError):
                    pass  # 忽略转换错误
    
    def _set_nested_value(self, obj: Any, path: str, value: Any):
        """设置嵌套属性值"""
        parts = path.split('.')
        for part in parts[:-1]:
            obj = getattr(obj, part)
        setattr(obj, parts[-1], value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        try:
            parts = key.split('.')
            value = self.config
            for part in parts:
                value = getattr(value, part)
            return value
        except AttributeError:
            return default

    def set(self, key: str, value: Any):
        """设置配置值"""
        self._set_nested_value(self.config, key, value)


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """获取应用配置"""
    return config_manager.config


def get_security_config() -> SecurityConfig:
    """获取安全配置"""
    return config_manager.config.security


def get_acme_config() -> ACMEConfig:
    """获取ACME配置"""
    return config_manager.config.acme


def get_logging_config() -> LoggingConfig:
    """获取日志配置"""
    return config_manager.config.logging


def get_notification_config():
    """获取通知配置"""
    # 返回默认通知配置
    class NotificationConfig:
        def __init__(self):
            self.email = type('obj', (object,), {
                'enabled': False,
                'smtp_host': 'localhost',
                'smtp_port': 587,
                'smtp_use_tls': True,
                'username': '',
                'password': '',
                'recipients': []
            })()
            self.webhook = type('obj', (object,), {
                'enabled': False,
                'urls': []
            })()
            self.slack = type('obj', (object,), {
                'enabled': False,
                'webhook_url': ''
            })()
            self.dingtalk = type('obj', (object,), {
                'enabled': False,
                'webhook_url': ''
            })()

    return NotificationConfig()
