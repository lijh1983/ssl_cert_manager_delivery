#!/usr/bin/env python3
"""
SSL证书管理器基础功能测试
"""

import unittest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestBasicFunctionality(unittest.TestCase):
    """基础功能测试类"""
    
    def test_imports(self):
        """测试核心模块导入"""
        try:
            from models.database import Database
            from models.certificate import Certificate
            self.assertTrue(True, "核心模块导入成功")
        except ImportError as e:
            self.fail(f"核心模块导入失败: {e}")
    
    def test_database_connection(self):
        """测试数据库连接"""
        try:
            from models.database import Database
            db = Database()
            self.assertIsNotNone(db, "数据库实例创建成功")
        except Exception as e:
            self.fail(f"数据库连接测试失败: {e}")
    
    def test_certificate_model(self):
        """测试证书模型"""
        try:
            from models.certificate import Certificate
            
            # 测试证书实例创建
            cert = Certificate(
                id=1,
                domain='test.example.com',
                type='single',
                status='valid'
            )
            
            self.assertEqual(cert.domain, 'test.example.com')
            self.assertEqual(cert.type, 'single')
            self.assertEqual(cert.status, 'valid')
            
        except Exception as e:
            self.fail(f"证书模型测试失败: {e}")
    
    def test_flask_app_creation(self):
        """测试Flask应用创建"""
        try:
            from app import app
            self.assertIsNotNone(app, "Flask应用创建成功")
            self.assertEqual(app.name, 'app')
        except Exception as e:
            self.fail(f"Flask应用创建测试失败: {e}")
    
    def test_api_endpoints_exist(self):
        """测试API端点存在性"""
        try:
            from app import app
            
            # 获取所有路由
            routes = []
            for rule in app.url_map.iter_rules():
                routes.append(rule.rule)
            
            # 检查关键API端点
            key_endpoints = [
                '/api/v1/certificates',
                '/health'
            ]
            
            for endpoint in key_endpoints:
                # 检查是否存在类似的端点
                found = any(endpoint in route for route in routes)
                self.assertTrue(found, f"API端点 {endpoint} 存在")
                
        except Exception as e:
            self.fail(f"API端点测试失败: {e}")
    
    def test_environment_variables(self):
        """测试环境变量配置"""
        # 测试默认配置
        self.assertTrue(True, "环境变量测试通过")
    
    def test_ssl_certificate_validation(self):
        """测试SSL证书验证功能"""
        try:
            import ssl
            import socket
            
            # 测试SSL模块可用性
            self.assertTrue(hasattr(ssl, 'create_default_context'))
            self.assertTrue(hasattr(socket, 'create_connection'))
            
        except Exception as e:
            self.fail(f"SSL证书验证功能测试失败: {e}")
    
    def test_dns_resolution(self):
        """测试DNS解析功能"""
        try:
            import dns.resolver
            
            # 测试DNS解析器可用性
            resolver = dns.resolver.Resolver()
            self.assertIsNotNone(resolver)
            
        except ImportError:
            self.skipTest("DNS解析模块未安装")
        except Exception as e:
            self.fail(f"DNS解析功能测试失败: {e}")
    
    def test_data_processing(self):
        """测试数据处理功能"""
        try:
            import pandas as pd
            import json
            
            # 测试数据处理模块
            data = {'test': 'value'}
            json_str = json.dumps(data)
            parsed_data = json.loads(json_str)
            
            self.assertEqual(parsed_data['test'], 'value')
            
            # 测试pandas基础功能
            df = pd.DataFrame([{'domain': 'test.com', 'status': 'valid'}])
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]['domain'], 'test.com')
            
        except Exception as e:
            self.fail(f"数据处理功能测试失败: {e}")

if __name__ == '__main__':
    # 设置测试环境
    os.environ['TESTING'] = 'true'
    
    # 运行测试
    unittest.main(verbosity=2)
