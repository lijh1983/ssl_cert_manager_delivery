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
        self.execute('CREATE INDEX IF NOT EXISTS idx_alerts_certificate_id ON alerts(certificate_id)')
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
