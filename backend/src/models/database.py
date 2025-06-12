"""
数据库模型定义模块 - MySQL 8.0.41 支持
"""
import os
import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# MySQL数据库配置
class DatabaseConfig:
    """数据库配置类 - 支持完整的MySQL配置参数"""

    def __init__(self):
        # 基本连接配置
        self.host = os.getenv('MYSQL_HOST', 'localhost')
        self.port = int(os.getenv('MYSQL_PORT', 3306))
        self.username = os.getenv('MYSQL_USERNAME', os.getenv('MYSQL_USER', 'ssl_manager'))
        self.password = os.getenv('MYSQL_PASSWORD', 'ssl_manager_password')
        self.database = os.getenv('MYSQL_DATABASE', 'ssl_manager')
        self.charset = os.getenv('MYSQL_CHARSET', 'utf8mb4')
        self.autocommit = os.getenv('MYSQL_AUTOCOMMIT', 'false').lower() == 'true'

        # 连接池配置
        self.pool_size = int(os.getenv('MYSQL_POOL_SIZE', 10))
        self.max_overflow = int(os.getenv('MYSQL_MAX_OVERFLOW', 20))
        self.pool_timeout = int(os.getenv('MYSQL_POOL_TIMEOUT', 30))
        self.pool_recycle = int(os.getenv('MYSQL_POOL_RECYCLE', 3600))

        # 连接超时配置
        self.connect_timeout = int(os.getenv('MYSQL_CONNECT_TIMEOUT', 10))
        self.read_timeout = int(os.getenv('MYSQL_READ_TIMEOUT', 30))
        self.write_timeout = int(os.getenv('MYSQL_WRITE_TIMEOUT', 30))

        # SSL配置
        self.ssl_disabled = os.getenv('MYSQL_SSL_DISABLED', 'false').lower() == 'true'
        self.ssl_ca = os.getenv('MYSQL_SSL_CA', None)
        self.ssl_cert = os.getenv('MYSQL_SSL_CERT', None)
        self.ssl_key = os.getenv('MYSQL_SSL_KEY', None)
        self.ssl_verify_cert = os.getenv('MYSQL_SSL_VERIFY_CERT', 'true').lower() == 'true'
        self.ssl_verify_identity = os.getenv('MYSQL_SSL_VERIFY_IDENTITY', 'false').lower() == 'true'

        # 高级配置
        self.init_command = os.getenv('MYSQL_INIT_COMMAND', "SET sql_mode='STRICT_TRANS_TABLES'")
        self.sql_mode = os.getenv('MYSQL_SQL_MODE', 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO')

        # 验证配置
        self._validate_config()

    def _validate_config(self):
        """验证配置参数"""
        if not self.host:
            raise ValueError("MySQL主机地址不能为空")

        if not (1 <= self.port <= 65535):
            raise ValueError(f"MySQL端口必须在1-65535范围内，当前值: {self.port}")

        if not self.username:
            raise ValueError("MySQL用户名不能为空")

        if not self.password:
            raise ValueError("MySQL密码不能为空")

        if not self.database:
            raise ValueError("MySQL数据库名不能为空")

        if self.pool_size < 1:
            raise ValueError(f"连接池大小必须大于0，当前值: {self.pool_size}")

        if self.max_overflow < 0:
            raise ValueError(f"最大溢出连接数不能为负数，当前值: {self.max_overflow}")

        if self.pool_timeout < 1:
            raise ValueError(f"连接池超时时间必须大于0，当前值: {self.pool_timeout}")

        if self.pool_recycle < 0:
            raise ValueError(f"连接回收时间不能为负数，当前值: {self.pool_recycle}")

    def get_connection_params(self) -> Dict[str, Any]:
        """获取连接参数"""
        params = {
            'host': self.host,
            'port': self.port,
            'user': self.username,
            'password': self.password,
            'database': self.database,
            'charset': self.charset,
            'autocommit': self.autocommit,
            'connect_timeout': self.connect_timeout,
            'read_timeout': self.read_timeout,
            'write_timeout': self.write_timeout,
            'cursorclass': DictCursor,
            'sql_mode': self.sql_mode,
            'init_command': self.init_command
        }

        # 添加SSL配置
        if not self.ssl_disabled:
            ssl_config = {}
            if self.ssl_ca:
                ssl_config['ca'] = self.ssl_ca
            if self.ssl_cert:
                ssl_config['cert'] = self.ssl_cert
            if self.ssl_key:
                ssl_config['key'] = self.ssl_key

            ssl_config['check_hostname'] = self.ssl_verify_identity
            ssl_config['verify_mode'] = 2 if self.ssl_verify_cert else 0  # ssl.CERT_REQUIRED : ssl.CERT_NONE

            if ssl_config:
                params['ssl'] = ssl_config
        else:
            params['ssl_disabled'] = True

        return params

    def get_connection_string(self) -> str:
        """获取SQLAlchemy连接字符串"""
        base_url = f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

        # 添加查询参数
        query_params = [
            f"charset={self.charset}",
            f"autocommit={'true' if self.autocommit else 'false'}"
        ]

        if not self.ssl_disabled and self.ssl_ca:
            query_params.append(f"ssl_ca={self.ssl_ca}")
        if not self.ssl_disabled and self.ssl_cert:
            query_params.append(f"ssl_cert={self.ssl_cert}")
        if not self.ssl_disabled and self.ssl_key:
            query_params.append(f"ssl_key={self.ssl_key}")

        return f"{base_url}?{'&'.join(query_params)}"

    def get_pool_config(self) -> Dict[str, Any]:
        """获取连接池配置"""
        return {
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_timeout': self.pool_timeout,
            'pool_recycle': self.pool_recycle,
            'pool_pre_ping': True  # 启用连接预检查
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（隐藏敏感信息）"""
        return {
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': '***' if self.password else None,
            'database': self.database,
            'charset': self.charset,
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_timeout': self.pool_timeout,
            'pool_recycle': self.pool_recycle,
            'ssl_enabled': not self.ssl_disabled,
            'ssl_verify_cert': self.ssl_verify_cert,
            'ssl_verify_identity': self.ssl_verify_identity
        }

class Database:
    """MySQL数据库操作类"""

    def __init__(self, config: DatabaseConfig = None):
        """初始化数据库连接"""
        self.config = config or DatabaseConfig()
        self.conn = None
        self._connection_pool = []
        self._pool_size = 0
        self._max_pool_size = self.config.pool_size + self.config.max_overflow

    def connect(self):
        """连接数据库"""
        try:
            self.conn = pymysql.connect(**self.config.get_connection_params())
            logger.debug("MySQL数据库连接成功")
            return self.conn
        except Exception as e:
            logger.error(f"MySQL数据库连接失败: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            try:
                self.conn.close()
                logger.debug("MySQL数据库连接已关闭")
            except Exception as e:
                logger.warning(f"关闭数据库连接时出错: {e}")
            finally:
                self.conn = None

    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        conn = None
        try:
            conn = pymysql.connect(**self.config.get_connection_params())
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute(self, sql: str, params: tuple = ()) -> pymysql.cursors.Cursor:
        """执行SQL语句"""
        if not self.conn:
            self.connect()

        # 将SQLite的?占位符转换为MySQL的%s占位符
        mysql_sql = sql.replace('?', '%s')

        try:
            cursor = self.conn.cursor()
            cursor.execute(mysql_sql, params)
            return cursor
        except Exception as e:
            logger.error(f"SQL执行失败: {mysql_sql}, 参数: {params}, 错误: {e}")
            raise

    def executemany(self, sql: str, params_list: List[tuple]) -> pymysql.cursors.Cursor:
        """执行多条SQL语句"""
        if not self.conn:
            self.connect()

        # 将SQLite的?占位符转换为MySQL的%s占位符
        mysql_sql = sql.replace('?', '%s')

        try:
            cursor = self.conn.cursor()
            cursor.executemany(mysql_sql, params_list)
            return cursor
        except Exception as e:
            logger.error(f"批量SQL执行失败: {mysql_sql}, 错误: {e}")
            raise

    def commit(self):
        """提交事务"""
        if self.conn:
            try:
                self.conn.commit()
            except Exception as e:
                logger.error(f"事务提交失败: {e}")
                raise

    def rollback(self):
        """回滚事务"""
        if self.conn:
            try:
                self.conn.rollback()
            except Exception as e:
                logger.error(f"事务回滚失败: {e}")
                raise

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """查询单条记录"""
        cursor = self.execute(sql, params)
        result = cursor.fetchone()
        cursor.close()
        return result

    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """查询多条记录"""
        cursor = self.execute(sql, params)
        results = cursor.fetchall()
        cursor.close()
        return results or []

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """插入数据"""
        columns = ', '.join([f"`{k}`" for k in data.keys()])
        placeholders = ', '.join(['%s' for _ in data])
        sql = f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders})"

        try:
            cursor = self.execute(sql, tuple(data.values()))
            self.commit()
            insert_id = cursor.lastrowid
            cursor.close()
            return insert_id
        except Exception as e:
            self.rollback()
            logger.error(f"插入数据失败: {sql}, 数据: {data}, 错误: {e}")
            raise

    def update(self, table: str, data: Dict[str, Any], condition: str, params: tuple = ()) -> int:
        """更新数据"""
        set_clause = ', '.join([f"`{k}` = %s" for k in data.keys()])
        # 将条件中的?替换为%s
        mysql_condition = condition.replace('?', '%s')
        sql = f"UPDATE `{table}` SET {set_clause} WHERE {mysql_condition}"

        try:
            cursor = self.execute(sql, tuple(data.values()) + params)
            self.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
        except Exception as e:
            self.rollback()
            logger.error(f"更新数据失败: {sql}, 数据: {data}, 条件参数: {params}, 错误: {e}")
            raise

    def delete(self, table: str, condition: str, params: tuple = ()) -> int:
        """删除数据"""
        # 将条件中的?替换为%s
        mysql_condition = condition.replace('?', '%s')
        sql = f"DELETE FROM `{table}` WHERE {mysql_condition}"

        try:
            cursor = self.execute(sql, params)
            self.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
        except Exception as e:
            self.rollback()
            logger.error(f"删除数据失败: {sql}, 条件参数: {params}, 错误: {e}")
            raise

    def table_exists(self, table: str) -> bool:
        """检查表是否存在"""
        sql = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s"
        result = self.fetchone(sql, (self.config.database, table))
        return result is not None
    
    def create_tables(self):
        """创建数据库表 - MySQL 8.0.41语法"""

        # 用户表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `users` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `username` VARCHAR(50) NOT NULL UNIQUE,
            `password_hash` VARCHAR(255) NOT NULL,
            `email` VARCHAR(100) NOT NULL UNIQUE,
            `role` VARCHAR(20) NOT NULL,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX `idx_users_username` (`username`),
            INDEX `idx_users_email` (`email`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # 服务器表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `servers` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `name` VARCHAR(100) NOT NULL,
            `ip` VARCHAR(45),
            `os_type` VARCHAR(50),
            `version` VARCHAR(20),
            `token` VARCHAR(255) NOT NULL UNIQUE,
            `auto_renew` BOOLEAN NOT NULL DEFAULT TRUE,
            `user_id` INT NOT NULL,
            `server_type` VARCHAR(50) DEFAULT 'nginx',
            `description` TEXT,
            `status` VARCHAR(20) DEFAULT 'unknown',
            `last_seen` TIMESTAMP NULL,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX `idx_servers_ip` (`ip`),
            INDEX `idx_servers_token` (`token`),
            INDEX `idx_servers_user_id` (`user_id`),
            INDEX `idx_servers_status` (`status`),
            FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        
        # 证书表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `certificates` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `domain` VARCHAR(255) NOT NULL,
            `type` VARCHAR(20) NOT NULL,
            `status` VARCHAR(20) NOT NULL,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `expires_at` TIMESTAMP NOT NULL,
            `server_id` INT NOT NULL,
            `ca_type` VARCHAR(50) NOT NULL,
            `private_key` LONGTEXT NOT NULL,
            `certificate` LONGTEXT NOT NULL,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            `monitoring_enabled` BOOLEAN DEFAULT TRUE,
            `monitoring_frequency` INT DEFAULT 3600,
            `alert_enabled` BOOLEAN DEFAULT TRUE,
            `notes` TEXT,
            `tags` TEXT,
            `owner` VARCHAR(100),
            `business_unit` VARCHAR(100),
            `dns_status` VARCHAR(20),
            `dns_response_time` INT,
            `domain_reachable` BOOLEAN,
            `http_status_code` INT,
            `last_dns_check` TIMESTAMP NULL,
            `last_reachability_check` TIMESTAMP NULL,
            `monitored_ports` TEXT,
            `ssl_handshake_time` INT,
            `tls_version` VARCHAR(10),
            `cipher_suite` VARCHAR(100),
            `certificate_chain_valid` BOOLEAN,
            `http_redirect_status` VARCHAR(20),
            `last_port_check` TIMESTAMP NULL,
            `last_manual_check` TIMESTAMP NULL,
            `check_in_progress` BOOLEAN DEFAULT FALSE,
            `renewal_status` VARCHAR(20) DEFAULT 'pending',
            `auto_renewal_enabled` BOOLEAN DEFAULT FALSE,
            `renewal_days_before` INT DEFAULT 30,
            `import_source` VARCHAR(50) DEFAULT 'manual',
            `last_renewal_attempt` TIMESTAMP NULL,
            INDEX `idx_certificates_domain` (`domain`),
            INDEX `idx_certificates_expires_at` (`expires_at`),
            INDEX `idx_certificates_server_id` (`server_id`),
            INDEX `idx_certificates_status` (`status`),
            INDEX `idx_certificates_monitoring_enabled` (`monitoring_enabled`),
            INDEX `idx_certificates_owner` (`owner`),
            INDEX `idx_certificates_business_unit` (`business_unit`),
            INDEX `idx_certificates_dns_status` (`dns_status`),
            INDEX `idx_certificates_domain_reachable` (`domain_reachable`),
            INDEX `idx_certificates_renewal_status` (`renewal_status`),
            INDEX `idx_certificates_auto_renewal_enabled` (`auto_renewal_enabled`),
            FOREIGN KEY (`server_id`) REFERENCES `servers`(`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        
        # 告警表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `alerts` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `type` VARCHAR(50) NOT NULL,
            `message` TEXT NOT NULL,
            `status` VARCHAR(20) NOT NULL,
            `certificate_id` INT NOT NULL,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX `idx_alerts_certificate_id` (`certificate_id`),
            INDEX `idx_alerts_status` (`status`),
            INDEX `idx_alerts_type` (`type`),
            FOREIGN KEY (`certificate_id`) REFERENCES `certificates`(`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # 域名监控历史记录表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `domain_monitoring_history` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `certificate_id` INT NOT NULL,
            `check_type` VARCHAR(20) NOT NULL,
            `status` VARCHAR(20) NOT NULL,
            `response_time` INT,
            `details` TEXT,
            `error_message` TEXT,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_domain_monitoring_history_certificate_id` (`certificate_id`),
            INDEX `idx_domain_monitoring_history_check_type` (`check_type`),
            INDEX `idx_domain_monitoring_history_status` (`status`),
            INDEX `idx_domain_monitoring_history_created_at` (`created_at`),
            FOREIGN KEY (`certificate_id`) REFERENCES `certificates`(`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # 域名监控配置表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `domain_monitoring_config` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `certificate_id` INT NOT NULL UNIQUE,
            `dns_check_enabled` BOOLEAN DEFAULT TRUE,
            `reachability_check_enabled` BOOLEAN DEFAULT TRUE,
            `dns_timeout` INT DEFAULT 5000,
            `http_timeout` INT DEFAULT 10000,
            `check_ports` TEXT,
            `custom_headers` TEXT,
            `alert_on_dns_failure` BOOLEAN DEFAULT TRUE,
            `alert_on_unreachable` BOOLEAN DEFAULT TRUE,
            `consecutive_failure_threshold` INT DEFAULT 3,
            `response_time_threshold` INT DEFAULT 5000,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX `idx_domain_monitoring_config_certificate_id` (`certificate_id`),
            FOREIGN KEY (`certificate_id`) REFERENCES `certificates`(`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # 端口监控历史记录表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `port_monitoring_history` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `certificate_id` INT NOT NULL,
            `port` INT NOT NULL,
            `check_type` VARCHAR(20) NOT NULL,
            `status` VARCHAR(20) NOT NULL,
            `handshake_time` INT,
            `tls_version` VARCHAR(10),
            `cipher_suite` VARCHAR(100),
            `security_grade` VARCHAR(5),
            `details` TEXT,
            `error_message` TEXT,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_port_monitoring_history_certificate_id` (`certificate_id`),
            INDEX `idx_port_monitoring_history_port` (`port`),
            INDEX `idx_port_monitoring_history_check_type` (`check_type`),
            INDEX `idx_port_monitoring_history_status` (`status`),
            INDEX `idx_port_monitoring_history_security_grade` (`security_grade`),
            INDEX `idx_port_monitoring_history_created_at` (`created_at`),
            FOREIGN KEY (`certificate_id`) REFERENCES `certificates`(`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # SSL安全配置表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `ssl_security_config` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `certificate_id` INT NOT NULL UNIQUE,
            `min_tls_version` VARCHAR(10) DEFAULT 'TLS 1.2',
            `allowed_cipher_suites` TEXT,
            `require_perfect_forward_secrecy` BOOLEAN DEFAULT TRUE,
            `hsts_enabled` BOOLEAN DEFAULT FALSE,
            `hsts_max_age` INT DEFAULT 31536000,
            `hsts_include_subdomains` BOOLEAN DEFAULT FALSE,
            `ocsp_stapling_enabled` BOOLEAN DEFAULT FALSE,
            `security_grade_threshold` VARCHAR(5) DEFAULT 'B',
            `alert_on_grade_drop` BOOLEAN DEFAULT TRUE,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX `idx_ssl_security_config_certificate_id` (`certificate_id`),
            FOREIGN KEY (`certificate_id`) REFERENCES `certificates`(`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # 证书操作历史记录表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `certificate_operations` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `certificate_id` INT,
            `operation_type` VARCHAR(50) NOT NULL,
            `status` VARCHAR(20) NOT NULL,
            `details` TEXT,
            `user_id` INT,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `completed_at` TIMESTAMP NULL,
            `error_message` TEXT,
            INDEX `idx_certificate_operations_certificate_id` (`certificate_id`),
            INDEX `idx_certificate_operations_operation_type` (`operation_type`),
            INDEX `idx_certificate_operations_status` (`status`),
            INDEX `idx_certificate_operations_user_id` (`user_id`),
            INDEX `idx_certificate_operations_created_at` (`created_at`),
            FOREIGN KEY (`certificate_id`) REFERENCES `certificates`(`id`) ON DELETE CASCADE,
            FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # 证书发现记录表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `certificate_discovery` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `ip_address` VARCHAR(45) NOT NULL,
            `port` INT NOT NULL,
            `domain` VARCHAR(255),
            `san_domains` TEXT,
            `certificate_fingerprint` VARCHAR(64),
            `issuer_info` TEXT,
            `expires_at` TIMESTAMP NULL,
            `discovery_method` VARCHAR(20) DEFAULT 'network_scan',
            `imported` BOOLEAN DEFAULT FALSE,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX `idx_certificate_discovery_ip_port` (`ip_address`, `port`),
            INDEX `idx_certificate_discovery_domain` (`domain`),
            INDEX `idx_certificate_discovery_fingerprint` (`certificate_fingerprint`),
            INDEX `idx_certificate_discovery_imported` (`imported`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # 任务队列表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `operation_tasks` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `task_id` VARCHAR(36) NOT NULL UNIQUE,
            `task_type` VARCHAR(50) NOT NULL,
            `status` VARCHAR(20) DEFAULT 'pending',
            `progress` INT DEFAULT 0,
            `total_items` INT DEFAULT 0,
            `processed_items` INT DEFAULT 0,
            `success_count` INT DEFAULT 0,
            `failed_count` INT DEFAULT 0,
            `task_data` TEXT,
            `result_data` TEXT,
            `error_message` TEXT,
            `user_id` INT,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `started_at` TIMESTAMP NULL,
            `completed_at` TIMESTAMP NULL,
            `expires_at` TIMESTAMP NULL,
            INDEX `idx_operation_tasks_task_id` (`task_id`),
            INDEX `idx_operation_tasks_task_type` (`task_type`),
            INDEX `idx_operation_tasks_status` (`status`),
            INDEX `idx_operation_tasks_user_id` (`user_id`),
            FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # 操作日志表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `operation_logs` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `user_id` INT,
            `action` VARCHAR(50) NOT NULL,
            `target_type` VARCHAR(50) NOT NULL,
            `target_id` INT NOT NULL,
            `ip` VARCHAR(45) NOT NULL,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX `idx_operation_logs_user_id` (`user_id`),
            INDEX `idx_operation_logs_target` (`target_type`, `target_id`),
            INDEX `idx_operation_logs_created_at` (`created_at`),
            FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        
        # 证书部署记录表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `certificate_deployments` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `certificate_id` INT NOT NULL,
            `deploy_type` VARCHAR(50) NOT NULL,
            `deploy_target` VARCHAR(255) NOT NULL,
            `status` VARCHAR(20) NOT NULL,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX `idx_certificate_deployments_certificate_id` (`certificate_id`),
            INDEX `idx_certificate_deployments_deploy_type` (`deploy_type`),
            INDEX `idx_certificate_deployments_status` (`status`),
            FOREIGN KEY (`certificate_id`) REFERENCES `certificates`(`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # 系统设置表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `settings` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `key` VARCHAR(50) NOT NULL UNIQUE,
            `value` TEXT NOT NULL,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX `idx_settings_key` (`key`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # 监控配置表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `monitoring_configs` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `domain` VARCHAR(255) NOT NULL,
            `port` INT DEFAULT 443,
            `ip_type` VARCHAR(10) DEFAULT 'ipv4',
            `ip_address` VARCHAR(45),
            `monitoring_enabled` BOOLEAN DEFAULT TRUE,
            `description` TEXT,
            `user_id` INT NOT NULL,
            `status` VARCHAR(20) DEFAULT 'unknown',
            `days_left` INT DEFAULT 0,
            `cert_level` VARCHAR(10) DEFAULT 'DV',
            `encryption_type` VARCHAR(10) DEFAULT 'RSA',
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX `idx_monitoring_configs_user_id` (`user_id`),
            INDEX `idx_monitoring_configs_domain` (`domain`),
            INDEX `idx_monitoring_configs_status` (`status`),
            UNIQUE KEY `unique_domain_user` (`domain`, `user_id`),
            FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        # 监控历史表
        self.execute('''
        CREATE TABLE IF NOT EXISTS `monitoring_history` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `monitoring_id` INT NOT NULL,
            `check_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `status` VARCHAR(20) NOT NULL,
            `days_left` INT DEFAULT 0,
            `response_time` INT DEFAULT 0,
            `ssl_version` VARCHAR(20),
            `message` TEXT,
            INDEX `idx_monitoring_history_monitoring_id` (`monitoring_id`),
            INDEX `idx_monitoring_history_check_time` (`check_time`),
            INDEX `idx_monitoring_history_status` (`status`),
            FOREIGN KEY (`monitoring_id`) REFERENCES `monitoring_configs`(`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')

        self.commit()
        logger.info("MySQL数据库表创建完成")
    
    def init_default_data(self):
        """初始化默认数据"""
        try:
            # 检查是否已有管理员用户
            admin = self.fetchone("SELECT * FROM `users` WHERE `role` = %s LIMIT 1", ('admin',))
            if not admin:
                # 创建默认管理员用户 (密码: admin123)
                self.insert('users', {
                    'username': 'admin',
                    'password_hash': '$2b$12$1234567890123456789012uGZLCTXlLKw0GETpR5.Pu.ZV0vpbUW6',
                    'email': 'admin@example.com',
                    'role': 'admin'
                })
                logger.info("默认管理员用户创建成功")

            # 初始化系统设置
            default_settings = [
                ('default_ca', 'letsencrypt'),
                ('renew_before_days', '15'),
                ('alert_before_days', '30'),
                ('email_notification', 'true'),
                ('notification_email', 'admin@example.com'),
                ('mysql_version', '8.0.41'),
                ('system_initialized', 'true')
            ]

            for key, value in default_settings:
                setting = self.fetchone("SELECT * FROM `settings` WHERE `key` = %s", (key,))
                if not setting:
                    self.insert('settings', {
                        'key': key,
                        'value': value
                    })

            logger.info("默认系统设置初始化完成")
            self.commit()

        except Exception as e:
            logger.error(f"初始化默认数据失败: {e}")
            self.rollback()
            raise

# 创建全局数据库实例
db = Database()

def init_db():
    """初始化MySQL数据库"""
    try:
        logger.info("开始初始化MySQL数据库...")
        db.connect()
        db.create_tables()
        db.init_default_data()
        logger.info("MySQL数据库初始化完成")
    except Exception as e:
        logger.error(f"MySQL数据库初始化失败: {e}")
        raise
    finally:
        db.close()

def test_connection():
    """测试数据库连接"""
    try:
        db.connect()
        result = db.fetchone("SELECT 1 as test")
        db.close()
        return result is not None
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False

if __name__ == "__main__":
    # 直接运行此模块时初始化数据库
    config = DatabaseConfig()
    print(f"MySQL连接配置:")
    print(f"  主机: {config.host}:{config.port}")
    print(f"  数据库: {config.database}")
    print(f"  用户: {config.user}")
    print(f"  字符集: {config.charset}")

    if test_connection():
        print("数据库连接测试成功")
        init_db()
        print("MySQL数据库初始化完成")
    else:
        print("数据库连接测试失败，请检查配置")
