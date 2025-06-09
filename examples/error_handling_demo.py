#!/usr/bin/env python3
"""
错误处理机制演示脚本
展示如何使用新的异常处理、日志记录和配置管理功能
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'src'))

from utils.exceptions import (
    ErrorCode, ValidationError, AuthenticationError, 
    ACMEError, CertificateError, ResourceNotFoundError
)
from utils.logging_config import setup_logging, get_logger
from utils.config_manager import get_config, get_security_config
from utils.error_handler import create_error_response


def demo_exceptions():
    """演示异常处理"""
    print("🔥 异常处理演示")
    print("=" * 50)
    
    # 1. 验证异常
    try:
        raise ValidationError(
            "用户输入验证失败",
            field_errors={
                'email': '邮箱格式不正确',
                'password': '密码长度不足8位'
            }
        )
    except ValidationError as e:
        print(f"✅ 捕获验证异常: {e.message}")
        print(f"   错误码: {e.error_code.value}")
        print(f"   字段错误: {e.details['field_errors']}")
        print(f"   建议: {e.suggestions}")
        print()
    
    # 2. 认证异常
    try:
        raise AuthenticationError(
            ErrorCode.INVALID_CREDENTIALS,
            "用户名或密码错误"
        )
    except AuthenticationError as e:
        print(f"✅ 捕获认证异常: {e.message}")
        print(f"   HTTP状态码: {e.http_status}")
        print(f"   建议: {e.suggestions}")
        print()


def demo_logging():
    """演示日志记录"""
    print("📝 日志记录演示")
    print("=" * 50)
    
    # 设置日志
    setup_logging('demo_app', 'INFO', '/tmp/demo.log', True)
    logger = get_logger('demo')
    
    # 基础日志
    logger.info("应用启动", version="1.0.0", environment="demo")
    logger.warning("配置项缺失", config_key="smtp_host")
    logger.error("数据库连接失败", error_code=1601, retry_count=3)
    
    # 审计日志
    logger.audit(
        action="create",
        resource_type="certificate",
        resource_id="cert-123",
        result="success",
        user_id=456,
        domain="demo.example.com"
    )
    
    print("✅ 日志记录完成，查看 /tmp/demo.log 文件")
    print()


def demo_configuration():
    """演示配置管理"""
    print("⚙️  配置管理演示")
    print("=" * 50)
    
    # 获取配置
    config = get_config()
    security_config = get_security_config()
    
    print(f"✅ 应用名称: {config.app_name}")
    print(f"✅ 应用版本: {config.version}")
    print(f"✅ 运行环境: {config.environment}")
    print(f"✅ JWT过期时间: {security_config.jwt_expiration}秒")
    print()


def main():
    """主函数"""
    print("🚀 SSL证书管理系统 - 错误处理机制演示")
    print("=" * 60)
    print()
    
    try:
        demo_exceptions()
        demo_logging()
        demo_configuration()
        
        print("🎉 演示完成！")
        print()
        print("📋 查看生成的文件:")
        print("   - /tmp/demo.log (演示日志)")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
