"""
告警管理测试模块
测试告警规则、告警触发和通知功能
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend/src'))

from services.alert_manager import (
    AlertManager, AlertRule, Alert, AlertType, AlertSeverity
)


class TestAlertRule:
    """告警规则测试类"""
    
    def test_alert_rule_creation(self):
        """测试告警规则创建"""
        rule = AlertRule(
            id='test_rule',
            name='测试规则',
            alert_type=AlertType.CERTIFICATE_EXPIRING,
            severity=AlertSeverity.HIGH,
            enabled=True,
            conditions={'days_before_expiry': 7},
            notification_providers=['email'],
            notification_template='certificate_expiring',
            cooldown_minutes=60
        )
        
        assert rule.id == 'test_rule'
        assert rule.name == '测试规则'
        assert rule.alert_type == AlertType.CERTIFICATE_EXPIRING
        assert rule.severity == AlertSeverity.HIGH
        assert rule.enabled == True
        assert rule.conditions['days_before_expiry'] == 7
        assert rule.notification_providers == ['email']
        assert rule.cooldown_minutes == 60
        assert rule.created_at is not None
        assert rule.updated_at is not None
    
    def test_alert_rule_post_init(self):
        """测试告警规则后初始化"""
        rule = AlertRule(
            id='test_rule',
            name='测试规则',
            alert_type=AlertType.CERTIFICATE_EXPIRING,
            severity=AlertSeverity.HIGH,
            enabled=True,
            conditions={},
            notification_providers=[],
            notification_template='test'
        )
        
        # 检查默认值
        assert isinstance(rule.created_at, datetime)
        assert isinstance(rule.updated_at, datetime)


class TestAlert:
    """告警实例测试类"""
    
    def test_alert_creation(self):
        """测试告警实例创建"""
        alert = Alert(
            id='test_alert',
            rule_id='test_rule',
            alert_type=AlertType.CERTIFICATE_EXPIRING,
            severity=AlertSeverity.HIGH,
            title='测试告警',
            description='这是一个测试告警',
            context={'domain': 'example.com'}
        )
        
        assert alert.id == 'test_alert'
        assert alert.rule_id == 'test_rule'
        assert alert.alert_type == AlertType.CERTIFICATE_EXPIRING
        assert alert.severity == AlertSeverity.HIGH
        assert alert.title == '测试告警'
        assert alert.description == '这是一个测试告警'
        assert alert.context['domain'] == 'example.com'
        assert alert.status == 'active'
        assert alert.created_at is not None


class TestAlertManager:
    """告警管理器测试类"""
    
    @pytest.fixture
    def alert_manager(self):
        """告警管理器实例"""
        with patch.object(AlertManager, '_start_monitoring'):
            manager = AlertManager()
            return manager
    
    def test_alert_manager_initialization(self, alert_manager):
        """测试告警管理器初始化"""
        assert isinstance(alert_manager.rules, dict)
        assert isinstance(alert_manager.active_alerts, dict)
        assert isinstance(alert_manager.alert_history, list)
        assert alert_manager.monitoring_enabled == True
        
        # 检查默认规则是否加载
        assert len(alert_manager.rules) > 0
        assert 'cert_expiring_30d' in alert_manager.rules
        assert 'cert_expiring_7d' in alert_manager.rules
        assert 'cert_expired' in alert_manager.rules
    
    def test_add_rule(self, alert_manager):
        """测试添加告警规则"""
        rule = AlertRule(
            id='new_rule',
            name='新规则',
            alert_type=AlertType.SERVER_OFFLINE,
            severity=AlertSeverity.MEDIUM,
            enabled=True,
            conditions={'offline_threshold_minutes': 15},
            notification_providers=['email'],
            notification_template='system_alert'
        )
        
        result = alert_manager.add_rule(rule)
        
        assert result == True
        assert 'new_rule' in alert_manager.rules
        assert alert_manager.rules['new_rule'].name == '新规则'
    
    def test_update_rule(self, alert_manager):
        """测试更新告警规则"""
        # 先添加一个规则
        rule = AlertRule(
            id='update_rule',
            name='原规则',
            alert_type=AlertType.CERTIFICATE_EXPIRING,
            severity=AlertSeverity.LOW,
            enabled=True,
            conditions={},
            notification_providers=[],
            notification_template='test'
        )
        alert_manager.add_rule(rule)
        
        # 更新规则
        updates = {
            'name': '更新后的规则',
            'severity': AlertSeverity.HIGH,
            'enabled': False
        }
        
        result = alert_manager.update_rule('update_rule', updates)
        
        assert result == True
        updated_rule = alert_manager.rules['update_rule']
        assert updated_rule.name == '更新后的规则'
        assert updated_rule.severity == AlertSeverity.HIGH
        assert updated_rule.enabled == False
    
    def test_update_nonexistent_rule(self, alert_manager):
        """测试更新不存在的规则"""
        result = alert_manager.update_rule('nonexistent', {'name': 'test'})
        assert result == False
    
    def test_delete_rule(self, alert_manager):
        """测试删除告警规则"""
        # 先添加一个规则
        rule = AlertRule(
            id='delete_rule',
            name='待删除规则',
            alert_type=AlertType.CERTIFICATE_EXPIRING,
            severity=AlertSeverity.LOW,
            enabled=True,
            conditions={},
            notification_providers=[],
            notification_template='test'
        )
        alert_manager.add_rule(rule)
        
        # 删除规则
        result = alert_manager.delete_rule('delete_rule')
        
        assert result == True
        assert 'delete_rule' not in alert_manager.rules
    
    def test_delete_nonexistent_rule(self, alert_manager):
        """测试删除不存在的规则"""
        result = alert_manager.delete_rule('nonexistent')
        assert result == False
    
    def test_get_rules(self, alert_manager):
        """测试获取所有规则"""
        rules = alert_manager.get_rules()
        
        assert isinstance(rules, list)
        assert len(rules) > 0
        assert all(isinstance(rule, AlertRule) for rule in rules)
    
    def test_get_rule(self, alert_manager):
        """测试获取指定规则"""
        # 获取存在的规则
        rule = alert_manager.get_rule('cert_expiring_30d')
        assert rule is not None
        assert rule.id == 'cert_expiring_30d'
        
        # 获取不存在的规则
        rule = alert_manager.get_rule('nonexistent')
        assert rule is None
    
    @pytest.mark.asyncio
    async def test_trigger_alert(self, alert_manager):
        """测试触发告警"""
        rule = alert_manager.get_rule('cert_expiring_30d')
        context = {
            'resource_id': 'cert_1',
            'domain': 'example.com',
            'days_remaining': 25
        }
        
        with patch.object(alert_manager, '_send_alert_notification', new_callable=AsyncMock):
            alert = await alert_manager.trigger_alert(rule, context)
            
            assert alert is not None
            assert alert.rule_id == rule.id
            assert alert.context['domain'] == 'example.com'
            assert alert.id in alert_manager.active_alerts
            assert alert in alert_manager.alert_history
    
    @pytest.mark.asyncio
    async def test_trigger_alert_in_cooldown(self, alert_manager):
        """测试冷却期内的告警触发"""
        rule = alert_manager.get_rule('cert_expiring_30d')
        context = {
            'resource_id': 'cert_1',
            'domain': 'example.com',
            'days_remaining': 25
        }
        
        # 先触发一次告警
        with patch.object(alert_manager, '_send_alert_notification', new_callable=AsyncMock):
            alert1 = await alert_manager.trigger_alert(rule, context)
            assert alert1 is not None
            
            # 立即再次触发相同告警（应该被冷却期阻止）
            alert2 = await alert_manager.trigger_alert(rule, context)
            assert alert2 is None
    
    def test_is_in_cooldown(self, alert_manager):
        """测试冷却期检查"""
        rule = AlertRule(
            id='cooldown_test',
            name='冷却测试',
            alert_type=AlertType.CERTIFICATE_EXPIRING,
            severity=AlertSeverity.LOW,
            enabled=True,
            conditions={},
            notification_providers=[],
            notification_template='test',
            cooldown_minutes=60
        )
        
        context = {'resource_id': 'test_resource'}
        
        # 没有历史告警，不在冷却期
        assert alert_manager._is_in_cooldown(rule, context) == False
        
        # 添加一个最近的告警
        recent_alert = Alert(
            id='recent_alert',
            rule_id='cooldown_test',
            alert_type=AlertType.CERTIFICATE_EXPIRING,
            severity=AlertSeverity.LOW,
            title='测试',
            description='测试',
            context={'resource_id': 'test_resource'}
        )
        recent_alert.created_at = datetime.now() - timedelta(minutes=30)  # 30分钟前
        alert_manager.alert_history.append(recent_alert)
        
        # 现在应该在冷却期内
        assert alert_manager._is_in_cooldown(rule, context) == True
        
        # 修改告警时间为2小时前
        recent_alert.created_at = datetime.now() - timedelta(hours=2)
        
        # 现在应该不在冷却期内
        assert alert_manager._is_in_cooldown(rule, context) == False
    
    def test_generate_alert_title(self, alert_manager):
        """测试生成告警标题"""
        rule = AlertRule(
            id='test',
            name='测试',
            alert_type=AlertType.CERTIFICATE_EXPIRING,
            severity=AlertSeverity.LOW,
            enabled=True,
            conditions={},
            notification_providers=[],
            notification_template='test'
        )
        
        context = {'domain': 'example.com'}
        title = alert_manager._generate_alert_title(rule, context)
        
        assert 'example.com' in title
        assert '证书即将过期' in title
    
    def test_generate_alert_description(self, alert_manager):
        """测试生成告警描述"""
        rule = AlertRule(
            id='test',
            name='测试',
            alert_type=AlertType.CERTIFICATE_EXPIRING,
            severity=AlertSeverity.LOW,
            enabled=True,
            conditions={},
            notification_providers=[],
            notification_template='test'
        )
        
        context = {'days_remaining': 7}
        description = alert_manager._generate_alert_description(rule, context)
        
        assert '7' in description
        assert '天' in description
    
    def test_resolve_alert(self, alert_manager):
        """测试解决告警"""
        # 创建一个活跃告警
        alert = Alert(
            id='test_alert',
            rule_id='test_rule',
            alert_type=AlertType.CERTIFICATE_EXPIRING,
            severity=AlertSeverity.LOW,
            title='测试告警',
            description='测试',
            context={}
        )
        alert_manager.active_alerts['test_alert'] = alert
        
        # 解决告警
        result = alert_manager.resolve_alert('test_alert')
        
        assert result == True
        assert 'test_alert' not in alert_manager.active_alerts
        assert alert.status == 'resolved'
        assert alert.resolved_at is not None
    
    def test_resolve_nonexistent_alert(self, alert_manager):
        """测试解决不存在的告警"""
        result = alert_manager.resolve_alert('nonexistent')
        assert result == False
    
    def test_get_active_alerts(self, alert_manager):
        """测试获取活跃告警"""
        # 添加一些活跃告警
        for i in range(3):
            alert = Alert(
                id=f'alert_{i}',
                rule_id='test_rule',
                alert_type=AlertType.CERTIFICATE_EXPIRING,
                severity=AlertSeverity.LOW,
                title=f'告警 {i}',
                description='测试',
                context={}
            )
            alert_manager.active_alerts[f'alert_{i}'] = alert
        
        active_alerts = alert_manager.get_active_alerts()
        
        assert len(active_alerts) == 3
        assert all(isinstance(alert, Alert) for alert in active_alerts)
    
    def test_get_alert_history(self, alert_manager):
        """测试获取告警历史"""
        # 添加一些历史告警
        for i in range(5):
            alert = Alert(
                id=f'history_alert_{i}',
                rule_id='test_rule',
                alert_type=AlertType.CERTIFICATE_EXPIRING,
                severity=AlertSeverity.LOW,
                title=f'历史告警 {i}',
                description='测试',
                context={}
            )
            alert_manager.alert_history.append(alert)
        
        # 获取最近3个告警
        history = alert_manager.get_alert_history(limit=3)
        
        assert len(history) == 3
        assert all(isinstance(alert, Alert) for alert in history)
    
    @patch('services.alert_manager.Certificate')
    def test_check_certificate_expiry(self, mock_cert_class, alert_manager):
        """测试检查证书过期"""
        # 模拟证书数据
        mock_cert = MagicMock()
        mock_cert.id = 1
        mock_cert.domain = 'example.com'
        mock_cert.expires_at = datetime.now() + timedelta(days=5)  # 5天后过期
        mock_cert.server.name = 'test-server'
        mock_cert.ca_type = 'letsencrypt'
        
        mock_cert_class.get_all.return_value = [mock_cert]
        
        with patch.object(alert_manager, 'trigger_alert', new_callable=AsyncMock) as mock_trigger:
            alert_manager._check_certificate_expiry()
            
            # 应该触发7天内过期的告警
            mock_trigger.assert_called()
            call_args = mock_trigger.call_args
            assert call_args[0][0].alert_type == AlertType.CERTIFICATE_EXPIRING
            assert call_args[0][1]['domain'] == 'example.com'
    
    @patch('services.alert_manager.Server')
    def test_check_server_status(self, mock_server_class, alert_manager):
        """测试检查服务器状态"""
        # 模拟离线服务器
        mock_server = MagicMock()
        mock_server.id = 1
        mock_server.name = 'test-server'
        mock_server.last_heartbeat = datetime.now() - timedelta(hours=1)  # 1小时前
        
        mock_server_class.get_all.return_value = [mock_server]
        
        with patch.object(alert_manager, 'trigger_alert', new_callable=AsyncMock) as mock_trigger:
            alert_manager._check_server_status()
            
            # 应该触发服务器离线告警
            mock_trigger.assert_called()
            call_args = mock_trigger.call_args
            assert call_args[0][0].alert_type == AlertType.SERVER_OFFLINE
            assert call_args[0][1]['server_name'] == 'test-server'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
