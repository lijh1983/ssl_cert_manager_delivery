#!/usr/bin/env python3
"""
ACME功能演示脚本
展示SSL证书自动化管理系统的ACME协议实现
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.acme_client import ACMEManager, CertificateAuthority
from services.dns_providers import DNSManager


def demo_acme_manager():
    """演示ACME管理器功能"""
    print("=" * 60)
    print("🔐 SSL证书自动化管理系统 - ACME功能演示")
    print("=" * 60)
    
    # 创建临时目录用于演示
    temp_dir = tempfile.mkdtemp()
    print(f"📁 临时存储目录: {temp_dir}")
    
    try:
        # 设置环境变量
        os.environ['CERT_STORAGE_PATH'] = temp_dir
        
        # 创建ACME管理器（使用staging环境）
        print("\n🚀 初始化ACME管理器...")
        acme_manager = ACMEManager('demo@example.com', staging=True)
        
        # 显示支持的CA
        print("\n📋 支持的证书颁发机构:")
        cas = acme_manager.get_supported_cas()
        for ca in cas:
            status = "✅ 可用" if ca['available'] else "❌ 不可用"
            print(f"  • {ca['display_name']} ({ca['name']}) - {status}")
            if ca['rate_limits']:
                print(f"    限制: 每周{ca['rate_limits']['certificates_per_week']}张证书")
        
        # 演示证书申请流程（模拟）
        print("\n🎯 证书申请流程演示:")
        domains = ['demo.example.com']
        print(f"  域名: {', '.join(domains)}")
        print(f"  CA: Let's Encrypt (Staging)")
        print(f"  验证方式: HTTP-01")
        
        # 注意：这里不会真正申请证书，因为域名不存在
        print("  ⚠️  注意: 这是演示模式，不会真正申请证书")
        
        # 演示CSR生成
        print("\n🔑 生成证书签名请求 (CSR)...")
        client = acme_manager.get_client('letsencrypt')
        if client:
            try:
                csr_pem, key_pem = client.generate_csr(domains)
                print(f"  ✅ CSR生成成功 ({len(csr_pem)} 字节)")
                print(f"  ✅ 私钥生成成功 ({len(key_pem)} 字节)")
                
                # 显示CSR的前几行
                csr_lines = csr_pem.decode().split('\n')
                print("  📄 CSR内容预览:")
                for line in csr_lines[:3]:
                    print(f"    {line}")
                print("    ...")
                
            except Exception as e:
                print(f"  ❌ CSR生成失败: {e}")
        
        # 演示DNS管理器
        print("\n🌐 DNS管理器演示:")
        dns_manager = DNSManager()
        providers = dns_manager.get_available_providers()
        
        if providers:
            print(f"  📡 可用的DNS提供商: {', '.join(providers)}")
        else:
            print("  ⚠️  未配置DNS提供商")
            print("  💡 提示: 设置环境变量来启用DNS提供商:")
            print("    - CLOUDFLARE_API_TOKEN 或 CLOUDFLARE_EMAIL + CLOUDFLARE_API_KEY")
            print("    - ALIYUN_ACCESS_KEY_ID + ALIYUN_ACCESS_KEY_SECRET")
            print("    - DNSPOD_TOKEN")
        
        # 演示证书状态检查
        print("\n📊 证书管理功能:")
        print("  • 证书申请 (request_certificate)")
        print("  • 证书续期 (renew_certificate)")
        print("  • 证书撤销 (revoke_certificate)")
        print("  • 状态检查 (get_certificate_status)")
        print("  • 自动续期 (auto_renew_certificates)")
        
        # 演示配置信息
        print("\n⚙️  系统配置:")
        print(f"  存储路径: {temp_dir}")
        print(f"  Staging模式: 是")
        print(f"  联系邮箱: demo@example.com")
        
        # 演示安全特性
        print("\n🔒 安全特性:")
        print("  • 账户私钥自动生成和保存")
        print("  • 证书私钥安全存储")
        print("  • DNS验证记录自动清理")
        print("  • 支持多种验证方式 (HTTP-01, DNS-01)")
        print("  • 证书信息加密存储")
        
        print("\n✨ 演示完成!")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 清理临时目录
        try:
            shutil.rmtree(temp_dir)
            print(f"🧹 已清理临时目录: {temp_dir}")
        except Exception as e:
            print(f"⚠️  清理临时目录失败: {e}")


def demo_certificate_authorities():
    """演示证书颁发机构信息"""
    print("\n" + "=" * 60)
    print("🏛️  证书颁发机构 (CA) 详细信息")
    print("=" * 60)
    
    cas = [
        ('Let\'s Encrypt', CertificateAuthority.LETS_ENCRYPT_PROD),
        ('ZeroSSL', CertificateAuthority.ZEROSSL),
        ('Buypass', CertificateAuthority.BUYPASS)
    ]
    
    for name, config in cas:
        print(f"\n📋 {name}:")
        print(f"  生产环境: {config['directory_url']}")
        print(f"  测试环境: {config['staging_url']}")
        print(f"  速率限制:")
        for limit_name, limit_value in config['rate_limits'].items():
            print(f"    • {limit_name}: {limit_value}")


def demo_validation_methods():
    """演示验证方式"""
    print("\n" + "=" * 60)
    print("🔍 域名验证方式说明")
    print("=" * 60)
    
    print("\n1️⃣  HTTP-01 验证:")
    print("  • 在域名的 /.well-known/acme-challenge/ 路径下放置验证文件")
    print("  • 适用于有Web服务器的域名")
    print("  • 不支持通配符证书")
    print("  • 端口要求: 80")
    
    print("\n2️⃣  DNS-01 验证:")
    print("  • 在域名的DNS记录中添加TXT记录")
    print("  • 支持通配符证书")
    print("  • 需要DNS API访问权限")
    print("  • 记录名称: _acme-challenge.domain.com")
    
    print("\n🎯 推荐使用场景:")
    print("  • HTTP验证: 普通网站、单域名证书")
    print("  • DNS验证: 通配符证书、内网服务、多域名证书")


def main():
    """主函数"""
    print("🎉 欢迎使用SSL证书自动化管理系统!")
    print("本演示将展示ACME协议实现的主要功能\n")
    
    try:
        # 演示ACME管理器
        demo_acme_manager()
        
        # 演示CA信息
        demo_certificate_authorities()
        
        # 演示验证方式
        demo_validation_methods()
        
        print("\n" + "=" * 60)
        print("🎊 演示结束，感谢使用!")
        print("=" * 60)
        print("\n💡 下一步:")
        print("  1. 配置DNS提供商API密钥")
        print("  2. 设置生产环境邮箱地址")
        print("  3. 运行真实的证书申请测试")
        print("  4. 配置自动续期任务")
        
    except KeyboardInterrupt:
        print("\n\n👋 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
