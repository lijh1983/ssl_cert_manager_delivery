#!/usr/bin/env python3
"""
监控告警系统演示脚本
展示SSL证书自动化管理系统的监控告警功能
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 禁用监控线程以避免演示时的干扰
os.environ['DISABLE_MONITORING'] = '1'

from services.notification import NotificationManager, NotificationTemplate, EmailProvider
from services.alert_manager import AlertManager, AlertRule, AlertType, AlertSeverity


def demo_notification_templates():
    """演示通知模板功能"""
    print("=" * 60)
    print("📧 通知模板系统演示")
    print("=" * 60)
    
    # 演示证书过期模板
    print("\n1️⃣  证书即将过期通知模板:")
    context = {
        'domain': 'example.com',
        'expires_at': '2024-01-01 00:00:00',
        'days_remaining': 7,
        'server_name': 'web-server-01',
        'ca_type': 'Let\'s Encrypt'
    }
    
    # 渲染邮件模板
    email_template = NotificationTemplate.render('certificate_expiring', 'email', context)
    print(f"  📧 邮件主题: {email_template['subject']}")
    print(f"  📧 邮件内容: {email_template['content'][:100]}...")
    
    # 渲染Slack模板
    slack_template = NotificationTemplate.render('certificate_expiring', 'slack', context)
    print(f"  💬 Slack消息: {slack_template['text']}")
    print(f"  📎 Slack附件数量: {len(slack_template.get('attachments', []))}")
    
    # 演示证书已过期模板
    print("\n2️⃣  证书已过期通知模板:")
    expired_context = {
        'domain': 'expired.example.com',
        'expires_at': '2023-12-01 00:00:00',
        'days_expired': 5,
        'server_name': 'api-server-02'
    }
    
    expired_template = NotificationTemplate.render('certificate_expired', 'email', expired_context)
    print(f"  🚨 邮件主题: {expired_template['subject']}")
    
    # 演示系统告警模板
    print("\n3️⃣  系统告警通知模板:")
    system_context = {
        'alert_type': 'server_offline',
        'severity': 'high',
        'alert_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'description': '服务器 web-01 已离线超过30分钟',
        'details': 'Last heartbeat: 2023-12-15 14:30:00\nStatus: offline\nUptime: 0 days'
    }
    
    system_template = NotificationTemplate.render('system_alert', 'email', system_context)
    print(f"  ⚠️  邮件主题: {system_template['subject']}")


def demo_notification_providers():
    """演示通知提供商"""
    print("\n" + "=" * 60)
    print("📡 通知提供商演示")
    print("=" * 60)
    
    # 创建通知管理器
    nm = NotificationManager()
    available_providers = nm.get_available_providers()
    
    print(f"\n📋 当前可用的通知提供商: {available_providers}")
    
    if not available_providers:
        print("\n💡 要启用通知提供商，请设置以下环境变量:")
        print("  📧 邮件通知:")
        print("    - SMTP_HOST: SMTP服务器地址")
        print("    - SMTP_USERNAME: SMTP用户名")
        print("    - SMTP_PASSWORD: SMTP密码")
        print("    - SMTP_FROM_EMAIL: 发件人邮箱")
        
        print("\n  🔗 Webhook通知:")
        print("    - WEBHOOK_URL: Webhook URL地址")
        
        print("\n  💬 Slack通知:")
        print("    - SLACK_WEBHOOK_URL: Slack Webhook URL")
        
        print("\n  📱 钉钉通知:")
        print("    - DINGTALK_WEBHOOK_URL: 钉钉机器人Webhook URL")
    
    # 演示邮件提供商配置
    print("\n📧 邮件提供商配置示例:")
    email_config = {
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'username': 'your-email@gmail.com',
        'password': 'your-app-password',
        'use_tls': True,
        'from_email': 'your-email@gmail.com',
        'from_name': 'SSL证书管理系统'
    }
    
    email_provider = EmailProvider(email_config)
    print(f"  ✅ 配置验证: {'通过' if email_provider.validate_config() else '失败'}")
    print(f"  📤 SMTP服务器: {email_provider.smtp_host}:{email_provider.smtp_port}")
    print(f"  🔐 TLS加密: {'启用' if email_provider.use_tls else '禁用'}")


def demo_alert_rules():
    """演示告警规则"""
    print("\n" + "=" * 60)
    print("📋 告警规则系统演示")
    print("=" * 60)
    
    # 创建告警管理器
    am = AlertManager()
    
    print(f"\n📊 系统默认告警规则数量: {len(am.get_rules())}")
    
    print("\n📝 默认告警规则详情:")
    for i, rule in enumerate(am.get_rules(), 1):
        severity_emoji = {
            'low': '🟢',
            'medium': '🟡', 
            'high': '🟠',
            'critical': '🔴'
        }.get(rule.severity.value, '⚪')
        
        print(f"  {i}. {severity_emoji} {rule.name}")
        print(f"     类型: {rule.alert_type.value}")
        print(f"     级别: {rule.severity.value}")
        print(f"     状态: {'启用' if rule.enabled else '禁用'}")
        print(f"     冷却: {rule.cooldown_minutes}分钟")
        print(f"     条件: {rule.conditions}")
        print(f"     通知: {', '.join(rule.notification_providers)}")
        print()
    
    # 演示创建自定义规则
    print("🔧 创建自定义告警规则:")
    custom_rule = AlertRule(
        id='custom_cert_warning',
        name='自定义证书预警',
        alert_type=AlertType.CERTIFICATE_EXPIRING,
        severity=AlertSeverity.MEDIUM,
        enabled=True,
        conditions={
            'days_before_expiry': 15,
            'check_interval_hours': 6
        },
        notification_providers=['email', 'slack'],
        notification_template='certificate_expiring',
        cooldown_minutes=360
    )
    
    success = am.add_rule(custom_rule)
    print(f"  ✅ 自定义规则创建: {'成功' if success else '失败'}")
    print(f"  📋 当前规则总数: {len(am.get_rules())}")


async def demo_alert_triggering():
    """演示告警触发"""
    print("\n" + "=" * 60)
    print("🚨 告警触发演示")
    print("=" * 60)
    
    # 创建告警管理器
    am = AlertManager()
    
    # 获取一个告警规则
    rule = am.get_rule('cert_expiring_7d')
    if not rule:
        print("❌ 未找到测试规则")
        return
    
    print(f"\n📋 使用规则: {rule.name}")
    
    # 模拟证书即将过期的情况
    context = {
        'resource_id': 'cert_demo_123',
        'domain': 'demo.example.com',
        'expires_at': (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
        'days_remaining': 5,
        'server_name': 'demo-web-server',
        'ca_type': 'Let\'s Encrypt'
    }
    
    print(f"\n🎯 模拟告警场景:")
    print(f"  域名: {context['domain']}")
    print(f"  过期时间: {context['expires_at']}")
    print(f"  剩余天数: {context['days_remaining']}")
    print(f"  服务器: {context['server_name']}")
    
    # 触发告警
    print(f"\n🚨 触发告警...")
    alert = await am.trigger_alert(rule, context)
    
    if alert:
        print(f"  ✅ 告警创建成功")
        print(f"  🆔 告警ID: {alert.id}")
        print(f"  📝 告警标题: {alert.title}")
        print(f"  📄 告警描述: {alert.description}")
        print(f"  ⏰ 创建时间: {alert.created_at}")
        
        # 显示活跃告警
        active_alerts = am.get_active_alerts()
        print(f"\n📊 当前活跃告警数量: {len(active_alerts)}")
        
        # 解决告警
        print(f"\n✅ 解决告警...")
        resolved = am.resolve_alert(alert.id)
        print(f"  解决结果: {'成功' if resolved else '失败'}")
        
        # 再次检查活跃告警
        active_alerts = am.get_active_alerts()
        print(f"  剩余活跃告警: {len(active_alerts)}")
        
    else:
        print(f"  ⚠️  告警未创建（可能在冷却期内）")


def demo_alert_statistics():
    """演示告警统计"""
    print("\n" + "=" * 60)
    print("📊 告警统计演示")
    print("=" * 60)
    
    am = AlertManager()
    
    # 按级别统计规则
    rules = am.get_rules()
    severity_stats = {}
    type_stats = {}
    
    for rule in rules:
        severity = rule.severity.value
        alert_type = rule.alert_type.value
        
        severity_stats[severity] = severity_stats.get(severity, 0) + 1
        type_stats[alert_type] = type_stats.get(alert_type, 0) + 1
    
    print(f"\n📈 按严重程度统计:")
    for severity, count in severity_stats.items():
        emoji = {'low': '🟢', 'medium': '🟡', 'high': '🟠', 'critical': '🔴'}.get(severity, '⚪')
        print(f"  {emoji} {severity}: {count} 个规则")
    
    print(f"\n📈 按告警类型统计:")
    for alert_type, count in type_stats.items():
        emoji = {
            'certificate_expiring': '📅',
            'certificate_expired': '🚨',
            'server_offline': '💻',
            'certificate_renewal_failed': '🔄',
            'system_error': '⚠️'
        }.get(alert_type, '📋')
        print(f"  {emoji} {alert_type}: {count} 个规则")
    
    # 显示告警历史统计
    history = am.get_alert_history()
    print(f"\n📚 告警历史: {len(history)} 条记录")


async def main():
    """主函数"""
    print("🎉 欢迎使用SSL证书自动化管理系统监控告警演示!")
    print("本演示将展示监控告警系统的主要功能\n")
    
    try:
        # 演示通知模板
        demo_notification_templates()
        
        # 演示通知提供商
        demo_notification_providers()
        
        # 演示告警规则
        demo_alert_rules()
        
        # 演示告警触发
        await demo_alert_triggering()
        
        # 演示告警统计
        demo_alert_statistics()
        
        print("\n" + "=" * 60)
        print("🎊 监控告警系统演示结束!")
        print("=" * 60)
        print("\n💡 下一步:")
        print("  1. 配置邮件/Slack/钉钉等通知提供商")
        print("  2. 根据需要调整告警规则")
        print("  3. 测试真实的告警通知")
        print("  4. 监控系统运行状态")
        print("  5. 查看告警历史和统计")
        
    except KeyboardInterrupt:
        print("\n\n👋 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
