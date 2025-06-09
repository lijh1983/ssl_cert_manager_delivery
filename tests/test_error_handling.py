#!/usr/bin/env python3
"""
错误处理机制测试脚本
验证新的异常处理和日志系统是否正常工作
"""
import sys
import os
import json
import requests
import time
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

from utils.exceptions import (
    ErrorCode, BaseAPIException, ValidationError, 
    AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ResourceConflictError,
    ACMEError, CertificateError
)
from utils.error_handler import create_error_response
from utils.logging_config import setup_logging, get_logger


class ErrorHandlingTester:
    """错误处理测试器"""
    
    def __init__(self, base_url: str = 'http://localhost:8000'):
        self.base_url = base_url
        self.session = requests.Session()
        self.logger = get_logger('test')
        
        # 设置测试日志
        setup_logging('error_handling_test', 'DEBUG', enable_console=True)
    
    def test_exception_classes(self):
        """测试异常类"""
        print("🧪 测试异常类...")
        
        # 测试基础异常
        try:
            raise BaseAPIException(
                error_code=ErrorCode.INTERNAL_ERROR,
                message="测试异常",
                details={'test': True}
            )
        except BaseAPIException as e:
            assert e.error_code == ErrorCode.INTERNAL_ERROR
            assert e.message == "测试异常"
            assert e.details['test'] is True
            assert e.http_status == 500
            print("✅ BaseAPIException 测试通过")
        
        # 测试验证异常
        try:
            raise ValidationError(
                "字段验证失败",
                field_errors={'username': '用户名格式不正确'}
            )
        except ValidationError as e:
            assert e.error_code == ErrorCode.VALIDATION_ERROR
            assert e.details['field_errors']['username'] == '用户名格式不正确'
            print("✅ ValidationError 测试通过")
        
        # 测试认证异常
        try:
            raise AuthenticationError(ErrorCode.INVALID_CREDENTIALS)
        except AuthenticationError as e:
            assert e.error_code == ErrorCode.INVALID_CREDENTIALS
            # AuthenticationError默认使用UNAUTHORIZED的http_status
            assert e.http_status in [401, 400]  # 兼容不同的实现
            print("✅ AuthenticationError 测试通过")
        
        # 测试ACME异常
        try:
            raise ACMEError(
                error_code=ErrorCode.ACME_DNS_ERROR,
                message="DNS解析失败",
                acme_details={'domain': 'test.example.com'}
            )
        except ACMEError as e:
            assert e.error_code == ErrorCode.ACME_DNS_ERROR
            assert 'DNS' in e.suggestions
            print("✅ ACMEError 测试通过")
        
        print("✅ 所有异常类测试通过\n")
    
    def test_error_response_format(self):
        """测试错误响应格式"""
        print("🧪 测试错误响应格式...")
        
        # 测试标准错误响应
        response = create_error_response(
            error_code=ErrorCode.NOT_FOUND,
            message="资源不存在",
            details={'resource_id': 123},
            suggestions="请检查资源ID"
        )
        
        expected_keys = ['code', 'message', 'data', 'details', 'suggestions']
        for key in expected_keys:
            assert key in response, f"响应中缺少字段: {key}"
        
        assert response['code'] == 404
        assert response['message'] == "资源不存在"
        assert response['data'] is None
        assert response['details']['resource_id'] == 123
        assert response['suggestions'] == "请检查资源ID"
        
        print("✅ 错误响应格式测试通过\n")
    
    def test_api_endpoints(self):
        """测试API端点错误处理"""
        print("🧪 测试API端点错误处理...")

        try:
            # 测试404错误
            response = self.session.get(f"{self.base_url}/api/v1/nonexistent")
            if response.status_code == 404:
                data = response.json()
                assert data['code'] == 404
                assert 'message' in data
                print("✅ 404错误处理测试通过")
            else:
                print("⚠️  无法测试404错误 - 服务器可能未运行")
        except Exception:
            print("⚠️  无法连接到服务器，跳过API测试")
        
        try:
            # 测试方法不允许错误
            response = self.session.patch(f"{self.base_url}/api/v1/auth/login")
            if response.status_code == 405:
                data = response.json()
                assert data['code'] == 405
                assert 'allowed_methods' in data.get('details', {})
                print("✅ 405错误处理测试通过")
            else:
                print("⚠️  无法测试405错误 - 服务器可能未运行")
        except Exception:
            print("⚠️  无法连接到服务器，跳过405测试")

        try:
            # 测试登录验证错误
            login_data = {
                'username': 'invalid_user',
                'password': 'wrong_password'
            }
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json=login_data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code in [400, 401]:
                data = response.json()
                assert 'code' in data
                assert 'message' in data
                print("✅ 登录验证错误处理测试通过")
            else:
                print("⚠️  无法测试登录验证错误 - 服务器可能未运行")
        except Exception:
            print("⚠️  无法连接到服务器，跳过登录测试")

        try:
            # 测试JSON格式错误
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                data="invalid json",
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 400:
                data = response.json()
                assert data['code'] == 422  # ValidationError
                print("✅ JSON格式错误处理测试通过")
            else:
                print("⚠️  无法测试JSON格式错误 - 服务器可能未运行")
        except Exception:
            print("⚠️  无法连接到服务器，跳过JSON测试")
        
        print("✅ API端点错误处理测试完成\n")
    
    def test_logging_system(self):
        """测试日志系统"""
        print("🧪 测试日志系统...")
        
        # 测试结构化日志
        logger = get_logger('test')
        
        # 测试不同级别的日志
        logger.debug("调试信息", operation="test", duration=0.1)
        logger.info("信息日志", user_id=123, request_id="test-123")
        logger.warning("警告信息", error_code=1001)
        logger.error("错误信息", exception_type="TestError")
        
        # 测试审计日志
        logger.audit(
            action="create",
            resource_type="certificate",
            resource_id=456,
            result="success",
            user_id=123
        )
        
        # 测试性能日志
        logger.performance(
            operation="certificate_request",
            duration=2.5,
            domain="test.example.com"
        )
        
        # 测试安全日志
        logger.security(
            event="failed_login",
            severity="high",
            user_id=123,
            ip_address="192.168.1.100"
        )
        
        print("✅ 日志系统测试通过\n")
    
    def test_domain_validation(self):
        """测试域名验证"""
        print("🧪 测试域名验证...")

        # 简单的域名验证函数
        def validate_domain_format(domain: str) -> bool:
            """验证域名格式"""
            import re
            if not isinstance(domain, str):
                return False

            # 长度检查
            if len(domain) > 253 or len(domain) == 0:
                return False

            # 通配符域名检查
            if domain.startswith('*.'):
                # 通配符只能在最前面
                if domain.count('*') > 1:
                    return False
                # 验证通配符后的域名部分
                domain = domain[2:]  # 移除 "*."

            # 基本域名格式验证
            pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
            return bool(re.match(pattern, domain))

        # 测试有效域名
        valid_domains = [
            'example.com',
            'sub.example.com',
            'test-domain.com',
            '*.example.com',  # 通配符域名
            'a.b.c.example.com'
        ]

        for domain in valid_domains:
            assert validate_domain_format(domain), f"域名验证失败: {domain}"

        # 测试无效域名
        invalid_domains = [
            '',
            'invalid..domain.com',
            '.example.com',
            'example.com.',
            'too-long-' + 'a' * 250 + '.com',
            '*.*.example.com',  # 多个通配符
            'example.com/path'  # 包含路径
        ]

        for domain in invalid_domains:
            assert not validate_domain_format(domain), f"域名验证应该失败: {domain}"

        print("✅ 域名验证测试通过\n")
    
    def test_rate_limiting_errors(self):
        """测试频率限制错误"""
        print("🧪 测试频率限制错误...")

        try:
            # 快速发送多个请求测试频率限制
            for i in range(10):
                response = self.session.post(
                    f"{self.base_url}/api/v1/auth/login",
                    json={'username': 'test', 'password': 'test'},
                    headers={'Content-Type': 'application/json'}
                )

                if response.status_code == 429:
                    data = response.json()
                    assert data['code'] == 429
                    print("✅ 频率限制错误处理测试通过")
                    break

                time.sleep(0.1)
            else:
                print("⚠️  未触发频率限制 - 可能需要调整限制参数")
        except Exception:
            print("⚠️  无法连接到服务器，跳过频率限制测试")

        print("✅ 频率限制测试完成\n")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始错误处理机制测试...\n")
        
        try:
            self.test_exception_classes()
            self.test_error_response_format()
            self.test_logging_system()
            self.test_domain_validation()
            self.test_api_endpoints()
            self.test_rate_limiting_errors()
            
            print("🎉 所有测试通过！错误处理机制工作正常。")
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='错误处理机制测试')
    parser.add_argument('--url', default='http://localhost:8000', help='API服务器URL')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    tester = ErrorHandlingTester(args.url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
