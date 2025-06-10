"""
数据库模型定义模块
"""
import os
import sqlite3
import datetime
from typing import Dict, List, Any, Optional, Tuple

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database', 'ssl_cert.db')

def dict_factory(cursor, row):
    """将查询结果转换为字典格式"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class Database:
    """数据库操作类"""
    
    def __init__(self, db_path: str = DB_PATH):
        """初始化数据库连接"""
        self.db_path = db_path
        self._ensure_db_dir()
        self.conn = None
        
    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    def connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = dict_factory
        return self.conn
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行SQL语句"""
        if not self.conn:
            self.connect()
        return self.conn.execute(sql, params)
    
    def executemany(self, sql: str, params_list: List[tuple]) -> sqlite3.Cursor:
        """执行多条SQL语句"""
        if not self.conn:
            self.connect()
        return self.conn.executemany(sql, params_list)
    
    def commit(self):
        """提交事务"""
        if self.conn:
            self.conn.commit()
    
    def rollback(self):
        """回滚事务"""
        if self.conn:
            self.conn.rollback()
    
    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """查询单条记录"""
        cursor = self.execute(sql, params)
        return cursor.fetchone()
    
    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """查询多条记录"""
        cursor = self.execute(sql, params)
        return cursor.fetchall()
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """插入数据"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cursor = self.execute(sql, tuple(data.values()))
        self.commit()
        return cursor.lastrowid
    
    def update(self, table: str, data: Dict[str, Any], condition: str, params: tuple = ()) -> int:
        """更新数据"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        cursor = self.execute(sql, tuple(data.values()) + params)
        self.commit()
        return cursor.rowcount
    
    def delete(self, table: str, condition: str, params: tuple = ()) -> int:
        """删除数据"""
        sql = f"DELETE FROM {table} WHERE {condition}"
        cursor = self.execute(sql, params)
        self.commit()
        return cursor.rowcount
    
    def table_exists(self, table: str) -> bool:
        """检查表是否存在"""
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.fetchone(sql, (table,))
        return result is not None
    
    def create_tables(self):
        """创建数据库表"""
        # 用户表
        self.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            role VARCHAR(20) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 服务器表
        self.execute('''
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            ip VARCHAR(45) NOT NULL,
            os_type VARCHAR(50) NOT NULL,
            version VARCHAR(20) NOT NULL,
            token VARCHAR(255) NOT NULL UNIQUE,
            auto_renew BOOLEAN NOT NULL DEFAULT TRUE,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # 证书表
        self.execute('''
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain VARCHAR(255) NOT NULL,
            type VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            server_id INTEGER NOT NULL,
            ca_type VARCHAR(50) NOT NULL,
            private_key TEXT NOT NULL,
            certificate TEXT NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            monitoring_enabled BOOLEAN DEFAULT 1,
            monitoring_frequency INTEGER DEFAULT 3600,
            alert_enabled BOOLEAN DEFAULT 1,
            notes TEXT,
            tags TEXT,
            owner VARCHAR(100),
            business_unit VARCHAR(100),
            dns_status VARCHAR(20),
            dns_response_time INTEGER,
            domain_reachable BOOLEAN,
            http_status_code INTEGER,
            last_dns_check TIMESTAMP,
            last_reachability_check TIMESTAMP,
            monitored_ports TEXT,
            ssl_handshake_time INTEGER,
            tls_version VARCHAR(10),
            cipher_suite VARCHAR(100),
            certificate_chain_valid BOOLEAN,
            http_redirect_status VARCHAR(20),
            last_port_check TIMESTAMP,
            last_manual_check TIMESTAMP,
            check_in_progress BOOLEAN DEFAULT 0,
            renewal_status VARCHAR(20) DEFAULT 'pending',
            auto_renewal_enabled BOOLEAN DEFAULT 0,
            renewal_days_before INTEGER DEFAULT 30,
            import_source VARCHAR(50) DEFAULT 'manual',
            last_renewal_attempt TIMESTAMP,
            FOREIGN KEY (server_id) REFERENCES servers(id)
        )
        ''')
        
        # 告警表
        self.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type VARCHAR(50) NOT NULL,
            message TEXT NOT NULL,
            status VARCHAR(20) NOT NULL,
            certificate_id INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (certificate_id) REFERENCES certificates(id)
        )
        ''')

        # 域名监控历史记录表
        self.execute('''
        CREATE TABLE IF NOT EXISTS domain_monitoring_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificate_id INTEGER NOT NULL,
            check_type VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL,
            response_time INTEGER,
            details TEXT,
            error_message TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
        )
        ''')

        # 域名监控配置表
        self.execute('''
        CREATE TABLE IF NOT EXISTS domain_monitoring_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificate_id INTEGER NOT NULL UNIQUE,
            dns_check_enabled BOOLEAN DEFAULT 1,
            reachability_check_enabled BOOLEAN DEFAULT 1,
            dns_timeout INTEGER DEFAULT 5000,
            http_timeout INTEGER DEFAULT 10000,
            check_ports TEXT,
            custom_headers TEXT,
            alert_on_dns_failure BOOLEAN DEFAULT 1,
            alert_on_unreachable BOOLEAN DEFAULT 1,
            consecutive_failure_threshold INTEGER DEFAULT 3,
            response_time_threshold INTEGER DEFAULT 5000,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
        )
        ''')

        # 端口监控历史记录表
        self.execute('''
        CREATE TABLE IF NOT EXISTS port_monitoring_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificate_id INTEGER NOT NULL,
            port INTEGER NOT NULL,
            check_type VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL,
            handshake_time INTEGER,
            tls_version VARCHAR(10),
            cipher_suite VARCHAR(100),
            security_grade VARCHAR(5),
            details TEXT,
            error_message TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
        )
        ''')

        # SSL安全配置表
        self.execute('''
        CREATE TABLE IF NOT EXISTS ssl_security_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificate_id INTEGER NOT NULL UNIQUE,
            min_tls_version VARCHAR(10) DEFAULT 'TLS 1.2',
            allowed_cipher_suites TEXT,
            require_perfect_forward_secrecy BOOLEAN DEFAULT 1,
            hsts_enabled BOOLEAN DEFAULT 0,
            hsts_max_age INTEGER DEFAULT 31536000,
            hsts_include_subdomains BOOLEAN DEFAULT 0,
            ocsp_stapling_enabled BOOLEAN DEFAULT 0,
            security_grade_threshold VARCHAR(5) DEFAULT 'B',
            alert_on_grade_drop BOOLEAN DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
        )
        ''')

        # 证书操作历史记录表
        self.execute('''
        CREATE TABLE IF NOT EXISTS certificate_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificate_id INTEGER,
            operation_type VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL,
            details TEXT,
            user_id INTEGER,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            FOREIGN KEY (certificate_id) REFERENCES certificates(id) ON DELETE CASCADE
        )
        ''')

        # 证书发现记录表
        self.execute('''
        CREATE TABLE IF NOT EXISTS certificate_discovery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address VARCHAR(45) NOT NULL,
            port INTEGER NOT NULL,
            domain VARCHAR(255),
            san_domains TEXT,
            certificate_fingerprint VARCHAR(64),
            issuer_info TEXT,
            expires_at TIMESTAMP,
            discovery_method VARCHAR(20) DEFAULT 'network_scan',
            imported BOOLEAN DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # 任务队列表
        self.execute('''
        CREATE TABLE IF NOT EXISTS operation_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id VARCHAR(36) NOT NULL UNIQUE,
            task_type VARCHAR(50) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            total_items INTEGER DEFAULT 0,
            processed_items INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            task_data TEXT,
            result_data TEXT,
            error_message TEXT,
            user_id INTEGER,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            expires_at TIMESTAMP
        )
        ''')
        
        # 操作日志表
        self.execute('''
        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action VARCHAR(50) NOT NULL,
            target_type VARCHAR(50) NOT NULL,
            target_id INTEGER NOT NULL,
            ip VARCHAR(45) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # 证书部署记录表
        self.execute('''
        CREATE TABLE IF NOT EXISTS certificate_deployments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            certificate_id INTEGER NOT NULL,
            deploy_type VARCHAR(50) NOT NULL,
            deploy_target VARCHAR(255) NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (certificate_id) REFERENCES certificates(id)
        )
        ''')
        
        # 系统设置表
        self.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key VARCHAR(50) NOT NULL UNIQUE,
            value TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建索引
        self.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_servers_ip ON servers(ip)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_servers_token ON servers(token)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_servers_user_id ON servers(user_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_domain ON certificates(domain)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_expires_at ON certificates(expires_at)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_server_id ON certificates(server_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_status ON certificates(status)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_monitoring_enabled ON certificates(monitoring_enabled)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_owner ON certificates(owner)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_business_unit ON certificates(business_unit)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_dns_status ON certificates(dns_status)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_domain_reachable ON certificates(domain_reachable)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_http_status_code ON certificates(http_status_code)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_last_dns_check ON certificates(last_dns_check)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_last_reachability_check ON certificates(last_reachability_check)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_ssl_handshake_time ON certificates(ssl_handshake_time)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_tls_version ON certificates(tls_version)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_certificate_chain_valid ON certificates(certificate_chain_valid)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_http_redirect_status ON certificates(http_redirect_status)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_last_port_check ON certificates(last_port_check)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_last_manual_check ON certificates(last_manual_check)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_check_in_progress ON certificates(check_in_progress)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_renewal_status ON certificates(renewal_status)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_auto_renewal_enabled ON certificates(auto_renewal_enabled)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_import_source ON certificates(import_source)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificates_last_renewal_attempt ON certificates(last_renewal_attempt)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_alerts_certificate_id ON alerts(certificate_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_domain_monitoring_history_certificate_id ON domain_monitoring_history(certificate_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_domain_monitoring_history_check_type ON domain_monitoring_history(check_type)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_domain_monitoring_history_status ON domain_monitoring_history(status)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_domain_monitoring_history_created_at ON domain_monitoring_history(created_at)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_domain_monitoring_config_certificate_id ON domain_monitoring_config(certificate_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_port_monitoring_history_certificate_id ON port_monitoring_history(certificate_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_port_monitoring_history_port ON port_monitoring_history(port)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_port_monitoring_history_check_type ON port_monitoring_history(check_type)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_port_monitoring_history_status ON port_monitoring_history(status)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_port_monitoring_history_security_grade ON port_monitoring_history(security_grade)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_port_monitoring_history_created_at ON port_monitoring_history(created_at)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_ssl_security_config_certificate_id ON ssl_security_config(certificate_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificate_operations_certificate_id ON certificate_operations(certificate_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificate_operations_operation_type ON certificate_operations(operation_type)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificate_operations_status ON certificate_operations(status)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificate_operations_user_id ON certificate_operations(user_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificate_operations_created_at ON certificate_operations(created_at)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificate_discovery_ip_port ON certificate_discovery(ip_address, port)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificate_discovery_domain ON certificate_discovery(domain)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificate_discovery_fingerprint ON certificate_discovery(certificate_fingerprint)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificate_discovery_imported ON certificate_discovery(imported)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_operation_tasks_task_id ON operation_tasks(task_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_operation_tasks_task_type ON operation_tasks(task_type)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_operation_tasks_status ON operation_tasks(status)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_operation_tasks_user_id ON operation_tasks(user_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(type)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_operation_logs_user_id ON operation_logs(user_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_operation_logs_target ON operation_logs(target_type, target_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_operation_logs_created_at ON operation_logs(created_at)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificate_deployments_certificate_id ON certificate_deployments(certificate_id)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificate_deployments_deploy_type ON certificate_deployments(deploy_type)')
        self.execute('CREATE INDEX IF NOT EXISTS idx_certificate_deployments_status ON certificate_deployments(status)')
        
        self.commit()
    
    def init_default_data(self):
        """初始化默认数据"""
        # 检查是否已有管理员用户
        admin = self.fetchone("SELECT * FROM users WHERE role = 'admin' LIMIT 1")
        if not admin:
            # 创建默认管理员用户 (密码: admin123)
            self.insert('users', {
                'username': 'admin',
                'password_hash': '$2b$12$1234567890123456789012uGZLCTXlLKw0GETpR5.Pu.ZV0vpbUW6',
                'email': 'admin@example.com',
                'role': 'admin',
                'created_at': datetime.datetime.now().isoformat(),
                'updated_at': datetime.datetime.now().isoformat()
            })
        
        # 初始化系统设置
        default_settings = [
            ('default_ca', 'letsencrypt'),
            ('renew_before_days', '15'),
            ('alert_before_days', '30'),
            ('email_notification', 'true'),
            ('notification_email', 'admin@example.com')
        ]
        
        for key, value in default_settings:
            setting = self.fetchone("SELECT * FROM settings WHERE key = ?", (key,))
            if not setting:
                self.insert('settings', {
                    'key': key,
                    'value': value,
                    'created_at': datetime.datetime.now().isoformat(),
                    'updated_at': datetime.datetime.now().isoformat()
                })
        
        self.commit()

# 创建全局数据库实例
db = Database()

def init_db():
    """初始化数据库"""
    db.connect()
    db.create_tables()
    db.init_default_data()
    db.close()

if __name__ == "__main__":
    # 直接运行此模块时初始化数据库
    init_db()
    print(f"数据库初始化完成: {DB_PATH}")
