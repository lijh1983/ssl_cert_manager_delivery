"""
SSL证书域名监控定时任务调度器
"""

import time
import threading
import logging
import json
from typing import Dict, List, Any
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from .domain_monitoring_service import DomainMonitoringService
from models.certificate import Certificate
from models.database import db

logger = logging.getLogger(__name__)

class DomainMonitoringScheduler:
    """域名监控定时任务调度器"""
    
    def __init__(self):
        self.domain_service = DomainMonitoringService()
        self.running = False
        self.scheduler_thread = None
        self.max_concurrent_checks = 5
        self.check_interval = 60  # 检查间隔(秒)
        
    def start(self) -> None:
        """启动调度器"""
        if self.running:
            logger.warning("域名监控调度器已在运行")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("域名监控调度器已启动")
    
    def stop(self) -> None:
        """停止调度器"""
        if not self.running:
            return
        
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        logger.info("域名监控调度器已停止")
    
    def _run_scheduler(self) -> None:
        """运行调度器主循环"""
        logger.info("域名监控调度器主循环开始")
        
        while self.running:
            try:
                # 获取需要检查的证书
                certificates_to_check = self._get_certificates_to_check()
                
                if certificates_to_check:
                    logger.info(f"发现 {len(certificates_to_check)} 个证书需要进行域名检查")
                    
                    # 执行批量检查
                    self._execute_batch_checks(certificates_to_check)
                
                # 等待下一次检查
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"域名监控调度器执行失败: {str(e)}")
                time.sleep(self.check_interval)
    
    def _get_certificates_to_check(self) -> List[Dict[str, Any]]:
        """获取需要检查的证书列表"""
        try:
            db.connect()

            # 查询启用监控且需要检查的证书
            certificates = db.fetchall("""
                SELECT
                    id, domain, monitoring_frequency, last_dns_check, last_reachability_check
                FROM certificates
                WHERE monitoring_enabled = 1
                AND (
                    last_dns_check IS NULL
                    OR datetime(last_dns_check, '+' || monitoring_frequency || ' seconds') <= datetime('now')
                )
                ORDER BY
                    CASE WHEN last_dns_check IS NULL THEN 0 ELSE 1 END,
                    last_dns_check ASC
                LIMIT 50
            """)

            return certificates or []

        except Exception as e:
            logger.error(f"获取待检查证书列表失败: {str(e)}")
            return []
        finally:
            db.close()
    
    def _execute_batch_checks(self, certificates: List[Dict[str, Any]]) -> None:
        """执行批量域名检查"""
        try:
            # 按优先级分组
            high_priority = []  # 从未检查过的
            normal_priority = []  # 正常检查的
            
            for cert in certificates:
                if cert['last_dns_check'] is None:
                    high_priority.append(cert)
                else:
                    normal_priority.append(cert)
            
            # 先处理高优先级
            if high_priority:
                self._process_certificate_batch(high_priority, "高优先级")
            
            # 再处理普通优先级
            if normal_priority:
                self._process_certificate_batch(normal_priority, "普通优先级")
                
        except Exception as e:
            logger.error(f"执行批量域名检查失败: {str(e)}")
    
    def _process_certificate_batch(self, certificates: List[Dict[str, Any]], batch_type: str) -> None:
        """处理证书批次"""
        try:
            certificate_ids = [cert['id'] for cert in certificates]
            
            logger.info(f"开始处理{batch_type}证书批次: {len(certificate_ids)} 个证书")
            
            # 使用线程池执行检查
            with ThreadPoolExecutor(max_workers=self.max_concurrent_checks) as executor:
                # 提交检查任务
                future_to_cert = {
                    executor.submit(self._check_single_certificate, cert['id']): cert
                    for cert in certificates
                }
                
                # 收集结果
                success_count = 0
                failed_count = 0
                
                for future in as_completed(future_to_cert):
                    cert = future_to_cert[future]
                    try:
                        result = future.result(timeout=30)
                        if result and result.get('success'):
                            success_count += 1
                        else:
                            failed_count += 1
                            logger.warning(f"证书 {cert['id']} ({cert['domain']}) 检查失败")
                    except Exception as e:
                        failed_count += 1
                        logger.error(f"证书 {cert['id']} ({cert['domain']}) 检查异常: {str(e)}")
                
                logger.info(f"{batch_type}批次检查完成: 成功 {success_count}, 失败 {failed_count}")
                
        except Exception as e:
            logger.error(f"处理{batch_type}证书批次失败: {str(e)}")
    
    def _check_single_certificate(self, certificate_id: int) -> Dict[str, Any]:
        """检查单个证书"""
        try:
            # 记录检查历史
            self._record_check_start(certificate_id)
            
            # 执行域名检查
            result = self.domain_service.perform_comprehensive_domain_check(certificate_id)
            
            # 记录检查结果
            self._record_check_result(certificate_id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"检查证书 {certificate_id} 失败: {str(e)}")
            self._record_check_error(certificate_id, str(e))
            return {'success': False, 'error': str(e)}
    
    def _record_check_start(self, certificate_id: int) -> None:
        """记录检查开始"""
        try:
            db.connect()

            db.execute("""
                INSERT INTO domain_monitoring_history
                (certificate_id, check_type, status, created_at)
                VALUES (?, 'comprehensive', 'started', CURRENT_TIMESTAMP)
            """, (certificate_id,))

            db.commit()

        except Exception as e:
            logger.error(f"记录检查开始失败 {certificate_id}: {str(e)}")
        finally:
            db.close()
    
    def _record_check_result(self, certificate_id: int, result: Dict[str, Any]) -> None:
        """记录检查结果"""
        try:
            db.connect()

            if result.get('success'):
                status = result.get('overall_status', 'unknown')
                details = {
                    'dns_check': result.get('dns_check', {}),
                    'reachability_check': result.get('reachability_check', {}),
                    'dns_validation': result.get('dns_validation', {})
                }

                db.execute("""
                    INSERT INTO domain_monitoring_history
                    (certificate_id, check_type, status, details, created_at)
                    VALUES (?, 'comprehensive', ?, ?, CURRENT_TIMESTAMP)
                """, (certificate_id, status, json.dumps(details)))
            else:
                db.execute("""
                    INSERT INTO domain_monitoring_history
                    (certificate_id, check_type, status, error_message, created_at)
                    VALUES (?, 'comprehensive', 'failed', ?, CURRENT_TIMESTAMP)
                """, (certificate_id, result.get('error', '未知错误')))

            db.commit()

        except Exception as e:
            logger.error(f"记录检查结果失败 {certificate_id}: {str(e)}")
        finally:
            db.close()
    
    def _record_check_error(self, certificate_id: int, error_message: str) -> None:
        """记录检查错误"""
        try:
            db.connect()

            db.execute("""
                INSERT INTO domain_monitoring_history
                (certificate_id, check_type, status, error_message, created_at)
                VALUES (?, 'comprehensive', 'error', ?, CURRENT_TIMESTAMP)
            """, (certificate_id, error_message))

            db.commit()

        except Exception as e:
            logger.error(f"记录检查错误失败 {certificate_id}: {str(e)}")
        finally:
            db.close()
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            'running': self.running,
            'max_concurrent_checks': self.max_concurrent_checks,
            'check_interval': self.check_interval,
            'thread_alive': self.scheduler_thread.is_alive() if self.scheduler_thread else False
        }
    
    def update_config(self, max_concurrent_checks: int = None, check_interval: int = None) -> None:
        """更新调度器配置"""
        if max_concurrent_checks is not None:
            self.max_concurrent_checks = max(1, min(max_concurrent_checks, 20))
            logger.info(f"更新最大并发检查数: {self.max_concurrent_checks}")
        
        if check_interval is not None:
            self.check_interval = max(30, min(check_interval, 3600))  # 30秒到1小时
            logger.info(f"更新检查间隔: {self.check_interval}秒")

# 全局调度器实例
domain_monitoring_scheduler = DomainMonitoringScheduler()
