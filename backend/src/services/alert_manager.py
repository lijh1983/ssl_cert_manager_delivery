"""
告警管理模块
负责监控证书状态、系统状态，并触发相应的告警通知
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import schedule
import threading
import time

from .notification import notification_manager, NotificationTemplate
from models.certificate import Certificate
from models.server import Server
from models.user import User

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """告警级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """告警类型"""
    CERTIFICATE_EXPIRING = "certificate_expiring"
    CERTIFICATE_EXPIRED = "certificate_expired"
    CERTIFICATE_RENEWAL_FAILED = "certificate_renewal_failed"
    SERVER_OFFLINE = "server_offline"
    SYSTEM_ERROR = "system_error"
    QUOTA_EXCEEDED = "quota_exceeded"


@dataclass
class AlertRule:
    """告警规则"""
    id: str
    name: str
    alert_type: AlertType
    severity: AlertSeverity
    enabled: bool
    conditions: Dict[str, Any]
    notification_providers: List[str]
    notification_template: str
    cooldown_minutes: int = 60  # 冷却时间，防止重复告警
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class Alert:
    """告警实例"""
    id: str
    rule_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    context: Dict[str, Any]
    status: str = "active"  # active, resolved, suppressed
    created_at: datetime = None
    resolved_at: datetime = None
    last_sent_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class AlertManager:
    """告警管理器"""
    
    def __init__(self):
        """初始化告警管理器"""
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.monitoring_enabled = True
        self.scheduler_thread = None
        
        # 加载默认规则
        self._load_default_rules()
        
        # 启动监控
        self._start_monitoring()
    
    def _load_default_rules(self):
        """加载默认告警规则"""
        default_rules = [
            AlertRule(
                id="cert_expiring_30d",
                name="证书30天内过期告警",
                alert_type=AlertType.CERTIFICATE_EXPIRING,
                severity=AlertSeverity.MEDIUM,
                enabled=True,
                conditions={
                    "days_before_expiry": 30,
                    "check_interval_hours": 24
                },
                notification_providers=["email"],
                notification_template="certificate_expiring",
                cooldown_minutes=1440  # 24小时
            ),
            AlertRule(
                id="cert_expiring_7d",
                name="证书7天内过期告警",
                alert_type=AlertType.CERTIFICATE_EXPIRING,
                severity=AlertSeverity.HIGH,
                enabled=True,
                conditions={
                    "days_before_expiry": 7,
                    "check_interval_hours": 12
                },
                notification_providers=["email", "slack"],
                notification_template="certificate_expiring",
                cooldown_minutes=720  # 12小时
            ),
            AlertRule(
                id="cert_expiring_1d",
                name="证书1天内过期告警",
                alert_type=AlertType.CERTIFICATE_EXPIRING,
                severity=AlertSeverity.CRITICAL,
                enabled=True,
                conditions={
                    "days_before_expiry": 1,
                    "check_interval_hours": 6
                },
                notification_providers=["email", "slack", "dingtalk"],
                notification_template="certificate_expiring",
                cooldown_minutes=360  # 6小时
            ),
            AlertRule(
                id="cert_expired",
                name="证书已过期告警",
                alert_type=AlertType.CERTIFICATE_EXPIRED,
                severity=AlertSeverity.CRITICAL,
                enabled=True,
                conditions={
                    "check_interval_hours": 1
                },
                notification_providers=["email", "slack", "dingtalk"],
                notification_template="certificate_expired",
                cooldown_minutes=60  # 1小时
            ),
            AlertRule(
                id="server_offline",
                name="服务器离线告警",
                alert_type=AlertType.SERVER_OFFLINE,
                severity=AlertSeverity.HIGH,
                enabled=True,
                conditions={
                    "offline_threshold_minutes": 30,
                    "check_interval_minutes": 10
                },
                notification_providers=["email", "slack"],
                notification_template="system_alert",
                cooldown_minutes=120  # 2小时
            ),
            AlertRule(
                id="renewal_failed",
                name="证书续期失败告警",
                alert_type=AlertType.CERTIFICATE_RENEWAL_FAILED,
                severity=AlertSeverity.HIGH,
                enabled=True,
                conditions={
                    "max_retry_attempts": 3
                },
                notification_providers=["email", "slack"],
                notification_template="system_alert",
                cooldown_minutes=240  # 4小时
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.id] = rule
        
        logger.info(f"已加载 {len(default_rules)} 个默认告警规则")
    
    def add_rule(self, rule: AlertRule) -> bool:
        """
        添加告警规则
        
        Args:
            rule: 告警规则
            
        Returns:
            bool: 是否成功
        """
        try:
            rule.updated_at = datetime.now()
            self.rules[rule.id] = rule
            logger.info(f"添加告警规则: {rule.name}")
            return True
        except Exception as e:
            logger.error(f"添加告警规则失败: {e}")
            return False
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新告警规则
        
        Args:
            rule_id: 规则ID
            updates: 更新内容
            
        Returns:
            bool: 是否成功
        """
        try:
            if rule_id not in self.rules:
                return False
            
            rule = self.rules[rule_id]
            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            
            rule.updated_at = datetime.now()
            logger.info(f"更新告警规则: {rule.name}")
            return True
        except Exception as e:
            logger.error(f"更新告警规则失败: {e}")
            return False
    
    def delete_rule(self, rule_id: str) -> bool:
        """
        删除告警规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            bool: 是否成功
        """
        try:
            if rule_id in self.rules:
                rule = self.rules.pop(rule_id)
                logger.info(f"删除告警规则: {rule.name}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除告警规则失败: {e}")
            return False
    
    def get_rules(self) -> List[AlertRule]:
        """获取所有告警规则"""
        return list(self.rules.values())
    
    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """获取指定告警规则"""
        return self.rules.get(rule_id)
    
    async def trigger_alert(self, rule: AlertRule, context: Dict[str, Any]) -> Optional[Alert]:
        """
        触发告警
        
        Args:
            rule: 告警规则
            context: 告警上下文
            
        Returns:
            Alert: 告警实例
        """
        try:
            # 生成告警ID
            alert_id = f"{rule.id}_{context.get('resource_id', 'unknown')}_{int(datetime.now().timestamp())}"
            
            # 检查冷却时间
            if self._is_in_cooldown(rule, context):
                logger.debug(f"告警在冷却期内，跳过: {rule.name}")
                return None
            
            # 创建告警实例
            alert = Alert(
                id=alert_id,
                rule_id=rule.id,
                alert_type=rule.alert_type,
                severity=rule.severity,
                title=self._generate_alert_title(rule, context),
                description=self._generate_alert_description(rule, context),
                context=context
            )
            
            # 添加到活跃告警
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            
            # 发送通知
            await self._send_alert_notification(rule, alert)
            
            logger.info(f"触发告警: {alert.title}")
            return alert
            
        except Exception as e:
            logger.error(f"触发告警失败: {e}")
            return None
    
    def _is_in_cooldown(self, rule: AlertRule, context: Dict[str, Any]) -> bool:
        """检查是否在冷却期内"""
        resource_id = context.get('resource_id')
        if not resource_id:
            return False
        
        # 查找相同资源的最近告警
        cutoff_time = datetime.now() - timedelta(minutes=rule.cooldown_minutes)
        
        for alert in self.alert_history:
            if (alert.rule_id == rule.id and 
                alert.context.get('resource_id') == resource_id and
                alert.created_at > cutoff_time):
                return True
        
        return False
    
    def _generate_alert_title(self, rule: AlertRule, context: Dict[str, Any]) -> str:
        """生成告警标题"""
        if rule.alert_type == AlertType.CERTIFICATE_EXPIRING:
            return f"证书即将过期 - {context.get('domain', 'Unknown')}"
        elif rule.alert_type == AlertType.CERTIFICATE_EXPIRED:
            return f"证书已过期 - {context.get('domain', 'Unknown')}"
        elif rule.alert_type == AlertType.SERVER_OFFLINE:
            return f"服务器离线 - {context.get('server_name', 'Unknown')}"
        elif rule.alert_type == AlertType.CERTIFICATE_RENEWAL_FAILED:
            return f"证书续期失败 - {context.get('domain', 'Unknown')}"
        else:
            return f"系统告警 - {rule.name}"
    
    def _generate_alert_description(self, rule: AlertRule, context: Dict[str, Any]) -> str:
        """生成告警描述"""
        if rule.alert_type == AlertType.CERTIFICATE_EXPIRING:
            days = context.get('days_remaining', 0)
            return f"证书将在 {days} 天后过期，请及时续期"
        elif rule.alert_type == AlertType.CERTIFICATE_EXPIRED:
            days = context.get('days_expired', 0)
            return f"证书已过期 {days} 天，请立即处理"
        elif rule.alert_type == AlertType.SERVER_OFFLINE:
            return f"服务器已离线超过 {rule.conditions.get('offline_threshold_minutes', 30)} 分钟"
        else:
            return context.get('description', '系统检测到异常情况')
    
    async def _send_alert_notification(self, rule: AlertRule, alert: Alert):
        """发送告警通知"""
        try:
            # 准备通知上下文
            notification_context = {
                **alert.context,
                'alert_type': alert.alert_type.value,
                'severity': alert.severity.value,
                'alert_time': alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'description': alert.description
            }
            
            # 发送通知
            result = await notification_manager.send_notification(
                template_name=rule.notification_template,
                context=notification_context,
                providers=rule.notification_providers
            )
            
            if result['success']:
                alert.last_sent_at = datetime.now()
                logger.info(f"告警通知发送成功: {alert.title}")
            else:
                logger.error(f"告警通知发送失败: {result.get('failed', [])}")
                
        except Exception as e:
            logger.error(f"发送告警通知异常: {e}")
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        解决告警
        
        Args:
            alert_id: 告警ID
            
        Returns:
            bool: 是否成功
        """
        try:
            if alert_id in self.active_alerts:
                alert = self.active_alerts.pop(alert_id)
                alert.status = "resolved"
                alert.resolved_at = datetime.now()
                logger.info(f"告警已解决: {alert.title}")
                return True
            return False
        except Exception as e:
            logger.error(f"解决告警失败: {e}")
            return False
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return self.alert_history[-limit:]
    
    def _start_monitoring(self):
        """启动监控"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            return
        
        # 设置定时任务
        schedule.every(10).minutes.do(self._check_certificate_expiry)
        schedule.every(5).minutes.do(self._check_server_status)
        schedule.every(1).hours.do(self._cleanup_old_alerts)
        
        # 启动调度器线程
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("告警监控已启动")
    
    def _run_scheduler(self):
        """运行调度器"""
        while self.monitoring_enabled:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"调度器运行异常: {e}")
                time.sleep(60)
    
    def _check_certificate_expiry(self):
        """检查证书过期情况"""
        try:
            logger.debug("检查证书过期情况")
            
            # 获取所有证书
            certificates = Certificate.get_all()
            
            for cert in certificates:
                if not cert.expires_at:
                    continue
                
                now = datetime.now()
                days_until_expiry = (cert.expires_at - now).days
                
                # 检查各种过期规则
                for rule in self.rules.values():
                    if not rule.enabled:
                        continue
                    
                    if rule.alert_type == AlertType.CERTIFICATE_EXPIRING:
                        threshold = rule.conditions.get('days_before_expiry', 30)
                        if 0 <= days_until_expiry <= threshold:
                            context = {
                                'resource_id': f"cert_{cert.id}",
                                'domain': cert.domain,
                                'expires_at': cert.expires_at.strftime('%Y-%m-%d %H:%M:%S'),
                                'days_remaining': days_until_expiry,
                                'server_name': cert.server.name if cert.server else 'Unknown',
                                'ca_type': cert.ca_type or 'Unknown'
                            }
                            asyncio.create_task(self.trigger_alert(rule, context))
                    
                    elif rule.alert_type == AlertType.CERTIFICATE_EXPIRED:
                        if days_until_expiry < 0:
                            context = {
                                'resource_id': f"cert_{cert.id}",
                                'domain': cert.domain,
                                'expires_at': cert.expires_at.strftime('%Y-%m-%d %H:%M:%S'),
                                'days_expired': abs(days_until_expiry),
                                'server_name': cert.server.name if cert.server else 'Unknown'
                            }
                            asyncio.create_task(self.trigger_alert(rule, context))
                            
        except Exception as e:
            logger.error(f"检查证书过期异常: {e}")
    
    def _check_server_status(self):
        """检查服务器状态"""
        try:
            logger.debug("检查服务器状态")
            
            # 获取所有服务器
            servers = Server.get_all()
            
            for server in servers:
                if not server.last_heartbeat:
                    continue
                
                # 检查服务器离线规则
                for rule in self.rules.values():
                    if (not rule.enabled or 
                        rule.alert_type != AlertType.SERVER_OFFLINE):
                        continue
                    
                    threshold_minutes = rule.conditions.get('offline_threshold_minutes', 30)
                    threshold_time = datetime.now() - timedelta(minutes=threshold_minutes)
                    
                    if server.last_heartbeat < threshold_time:
                        context = {
                            'resource_id': f"server_{server.id}",
                            'server_name': server.name,
                            'server_id': server.id,
                            'last_heartbeat': server.last_heartbeat.strftime('%Y-%m-%d %H:%M:%S'),
                            'offline_minutes': int((datetime.now() - server.last_heartbeat).total_seconds() / 60)
                        }
                        asyncio.create_task(self.trigger_alert(rule, context))
                        
        except Exception as e:
            logger.error(f"检查服务器状态异常: {e}")
    
    def _cleanup_old_alerts(self):
        """清理旧告警"""
        try:
            # 保留最近30天的告警历史
            cutoff_time = datetime.now() - timedelta(days=30)
            self.alert_history = [
                alert for alert in self.alert_history 
                if alert.created_at > cutoff_time
            ]
            
            # 清理已解决的活跃告警
            resolved_alerts = []
            for alert_id, alert in self.active_alerts.items():
                if alert.status == "resolved":
                    resolved_alerts.append(alert_id)
            
            for alert_id in resolved_alerts:
                self.active_alerts.pop(alert_id, None)
                
            logger.debug(f"清理了 {len(resolved_alerts)} 个已解决的告警")
            
        except Exception as e:
            logger.error(f"清理旧告警异常: {e}")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_enabled = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("告警监控已停止")


# 全局告警管理器实例
alert_manager = AlertManager()
