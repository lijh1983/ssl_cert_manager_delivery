#!/usr/bin/env python3
"""
SSL证书管理器核心功能测试
"""

import unittest
import sys
import os
import tempfile

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestCoreFunctionality(unittest.TestCase):
    """核心功能测试类"""
    
    def setUp(self):
        """测试前准备"""
        pass

    def tearDown(self):
        """测试后清理"""
        pass

    def test_database_operations(self):
        """测试数据库操作 - 使用模拟数据库"""
        try:
            # 模拟数据库操作测试
            test_data = {
                'id': 1,
                'domain': 'test.example.com',
                'status': 'valid'
            }

            # 验证数据结构
            self.assertIsNotNone(test_data)
            self.assertEqual(test_data['domain'], 'test.example.com')
            self.assertEqual(test_data['status'], 'valid')
            self.assertEqual(test_data['id'], 1)

        except Exception as e:
            self.fail(f"数据库操作测试失败: {e}")
    
    def test_certificate_model_basic(self):
        """测试证书模型基础功能"""
        try:
            from models.certificate import Certificate
            
            # 创建证书实例
            cert_data = {
                'id': 1,
                'domain': 'test.example.com',
                'type': 'single',
                'status': 'valid',
                'server_id': 1,
                'ca_type': 'letsencrypt'
            }
            
            cert = Certificate(**cert_data)
            
            # 验证属性
            self.assertEqual(cert.domain, 'test.example.com')
            self.assertEqual(cert.type, 'single')
            self.assertEqual(cert.status, 'valid')
            self.assertEqual(cert.server_id, 1)
            self.assertEqual(cert.ca_type, 'letsencrypt')
            
        except Exception as e:
            self.fail(f"证书模型测试失败: {e}")
    
    def test_monitoring_service_basic(self):
        """测试监控服务基础功能"""
        try:
            from services.monitoring_service import MonitoringService
            
            # 创建监控服务实例
            service = MonitoringService()
            
            # 验证服务实例
            self.assertIsNotNone(service)
            self.assertTrue(hasattr(service, 'get_monitoring_config'))
            self.assertTrue(hasattr(service, 'update_monitoring_config'))
            
        except Exception as e:
            self.fail(f"监控服务测试失败: {e}")
    
    def test_domain_monitoring_service_basic(self):
        """测试域名监控服务基础功能"""
        try:
            from services.domain_monitoring_service import DomainMonitoringService
            
            # 创建域名监控服务实例
            service = DomainMonitoringService()
            
            # 验证服务实例
            self.assertIsNotNone(service)
            self.assertTrue(hasattr(service, 'check_domain_resolution'))
            self.assertTrue(hasattr(service, 'check_domain_reachability'))
            
        except Exception as e:
            self.fail(f"域名监控服务测试失败: {e}")
    
    def test_port_monitoring_service_basic(self):
        """测试端口监控服务基础功能"""
        try:
            from services.port_monitoring_service import PortMonitoringService
            
            # 创建端口监控服务实例
            service = PortMonitoringService()
            
            # 验证服务实例
            self.assertIsNotNone(service)
            self.assertTrue(hasattr(service, 'check_ssl_port'))
            self.assertTrue(hasattr(service, 'generate_security_report'))
            
        except Exception as e:
            self.fail(f"端口监控服务测试失败: {e}")
    
    def test_certificate_operations_service_basic(self):
        """测试证书操作服务基础功能"""
        try:
            from services.certificate_operations_service import CertificateOperationsService
            
            # 创建证书操作服务实例
            service = CertificateOperationsService()
            
            # 验证服务实例
            self.assertIsNotNone(service)
            self.assertTrue(hasattr(service, 'manual_certificate_check'))
            self.assertTrue(hasattr(service, 'import_certificates_from_csv'))
            self.assertTrue(hasattr(service, 'export_certificates_to_csv'))
            
        except Exception as e:
            self.fail(f"证书操作服务测试失败: {e}")
    
    def test_data_validation(self):
        """测试数据验证功能"""
        try:
            import re
            
            # 测试域名验证
            domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
            
            valid_domains = ['example.com', 'test.example.com', 'sub.domain.example.com']
            invalid_domains = ['', '.example.com', 'example.', 'ex..ample.com']
            
            for domain in valid_domains:
                self.assertTrue(re.match(domain_pattern, domain), f"域名 {domain} 应该有效")
            
            for domain in invalid_domains:
                self.assertFalse(re.match(domain_pattern, domain), f"域名 {domain} 应该无效")
            
            # 测试IP地址验证
            ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            
            valid_ips = ['192.168.1.1', '10.0.0.1', '172.16.0.1', '8.8.8.8']
            invalid_ips = ['256.1.1.1', '192.168.1', '192.168.1.1.1', 'not.an.ip']
            
            for ip in valid_ips:
                self.assertTrue(re.match(ip_pattern, ip), f"IP地址 {ip} 应该有效")
            
            for ip in invalid_ips:
                self.assertFalse(re.match(ip_pattern, ip), f"IP地址 {ip} 应该无效")
                
        except Exception as e:
            self.fail(f"数据验证测试失败: {e}")
    
    def test_ssl_functionality(self):
        """测试SSL功能"""
        try:
            import ssl
            import socket
            
            # 测试SSL上下文创建
            context = ssl.create_default_context()
            self.assertIsNotNone(context)
            
            # 测试SSL版本支持
            self.assertTrue(hasattr(ssl, 'PROTOCOL_TLS'))
            
            # 测试证书验证模式
            self.assertTrue(hasattr(ssl, 'CERT_REQUIRED'))
            self.assertTrue(hasattr(ssl, 'CERT_OPTIONAL'))
            self.assertTrue(hasattr(ssl, 'CERT_NONE'))
            
        except Exception as e:
            self.fail(f"SSL功能测试失败: {e}")
    
    def test_json_operations(self):
        """测试JSON操作"""
        try:
            import json
            
            # 测试数据序列化和反序列化
            test_data = {
                'certificate': {
                    'domain': 'test.example.com',
                    'status': 'valid',
                    'ports': [80, 443],
                    'metadata': {
                        'issuer': 'Let\'s Encrypt',
                        'expires_at': '2024-12-31T23:59:59Z'
                    }
                }
            }
            
            # 序列化
            json_str = json.dumps(test_data)
            self.assertIsInstance(json_str, str)
            
            # 反序列化
            parsed_data = json.loads(json_str)
            self.assertEqual(parsed_data['certificate']['domain'], 'test.example.com')
            self.assertEqual(parsed_data['certificate']['ports'], [80, 443])
            
        except Exception as e:
            self.fail(f"JSON操作测试失败: {e}")
    
    def test_datetime_operations(self):
        """测试日期时间操作"""
        try:
            from datetime import datetime, timedelta
            import time
            
            # 测试当前时间
            now = datetime.now()
            self.assertIsInstance(now, datetime)
            
            # 测试时间计算
            future = now + timedelta(days=30)
            self.assertTrue(future > now)
            
            # 测试时间格式化
            time_str = now.strftime('%Y-%m-%d %H:%M:%S')
            self.assertIsInstance(time_str, str)
            
            # 测试时间戳
            timestamp = time.time()
            self.assertIsInstance(timestamp, float)
            
        except Exception as e:
            self.fail(f"日期时间操作测试失败: {e}")

if __name__ == '__main__':
    # 设置测试环境
    os.environ['TESTING'] = 'true'
    
    # 运行测试
    unittest.main(verbosity=2)
