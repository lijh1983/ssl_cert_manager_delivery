#!/usr/bin/env python3
"""
SSL证书管理器模块测试脚本
"""

import sys
import os
import traceback

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_database():
    """测试数据库模块"""
    try:
        from models.database import Database
        print('✓ Database 模型导入成功')
        
        # 测试数据库连接
        db = Database()
        print('✓ Database 实例化成功')
        return True
    except Exception as e:
        print(f'✗ Database 测试失败: {e}')
        traceback.print_exc()
        return False

def test_certificate_model():
    """测试证书模型"""
    try:
        from models.certificate import Certificate
        print('✓ Certificate 模型导入成功')
        return True
    except Exception as e:
        print(f'✗ Certificate 模型测试失败: {e}')
        traceback.print_exc()
        return False

def test_monitoring_service():
    """测试监控服务"""
    try:
        # 修改导入方式避免相对导入问题
        import models.database
        import models.certificate
        
        # 手动导入服务
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "monitoring_service", 
            "src/services/monitoring_service.py"
        )
        monitoring_module = importlib.util.module_from_spec(spec)
        
        # 设置模块的依赖
        monitoring_module.Certificate = models.certificate.Certificate
        monitoring_module.Database = models.database.Database
        
        spec.loader.exec_module(monitoring_module)
        
        service = monitoring_module.MonitoringService()
        print('✓ MonitoringService 测试成功')
        return True
    except Exception as e:
        print(f'✗ MonitoringService 测试失败: {e}')
        traceback.print_exc()
        return False

def test_domain_monitoring_service():
    """测试域名监控服务"""
    try:
        import dns.resolver
        print('✓ DNS 依赖可用')
        
        import requests
        print('✓ Requests 依赖可用')
        
        print('✓ DomainMonitoringService 依赖测试成功')
        return True
    except Exception as e:
        print(f'✗ DomainMonitoringService 依赖测试失败: {e}')
        return False

def test_port_monitoring_service():
    """测试端口监控服务"""
    try:
        import socket
        import ssl
        print('✓ Socket/SSL 依赖可用')
        
        import requests
        print('✓ Requests 依赖可用')
        
        print('✓ PortMonitoringService 依赖测试成功')
        return True
    except Exception as e:
        print(f'✗ PortMonitoringService 依赖测试失败: {e}')
        return False

def test_certificate_operations_service():
    """测试证书操作服务"""
    try:
        import pandas as pd
        print('✓ Pandas 依赖可用')
        
        import threading
        import uuid
        print('✓ Threading/UUID 依赖可用')
        
        print('✓ CertificateOperationsService 依赖测试成功')
        return True
    except Exception as e:
        print(f'✗ CertificateOperationsService 依赖测试失败: {e}')
        return False

def test_api_imports():
    """测试API相关导入"""
    try:
        from flask import Flask, request, jsonify
        print('✓ Flask 依赖可用')
        
        from flask_cors import CORS
        print('✓ Flask-CORS 依赖可用')
        
        return True
    except Exception as e:
        print(f'✗ API 依赖测试失败: {e}')
        return False

def main():
    """主测试函数"""
    print("SSL证书管理器模块测试开始\n")
    
    tests = [
        ("数据库模块", test_database),
        ("证书模型", test_certificate_model),
        ("监控服务", test_monitoring_service),
        ("域名监控服务", test_domain_monitoring_service),
        ("端口监控服务", test_port_monitoring_service),
        ("证书操作服务", test_certificate_operations_service),
        ("API依赖", test_api_imports)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- 测试 {test_name} ---")
        if test_func():
            passed += 1
        print()
    
    print(f"测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("✅ 所有测试通过！")
        return True
    else:
        print("❌ 部分测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
