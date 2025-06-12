#!/usr/bin/env python3
"""
SSL证书管理系统配置验证脚本
验证MySQL数据库配置和Nginx代理配置的正确性
"""

import os
import sys
import re
import socket
import logging
from typing import Dict, List, Tuple, Any
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self, env_file: str = '.env.production'):
        """初始化验证器"""
        self.env_file = env_file
        self.config = {}
        self.errors = []
        self.warnings = []
        
    def load_env_config(self) -> bool:
        """加载环境变量配置"""
        try:
            if not os.path.exists(self.env_file):
                self.errors.append(f"环境配置文件不存在: {self.env_file}")
                return False
            
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.config[key.strip()] = value.strip()
            
            logger.info(f"成功加载配置文件: {self.env_file}")
            return True
            
        except Exception as e:
            self.errors.append(f"加载配置文件失败: {e}")
            return False
    
    def validate_mysql_config(self) -> bool:
        """验证MySQL配置"""
        logger.info("验证MySQL数据库配置...")
        
        # 必需的MySQL配置项
        required_mysql_configs = [
            'MYSQL_HOST',
            'MYSQL_USERNAME',
            'MYSQL_PASSWORD',
            'MYSQL_DATABASE'
        ]
        
        # 检查必需配置
        for config_key in required_mysql_configs:
            if not self.config.get(config_key):
                self.errors.append(f"缺少必需的MySQL配置: {config_key}")
        
        # 验证MySQL主机
        mysql_host = self.config.get('MYSQL_HOST', 'localhost')
        if not self._validate_hostname(mysql_host):
            self.errors.append(f"无效的MySQL主机地址: {mysql_host}")
        
        # 验证MySQL端口
        mysql_port = self.config.get('MYSQL_PORT', '3306')
        try:
            port = int(mysql_port)
            if not (1 <= port <= 65535):
                self.errors.append(f"MySQL端口超出有效范围: {port}")
        except ValueError:
            self.errors.append(f"无效的MySQL端口: {mysql_port}")
        
        # 验证连接池配置
        pool_configs = {
            'MYSQL_POOL_SIZE': (1, 100),
            'MYSQL_MAX_OVERFLOW': (0, 200),
            'MYSQL_POOL_TIMEOUT': (1, 300),
            'MYSQL_POOL_RECYCLE': (0, 86400)
        }
        
        for config_key, (min_val, max_val) in pool_configs.items():
            value = self.config.get(config_key)
            if value:
                try:
                    int_value = int(value)
                    if not (min_val <= int_value <= max_val):
                        self.errors.append(f"{config_key} 超出有效范围 [{min_val}, {max_val}]: {int_value}")
                except ValueError:
                    self.errors.append(f"无效的{config_key}值: {value}")
        
        # 验证SSL配置
        ssl_disabled = self.config.get('MYSQL_SSL_DISABLED', 'false').lower() == 'true'
        if not ssl_disabled:
            ssl_files = ['MYSQL_SSL_CA', 'MYSQL_SSL_CERT', 'MYSQL_SSL_KEY']
            for ssl_file_key in ssl_files:
                ssl_file = self.config.get(ssl_file_key)
                if ssl_file and not os.path.exists(ssl_file):
                    self.warnings.append(f"MySQL SSL文件不存在: {ssl_file}")
        
        # 验证字符集
        charset = self.config.get('MYSQL_CHARSET', 'utf8mb4')
        if charset not in ['utf8', 'utf8mb4']:
            self.warnings.append(f"推荐使用utf8mb4字符集，当前: {charset}")
        
        return len([e for e in self.errors if 'MySQL' in e]) == 0
    
    def validate_nginx_config(self) -> bool:
        """验证Nginx配置"""
        logger.info("验证Nginx代理配置...")
        
        # 验证域名配置
        domain_name = self.config.get('DOMAIN_NAME')
        if not domain_name:
            self.errors.append("缺少域名配置: DOMAIN_NAME")
        elif not self._validate_domain(domain_name):
            self.errors.append(f"无效的域名格式: {domain_name}")
        
        # 验证SSL证书路径
        ssl_cert_path = self.config.get('SSL_CERTIFICATE_PATH')
        ssl_key_path = self.config.get('SSL_CERTIFICATE_KEY_PATH')
        
        if ssl_cert_path and not os.path.exists(ssl_cert_path):
            self.warnings.append(f"SSL证书文件不存在: {ssl_cert_path}")
        
        if ssl_key_path and not os.path.exists(ssl_key_path):
            self.warnings.append(f"SSL私钥文件不存在: {ssl_key_path}")
        
        # 验证端口配置
        port_configs = {
            'NGINX_HTTP_PORT': (1, 65535),
            'NGINX_HTTPS_PORT': (1, 65535),
            'BACKEND_PORT': (1, 65535),
            'FRONTEND_PORT': (1, 65535)
        }
        
        for config_key, (min_val, max_val) in port_configs.items():
            value = self.config.get(config_key)
            if value:
                try:
                    port = int(value)
                    if not (min_val <= port <= max_val):
                        self.errors.append(f"{config_key} 超出有效范围: {port}")
                except ValueError:
                    self.errors.append(f"无效的端口配置: {config_key}={value}")
        
        # 验证后端服务器配置
        backend_servers = self.config.get('BACKEND_UPSTREAM_SERVERS')
        if backend_servers:
            servers = backend_servers.split(',')
            for server in servers:
                server = server.strip()
                if ':' in server:
                    host, port = server.split(':', 1)
                    if not self._validate_hostname(host.strip()):
                        self.errors.append(f"无效的后端服务器地址: {host}")
                    try:
                        port_num = int(port.strip())
                        if not (1 <= port_num <= 65535):
                            self.errors.append(f"无效的后端服务器端口: {port_num}")
                    except ValueError:
                        self.errors.append(f"无效的后端服务器端口: {port}")
        
        # 验证URL配置
        url_configs = ['API_BASE_URL', 'FRONTEND_URL']
        for url_config in url_configs:
            url = self.config.get(url_config)
            if url and not self._validate_url(url):
                self.errors.append(f"无效的URL配置: {url_config}={url}")
        
        return len([e for e in self.errors if 'Nginx' in e or 'SSL' in e or 'URL' in e or '端口' in e]) == 0
    
    def validate_security_config(self) -> bool:
        """验证安全配置"""
        logger.info("验证安全配置...")
        
        # 验证密钥长度
        secret_keys = ['SECRET_KEY', 'JWT_SECRET_KEY', 'CSRF_SECRET_KEY']
        for key in secret_keys:
            value = self.config.get(key)
            if not value:
                self.errors.append(f"缺少安全密钥: {key}")
            elif len(value) < 32:
                self.warnings.append(f"安全密钥长度不足32位: {key}")
        
        # 验证密码强度
        passwords = ['MYSQL_PASSWORD', 'REDIS_PASSWORD']
        for pwd_key in passwords:
            password = self.config.get(pwd_key)
            if password and not self._validate_password_strength(password):
                self.warnings.append(f"密码强度不足: {pwd_key}")
        
        # 验证CORS配置
        cors_origins = self.config.get('CORS_ORIGINS')
        if cors_origins and cors_origins != '*':
            origins = cors_origins.split(',')
            for origin in origins:
                origin = origin.strip()
                if not self._validate_url(origin):
                    self.errors.append(f"无效的CORS源: {origin}")
        
        return len([e for e in self.errors if '密钥' in e or 'CORS' in e]) == 0
    
    def validate_file_paths(self) -> bool:
        """验证文件路径配置"""
        logger.info("验证文件路径配置...")
        
        # 验证目录路径
        directory_configs = [
            'CERT_STORAGE_PATH',
            'CERT_BACKUP_PATH',
            'BACKUP_STORAGE_PATH'
        ]
        
        for dir_config in directory_configs:
            path = self.config.get(dir_config)
            if path:
                # 检查父目录是否存在
                parent_dir = os.path.dirname(path)
                if parent_dir and not os.path.exists(parent_dir):
                    self.warnings.append(f"目录的父路径不存在: {path}")
                
                # 检查路径是否为绝对路径
                if not os.path.isabs(path):
                    self.warnings.append(f"建议使用绝对路径: {dir_config}={path}")
        
        # 验证日志文件路径
        log_file = self.config.get('LOG_FILE')
        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                self.warnings.append(f"日志目录不存在: {log_dir}")
        
        return True
    
    def validate_docker_config(self) -> bool:
        """验证Docker配置"""
        logger.info("验证Docker配置...")
        
        # 检查Docker Compose文件
        compose_files = [
            'docker-compose.production.yml',
            'docker-compose.mysql.yml'
        ]
        
        for compose_file in compose_files:
            if os.path.exists(compose_file):
                logger.info(f"找到Docker Compose文件: {compose_file}")
            else:
                self.warnings.append(f"Docker Compose文件不存在: {compose_file}")
        
        # 验证网络配置
        network_subnet = self.config.get('DOCKER_NETWORK_SUBNET', '172.20.0.0/16')
        if not self._validate_cidr(network_subnet):
            self.errors.append(f"无效的Docker网络子网: {network_subnet}")
        
        return True
    
    def _validate_hostname(self, hostname: str) -> bool:
        """验证主机名"""
        if not hostname:
            return False
        
        # 检查是否为IP地址
        try:
            socket.inet_aton(hostname)
            return True
        except socket.error:
            pass
        
        # 检查域名格式
        if len(hostname) > 255:
            return False
        
        hostname_pattern = re.compile(
            r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        )
        return bool(hostname_pattern.match(hostname))
    
    def _validate_domain(self, domain: str) -> bool:
        """验证域名"""
        if not domain:
            return False
        
        domain_pattern = re.compile(
            r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)+$'
        )
        return bool(domain_pattern.match(domain))
    
    def _validate_url(self, url: str) -> bool:
        """验证URL"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _validate_password_strength(self, password: str) -> bool:
        """验证密码强度"""
        if len(password) < 8:
            return False
        
        # 检查是否包含大小写字母、数字
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        return has_upper and has_lower and has_digit
    
    def _validate_cidr(self, cidr: str) -> bool:
        """验证CIDR格式"""
        try:
            ip, prefix = cidr.split('/')
            socket.inet_aton(ip)
            prefix_int = int(prefix)
            return 0 <= prefix_int <= 32
        except Exception:
            return False
    
    def run_validation(self) -> bool:
        """运行完整验证"""
        logger.info("开始配置验证...")
        
        # 加载配置
        if not self.load_env_config():
            return False
        
        # 执行各项验证
        validations = [
            self.validate_mysql_config,
            self.validate_nginx_config,
            self.validate_security_config,
            self.validate_file_paths,
            self.validate_docker_config
        ]
        
        all_valid = True
        for validation in validations:
            try:
                if not validation():
                    all_valid = False
            except Exception as e:
                self.errors.append(f"验证过程中出现异常: {e}")
                all_valid = False
        
        # 输出结果
        self._print_results()
        
        return all_valid and len(self.errors) == 0
    
    def _print_results(self):
        """输出验证结果"""
        print("\n" + "="*60)
        print("配置验证结果")
        print("="*60)
        
        if self.errors:
            print(f"\n❌ 发现 {len(self.errors)} 个错误:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️  发现 {len(self.warnings)} 个警告:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ 所有配置验证通过！")
        elif not self.errors:
            print("\n✅ 配置验证通过（有警告）")
        else:
            print("\n❌ 配置验证失败")
        
        print("\n配置统计:")
        print(f"  - 总配置项: {len(self.config)}")
        print(f"  - 错误数量: {len(self.errors)}")
        print(f"  - 警告数量: {len(self.warnings)}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SSL证书管理系统配置验证工具')
    parser.add_argument('--env-file', default='.env.production', help='环境配置文件路径')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 运行验证
    validator = ConfigValidator(args.env_file)
    
    if validator.run_validation():
        print("\n🎉 配置验证成功！系统可以部署。")
        sys.exit(0)
    else:
        print("\n💥 配置验证失败！请修复错误后重试。")
        sys.exit(1)


if __name__ == '__main__':
    main()
