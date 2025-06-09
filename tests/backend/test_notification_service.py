"""
通知服务测试
测试告警和通知功能
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src'))

from services.notification_service import NotificationManager
from utils.exceptions import ErrorCode, ValidationError


class TestNotificationManager:
    """通知管理器测试类"""
    
    @pytest.fixture
    def notification_manager(self):
        """创建通知管理器实例"""
        return NotificationManager()
    
    def test_send_email_notification_success(self, notification_manager):
        """测试邮件通知发送成功"""
        template_name = 'certificate_expiring'
        context = {
            'domain': 'test.example.com',
            'expires_at': '2024-01-01 00:00:00',
            'days_remaining': 7,
            'server_name': '测试服务器'
        }
        recipients = ['admin@example.com']
        
        with patch('smtplib.SMTP') as mock_smtp:
            # 模拟SMTP连接成功
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            mock_server.send_message.return_value = {}
            
            # 执行测试
            result = notification_manager.send_email_notification(
                template_name, context, recipients
            )
            
            # 验证结果
            assert result['success'] is True
            assert result['sent'] == recipients
            assert result['failed'] == []
            
            # 验证SMTP方法被调用
            mock_server.send_message.assert_called_once()
    
    def test_send_email_notification_smtp_error(self, notification_manager):
        """测试邮件通知SMTP错误"""
        template_name = 'certificate_expiring'
        context = {'domain': 'test.example.com'}
        recipients = ['admin@example.com']
        
        with patch('smtplib.SMTP') as mock_smtp:
            # 模拟SMTP连接失败
            mock_smtp.side_effect = Exception("SMTP连接失败")
            
            # 执行测试
            result = notification_manager.send_email_notification(
                template_name, context, recipients
            )
            
            # 验证结果
            assert result['success'] is False
            assert result['sent'] == []
            assert result['failed'] == recipients
    
    def test_send_webhook_notification_success(self, notification_manager):
        """测试Webhook通知发送成功"""
        webhook_url = 'https://example.com/webhook'
        payload = {
            'type': 'certificate_expiring',
            'domain': 'test.example.com',
            'message': '证书即将过期'
        }
        
        with patch('requests.post') as mock_post:
            # 模拟HTTP请求成功
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'ok'}
            mock_post.return_value = mock_response
            
            # 执行测试
            result = notification_manager.send_webhook_notification(
                webhook_url, payload
            )
            
            # 验证结果
            assert result['success'] is True
            assert result['status_code'] == 200
            
            # 验证HTTP请求被调用
            mock_post.assert_called_once_with(
                webhook_url,
                json=payload,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
    
    def test_send_webhook_notification_http_error(self, notification_manager):
        """测试Webhook通知HTTP错误"""
        webhook_url = 'https://example.com/webhook'
        payload = {'type': 'test'}
        
        with patch('requests.post') as mock_post:
            # 模拟HTTP请求失败
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = 'Internal Server Error'
            mock_post.return_value = mock_response
            
            # 执行测试
            result = notification_manager.send_webhook_notification(
                webhook_url, payload
            )
            
            # 验证结果
            assert result['success'] is False
            assert result['status_code'] == 500
            assert 'error' in result
    
    def test_send_webhook_notification_connection_error(self, notification_manager):
        """测试Webhook通知连接错误"""
        webhook_url = 'https://invalid-url.example.com/webhook'
        payload = {'type': 'test'}
        
        with patch('requests.post') as mock_post:
            # 模拟连接错误
            import requests
            mock_post.side_effect = requests.exceptions.ConnectionError("连接失败")
            
            # 执行测试
            result = notification_manager.send_webhook_notification(
                webhook_url, payload
            )
            
            # 验证结果
            assert result['success'] is False
            assert 'error' in result
            assert '连接失败' in result['error']
    
    def test_send_slack_notification_success(self, notification_manager):
        """测试Slack通知发送成功"""
        webhook_url = 'https://hooks.slack.com/services/test'
        message = '证书test.example.com即将过期'
        
        with patch('requests.post') as mock_post:
            # 模拟Slack API成功响应
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = 'ok'
            mock_post.return_value = mock_response
            
            # 执行测试
            result = notification_manager.send_slack_notification(
                webhook_url, message
            )
            
            # 验证结果
            assert result['success'] is True
            
            # 验证请求格式
            call_args = mock_post.call_args
            assert call_args[0][0] == webhook_url
            assert 'json' in call_args[1]
            assert 'text' in call_args[1]['json']
    
    def test_send_dingtalk_notification_success(self, notification_manager):
        """测试钉钉通知发送成功"""
        webhook_url = 'https://oapi.dingtalk.com/robot/send?access_token=test'
        message = '证书test.example.com即将过期'
        
        with patch('requests.post') as mock_post:
            # 模拟钉钉API成功响应
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'errcode': 0, 'errmsg': 'ok'}
            mock_post.return_value = mock_response
            
            # 执行测试
            result = notification_manager.send_dingtalk_notification(
                webhook_url, message
            )
            
            # 验证结果
            assert result['success'] is True
            
            # 验证请求格式
            call_args = mock_post.call_args
            assert call_args[0][0] == webhook_url
            payload = call_args[1]['json']
            assert payload['msgtype'] == 'text'
            assert payload['text']['content'] == message
    
    def test_send_notification_multiple_providers(self, notification_manager):
        """测试多提供商通知发送"""
        template_name = 'certificate_expiring'
        context = {
            'domain': 'test.example.com',
            'expires_at': '2024-01-01 00:00:00',
            'days_remaining': 7
        }
        providers = ['email', 'slack']
        
        with patch.object(notification_manager, 'send_email_notification') as mock_email, \
             patch.object(notification_manager, 'send_slack_notification') as mock_slack, \
             patch.object(notification_manager, '_get_notification_config') as mock_config:
            
            # 模拟配置
            mock_config.return_value = {
                'email': {
                    'enabled': True,
                    'recipients': ['admin@example.com']
                },
                'slack': {
                    'enabled': True,
                    'webhook_url': 'https://hooks.slack.com/test'
                }
            }
            
            # 模拟发送成功
            mock_email.return_value = {'success': True, 'sent': ['admin@example.com']}
            mock_slack.return_value = {'success': True}
            
            # 执行测试
            result = notification_manager.send_notification(
                template_name, context, providers
            )
            
            # 验证结果
            assert result['success'] is True
            assert 'email' in result['sent']
            assert 'slack' in result['sent']
            assert result['failed'] == []
    
    def test_send_notification_partial_failure(self, notification_manager):
        """测试部分通知发送失败"""
        template_name = 'certificate_expiring'
        context = {'domain': 'test.example.com'}
        providers = ['email', 'webhook']
        
        with patch.object(notification_manager, 'send_email_notification') as mock_email, \
             patch.object(notification_manager, 'send_webhook_notification') as mock_webhook, \
             patch.object(notification_manager, '_get_notification_config') as mock_config:
            
            # 模拟配置
            mock_config.return_value = {
                'email': {
                    'enabled': True,
                    'recipients': ['admin@example.com']
                },
                'webhook': {
                    'enabled': True,
                    'urls': ['https://example.com/webhook']
                }
            }
            
            # 模拟邮件成功，Webhook失败
            mock_email.return_value = {'success': True, 'sent': ['admin@example.com']}
            mock_webhook.return_value = {'success': False, 'error': '连接失败'}
            
            # 执行测试
            result = notification_manager.send_notification(
                template_name, context, providers
            )
            
            # 验证结果
            assert result['success'] is False  # 部分失败
            assert 'email' in result['sent']
            assert 'webhook' in result['failed']
    
    def test_render_template_success(self, notification_manager):
        """测试模板渲染成功"""
        template_name = 'certificate_expiring'
        context = {
            'domain': 'test.example.com',
            'expires_at': '2024-01-01 00:00:00',
            'days_remaining': 7,
            'server_name': '测试服务器'
        }
        
        # 执行测试
        result = notification_manager._render_template(template_name, context)
        
        # 验证结果
        assert 'subject' in result
        assert 'body' in result
        assert context['domain'] in result['body']
        assert str(context['days_remaining']) in result['body']
    
    def test_render_template_missing_template(self, notification_manager):
        """测试渲染不存在的模板"""
        template_name = 'nonexistent_template'
        context = {}
        
        # 执行测试并验证异常
        with pytest.raises(ValidationError) as exc_info:
            notification_manager._render_template(template_name, context)
        
        assert '模板不存在' in exc_info.value.message
    
    def test_validate_email_addresses(self, notification_manager):
        """测试邮箱地址验证"""
        # 测试有效邮箱
        valid_emails = [
            'test@example.com',
            'user.name@domain.co.uk',
            'admin+alerts@company.org'
        ]
        
        for email in valid_emails:
            assert notification_manager._validate_email(email), f"邮箱验证失败: {email}"
        
        # 测试无效邮箱
        invalid_emails = [
            'invalid-email',
            '@domain.com',
            'user@',
            'user..name@domain.com'
        ]
        
        for email in invalid_emails:
            assert not notification_manager._validate_email(email), f"邮箱验证应该失败: {email}"
    
    def test_get_notification_config(self, notification_manager):
        """测试获取通知配置"""
        with patch('services.notification_service.get_notification_config') as mock_get_config:
            mock_config = {
                'email': {
                    'enabled': True,
                    'smtp_host': 'smtp.example.com',
                    'smtp_port': 587,
                    'username': 'test@example.com',
                    'password': 'password',
                    'recipients': ['admin@example.com']
                },
                'slack': {
                    'enabled': True,
                    'webhook_url': 'https://hooks.slack.com/test'
                }
            }
            mock_get_config.return_value = mock_config
            
            # 执行测试
            result = notification_manager._get_notification_config()
            
            # 验证结果
            assert result == mock_config
            assert result['email']['enabled'] is True
            assert result['slack']['enabled'] is True
    
    def test_format_certificate_expiring_message(self, notification_manager):
        """测试证书过期消息格式化"""
        context = {
            'domain': 'test.example.com',
            'expires_at': '2024-01-01 00:00:00',
            'days_remaining': 7,
            'server_name': '测试服务器',
            'ca_type': 'Let\'s Encrypt'
        }
        
        # 执行测试
        message = notification_manager._format_certificate_expiring_message(context)
        
        # 验证结果
        assert context['domain'] in message
        assert str(context['days_remaining']) in message
        assert context['server_name'] in message
        assert context['ca_type'] in message
    
    def test_format_certificate_renewed_message(self, notification_manager):
        """测试证书续期消息格式化"""
        context = {
            'domain': 'test.example.com',
            'new_expires_at': '2025-01-01 00:00:00',
            'server_name': '测试服务器',
            'ca_type': 'Let\'s Encrypt'
        }
        
        # 执行测试
        message = notification_manager._format_certificate_renewed_message(context)
        
        # 验证结果
        assert context['domain'] in message
        assert context['new_expires_at'] in message
        assert context['server_name'] in message
        assert '续期成功' in message
    
    def test_format_system_alert_message(self, notification_manager):
        """测试系统告警消息格式化"""
        context = {
            'alert_type': 'system_error',
            'severity': 'high',
            'alert_time': '2024-01-01 12:00:00',
            'description': '数据库连接失败',
            'server_name': '主服务器'
        }
        
        # 执行测试
        message = notification_manager._format_system_alert_message(context)
        
        # 验证结果
        assert context['alert_type'] in message
        assert context['severity'] in message
        assert context['description'] in message
        assert context['server_name'] in message
    
    def test_notification_rate_limiting(self, notification_manager):
        """测试通知频率限制"""
        template_name = 'certificate_expiring'
        context = {'domain': 'test.example.com'}
        
        with patch.object(notification_manager, '_check_rate_limit') as mock_rate_limit:
            # 模拟频率限制触发
            mock_rate_limit.return_value = False
            
            # 执行测试
            result = notification_manager.send_notification(
                template_name, context, ['email']
            )
            
            # 验证结果
            assert result['success'] is False
            assert '频率限制' in result.get('error', '')
    
    def test_notification_template_caching(self, notification_manager):
        """测试通知模板缓存"""
        template_name = 'certificate_expiring'
        context = {'domain': 'test.example.com'}
        
        # 第一次渲染
        result1 = notification_manager._render_template(template_name, context)
        
        # 第二次渲染（应该使用缓存）
        result2 = notification_manager._render_template(template_name, context)
        
        # 验证结果一致
        assert result1 == result2
