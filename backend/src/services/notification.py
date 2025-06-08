"""
通知服务模块
支持邮件、Webhook、短信等多种通知方式
"""

import os
import json
import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from jinja2 import Template
import asyncio
import aiohttp
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NotificationProvider(ABC):
    """通知提供商抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化通知提供商
        
        Args:
            config: 配置信息
        """
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送通知
        
        Args:
            message: 消息内容
            
        Returns:
            Dict: 发送结果
        """
        pass
    
    def validate_config(self) -> bool:
        """验证配置是否有效"""
        return True


class EmailProvider(NotificationProvider):
    """邮件通知提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化邮件提供商
        
        Args:
            config: 邮件配置
                - smtp_host: SMTP服务器地址
                - smtp_port: SMTP端口
                - username: 用户名
                - password: 密码
                - use_tls: 是否使用TLS
                - from_email: 发件人邮箱
                - from_name: 发件人姓名
        """
        super().__init__(config)
        self.smtp_host = config.get('smtp_host')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.use_tls = config.get('use_tls', True)
        self.from_email = config.get('from_email')
        self.from_name = config.get('from_name', 'SSL证书管理系统')
    
    def validate_config(self) -> bool:
        """验证邮件配置"""
        required_fields = ['smtp_host', 'username', 'password', 'from_email']
        return all(self.config.get(field) for field in required_fields)
    
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送邮件
        
        Args:
            message: 邮件消息
                - to: 收件人列表
                - subject: 主题
                - content: 内容
                - content_type: 内容类型 (text/html)
                - attachments: 附件列表
                
        Returns:
            Dict: 发送结果
        """
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['Subject'] = message.get('subject', '通知')
            
            # 处理收件人
            recipients = message.get('to', [])
            if isinstance(recipients, str):
                recipients = [recipients]
            msg['To'] = ', '.join(recipients)
            
            # 添加邮件内容
            content = message.get('content', '')
            content_type = message.get('content_type', 'html')
            
            if content_type == 'html':
                msg.attach(MIMEText(content, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # 处理附件
            attachments = message.get('attachments', [])
            for attachment in attachments:
                self._add_attachment(msg, attachment)
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                
                server.login(self.username, self.password)
                server.send_message(msg, to_addrs=recipients)
            
            logger.info(f"邮件发送成功: {recipients}")
            
            return {
                'success': True,
                'provider': 'email',
                'recipients': recipients,
                'message': '邮件发送成功'
            }
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return {
                'success': False,
                'provider': 'email',
                'error': str(e)
            }
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """添加附件"""
        try:
            filename = attachment.get('filename')
            content = attachment.get('content')
            content_type = attachment.get('content_type', 'application/octet-stream')
            
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            part = MIMEBase(*content_type.split('/'))
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(part)
            
        except Exception as e:
            logger.error(f"添加附件失败: {e}")


class WebhookProvider(NotificationProvider):
    """Webhook通知提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Webhook提供商
        
        Args:
            config: Webhook配置
                - url: Webhook URL
                - method: HTTP方法 (POST/PUT)
                - headers: 请求头
                - timeout: 超时时间
                - retry_count: 重试次数
        """
        super().__init__(config)
        self.url = config.get('url')
        self.method = config.get('method', 'POST').upper()
        self.headers = config.get('headers', {})
        self.timeout = config.get('timeout', 30)
        self.retry_count = config.get('retry_count', 3)
    
    def validate_config(self) -> bool:
        """验证Webhook配置"""
        return bool(self.url)
    
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送Webhook通知
        
        Args:
            message: 消息内容
                - payload: 发送的数据
                - headers: 额外的请求头
                
        Returns:
            Dict: 发送结果
        """
        try:
            # 准备请求数据
            payload = message.get('payload', message)
            headers = {**self.headers, **message.get('headers', {})}
            
            # 设置默认Content-Type
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'application/json'
            
            # 重试机制
            last_error = None
            for attempt in range(self.retry_count + 1):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.request(
                            self.method,
                            self.url,
                            json=payload,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=self.timeout)
                        ) as response:
                            response_text = await response.text()
                            
                            if response.status < 400:
                                logger.info(f"Webhook发送成功: {self.url}")
                                return {
                                    'success': True,
                                    'provider': 'webhook',
                                    'url': self.url,
                                    'status_code': response.status,
                                    'response': response_text
                                }
                            else:
                                raise aiohttp.ClientResponseError(
                                    request_info=response.request_info,
                                    history=response.history,
                                    status=response.status,
                                    message=response_text
                                )
                                
                except Exception as e:
                    last_error = e
                    if attempt < self.retry_count:
                        wait_time = 2 ** attempt  # 指数退避
                        logger.warning(f"Webhook发送失败，{wait_time}秒后重试: {e}")
                        await asyncio.sleep(wait_time)
                    else:
                        break
            
            logger.error(f"Webhook发送失败，已重试{self.retry_count}次: {last_error}")
            return {
                'success': False,
                'provider': 'webhook',
                'url': self.url,
                'error': str(last_error)
            }
            
        except Exception as e:
            logger.error(f"Webhook发送异常: {e}")
            return {
                'success': False,
                'provider': 'webhook',
                'error': str(e)
            }


class SlackProvider(NotificationProvider):
    """Slack通知提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Slack提供商
        
        Args:
            config: Slack配置
                - webhook_url: Slack Webhook URL
                - channel: 频道名称
                - username: 机器人用户名
                - icon_emoji: 图标表情
        """
        super().__init__(config)
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel')
        self.username = config.get('username', 'SSL证书管理系统')
        self.icon_emoji = config.get('icon_emoji', ':lock:')
    
    def validate_config(self) -> bool:
        """验证Slack配置"""
        return bool(self.webhook_url)
    
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送Slack通知
        
        Args:
            message: 消息内容
                - text: 消息文本
                - attachments: 附件
                - blocks: 块元素
                
        Returns:
            Dict: 发送结果
        """
        try:
            # 构建Slack消息
            slack_message = {
                'username': self.username,
                'icon_emoji': self.icon_emoji,
                'text': message.get('text', message.get('content', ''))
            }
            
            if self.channel:
                slack_message['channel'] = self.channel
            
            # 添加附件或块
            if 'attachments' in message:
                slack_message['attachments'] = message['attachments']
            
            if 'blocks' in message:
                slack_message['blocks'] = message['blocks']
            
            # 发送到Slack
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=slack_message,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_text = await response.text()
                    
                    if response.status == 200 and response_text == 'ok':
                        logger.info("Slack消息发送成功")
                        return {
                            'success': True,
                            'provider': 'slack',
                            'message': 'Slack消息发送成功'
                        }
                    else:
                        raise Exception(f"Slack API错误: {response.status} - {response_text}")
            
        except Exception as e:
            logger.error(f"Slack消息发送失败: {e}")
            return {
                'success': False,
                'provider': 'slack',
                'error': str(e)
            }


class DingTalkProvider(NotificationProvider):
    """钉钉通知提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化钉钉提供商
        
        Args:
            config: 钉钉配置
                - webhook_url: 钉钉机器人Webhook URL
                - secret: 签名密钥
        """
        super().__init__(config)
        self.webhook_url = config.get('webhook_url')
        self.secret = config.get('secret')
    
    def validate_config(self) -> bool:
        """验证钉钉配置"""
        return bool(self.webhook_url)
    
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送钉钉通知
        
        Args:
            message: 消息内容
                - text: 消息文本
                - msgtype: 消息类型 (text/markdown)
                - at: @用户
                
        Returns:
            Dict: 发送结果
        """
        try:
            # 构建钉钉消息
            dingtalk_message = {
                'msgtype': message.get('msgtype', 'text'),
                'text': {
                    'content': message.get('text', message.get('content', ''))
                }
            }
            
            # 处理@用户
            if 'at' in message:
                dingtalk_message['at'] = message['at']
            
            # 如果是markdown消息
            if dingtalk_message['msgtype'] == 'markdown':
                dingtalk_message['markdown'] = {
                    'title': message.get('title', '通知'),
                    'text': message.get('text', message.get('content', ''))
                }
                del dingtalk_message['text']
            
            # 生成签名（如果配置了密钥）
            url = self.webhook_url
            if self.secret:
                import time
                import hmac
                import hashlib
                import base64
                import urllib.parse
                
                timestamp = str(round(time.time() * 1000))
                secret_enc = self.secret.encode('utf-8')
                string_to_sign = f'{timestamp}\n{self.secret}'
                string_to_sign_enc = string_to_sign.encode('utf-8')
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                url = f'{self.webhook_url}&timestamp={timestamp}&sign={sign}'
            
            # 发送到钉钉
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=dingtalk_message,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    response_data = await response.json()
                    
                    if response_data.get('errcode') == 0:
                        logger.info("钉钉消息发送成功")
                        return {
                            'success': True,
                            'provider': 'dingtalk',
                            'message': '钉钉消息发送成功'
                        }
                    else:
                        raise Exception(f"钉钉API错误: {response_data}")
            
        except Exception as e:
            logger.error(f"钉钉消息发送失败: {e}")
            return {
                'success': False,
                'provider': 'dingtalk',
                'error': str(e)
            }


class NotificationTemplate:
    """通知模板类"""

    # 预定义模板
    TEMPLATES = {
        'certificate_expiring': {
            'email': {
                'subject': '🔔 证书即将过期提醒 - {{domain}}',
                'content': '''
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #e74c3c;">🔔 证书即将过期提醒</h2>

                        <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #856404;">证书信息</h3>
                            <ul style="margin: 0; padding-left: 20px;">
                                <li><strong>域名:</strong> {{domain}}</li>
                                <li><strong>过期时间:</strong> {{expires_at}}</li>
                                <li><strong>剩余天数:</strong> {{days_remaining}} 天</li>
                                <li><strong>服务器:</strong> {{server_name}}</li>
                                <li><strong>CA类型:</strong> {{ca_type}}</li>
                            </ul>
                        </div>

                        <div style="background: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 20px 0;">
                            <h4 style="margin-top: 0; color: #007bff;">建议操作</h4>
                            <p>请及时续期证书以避免服务中断。您可以：</p>
                            <ul>
                                <li>登录管理系统手动续期</li>
                                <li>检查自动续期配置</li>
                                <li>联系系统管理员</li>
                            </ul>
                        </div>

                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{{dashboard_url}}" style="background: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                                前往管理系统
                            </a>
                        </div>

                        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                        <p style="font-size: 12px; color: #666; text-align: center;">
                            此邮件由SSL证书管理系统自动发送，请勿回复。<br>
                            发送时间: {{sent_at}}
                        </p>
                    </div>
                </body>
                </html>
                '''
            },
            'slack': {
                'text': '🔔 证书即将过期提醒',
                'attachments': [
                    {
                        'color': 'warning',
                        'fields': [
                            {'title': '域名', 'value': '{{domain}}', 'short': True},
                            {'title': '过期时间', 'value': '{{expires_at}}', 'short': True},
                            {'title': '剩余天数', 'value': '{{days_remaining}} 天', 'short': True},
                            {'title': '服务器', 'value': '{{server_name}}', 'short': True}
                        ],
                        'footer': 'SSL证书管理系统',
                        'ts': '{{timestamp}}'
                    }
                ]
            },
            'dingtalk': {
                'msgtype': 'markdown',
                'title': '证书即将过期提醒',
                'text': '''
                ## 🔔 证书即将过期提醒

                **证书信息:**
                - 域名: {{domain}}
                - 过期时间: {{expires_at}}
                - 剩余天数: {{days_remaining}} 天
                - 服务器: {{server_name}}

                **建议操作:**
                请及时续期证书以避免服务中断

                [前往管理系统]({{dashboard_url}})
                '''
            }
        },

        'certificate_expired': {
            'email': {
                'subject': '🚨 证书已过期警告 - {{domain}}',
                'content': '''
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #dc3545;">🚨 证书已过期警告</h2>

                        <div style="background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #721c24;">紧急通知</h3>
                            <p style="margin: 0;"><strong>域名 {{domain}} 的SSL证书已过期，可能影响服务正常运行！</strong></p>
                        </div>

                        <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #856404;">证书信息</h3>
                            <ul style="margin: 0; padding-left: 20px;">
                                <li><strong>域名:</strong> {{domain}}</li>
                                <li><strong>过期时间:</strong> {{expires_at}}</li>
                                <li><strong>已过期:</strong> {{days_expired}} 天</li>
                                <li><strong>服务器:</strong> {{server_name}}</li>
                            </ul>
                        </div>

                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{{dashboard_url}}" style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                                立即处理
                            </a>
                        </div>
                    </div>
                </body>
                </html>
                '''
            }
        },

        'certificate_renewed': {
            'email': {
                'subject': '✅ 证书续期成功 - {{domain}}',
                'content': '''
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #28a745;">✅ 证书续期成功</h2>

                        <div style="background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p style="margin: 0;"><strong>域名 {{domain}} 的SSL证书已成功续期！</strong></p>
                        </div>

                        <div style="background: #f8f9fa; border-left: 4px solid #28a745; padding: 15px; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #28a745;">新证书信息</h3>
                            <ul style="margin: 0; padding-left: 20px;">
                                <li><strong>域名:</strong> {{domain}}</li>
                                <li><strong>新过期时间:</strong> {{new_expires_at}}</li>
                                <li><strong>有效期:</strong> {{validity_days}} 天</li>
                                <li><strong>续期时间:</strong> {{renewed_at}}</li>
                            </ul>
                        </div>
                    </div>
                </body>
                </html>
                '''
            }
        },

        'system_alert': {
            'email': {
                'subject': '⚠️ 系统告警 - {{alert_type}}',
                'content': '''
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #ffc107;">⚠️ 系统告警</h2>

                        <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #856404;">告警详情</h3>
                            <ul style="margin: 0; padding-left: 20px;">
                                <li><strong>告警类型:</strong> {{alert_type}}</li>
                                <li><strong>告警级别:</strong> {{severity}}</li>
                                <li><strong>告警时间:</strong> {{alert_time}}</li>
                                <li><strong>描述:</strong> {{description}}</li>
                            </ul>
                        </div>

                        {% if details %}
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h4 style="margin-top: 0;">详细信息</h4>
                            <pre style="background: #e9ecef; padding: 10px; border-radius: 3px; overflow-x: auto;">{{details}}</pre>
                        </div>
                        {% endif %}
                    </div>
                </body>
                </html>
                '''
            }
        }
    }

    @classmethod
    def render(cls, template_name: str, provider: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        渲染模板

        Args:
            template_name: 模板名称
            provider: 通知提供商
            context: 模板变量

        Returns:
            Dict: 渲染后的消息
        """
        try:
            template_config = cls.TEMPLATES.get(template_name, {}).get(provider, {})
            if not template_config:
                raise ValueError(f"未找到模板: {template_name}/{provider}")

            # 添加默认变量
            context.update({
                'sent_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'timestamp': int(datetime.now().timestamp()),
                'dashboard_url': os.getenv('DASHBOARD_URL', 'http://localhost:3000')
            })

            # 渲染模板
            rendered = {}
            for key, value in template_config.items():
                if isinstance(value, str):
                    template = Template(value)
                    rendered[key] = template.render(**context)
                elif isinstance(value, list):
                    rendered[key] = cls._render_list(value, context)
                elif isinstance(value, dict):
                    rendered[key] = cls._render_dict(value, context)
                else:
                    rendered[key] = value

            return rendered

        except Exception as e:
            logger.error(f"模板渲染失败: {e}")
            return {
                'subject': f'通知 - {template_name}',
                'content': f'模板渲染失败: {str(e)}'
            }

    @classmethod
    def _render_list(cls, items: List[Any], context: Dict[str, Any]) -> List[Any]:
        """渲染列表"""
        rendered_items = []
        for item in items:
            if isinstance(item, str):
                template = Template(item)
                rendered_items.append(template.render(**context))
            elif isinstance(item, dict):
                rendered_items.append(cls._render_dict(item, context))
            else:
                rendered_items.append(item)
        return rendered_items

    @classmethod
    def _render_dict(cls, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """渲染字典"""
        rendered_dict = {}
        for key, value in data.items():
            if isinstance(value, str):
                template = Template(value)
                rendered_dict[key] = template.render(**context)
            elif isinstance(value, list):
                rendered_dict[key] = cls._render_list(value, context)
            elif isinstance(value, dict):
                rendered_dict[key] = cls._render_dict(value, context)
            else:
                rendered_dict[key] = value
        return rendered_dict


class NotificationManager:
    """通知管理器"""

    def __init__(self):
        """初始化通知管理器"""
        self.providers = {}
        self._load_providers()

    def _load_providers(self):
        """加载通知提供商"""
        # 邮件提供商
        email_config = {
            'smtp_host': os.getenv('SMTP_HOST'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'username': os.getenv('SMTP_USERNAME'),
            'password': os.getenv('SMTP_PASSWORD'),
            'use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
            'from_email': os.getenv('SMTP_FROM_EMAIL'),
            'from_name': os.getenv('SMTP_FROM_NAME', 'SSL证书管理系统')
        }

        if email_config['smtp_host'] and email_config['username']:
            try:
                email_provider = EmailProvider(email_config)
                if email_provider.validate_config():
                    self.providers['email'] = email_provider
                    logger.info("邮件通知提供商已加载")
            except Exception as e:
                logger.error(f"加载邮件提供商失败: {e}")

        # Webhook提供商
        webhook_url = os.getenv('WEBHOOK_URL')
        if webhook_url:
            try:
                webhook_config = {
                    'url': webhook_url,
                    'method': os.getenv('WEBHOOK_METHOD', 'POST'),
                    'headers': json.loads(os.getenv('WEBHOOK_HEADERS', '{}')),
                    'timeout': int(os.getenv('WEBHOOK_TIMEOUT', '30')),
                    'retry_count': int(os.getenv('WEBHOOK_RETRY_COUNT', '3'))
                }
                webhook_provider = WebhookProvider(webhook_config)
                if webhook_provider.validate_config():
                    self.providers['webhook'] = webhook_provider
                    logger.info("Webhook通知提供商已加载")
            except Exception as e:
                logger.error(f"加载Webhook提供商失败: {e}")

        # Slack提供商
        slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        if slack_webhook:
            try:
                slack_config = {
                    'webhook_url': slack_webhook,
                    'channel': os.getenv('SLACK_CHANNEL'),
                    'username': os.getenv('SLACK_USERNAME', 'SSL证书管理系统'),
                    'icon_emoji': os.getenv('SLACK_ICON_EMOJI', ':lock:')
                }
                slack_provider = SlackProvider(slack_config)
                if slack_provider.validate_config():
                    self.providers['slack'] = slack_provider
                    logger.info("Slack通知提供商已加载")
            except Exception as e:
                logger.error(f"加载Slack提供商失败: {e}")

        # 钉钉提供商
        dingtalk_webhook = os.getenv('DINGTALK_WEBHOOK_URL')
        if dingtalk_webhook:
            try:
                dingtalk_config = {
                    'webhook_url': dingtalk_webhook,
                    'secret': os.getenv('DINGTALK_SECRET')
                }
                dingtalk_provider = DingTalkProvider(dingtalk_config)
                if dingtalk_provider.validate_config():
                    self.providers['dingtalk'] = dingtalk_provider
                    logger.info("钉钉通知提供商已加载")
            except Exception as e:
                logger.error(f"加载钉钉提供商失败: {e}")

    async def send_notification(self, template_name: str, context: Dict[str, Any],
                              providers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        发送通知

        Args:
            template_name: 模板名称
            context: 模板变量
            providers: 指定的提供商列表，None表示使用所有可用提供商

        Returns:
            Dict: 发送结果
        """
        if providers is None:
            providers = list(self.providers.keys())

        results = {
            'success': True,
            'results': [],
            'failed': []
        }

        for provider_name in providers:
            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"通知提供商不可用: {provider_name}")
                results['failed'].append({
                    'provider': provider_name,
                    'error': '提供商不可用'
                })
                continue

            try:
                # 渲染模板
                message = NotificationTemplate.render(template_name, provider_name, context)

                # 发送通知
                result = await provider.send(message)
                results['results'].append(result)

                if not result['success']:
                    results['failed'].append(result)

            except Exception as e:
                logger.error(f"发送通知失败 {provider_name}: {e}")
                results['failed'].append({
                    'provider': provider_name,
                    'error': str(e)
                })

        # 如果所有提供商都失败，则整体失败
        if len(results['failed']) == len(providers):
            results['success'] = False

        return results

    def get_available_providers(self) -> List[str]:
        """获取可用的通知提供商列表"""
        return list(self.providers.keys())


# 全局通知管理器实例
notification_manager = NotificationManager()
