#!/usr/bin/env python3
"""
SQLite到MySQL数据迁移脚本
支持从SQLite数据库迁移到MySQL 8.0.41
"""

import os
import sys
import sqlite3
import logging
import datetime
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.database import Database, DatabaseConfig
import pymysql

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SQLiteToMySQLMigrator:
    """SQLite到MySQL迁移器"""
    
    def __init__(self, sqlite_db_path: str, mysql_config: DatabaseConfig = None):
        """初始化迁移器"""
        self.sqlite_db_path = sqlite_db_path
        self.mysql_config = mysql_config or DatabaseConfig()
        self.mysql_db = Database(self.mysql_config)
        
        # 表迁移映射
        self.table_mappings = {
            'users': self._migrate_users,
            'servers': self._migrate_servers,
            'certificates': self._migrate_certificates,
            'alerts': self._migrate_alerts,
            'monitoring_configs': self._migrate_monitoring_configs,
            'monitoring_history': self._migrate_monitoring_history,
            'settings': self._migrate_settings,
        }
    
    def migrate(self) -> bool:
        """执行完整迁移"""
        try:
            logger.info("开始SQLite到MySQL数据迁移...")
            
            # 1. 检查SQLite数据库
            if not self._check_sqlite_database():
                return False
            
            # 2. 初始化MySQL数据库
            if not self._initialize_mysql_database():
                return False
            
            # 3. 迁移数据
            if not self._migrate_all_tables():
                return False
            
            # 4. 验证迁移结果
            if not self._verify_migration():
                return False
            
            logger.info("数据迁移完成！")
            return True
            
        except Exception as e:
            logger.error(f"迁移失败: {e}")
            return False
    
    def _check_sqlite_database(self) -> bool:
        """检查SQLite数据库"""
        try:
            if not os.path.exists(self.sqlite_db_path):
                logger.error(f"SQLite数据库文件不存在: {self.sqlite_db_path}")
                return False
            
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 检查表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            logger.info(f"SQLite数据库包含 {len(tables)} 个表: {', '.join(tables)}")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"检查SQLite数据库失败: {e}")
            return False
    
    def _initialize_mysql_database(self) -> bool:
        """初始化MySQL数据库"""
        try:
            logger.info("初始化MySQL数据库...")
            
            # 连接MySQL并创建数据库结构
            self.mysql_db.connect()
            self.mysql_db.create_tables()
            
            logger.info("MySQL数据库初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化MySQL数据库失败: {e}")
            return False
    
    def _migrate_all_tables(self) -> bool:
        """迁移所有表数据"""
        try:
            # 连接SQLite数据库
            sqlite_conn = sqlite3.connect(self.sqlite_db_path)
            sqlite_conn.row_factory = sqlite3.Row
            
            total_migrated = 0
            
            for table_name, migrate_func in self.table_mappings.items():
                logger.info(f"迁移表: {table_name}")
                
                try:
                    # 检查表是否存在
                    cursor = sqlite_conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                    if not cursor.fetchone():
                        logger.warning(f"表 {table_name} 在SQLite中不存在，跳过")
                        continue
                    
                    # 执行迁移
                    migrated_count = migrate_func(sqlite_conn)
                    total_migrated += migrated_count
                    logger.info(f"表 {table_name} 迁移完成，迁移 {migrated_count} 条记录")
                    
                except Exception as e:
                    logger.error(f"迁移表 {table_name} 失败: {e}")
                    return False
            
            sqlite_conn.close()
            logger.info(f"所有表迁移完成，总计迁移 {total_migrated} 条记录")
            return True
            
        except Exception as e:
            logger.error(f"迁移表数据失败: {e}")
            return False
    
    def _migrate_users(self, sqlite_conn: sqlite3.Connection) -> int:
        """迁移用户表"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        
        migrated_count = 0
        for row in rows:
            try:
                # 清理现有数据（如果存在）
                self.mysql_db.execute("DELETE FROM `users` WHERE `username` = %s", (row['username'],))
                
                # 插入数据
                self.mysql_db.insert('users', {
                    'username': row['username'],
                    'password_hash': row['password_hash'],
                    'email': row['email'],
                    'role': row['role']
                })
                migrated_count += 1
                
            except Exception as e:
                logger.warning(f"迁移用户记录失败: {e}")
        
        self.mysql_db.commit()
        return migrated_count
    
    def _migrate_servers(self, sqlite_conn: sqlite3.Connection) -> int:
        """迁移服务器表"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM servers")
        rows = cursor.fetchall()
        
        migrated_count = 0
        for row in rows:
            try:
                data = {
                    'name': row['name'],
                    'token': row['token'],
                    'auto_renew': bool(row['auto_renew']),
                    'user_id': row['user_id']
                }
                
                # 添加可选字段
                optional_fields = ['ip', 'os_type', 'version', 'server_type', 'description', 'status']
                for field in optional_fields:
                    if field in row.keys() and row[field]:
                        data[field] = row[field]
                
                self.mysql_db.insert('servers', data)
                migrated_count += 1
                
            except Exception as e:
                logger.warning(f"迁移服务器记录失败: {e}")
        
        self.mysql_db.commit()
        return migrated_count
    
    def _migrate_certificates(self, sqlite_conn: sqlite3.Connection) -> int:
        """迁移证书表"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM certificates")
        rows = cursor.fetchall()
        
        migrated_count = 0
        for row in rows:
            try:
                data = {
                    'domain': row['domain'],
                    'type': row['type'],
                    'status': row['status'],
                    'expires_at': row['expires_at'],
                    'server_id': row['server_id'],
                    'ca_type': row['ca_type'],
                    'private_key': row['private_key'],
                    'certificate': row['certificate']
                }
                
                # 添加可选字段
                optional_fields = [
                    'monitoring_enabled', 'monitoring_frequency', 'alert_enabled',
                    'notes', 'tags', 'owner', 'business_unit'
                ]
                
                for field in optional_fields:
                    if field in row.keys() and row[field] is not None:
                        data[field] = row[field]
                
                self.mysql_db.insert('certificates', data)
                migrated_count += 1
                
            except Exception as e:
                logger.warning(f"迁移证书记录失败: {e}")
        
        self.mysql_db.commit()
        return migrated_count
    
    def _migrate_alerts(self, sqlite_conn: sqlite3.Connection) -> int:
        """迁移告警表"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM alerts")
        rows = cursor.fetchall()
        
        migrated_count = 0
        for row in rows:
            try:
                self.mysql_db.insert('alerts', {
                    'type': row['type'],
                    'message': row['message'],
                    'status': row['status'],
                    'certificate_id': row['certificate_id']
                })
                migrated_count += 1
                
            except Exception as e:
                logger.warning(f"迁移告警记录失败: {e}")
        
        self.mysql_db.commit()
        return migrated_count
    
    def _migrate_monitoring_configs(self, sqlite_conn: sqlite3.Connection) -> int:
        """迁移监控配置表"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM monitoring_configs")
        rows = cursor.fetchall()
        
        migrated_count = 0
        for row in rows:
            try:
                data = {
                    'domain': row['domain'],
                    'user_id': row['user_id']
                }
                
                # 添加可选字段
                optional_fields = [
                    'port', 'ip_type', 'ip_address', 'monitoring_enabled',
                    'description', 'status', 'days_left', 'cert_level', 'encryption_type'
                ]
                
                for field in optional_fields:
                    if field in row.keys() and row[field] is not None:
                        data[field] = row[field]
                
                self.mysql_db.insert('monitoring_configs', data)
                migrated_count += 1
                
            except Exception as e:
                logger.warning(f"迁移监控配置记录失败: {e}")
        
        self.mysql_db.commit()
        return migrated_count
    
    def _migrate_monitoring_history(self, sqlite_conn: sqlite3.Connection) -> int:
        """迁移监控历史表"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM monitoring_history")
        rows = cursor.fetchall()
        
        migrated_count = 0
        for row in rows:
            try:
                data = {
                    'monitoring_id': row['monitoring_id'],
                    'status': row['status']
                }
                
                # 添加可选字段
                optional_fields = [
                    'check_time', 'days_left', 'response_time', 'ssl_version', 'message'
                ]
                
                for field in optional_fields:
                    if field in row.keys() and row[field] is not None:
                        data[field] = row[field]
                
                self.mysql_db.insert('monitoring_history', data)
                migrated_count += 1
                
            except Exception as e:
                logger.warning(f"迁移监控历史记录失败: {e}")
        
        self.mysql_db.commit()
        return migrated_count
    
    def _migrate_settings(self, sqlite_conn: sqlite3.Connection) -> int:
        """迁移设置表"""
        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT * FROM settings")
        rows = cursor.fetchall()
        
        migrated_count = 0
        for row in rows:
            try:
                # 清理现有设置（如果存在）
                self.mysql_db.execute("DELETE FROM `settings` WHERE `key` = %s", (row['key'],))
                
                self.mysql_db.insert('settings', {
                    'key': row['key'],
                    'value': row['value']
                })
                migrated_count += 1
                
            except Exception as e:
                logger.warning(f"迁移设置记录失败: {e}")
        
        self.mysql_db.commit()
        return migrated_count
    
    def _verify_migration(self) -> bool:
        """验证迁移结果"""
        try:
            logger.info("验证迁移结果...")
            
            # 连接SQLite数据库获取原始数据统计
            sqlite_conn = sqlite3.connect(self.sqlite_db_path)
            sqlite_cursor = sqlite_conn.cursor()
            
            verification_results = []
            
            for table_name in self.table_mappings.keys():
                try:
                    # 检查SQLite表是否存在
                    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                    if not sqlite_cursor.fetchone():
                        continue
                    
                    # 获取SQLite记录数
                    sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    sqlite_count = sqlite_cursor.fetchone()[0]
                    
                    # 获取MySQL记录数
                    mysql_result = self.mysql_db.fetchone(f"SELECT COUNT(*) as count FROM `{table_name}`")
                    mysql_count = mysql_result['count'] if mysql_result else 0
                    
                    verification_results.append({
                        'table': table_name,
                        'sqlite_count': sqlite_count,
                        'mysql_count': mysql_count,
                        'success': sqlite_count == mysql_count
                    })
                    
                    logger.info(f"表 {table_name}: SQLite={sqlite_count}, MySQL={mysql_count}")
                    
                except Exception as e:
                    logger.warning(f"验证表 {table_name} 失败: {e}")
            
            sqlite_conn.close()
            
            # 检查验证结果
            failed_tables = [r for r in verification_results if not r['success']]
            if failed_tables:
                logger.error(f"以下表迁移验证失败: {[t['table'] for t in failed_tables]}")
                return False
            
            logger.info("迁移验证成功！")
            return True
            
        except Exception as e:
            logger.error(f"验证迁移结果失败: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SQLite到MySQL数据迁移工具')
    parser.add_argument('--sqlite-db', required=True, help='SQLite数据库文件路径')
    parser.add_argument('--mysql-host', default='localhost', help='MySQL主机地址')
    parser.add_argument('--mysql-port', type=int, default=3306, help='MySQL端口')
    parser.add_argument('--mysql-user', required=True, help='MySQL用户名')
    parser.add_argument('--mysql-password', required=True, help='MySQL密码')
    parser.add_argument('--mysql-database', required=True, help='MySQL数据库名')
    
    args = parser.parse_args()
    
    # 创建MySQL配置
    mysql_config = DatabaseConfig()
    mysql_config.host = args.mysql_host
    mysql_config.port = args.mysql_port
    mysql_config.username = args.mysql_user
    mysql_config.password = args.mysql_password
    mysql_config.database = args.mysql_database
    
    # 执行迁移
    migrator = SQLiteToMySQLMigrator(args.sqlite_db, mysql_config)
    
    if migrator.migrate():
        print("数据迁移成功完成！")
        sys.exit(0)
    else:
        print("数据迁移失败！")
        sys.exit(1)


if __name__ == '__main__':
    main()
