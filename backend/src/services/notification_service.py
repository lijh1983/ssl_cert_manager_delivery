"""
通知服务模块
提供邮件、Webhook、Slack、钉钉等多种通知方式
"""
import smtplib
import requests
import json
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from datetime import datetime

from utils.logging_config import get_logger
from utils.config_manager import get_notification_config
from utils.exceptions import ValidationError, ErrorCode

logger = get_logger(__name__)


class NotificationManager:
    """通知管理器"""
    
    def __init__(self):
        self.config = self._get_notification_config()
        self.templates = self._load_templates()
        self.rate_limiter = {}
    
    def send_notification(self, template_name: str, context: Dict[str, Any], 
                         providers: List[str] = None) -> Dict[str, Any]:
        """发送通知"""
        if not providers:
            providers = ['email']  # 默认使用邮件
        
        # 检查频率限制
        if not self._check_rate_limit(template_name, context):
            return {
                'success': False,
                'error': '通知发送频率超限',
                'sent': [],
                'failed': providers
            }
        
        sent_providers = []
        failed_providers = []
        
        for provider in providers:
            try:
                if provider == 'email':
                    result = self._send_email(template_name, context)
                elif provider == 'webhook':
                    result = self._send_webhook(template_name, context)
                elif provider == 'slack':
                    result = self._send_slack(template_name, context)
                elif provider == 'dingtalk':
                    result = self._send_dingtalk(template_name, context)
                else:
                    logger.warning(f"不支持的通知提供商: {provider}")
                    failed_providers.append(provider)
                    continue
                
                if result.get('success'):
                    sent_providers.append(provider)
                else:
                    failed_providers.append(provider)
                    
            except Exception as e:
                logger.error(f"发送{provider}通知失败: {e}")
                failed_providers.append(provider)
        
        success = len(sent_providers) > 0
        
        return {
            'success': success,
            'sent': sent_providers,
            'failed': failed_providers,
            'total': len(providers)
        }
    
    def send_email_notification(self, template_name: str, context: Dict[str, Any], 
                               recipients: List[str]) -> Dict[str, Any]:
        """发送邮件通知"""
        try:
            # 渲染模板
            rendered = self._render_template(template_name, context)
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = self.config['email']['username']
            msg['Subject'] = rendered['subject']
            
            # 添加邮件内容
            msg.attach(MIMEText(rendered['body'], 'html', 'utf-8'))
            
            # 发送邮件
            sent_recipients = []
            failed_recipients = []
            
            with smtplib.SMTP(self.config['email']['smtp_host'], 
                             self.config['email']['smtp_port']) as server:
                if self.config['email']['smtp_use_tls']:
                    server.starttls()
                
                server.login(self.config['email']['username'], 
                           self.config['email']['password'])
                
                for recipient in recipients:
                    try:
                        if self._validate_email(recipient):
                            msg['To'] = recipient
                            server.send_message(msg)
                            sent_recipients.append(recipient)
                        else:
                            failed_recipients.append(recipient)
                    except Exception as e:
                        logger.error(f"发送邮件到{recipient}失败: {e}")
                        failed_recipients.append(recipient)
            
            return {
                'success': len(sent_recipients) > 0,
                'sent': sent_recipients,
                'failed': failed_recipients
            }
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return {
                'success': False,
                'sent': [],
                'failed': recipients,
                'error': str(e)
            }
    
    def send_webhook_notification(self, webhook_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发送Webhook通知"""
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'response': response.text
                }
            else:
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': response.text
                }
                
        except requests.exceptions.ConnectionError as e:
            return {
                'success': False,
                'error': f'连接失败: {str(e)}'
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': '请求超时'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_slack_notification(self, webhook_url: str, message: str) -> Dict[str, Any]:
        """发送Slack通知"""
        payload = {
            'text': message,
            'username': 'SSL证书管理器',
            'icon_emoji': ':lock:'
        }
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=30)
            
            if response.status_code == 200 and response.text == 'ok':
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': f'Slack API错误: {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_dingtalk_notification(self, webhook_url: str, message: str) -> Dict[str, Any]:
        """发送钉钉通知"""
        payload = {
            'msgtype': 'text',
            'text': {
                'content': message
            }
        }
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=30)
            result = response.json()
            
            if result.get('errcode') == 0:
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': f'钉钉API错误: {result.get("errmsg", "未知错误")}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_email(self, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """内部邮件发送方法"""
        if not self.config.get('email', {}).get('enabled'):
            return {'success': False, 'error': '邮件通知未启用'}
        
        recipients = self.config['email'].get('recipients', [])
        if not recipients:
            return {'success': False, 'error': '未配置邮件接收者'}
        
        return self.send_email_notification(template_name, context, recipients)
    
    def _send_webhook(self, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """内部Webhook发送方法"""
        if not self.config.get('webhook', {}).get('enabled'):
            return {'success': False, 'error': 'Webhook通知未启用'}
        
        webhook_urls = self.config['webhook'].get('urls', [])
        if not webhook_urls:
            return {'success': False, 'error': '未配置Webhook URL'}
        
        payload = {
            'type': template_name,
            'timestamp': datetime.now().isoformat(),
            'data': context
        }
        
        # 发送到第一个URL（可以扩展为发送到所有URL）
        return self.send_webhook_notification(webhook_urls[0], payload)
    
    def _send_slack(self, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """内部Slack发送方法"""
        if not self.config.get('slack', {}).get('enabled'):
            return {'success': False, 'error': 'Slack通知未启用'}
        
        webhook_url = self.config['slack'].get('webhook_url')
        if not webhook_url:
            return {'success': False, 'error': '未配置Slack Webhook URL'}
        
        message = self._format_message_for_slack(template_name, context)
        return self.send_slack_notification(webhook_url, message)
    
    def _send_dingtalk(self, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """内部钉钉发送方法"""
        if not self.config.get('dingtalk', {}).get('enabled'):
            return {'success': False, 'error': '钉钉通知未启用'}
        
        webhook_url = self.config['dingtalk'].get('webhook_url')
        if not webhook_url:
            return {'success': False, 'error': '未配置钉钉Webhook URL'}
        
        message = self._format_message_for_dingtalk(template_name, context)
        return self.send_dingtalk_notification(webhook_url, message)
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> Dict[str, str]:
        """渲染通知模板"""
        if template_name not in self.templates:
            raise ValidationError(f"通知模板不存在: {template_name}")
        
        template = self.templates[template_name]
        
        # 简单的模板渲染（替换变量）
        subject = template['subject']
        body = template['body']
        
        for key, value in context.items():
            placeholder = f'{{{key}}}'
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
        
        return {
            'subject': subject,
            'body': body
        }
    
    def _format_message_for_slack(self, template_name: str, context: Dict[str, Any]) -> str:
        """格式化Slack消息"""
        if template_name == 'certificate_expiring':
            return self._format_certificate_expiring_message(context)
        elif template_name == 'certificate_renewed':
            return self._format_certificate_renewed_message(context)
        elif template_name == 'system_alert':
            return self._format_system_alert_message(context)
        else:
            return f"通知: {template_name}"
    
    def _format_message_for_dingtalk(self, template_name: str, context: Dict[str, Any]) -> str:
        """格式化钉钉消息"""
        return self._format_message_for_slack(template_name, context)  # 使用相同格式
    
    def _format_certificate_expiring_message(self, context: Dict[str, Any]) -> str:
        """格式化证书过期消息"""
        domain = context.get('domain', '未知域名')
        days_remaining = context.get('days_remaining', 0)
        server_name = context.get('server_name', '未知服务器')
        ca_type = context.get('ca_type', '未知CA')
        
        return f"""🔒 SSL证书即将过期提醒
        
域名: {domain}
服务器: {server_name}
CA类型: {ca_type}
剩余天数: {days_remaining}天
        
请及时续期证书以避免服务中断。"""
    
    def _format_certificate_renewed_message(self, context: Dict[str, Any]) -> str:
        """格式化证书续期消息"""
        domain = context.get('domain', '未知域名')
        new_expires_at = context.get('new_expires_at', '未知')
        server_name = context.get('server_name', '未知服务器')
        ca_type = context.get('ca_type', '未知CA')
        
        return f"""✅ SSL证书续期成功
        
域名: {domain}
服务器: {server_name}
CA类型: {ca_type}
新过期时间: {new_expires_at}
        
证书已成功续期并部署。"""
    
    def _format_system_alert_message(self, context: Dict[str, Any]) -> str:
        """格式化系统告警消息"""
        alert_type = context.get('alert_type', '系统告警')
        severity = context.get('severity', 'medium')
        description = context.get('description', '无描述')
        server_name = context.get('server_name', '未知服务器')
        
        severity_emoji = {
            'low': '🟡',
            'medium': '🟠', 
            'high': '🔴',
            'critical': '💥'
        }
        
        return f"""{severity_emoji.get(severity, '⚠️')} 系统告警
        
告警类型: {alert_type}
严重程度: {severity}
服务器: {server_name}
描述: {description}
时间: {context.get('alert_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}
        
请及时处理。"""
    
    def _validate_email(self, email: str) -> bool:
        """验证邮箱地址"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _get_notification_config(self) -> Dict[str, Any]:
        """获取通知配置"""
        # 默认配置
        default_config = {
            'email': {
                'enabled': False,
                'smtp_host': 'localhost',
                'smtp_port': 587,
                'smtp_use_tls': True,
                'username': '',
                'password': '',
                'recipients': []
            },
            'webhook': {
                'enabled': False,
                'urls': []
            },
            'slack': {
                'enabled': False,
                'webhook_url': ''
            },
            'dingtalk': {
                'enabled': False,
                'webhook_url': ''
            }
        }
        
        try:
            config = get_notification_config()
            # 合并配置
            for key in default_config:
                if hasattr(config, key):
                    default_config[key].update(getattr(config, key).__dict__)
        except:
            pass
        
        return default_config
    
    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """加载通知模板"""
        return {
            'certificate_expiring': {
                'subject': 'SSL证书即将过期 - {domain}',
                'body': '''
                <h2>SSL证书即将过期提醒</h2>
                <p>您好，</p>
                <p>以下SSL证书即将过期，请及时续期：</p>
                <ul>
                    <li><strong>域名:</strong> {domain}</li>
                    <li><strong>服务器:</strong> {server_name}</li>
                    <li><strong>过期时间:</strong> {expires_at}</li>
                    <li><strong>剩余天数:</strong> {days_remaining}天</li>
                    <li><strong>CA类型:</strong> {ca_type}</li>
                </ul>
                <p>请登录SSL证书管理系统进行续期操作。</p>
                '''
            },
            'certificate_renewed': {
                'subject': 'SSL证书续期成功 - {domain}',
                'body': '''
                <h2>SSL证书续期成功</h2>
                <p>您好，</p>
                <p>以下SSL证书已成功续期：</p>
                <ul>
                    <li><strong>域名:</strong> {domain}</li>
                    <li><strong>服务器:</strong> {server_name}</li>
                    <li><strong>新过期时间:</strong> {new_expires_at}</li>
                    <li><strong>CA类型:</strong> {ca_type}</li>
                </ul>
                <p>证书已自动部署到相关服务器。</p>
                '''
            },
            'system_alert': {
                'subject': '系统告警 - {alert_type}',
                'body': '''
                <h2>系统告警通知</h2>
                <p>检测到系统异常，详情如下：</p>
                <ul>
                    <li><strong>告警类型:</strong> {alert_type}</li>
                    <li><strong>严重程度:</strong> {severity}</li>
                    <li><strong>服务器:</strong> {server_name}</li>
                    <li><strong>描述:</strong> {description}</li>
                    <li><strong>时间:</strong> {alert_time}</li>
                </ul>
                <p>请及时登录系统查看详情并处理。</p>
                '''
            }
        }
    
    def _check_rate_limit(self, template_name: str, context: Dict[str, Any]) -> bool:
        """检查通知频率限制"""
        # 简单的频率限制实现
        key = f"{template_name}:{context.get('domain', 'system')}"
        now = datetime.now()
        
        if key in self.rate_limiter:
            last_sent = self.rate_limiter[key]
            # 同一类型通知间隔至少5分钟
            if (now - last_sent).total_seconds() < 300:
                return False
        
        self.rate_limiter[key] = now
        return True
