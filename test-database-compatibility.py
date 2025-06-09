#!/usr/bin/env python3
"""
PostgreSQL数据库兼容性测试脚本
验证数据库初始化脚本与后端代码的兼容性
"""

import os
import sys
import uuid
import datetime
from typing import Dict, Any

# 添加后端模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))

try:
    from models.database_postgres import pg_db
    print("✅ 成功导入PostgreSQL数据库模块")
except ImportError as e:
    print(f"❌ 导入PostgreSQL数据库模块失败: {e}")
    sys.exit(1)

def test_database_connection():
    """测试数据库连接"""
    print("\n=== 测试数据库连接 ===")
    try:
        pg_db.connect()
        result = pg_db.fetchone("SELECT version() as version, current_database() as db, current_user as user")
        print(f"✅ 数据库连接成功")
        print(f"   版本: {result['version']}")
        print(f"   数据库: {result['db']}")
        print(f"   用户: {result['user']}")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False
    finally:
        pg_db.close()

def test_table_structure():
    """测试表结构"""
    print("\n=== 测试表结构 ===")
    expected_tables = [
        'users', 'servers', 'certificates', 'alerts', 
        'operation_logs', 'certificate_deployments', 'settings'
    ]
    
    try:
        pg_db.connect()
        existing_tables = pg_db.get_all_tables()
        
        print(f"📋 数据库中的表: {existing_tables}")
        
        missing_tables = []
        for table in expected_tables:
            if table not in existing_tables:
                missing_tables.append(table)
            else:
                print(f"✅ 表 {table} 存在")
        
        if missing_tables:
            print(f"❌ 缺少表: {missing_tables}")
            return False
        
        print("✅ 所有必需的表都存在")
        return True
        
    except Exception as e:
        print(f"❌ 表结构检查失败: {e}")
        return False
    finally:
        pg_db.close()

def test_crud_operations():
    """测试CRUD操作"""
    print("\n=== 测试CRUD操作 ===")
    
    try:
        pg_db.connect()
        
        # 测试用户表操作
        print("📝 测试用户表操作...")
        
        # 创建测试用户
        user_data = {
            'username': f'test_user_{uuid.uuid4().hex[:8]}',
            'email': f'test_{uuid.uuid4().hex[:8]}@example.com',
            'password_hash': '$2b$12$test_hash',
            'role': 'user'
        }
        
        user_id = pg_db.insert('users', user_data)
        print(f"✅ 创建用户成功，ID: {user_id}")
        
        # 查询用户
        user = pg_db.fetchone("SELECT * FROM users WHERE id = %s", (user_id,))
        if user:
            print(f"✅ 查询用户成功: {user['username']}")
        else:
            print("❌ 查询用户失败")
            return False
        
        # 更新用户
        update_count = pg_db.update('users', {'role': 'admin'}, 'id = %s', (user_id,))
        if update_count > 0:
            print("✅ 更新用户成功")
        else:
            print("❌ 更新用户失败")
            return False
        
        # 测试服务器表操作
        print("📝 测试服务器表操作...")
        
        server_data = {
            'name': f'test_server_{uuid.uuid4().hex[:8]}',
            'ip': '192.168.1.100',
            'os_type': 'Ubuntu',
            'version': '20.04',
            'token': uuid.uuid4().hex,
            'auto_renew': True,
            'user_id': user_id
        }
        
        server_id = pg_db.insert('servers', server_data)
        print(f"✅ 创建服务器成功，ID: {server_id}")
        
        # 测试证书表操作
        print("📝 测试证书表操作...")
        
        cert_data = {
            'domain': f'test{uuid.uuid4().hex[:8]}.example.com',
            'type': 'single',
            'status': 'pending',
            'expires_at': (datetime.datetime.now() + datetime.timedelta(days=90)).isoformat(),
            'server_id': server_id,
            'ca_type': 'letsencrypt',
            'private_key': '',
            'certificate': ''
        }
        
        cert_id = pg_db.insert('certificates', cert_data)
        print(f"✅ 创建证书成功，ID: {cert_id}")
        
        # 清理测试数据
        pg_db.delete('certificates', 'id = %s', (cert_id,))
        pg_db.delete('servers', 'id = %s', (server_id,))
        pg_db.delete('users', 'id = %s', (user_id,))
        print("✅ 清理测试数据成功")
        
        return True
        
    except Exception as e:
        print(f"❌ CRUD操作测试失败: {e}")
        return False
    finally:
        pg_db.close()

def test_default_data():
    """测试默认数据"""
    print("\n=== 测试默认数据 ===")
    
    try:
        pg_db.connect()
        
        # 检查默认管理员用户
        admin_user = pg_db.fetchone("SELECT * FROM users WHERE role = 'admin' LIMIT 1")
        if admin_user:
            print(f"✅ 默认管理员用户存在: {admin_user['username']}")
        else:
            print("❌ 默认管理员用户不存在")
            return False
        
        # 检查默认设置
        settings = pg_db.fetchall("SELECT * FROM settings")
        if len(settings) >= 5:
            print(f"✅ 默认设置存在 ({len(settings)} 项)")
            for setting in settings:
                print(f"   - {setting['key']}: {setting['value']}")
        else:
            print(f"❌ 默认设置不完整，只有 {len(settings)} 项")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 默认数据检查失败: {e}")
        return False
    finally:
        pg_db.close()

def test_indexes_and_constraints():
    """测试索引和约束"""
    print("\n=== 测试索引和约束 ===")

    try:
        pg_db.connect()

        # 简单检查是否有索引
        result = pg_db.fetchone("SELECT COUNT(*) as count FROM pg_indexes WHERE schemaname = 'public'")
        total_indexes = result['count'] if result else 0

        if total_indexes >= 15:
            print(f"✅ 索引创建成功 ({total_indexes} 个)")
        else:
            print(f"⚠️  索引数量: {total_indexes} 个")
            if total_indexes >= 10:
                print("✅ 基本索引存在，可以正常使用")
            else:
                print("❌ 索引数量不足")
                return False

        # 检查是否有外键约束
        result = pg_db.fetchone("SELECT COUNT(*) as count FROM pg_constraint WHERE contype = 'f'")
        constraint_count = result['count'] if result else 0

        if constraint_count >= 1:
            print(f"✅ 外键约束存在 ({constraint_count} 个)")
        else:
            print("❌ 没有外键约束")
            return False

        # 检查是否有主键约束
        result = pg_db.fetchone("SELECT COUNT(*) as count FROM pg_constraint WHERE contype = 'p'")
        pk_count = result['count'] if result else 0

        if pk_count >= 7:
            print(f"✅ 主键约束正常 ({pk_count} 个)")
        else:
            print(f"⚠️  主键约束数量: {pk_count} 个")

        return True

    except Exception as e:
        print(f"❌ 索引和约束检查失败: {e}")
        return False
    finally:
        pg_db.close()

def main():
    """主测试函数"""
    print("🔍 PostgreSQL数据库兼容性测试")
    print("=" * 50)
    
    tests = [
        ("数据库连接", test_database_connection),
        ("表结构", test_table_structure),
        ("CRUD操作", test_crud_operations),
        ("默认数据", test_default_data),
        ("索引和约束", test_indexes_and_constraints),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！PostgreSQL数据库配置完全兼容后端代码")
        return 0
    else:
        print("⚠️  部分测试失败，需要检查数据库配置")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
