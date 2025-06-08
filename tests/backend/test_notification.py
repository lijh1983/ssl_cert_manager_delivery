"""
通知服务测试模块
测试邮件、Webhook、Slack等通知功能
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend/src'))

from services.notification import (
    EmailProvider, WebhookProvider, SlackProvider, DingTalkProvider,
    NotificationManager, NotificationTemplate
)


class TestEmailProvider:
    """邮件提供商测试类"""
    
    @pytest.fixture
    def email_config(self):
        """邮件配置"""
        return {
            'smtp_host': 'smtp.example.com',
            'smtp_port': 587,
            'username': 'test@example.com',
            'password': 'testpass',
            'use_tls': True,
            'from_email': 'test@example.com',
            'from_name': 'Test System'
        }
    
    @pytest.fixture
    def email_provider(self, email_config):
        """邮件提供商实例"""
        return EmailProvider(email_config)
    
    def test_email_provider_initialization(self, email_provider):
        """测试邮件提供商初始化"""
        assert email_provider.smtp_host == 'smtp.example.com'
        assert email_provider.smtp_port == 587
        assert email_provider.username == 'test@example.com'
        assert email_provider.use_tls == True
        assert email_provider.from_email == 'test@example.com'
        assert email_provider.from_name == 'Test System'
    
    def test_validate_config_success(self, email_provider):
        """测试配置验证成功"""
        assert email_provider.validate_config() == True
    
    def test_validate_config_failure(self):
        """测试配置验证失败"""
        invalid_config = {
            'smtp_host': 'smtp.example.com',
            # 缺少必要字段
        }
        provider = EmailProvider(invalid_config)
        assert provider.validate_config() == False
    
    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_email_success(self, mock_smtp, email_provider):
        """测试发送邮件成功"""
        # 模拟SMTP服务器
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        message = {
            'to': ['recipient@example.com'],
            'subject': 'Test Subject',
            'content': 'Test Content',
            'content_type': 'html'
        }
        
        result = await email_provider.send(message)
        
        assert result['success'] == True
        assert result['provider'] == 'email'
        assert result['recipients'] == ['recipient@example.com']
        
        # 验证SMTP调用
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@example.com', 'testpass')
        mock_server.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('smtplib.SMTP')
    async def test_send_email_failure(self, mock_smtp, email_provider):
        """测试发送邮件失败"""
        # 模拟SMTP异常
        mock_smtp.side_effect = Exception('SMTP Error')
        
        message = {
            'to': ['recipient@example.com'],
            'subject': 'Test Subject',
            'content': 'Test Content'
        }
        
        result = await email_provider.send(message)
        
        assert result['success'] == False
        assert result['provider'] == 'email'
        assert 'SMTP Error' in result['error']


class TestWebhookProvider:
    """Webhook提供商测试类"""
    
    @pytest.fixture
    def webhook_config(self):
        """Webhook配置"""
        return {
            'url': 'https://example.com/webhook',
            'method': 'POST',
            'headers': {'Content-Type': 'application/json'},
            'timeout': 30,
            'retry_count': 3
        }
    
    @pytest.fixture
    def webhook_provider(self, webhook_config):
        """Webhook提供商实例"""
        return WebhookProvider(webhook_config)
    
    def test_webhook_provider_initialization(self, webhook_provider):
        """测试Webhook提供商初始化"""
        assert webhook_provider.url == 'https://example.com/webhook'
        assert webhook_provider.method == 'POST'
        assert webhook_provider.timeout == 30
        assert webhook_provider.retry_count == 3
    
    def test_validate_config_success(self, webhook_provider):
        """测试配置验证成功"""
        assert webhook_provider.validate_config() == True
    
    def test_validate_config_failure(self):
        """测试配置验证失败"""
        invalid_config = {}  # 缺少URL
        provider = WebhookProvider(invalid_config)
        assert provider.validate_config() == False
    
    @pytest.mark.asyncio
    async def test_send_webhook_success(self, webhook_provider):
        """测试发送Webhook成功"""
        with patch('aiohttp.ClientSession') as mock_session:
            # 模拟成功响应
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='OK')
            
            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value = mock_response
            
            message = {
                'payload': {'test': 'data'},
                'headers': {'Custom-Header': 'value'}
            }
            
            result = await webhook_provider.send(message)
            
            assert result['success'] == True
            assert result['provider'] == 'webhook'
            assert result['status_code'] == 200
    
    @pytest.mark.asyncio
    async def test_send_webhook_failure_with_retry(self, webhook_provider):
        """测试发送Webhook失败并重试"""
        with patch('aiohttp.ClientSession') as mock_session:
            # 模拟失败响应
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value='Internal Server Error')
            
            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value = mock_response
            
            with patch('asyncio.sleep', new_callable=AsyncMock):  # 跳过重试等待
                message = {'payload': {'test': 'data'}}
                result = await webhook_provider.send(message)
                
                assert result['success'] == False
                assert result['provider'] == 'webhook'


class TestSlackProvider:
    """Slack提供商测试类"""
    
    @pytest.fixture
    def slack_config(self):
        """Slack配置"""
        return {
            'webhook_url': 'https://hooks.slack.com/test',
            'channel': '#alerts',
            'username': 'SSL Bot',
            'icon_emoji': ':lock:'
        }
    
    @pytest.fixture
    def slack_provider(self, slack_config):
        """Slack提供商实例"""
        return SlackProvider(slack_config)
    
    def test_slack_provider_initialization(self, slack_provider):
        """测试Slack提供商初始化"""
        assert slack_provider.webhook_url == 'https://hooks.slack.com/test'
        assert slack_provider.channel == '#alerts'
        assert slack_provider.username == 'SSL Bot'
        assert slack_provider.icon_emoji == ':lock:'
    
    @pytest.mark.asyncio
    async def test_send_slack_success(self, slack_provider):
        """测试发送Slack消息成功"""
        with patch('aiohttp.ClientSession') as mock_session:
            # 模拟成功响应
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='ok')
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            message = {
                'text': 'Test message',
                'attachments': [{'color': 'warning', 'text': 'Alert details'}]
            }
            
            result = await slack_provider.send(message)
            
            assert result['success'] == True
            assert result['provider'] == 'slack'


class TestNotificationTemplate:
    """通知模板测试类"""
    
    def test_render_certificate_expiring_email(self):
        """测试渲染证书过期邮件模板"""
        context = {
            'domain': 'example.com',
            'expires_at': '2024-01-01 00:00:00',
            'days_remaining': 7,
            'server_name': 'web-server',
            'ca_type': 'Let\'s Encrypt'
        }
        
        result = NotificationTemplate.render('certificate_expiring', 'email', context)
        
        assert 'subject' in result
        assert 'content' in result
        assert 'example.com' in result['subject']
        assert 'example.com' in result['content']
        assert '7' in result['content']
    
    def test_render_slack_template(self):
        """测试渲染Slack模板"""
        context = {
            'domain': 'example.com',
            'expires_at': '2024-01-01 00:00:00',
            'days_remaining': 7,
            'server_name': 'web-server'
        }
        
        result = NotificationTemplate.render('certificate_expiring', 'slack', context)
        
        assert 'text' in result
        assert 'attachments' in result
        assert isinstance(result['attachments'], list)
        assert len(result['attachments']) > 0
    
    def test_render_nonexistent_template(self):
        """测试渲染不存在的模板"""
        context = {'domain': 'example.com'}
        
        result = NotificationTemplate.render('nonexistent', 'email', context)
        
        assert 'subject' in result
        assert 'content' in result
        assert '模板渲染失败' in result['content']


class TestNotificationManager:
    """通知管理器测试类"""
    
    @pytest.fixture
    def notification_manager(self):
        """通知管理器实例"""
        with patch.object(NotificationManager, '_load_providers'):
            manager = NotificationManager()
            return manager
    
    def test_notification_manager_initialization(self, notification_manager):
        """测试通知管理器初始化"""
        assert isinstance(notification_manager.providers, dict)
    
    @pytest.mark.asyncio
    async def test_send_notification_success(self, notification_manager):
        """测试发送通知成功"""
        # 模拟邮件提供商
        mock_email_provider = AsyncMock()
        mock_email_provider.send.return_value = {
            'success': True,
            'provider': 'email',
            'message': '发送成功'
        }
        notification_manager.providers['email'] = mock_email_provider
        
        context = {
            'domain': 'example.com',
            'expires_at': '2024-01-01 00:00:00',
            'days_remaining': 7
        }
        
        result = await notification_manager.send_notification(
            'certificate_expiring', context, ['email']
        )
        
        assert result['success'] == True
        assert len(result['results']) == 1
        assert len(result['failed']) == 0
        
        # 验证提供商被调用
        mock_email_provider.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_failure(self, notification_manager):
        """测试发送通知失败"""
        # 模拟失败的提供商
        mock_email_provider = AsyncMock()
        mock_email_provider.send.return_value = {
            'success': False,
            'provider': 'email',
            'error': '发送失败'
        }
        notification_manager.providers['email'] = mock_email_provider
        
        context = {'domain': 'example.com'}
        
        result = await notification_manager.send_notification(
            'certificate_expiring', context, ['email']
        )
        
        assert result['success'] == False
        assert len(result['failed']) == 1
    
    def test_get_available_providers(self, notification_manager):
        """测试获取可用提供商"""
        notification_manager.providers = {
            'email': MagicMock(),
            'slack': MagicMock()
        }
        
        providers = notification_manager.get_available_providers()
        
        assert isinstance(providers, list)
        assert 'email' in providers
        assert 'slack' in providers


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
