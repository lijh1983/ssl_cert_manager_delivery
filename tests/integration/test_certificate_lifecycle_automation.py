"""
证书生命周期管理自动化测试
测试证书续期、监控、告警等自动化功能
"""
import pytest
import sys
import os
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend', 'src'))

from services.certificate_service import CertificateService
from services.notification_service import NotificationManager
from utils.exceptions import CertificateError, ErrorCode
from utils.logging_config import get_logger

logger = get_logger(__name__)


class TestCertificateLifecycleAutomation:
    """证书生命周期自动化测试类"""
    
    @pytest.fixture
    def certificate_service(self):
        """创建证书服务实例"""
        with patch('services.certificate_service.ACMEManager') as mock_manager:
            service = CertificateService()
            service.acme_manager = mock_manager.return_value
            return service
    
    @pytest.fixture
    def notification_manager(self):
        """创建通知管理器实例"""
        return NotificationManager()
    
    @pytest.fixture
    def expiring_certificates(self):
        """创建即将过期的证书数据"""
        now = datetime.now()
        return [
            # 30天后过期
            Mock(
                id=1,
                domain='cert30.example.com',
                expires_at=(now + timedelta(days=30)).isoformat(),
                auto_renew=True,
                ca_type='letsencrypt',
                server=Mock(name='server1', id=1)
            ),
            # 7天后过期
            Mock(
                id=2,
                domain='cert7.example.com',
                expires_at=(now + timedelta(days=7)).isoformat(),
                auto_renew=True,
                ca_type='letsencrypt',
                server=Mock(name='server2', id=2)
            ),
            # 1天后过期
            Mock(
                id=3,
                domain='cert1.example.com',
                expires_at=(now + timedelta(days=1)).isoformat(),
                auto_renew=True,
                ca_type='letsencrypt',
                server=Mock(name='server3', id=3)
            ),
            # 已过期
            Mock(
                id=4,
                domain='expired.example.com',
                expires_at=(now - timedelta(days=1)).isoformat(),
                auto_renew=True,
                ca_type='letsencrypt',
                server=Mock(name='server4', id=4)
            ),
            # 不自动续期
            Mock(
                id=5,
                domain='manual.example.com',
                expires_at=(now + timedelta(days=7)).isoformat(),
                auto_renew=False,
                ca_type='letsencrypt',
                server=Mock(name='server5', id=5)
            )
        ]

    # ==================== 证书续期测试 ====================
    
    def test_auto_detect_expiring_certificates(self, certificate_service, expiring_certificates):
        """测试自动检测即将过期的证书"""
        with patch('models.certificate.Certificate.get_expiring') as mock_get_expiring:
            # 模拟30天内过期的证书
            mock_get_expiring.return_value = expiring_certificates[:4]  # 排除手动续期的证书
            
            # 执行检测
            result = certificate_service.check_expiring_certificates(days_before=30)
            
            # 验证结果
            assert result['checked'] == 4
            assert result['expiring'] == 4
            assert len(result['certificates']) == 4
            
            # 验证不同过期时间段的分类
            urgent_certs = [cert for cert in result['certificates'] if cert['days_remaining'] <= 7]
            warning_certs = [cert for cert in result['certificates'] if 7 < cert['days_remaining'] <= 30]
            
            assert len(urgent_certs) == 3  # 7天、1天、已过期
            assert len(warning_certs) == 1  # 30天
    
    def test_auto_renewal_success(self, certificate_service, expiring_certificates):
        """测试自动续期成功"""
        cert_to_renew = expiring_certificates[1]  # 7天后过期的证书
        
        # 模拟续期成功
        mock_renewal_result = {
            'success': True,
            'certificate': 'renewed_certificate_content',
            'private_key': 'renewed_private_key',
            'domains': [cert_to_renew.domain],
            'cert_info': {
                'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat(),
                'issuer': 'Let\'s Encrypt'
            }
        }
        
        with patch('models.certificate.Certificate.get_by_id', return_value=cert_to_renew):
            certificate_service.acme_manager.request_certificate.return_value = mock_renewal_result
            cert_to_renew.save = Mock()
            
            # 执行续期
            result = certificate_service.renew_certificate(cert_to_renew.id)
            
            # 验证结果
            assert result['success'] is True
            assert result['certificate_id'] == cert_to_renew.id
            assert 'expires_at' in result
            
            # 验证证书对象被更新
            cert_to_renew.save.assert_called_once()
    
    def test_auto_renewal_failure_with_retry(self, certificate_service, expiring_certificates):
        """测试自动续期失败时的重试机制"""
        cert_to_renew = expiring_certificates[1]
        
        # 模拟第一次续期失败，第二次成功
        mock_failure = {
            'success': False,
            'error': 'ACME服务器暂时不可用'
        }
        
        mock_success = {
            'success': True,
            'certificate': 'renewed_certificate_content',
            'private_key': 'renewed_private_key',
            'domains': [cert_to_renew.domain],
            'cert_info': {
                'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat()
            }
        }
        
        with patch('models.certificate.Certificate.get_by_id', return_value=cert_to_renew), \
             patch('time.sleep'):  # 加速测试
            
            certificate_service.acme_manager.request_certificate.side_effect = [mock_failure, mock_success]
            cert_to_renew.save = Mock()
            
            # 执行带重试的续期
            result = certificate_service.renew_certificate_with_retry(
                cert_to_renew.id, 
                max_retries=2, 
                retry_delay=1
            )
            
            # 验证结果
            assert result['success'] is True
            assert result['retry_count'] == 1
            
            # 验证ACME管理器被调用了两次
            assert certificate_service.acme_manager.request_certificate.call_count == 2
    
    def test_auto_renewal_degradation_strategy(self, certificate_service, expiring_certificates):
        """测试续期失败时的降级策略"""
        cert_to_renew = expiring_certificates[1]
        
        # 模拟Let's Encrypt失败，切换到ZeroSSL成功
        mock_le_failure = {
            'success': False,
            'error': 'Let\'s Encrypt频率限制'
        }
        
        mock_zerossl_success = {
            'success': True,
            'certificate': 'zerossl_certificate_content',
            'private_key': 'zerossl_private_key',
            'domains': [cert_to_renew.domain],
            'cert_info': {
                'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat(),
                'issuer': 'ZeroSSL'
            }
        }
        
        with patch('models.certificate.Certificate.get_by_id', return_value=cert_to_renew):
            # 模拟CA切换
            certificate_service.acme_manager.request_certificate.side_effect = [
                mock_le_failure,  # Let's Encrypt失败
                mock_zerossl_success  # ZeroSSL成功
            ]
            cert_to_renew.save = Mock()
            
            # 执行带降级策略的续期
            result = certificate_service.renew_certificate_with_fallback(
                cert_to_renew.id,
                fallback_cas=['zerossl', 'buypass']
            )
            
            # 验证结果
            assert result['success'] is True
            assert result['ca_used'] == 'zerossl'
            assert result['fallback_used'] is True
    
    def test_auto_deployment_after_renewal(self, certificate_service, expiring_certificates):
        """测试续期成功后的自动部署"""
        cert_to_renew = expiring_certificates[1]
        cert_to_renew.deployment_config = {
            'server_type': 'nginx',
            'config_path': '/etc/nginx/ssl/',
            'reload_command': 'systemctl reload nginx'
        }
        
        # 模拟续期成功
        mock_renewal_result = {
            'success': True,
            'certificate': 'renewed_certificate_content',
            'private_key': 'renewed_private_key',
            'domains': [cert_to_renew.domain],
            'cert_info': {
                'not_valid_after': (datetime.now() + timedelta(days=90)).isoformat()
            }
        }
        
        # 模拟部署成功
        mock_deployment_result = {
            'success': True,
            'deployed_files': [
                '/etc/nginx/ssl/cert.pem',
                '/etc/nginx/ssl/privkey.pem'
            ]
        }
        
        with patch('models.certificate.Certificate.get_by_id', return_value=cert_to_renew), \
             patch.object(certificate_service, 'deploy_certificate') as mock_deploy:
            
            certificate_service.acme_manager.request_certificate.return_value = mock_renewal_result
            mock_deploy.return_value = mock_deployment_result
            cert_to_renew.save = Mock()
            
            # 执行续期和自动部署
            result = certificate_service.renew_and_deploy_certificate(cert_to_renew.id)
            
            # 验证结果
            assert result['renewal']['success'] is True
            assert result['deployment']['success'] is True
            
            # 验证部署被调用
            mock_deploy.assert_called_once_with(
                cert_to_renew.id,
                cert_to_renew.deployment_config
            )

    # ==================== 证书监控测试 ====================
    
    def test_certificate_health_monitoring(self, certificate_service, expiring_certificates):
        """测试证书健康监控"""
        certificates = expiring_certificates[:3]
        
        # 模拟健康检查结果
        health_results = [
            {'valid': True, 'days_remaining': 30, 'health_score': 90},
            {'valid': True, 'days_remaining': 7, 'health_score': 60},
            {'valid': True, 'days_remaining': 1, 'health_score': 20}
        ]
        
        with patch('models.certificate.Certificate.get_all_active') as mock_get_all, \
             patch.object(certificate_service, 'check_certificate_health') as mock_health_check:
            
            mock_get_all.return_value = certificates
            mock_health_check.side_effect = [
                {'certificate_id': cert.id, 'health_status': health}
                for cert, health in zip(certificates, health_results)
            ]
            
            # 执行健康监控
            result = certificate_service.monitor_certificate_health()
            
            # 验证结果
            assert result['total_certificates'] == 3
            assert result['healthy_certificates'] == 1  # 只有30天的证书健康
            assert result['warning_certificates'] == 1  # 7天的证书警告
            assert result['critical_certificates'] == 1  # 1天的证书危险
            
            # 验证每个证书都被检查
            assert mock_health_check.call_count == 3
    
    def test_certificate_status_real_time_monitoring(self, certificate_service, expiring_certificates):
        """测试证书状态实时监控"""
        cert = expiring_certificates[0]
        
        # 模拟实时状态检查
        with patch('models.certificate.Certificate.get_by_id', return_value=cert), \
             patch('services.certificate_service.check_certificate_validity') as mock_check_validity:
            
            mock_check_validity.return_value = {
                'valid': True,
                'days_remaining': 30,
                'issuer': 'Let\'s Encrypt',
                'signature_algorithm': 'SHA256withRSA',
                'key_size': 2048,
                'san_domains': [cert.domain]
            }
            
            # 执行实时监控
            result = certificate_service.get_certificate_real_time_status(cert.id)
            
            # 验证结果
            assert result['certificate_id'] == cert.id
            assert result['domain'] == cert.domain
            assert result['real_time_status']['valid'] is True
            assert result['real_time_status']['days_remaining'] == 30
            assert 'last_checked' in result
    
    def test_alert_triggering_mechanism(self, certificate_service, notification_manager, expiring_certificates):
        """测试告警触发机制"""
        urgent_cert = expiring_certificates[2]  # 1天后过期
        
        with patch('models.certificate.Certificate.get_expiring') as mock_get_expiring, \
             patch.object(notification_manager, 'send_notification') as mock_send_notification:
            
            mock_get_expiring.return_value = [urgent_cert]
            mock_send_notification.return_value = {
                'success': True,
                'sent': ['email', 'slack'],
                'failed': []
            }
            
            # 执行告警检查
            result = certificate_service.check_and_send_alerts(days_before=7)
            
            # 验证结果
            assert result['alerts_sent'] == 1
            assert result['notifications_successful'] == 1
            
            # 验证通知被发送
            mock_send_notification.assert_called_once()
            call_args = mock_send_notification.call_args
            assert call_args[0][0] == 'certificate_expiring'  # 模板名称
            assert call_args[0][1]['domain'] == urgent_cert.domain  # 上下文
    
    def test_monitoring_data_accuracy(self, certificate_service, expiring_certificates):
        """测试监控数据的准确性"""
        certificates = expiring_certificates[:3]
        
        with patch('models.certificate.Certificate.get_all_active', return_value=certificates):
            
            # 执行监控数据收集
            result = certificate_service.collect_monitoring_data()
            
            # 验证数据准确性
            assert result['total_certificates'] == 3
            assert result['by_status']['valid'] == 3
            assert result['by_ca']['letsencrypt'] == 3
            
            # 验证过期时间分布
            expiry_distribution = result['expiry_distribution']
            assert expiry_distribution['30_days'] == 1
            assert expiry_distribution['7_days'] == 1
            assert expiry_distribution['1_day'] == 1
            
            # 验证自动续期统计
            auto_renew_stats = result['auto_renew_stats']
            assert auto_renew_stats['enabled'] == 3
            assert auto_renew_stats['disabled'] == 0

    # ==================== 批量操作测试 ====================
    
    def test_batch_certificate_renewal(self, certificate_service, expiring_certificates):
        """测试批量证书续期"""
        certs_to_renew = expiring_certificates[:3]
        cert_ids = [cert.id for cert in certs_to_renew]
        
        # 模拟续期结果（2成功，1失败）
        renewal_results = [
            {'success': True, 'certificate': 'renewed1', 'private_key': 'key1'},
            {'success': True, 'certificate': 'renewed2', 'private_key': 'key2'},
            {'success': False, 'error': 'ACME验证失败'}
        ]
        
        with patch('models.certificate.Certificate.get_by_id') as mock_get_cert:
            mock_get_cert.side_effect = certs_to_renew
            certificate_service.acme_manager.request_certificate.side_effect = renewal_results
            
            for cert in certs_to_renew:
                cert.save = Mock()
            
            # 执行批量续期
            result = certificate_service.batch_renew_certificates(cert_ids)
            
            # 验证结果
            assert result['total'] == 3
            assert result['successful'] == 2
            assert result['failed'] == 1
            assert len(result['results']) == 3
            
            # 验证成功的证书被保存
            assert certs_to_renew[0].save.called
            assert certs_to_renew[1].save.called
    
    def test_scheduled_maintenance_tasks(self, certificate_service, expiring_certificates):
        """测试定时维护任务"""
        with patch('models.certificate.Certificate.get_expiring') as mock_get_expiring, \
             patch('models.certificate.Certificate.get_all_active') as mock_get_all, \
             patch.object(certificate_service, 'cleanup_expired_certificates') as mock_cleanup:
            
            mock_get_expiring.return_value = expiring_certificates[:2]
            mock_get_all.return_value = expiring_certificates
            mock_cleanup.return_value = {'cleaned': 1, 'errors': 0}
            
            # 执行定时维护
            result = certificate_service.run_scheduled_maintenance()
            
            # 验证结果
            assert result['expiry_check']['checked'] == 2
            assert result['health_monitoring']['total'] == 5
            assert result['cleanup']['cleaned'] == 1
            assert result['maintenance_completed'] is True
            
            # 验证各项任务被执行
            mock_get_expiring.assert_called()
            mock_get_all.assert_called()
            mock_cleanup.assert_called()
