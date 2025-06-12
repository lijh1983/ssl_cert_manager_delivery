#!/usr/bin/env python3
"""
MySQL数据库连接测试脚本
用于验证MySQL 8.0.41连接和基本操作
"""

import os
import sys
import logging
import datetime
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.database import Database, DatabaseConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MySQLConnectionTester:
    """MySQL连接测试器"""
    
    def __init__(self, config: DatabaseConfig = None):
        """初始化测试器"""
        self.config = config or DatabaseConfig()
        self.db = Database(self.config)
        self.test_results = []
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        logger.info("开始MySQL数据库连接测试...")
        
        tests = [
            ("基本连接测试", self.test_basic_connection),
            ("数据库版本测试", self.test_database_version),
            ("字符集测试", self.test_charset),
            ("表创建测试", self.test_table_creation),
            ("数据插入测试", self.test_data_insertion),
            ("数据查询测试", self.test_data_query),
            ("数据更新测试", self.test_data_update),
            ("数据删除测试", self.test_data_deletion),
            ("事务测试", self.test_transaction),
            ("清理测试数据", self.cleanup_test_data)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                logger.info(f"执行测试: {test_name}")
                result = test_func()
                if result:
                    logger.info(f"✓ {test_name} - 通过")
                    passed += 1
                else:
                    logger.error(f"✗ {test_name} - 失败")
                    failed += 1
                self.test_results.append((test_name, result))
            except Exception as e:
                logger.error(f"✗ {test_name} - 异常: {e}")
                failed += 1
                self.test_results.append((test_name, False))
        
        # 输出测试结果摘要
        logger.info(f"\n测试结果摘要:")
        logger.info(f"总测试数: {len(tests)}")
        logger.info(f"通过: {passed}")
        logger.info(f"失败: {failed}")
        logger.info(f"成功率: {passed/len(tests)*100:.1f}%")
        
        return failed == 0
    
    def test_basic_connection(self) -> bool:
        """测试基本连接"""
        try:
            self.db.connect()
            result = self.db.fetchone("SELECT 1 as test")
            self.db.close()
            return result is not None and result['test'] == 1
        except Exception as e:
            logger.error(f"基本连接测试失败: {e}")
            return False
    
    def test_database_version(self) -> bool:
        """测试数据库版本"""
        try:
            self.db.connect()
            result = self.db.fetchone("SELECT VERSION() as version")
            self.db.close()
            
            if result and result['version']:
                version = result['version']
                logger.info(f"MySQL版本: {version}")
                return '8.0' in version
            return False
        except Exception as e:
            logger.error(f"数据库版本测试失败: {e}")
            return False
    
    def test_charset(self) -> bool:
        """测试字符集"""
        try:
            self.db.connect()
            result = self.db.fetchone("""
                SELECT 
                    @@character_set_database as db_charset,
                    @@collation_database as db_collation
            """)
            self.db.close()
            
            if result:
                charset = result['db_charset']
                collation = result['db_collation']
                logger.info(f"数据库字符集: {charset}, 排序规则: {collation}")
                return charset == 'utf8mb4' and 'utf8mb4' in collation
            return False
        except Exception as e:
            logger.error(f"字符集测试失败: {e}")
            return False
    
    def test_table_creation(self) -> bool:
        """测试表创建"""
        try:
            self.db.connect()
            
            # 创建测试表
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS `test_table` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `name` VARCHAR(100) NOT NULL,
                    `email` VARCHAR(255) UNIQUE,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX `idx_test_name` (`name`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            self.db.commit()
            
            # 验证表是否创建成功
            result = self.db.fetchone("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'test_table'
            """, (self.config.database,))
            
            self.db.close()
            return result is not None
        except Exception as e:
            logger.error(f"表创建测试失败: {e}")
            return False
    
    def test_data_insertion(self) -> bool:
        """测试数据插入"""
        try:
            self.db.connect()
            
            # 插入测试数据
            insert_id = self.db.insert('test_table', {
                'name': '测试用户',
                'email': 'test@example.com'
            })
            
            self.db.close()
            return insert_id > 0
        except Exception as e:
            logger.error(f"数据插入测试失败: {e}")
            return False
    
    def test_data_query(self) -> bool:
        """测试数据查询"""
        try:
            self.db.connect()
            
            # 查询测试数据
            result = self.db.fetchone("SELECT * FROM `test_table` WHERE `email` = %s", ('test@example.com',))
            
            self.db.close()
            return result is not None and result['name'] == '测试用户'
        except Exception as e:
            logger.error(f"数据查询测试失败: {e}")
            return False
    
    def test_data_update(self) -> bool:
        """测试数据更新"""
        try:
            self.db.connect()
            
            # 更新测试数据
            affected_rows = self.db.update('test_table', 
                {'name': '更新后的用户'}, 
                '`email` = %s', 
                ('test@example.com',))
            
            self.db.close()
            return affected_rows > 0
        except Exception as e:
            logger.error(f"数据更新测试失败: {e}")
            return False
    
    def test_data_deletion(self) -> bool:
        """测试数据删除"""
        try:
            self.db.connect()
            
            # 删除测试数据
            affected_rows = self.db.delete('test_table', '`email` = %s', ('test@example.com',))
            
            self.db.close()
            return affected_rows > 0
        except Exception as e:
            logger.error(f"数据删除测试失败: {e}")
            return False
    
    def test_transaction(self) -> bool:
        """测试事务"""
        try:
            self.db.connect()
            
            # 开始事务
            self.db.execute("START TRANSACTION")
            
            # 插入数据
            self.db.insert('test_table', {
                'name': '事务测试用户',
                'email': 'transaction@example.com'
            })
            
            # 回滚事务
            self.db.rollback()
            
            # 验证数据是否被回滚
            result = self.db.fetchone("SELECT * FROM `test_table` WHERE `email` = %s", ('transaction@example.com',))
            
            self.db.close()
            return result is None
        except Exception as e:
            logger.error(f"事务测试失败: {e}")
            return False
    
    def cleanup_test_data(self) -> bool:
        """清理测试数据"""
        try:
            self.db.connect()
            
            # 删除测试表
            self.db.execute("DROP TABLE IF EXISTS `test_table`")
            self.db.commit()
            
            self.db.close()
            return True
        except Exception as e:
            logger.error(f"清理测试数据失败: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MySQL数据库连接测试工具')
    parser.add_argument('--host', default='localhost', help='MySQL主机地址')
    parser.add_argument('--port', type=int, default=3306, help='MySQL端口')
    parser.add_argument('--user', default='ssl_manager', help='MySQL用户名')
    parser.add_argument('--password', default='ssl_manager_password', help='MySQL密码')
    parser.add_argument('--database', default='ssl_manager', help='MySQL数据库名')
    
    args = parser.parse_args()
    
    # 创建MySQL配置
    config = DatabaseConfig()
    config.host = args.host
    config.port = args.port
    config.username = args.user
    config.password = args.password
    config.database = args.database
    
    # 运行测试
    tester = MySQLConnectionTester(config)
    
    if tester.run_all_tests():
        print("\n✓ 所有测试通过！MySQL数据库配置正确。")
        sys.exit(0)
    else:
        print("\n✗ 部分测试失败！请检查MySQL配置。")
        sys.exit(1)


if __name__ == '__main__':
    main()
