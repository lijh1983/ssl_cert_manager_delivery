"""
SSL证书监控配置服务
提供证书监控开关控制、频率配置、批量操作等功能
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from models.certificate import Certificate
from models.database import Database

logger = logging.getLogger(__name__)

class MonitoringService:
    """证书监控配置服务"""
    
    def __init__(self):
        self.db = Database()
    
    def update_monitoring_config(self, certificate_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """更新证书监控配置"""
        try:
            # 获取证书
            certificate = Certificate.get_by_id(certificate_id)
            if not certificate:
                return {'success': False, 'error': '证书不存在'}
            
            # 更新监控配置
            if 'monitoring_enabled' in config:
                certificate.monitoring_enabled = config['monitoring_enabled']
            
            if 'monitoring_frequency' in config:
                frequency = config['monitoring_frequency']
                if frequency < 300:  # 最小5分钟
                    return {'success': False, 'error': '监控频率不能小于300秒'}
                certificate.monitoring_frequency = frequency
            
            if 'alert_enabled' in config:
                certificate.alert_enabled = config['alert_enabled']
            
            # 保存更改
            certificate.save()
            
            logger.info(f"更新证书 {certificate_id} 监控配置: {config}")
            
            return {
                'success': True,
                'message': '监控配置更新成功',
                'config': {
                    'monitoring_enabled': certificate.monitoring_enabled,
                    'monitoring_frequency': certificate.monitoring_frequency,
                    'alert_enabled': certificate.alert_enabled
                }
            }
            
        except Exception as e:
            logger.error(f"更新监控配置失败: {str(e)}")
            return {'success': False, 'error': f'更新失败: {str(e)}'}
    
    def get_monitoring_config(self, certificate_id: int) -> Dict[str, Any]:
        """获取证书监控配置"""
        try:
            certificate = Certificate.get_by_id(certificate_id)
            if not certificate:
                return {'success': False, 'error': '证书不存在'}
            
            return {
                'success': True,
                'config': {
                    'monitoring_enabled': getattr(certificate, 'monitoring_enabled', True),
                    'monitoring_frequency': getattr(certificate, 'monitoring_frequency', 3600),
                    'alert_enabled': getattr(certificate, 'alert_enabled', True)
                }
            }
            
        except Exception as e:
            logger.error(f"获取监控配置失败: {str(e)}")
            return {'success': False, 'error': f'获取失败: {str(e)}'}
    
    def batch_update_monitoring(self, certificate_ids: List[int], config: Dict[str, Any]) -> Dict[str, Any]:
        """批量更新监控配置"""
        try:
            success_count = 0
            failed_count = 0
            errors = []
            
            for cert_id in certificate_ids:
                result = self.update_monitoring_config(cert_id, config)
                if result['success']:
                    success_count += 1
                else:
                    failed_count += 1
                    errors.append(f"证书 {cert_id}: {result['error']}")
            
            return {
                'success': True,
                'message': f'批量更新完成: 成功 {success_count} 个，失败 {failed_count} 个',
                'details': {
                    'success_count': success_count,
                    'failed_count': failed_count,
                    'errors': errors
                }
            }
            
        except Exception as e:
            logger.error(f"批量更新监控配置失败: {str(e)}")
            return {'success': False, 'error': f'批量更新失败: {str(e)}'}
    
    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            # 统计监控状态
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_certificates,
                    SUM(CASE WHEN monitoring_enabled = 1 THEN 1 ELSE 0 END) as monitoring_enabled_count,
                    SUM(CASE WHEN alert_enabled = 1 THEN 1 ELSE 0 END) as alert_enabled_count,
                    AVG(monitoring_frequency) as avg_frequency
                FROM certificates
            """)
            
            stats = cursor.fetchone()
            
            # 统计不同频率的分布
            cursor.execute("""
                SELECT monitoring_frequency, COUNT(*) as count
                FROM certificates
                WHERE monitoring_enabled = 1
                GROUP BY monitoring_frequency
                ORDER BY monitoring_frequency
            """)
            
            frequency_distribution = cursor.fetchall()
            
            return {
                'success': True,
                'statistics': {
                    'total_certificates': stats[0] or 0,
                    'monitoring_enabled_count': stats[1] or 0,
                    'alert_enabled_count': stats[2] or 0,
                    'average_frequency': round(stats[3] or 3600, 2),
                    'frequency_distribution': [
                        {'frequency': row[0], 'count': row[1]} 
                        for row in frequency_distribution
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"获取监控统计失败: {str(e)}")
            return {'success': False, 'error': f'获取统计失败: {str(e)}'}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def get_certificates_by_monitoring_status(self, enabled: bool = True) -> Dict[str, Any]:
        """根据监控状态获取证书列表"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, domain, status, monitoring_enabled, monitoring_frequency, alert_enabled
                FROM certificates
                WHERE monitoring_enabled = ?
                ORDER BY domain
            """, (1 if enabled else 0,))
            
            certificates = []
            for row in cursor.fetchall():
                certificates.append({
                    'id': row[0],
                    'domain': row[1],
                    'status': row[2],
                    'monitoring_enabled': bool(row[3]),
                    'monitoring_frequency': row[4],
                    'alert_enabled': bool(row[5])
                })
            
            return {
                'success': True,
                'certificates': certificates,
                'count': len(certificates)
            }
            
        except Exception as e:
            logger.error(f"获取证书列表失败: {str(e)}")
            return {'success': False, 'error': f'获取失败: {str(e)}'}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def validate_monitoring_frequency(self, frequency: int) -> Dict[str, Any]:
        """验证监控频率"""
        if frequency < 300:  # 5分钟
            return {'valid': False, 'error': '监控频率不能小于300秒(5分钟)'}
        
        if frequency > 86400:  # 24小时
            return {'valid': False, 'error': '监控频率不能大于86400秒(24小时)'}
        
        # 推荐的频率值
        recommended_frequencies = [300, 600, 1800, 3600, 7200, 21600, 43200, 86400]
        
        return {
            'valid': True,
            'recommended': frequency in recommended_frequencies,
            'recommended_frequencies': recommended_frequencies
        }
