"""
PostgreSQL数据库模型定义模块
兼容Docker Compose中的PostgreSQL配置
"""
import os
import psycopg2
import psycopg2.extras
import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgreSQLDatabase:
    """PostgreSQL数据库操作类"""
    
    def __init__(self):
        """初始化数据库连接参数"""
        self.conn = None
        self.host = os.environ.get('DB_HOST', 'localhost')
        self.port = os.environ.get('DB_PORT', '5432')
        self.database = os.environ.get('DB_NAME', 'ssl_manager')
        self.user = os.environ.get('DB_USER', 'ssl_user')
        self.password = os.environ.get('DB_PASSWORD', 'ssl_password')
    
    def connect(self):
        """连接到PostgreSQL数据库"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            self.conn.autocommit = False
            logger.info(f"成功连接到PostgreSQL数据库: {self.host}:{self.port}/{self.database}")
        except psycopg2.Error as e:
            logger.error(f"连接PostgreSQL数据库失败: {e}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def execute(self, sql: str, params: tuple = ()) -> psycopg2.extras.RealDictCursor:
        """执行SQL语句"""
        if not self.conn:
            self.connect()
        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        return cursor
    
    def executemany(self, sql: str, params_list: List[tuple]) -> psycopg2.extras.RealDictCursor:
        """执行多条SQL语句"""
        if not self.conn:
            self.connect()
        cursor = self.conn.cursor()
        cursor.executemany(sql, params_list)
        return cursor
    
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
        result = cursor.fetchone()
        cursor.close()
        return dict(result) if result else None
    
    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """查询多条记录"""
        cursor = self.execute(sql, params)
        results = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in results]
    
    def insert(self, table: str, data: Dict[str, Any]) -> str:
        """插入数据，返回UUID"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s' for _ in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"
        cursor = self.execute(sql, tuple(data.values()))
        result = cursor.fetchone()
        cursor.close()
        self.commit()
        return result['id'] if result else None
    
    def update(self, table: str, data: Dict[str, Any], condition: str, params: tuple = ()) -> int:
        """更新数据"""
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        cursor = self.execute(sql, tuple(data.values()) + params)
        rowcount = cursor.rowcount
        cursor.close()
        self.commit()
        return rowcount
    
    def delete(self, table: str, condition: str, params: tuple = ()) -> int:
        """删除数据"""
        sql = f"DELETE FROM {table} WHERE {condition}"
        cursor = self.execute(sql, params)
        rowcount = cursor.rowcount
        cursor.close()
        self.commit()
        return rowcount
    
    def table_exists(self, table: str) -> bool:
        """检查表是否存在"""
        sql = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        )
        """
        result = self.fetchone(sql, (table,))
        return result['exists'] if result else False
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            self.connect()
            result = self.fetchone("SELECT version() as version")
            logger.info(f"数据库连接测试成功: {result['version']}")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
        finally:
            self.close()
    
    def get_table_info(self, table: str) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        sql = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """
        return self.fetchall(sql, (table,))
    
    def get_all_tables(self) -> List[str]:
        """获取所有表名"""
        sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        """
        results = self.fetchall(sql)
        return [row['table_name'] for row in results]

# 创建全局PostgreSQL数据库实例
pg_db = PostgreSQLDatabase()

def init_postgres_db():
    """初始化PostgreSQL数据库连接"""
    try:
        pg_db.connect()
        logger.info("PostgreSQL数据库初始化成功")
        return True
    except Exception as e:
        logger.error(f"PostgreSQL数据库初始化失败: {e}")
        return False
    finally:
        pg_db.close()

def test_postgres_connection():
    """测试PostgreSQL连接"""
    return pg_db.test_connection()

if __name__ == "__main__":
    # 直接运行此模块时测试数据库连接
    if test_postgres_connection():
        print("✅ PostgreSQL数据库连接测试成功")
        
        # 显示数据库信息
        pg_db.connect()
        tables = pg_db.get_all_tables()
        print(f"📋 数据库表列表: {tables}")
        
        for table in tables:
            columns = pg_db.get_table_info(table)
            print(f"\n📊 表 {table} 结构:")
            for col in columns:
                print(f"  - {col['column_name']}: {col['data_type']} ({'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'})")
        
        pg_db.close()
    else:
        print("❌ PostgreSQL数据库连接测试失败")
        exit(1)
