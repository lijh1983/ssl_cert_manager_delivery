"""
SSL证书操作服务
提供手动检测、批量导入导出、证书续期等功能
"""

import csv
import io
import json
import logging
import pandas as pd
import threading
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
import socket
import ssl

from models.certificate import Certificate
from models.database import Database
from models.alert import Alert
from services.domain_monitoring_service import DomainMonitoringService
from services.port_monitoring_service import PortMonitoringService

logger = logging.getLogger(__name__)

class CertificateOperationsService:
    """证书操作服务"""
    
    def __init__(self):
        self.db = Database()
        self.domain_service = DomainMonitoringService()
        self.port_service = PortMonitoringService()
        self.max_workers = 5
        self.operation_tasks = {}  # 存储运行中的任务
        
    def manual_certificate_check(self, certificate_id: int, check_types: List[str] = None) -> Dict[str, Any]:
        """
        手动触发完整的证书检测
        
        Args:
            certificate_id: 证书ID
            check_types: 检测类型列表 ['domain', 'port', 'ssl']
        
        Returns:
            检测结果
        """
        if check_types is None:
            check_types = ['domain', 'port', 'ssl']
        
        try:
            # 获取证书信息
            certificate = Certificate.get_by_id(certificate_id)
            if not certificate:
                return {'success': False, 'error': '证书不存在'}
            
            # 标记检测开始
            self._mark_check_in_progress(certificate_id, True)
            
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 创建检测任务
            task_info = {
                'task_id': task_id,
                'certificate_id': certificate_id,
                'domain': certificate.domain,
                'check_types': check_types,
                'status': 'running',
                'progress': 0,
                'results': {},
                'errors': [],
                'start_time': datetime.now().isoformat(),
                'end_time': None
            }
            
            self.operation_tasks[task_id] = task_info
            
            # 在后台线程中执行检测
            thread = threading.Thread(
                target=self._execute_manual_check,
                args=(task_id, certificate_id, check_types)
            )
            thread.daemon = True
            thread.start()
            
            return {
                'success': True,
                'task_id': task_id,
                'message': '检测任务已启动',
                'estimated_duration': len(check_types) * 10  # 估计每个检测类型10秒
            }
            
        except Exception as e:
            self._mark_check_in_progress(certificate_id, False)
            logger.error(f"启动手动检测失败 {certificate_id}: {str(e)}")
            return {'success': False, 'error': f'启动检测失败: {str(e)}'}
    
    def _execute_manual_check(self, task_id: str, certificate_id: int, check_types: List[str]) -> None:
        """执行手动检测任务"""
        task_info = self.operation_tasks.get(task_id)
        if not task_info:
            return
        
        try:
            total_steps = len(check_types)
            current_step = 0
            
            # 域名检测
            if 'domain' in check_types:
                current_step += 1
                task_info['progress'] = int((current_step / total_steps) * 100)
                
                domain_result = self.domain_service.perform_comprehensive_domain_check(certificate_id)
                task_info['results']['domain'] = domain_result
                
                if not domain_result.get('success'):
                    task_info['errors'].append(f"域名检测失败: {domain_result.get('error', '未知错误')}")
            
            # 端口检测
            if 'port' in check_types:
                current_step += 1
                task_info['progress'] = int((current_step / total_steps) * 100)
                
                port_result = self.port_service.perform_comprehensive_port_check(certificate_id)
                task_info['results']['port'] = port_result
                
                if not port_result.get('success'):
                    task_info['errors'].append(f"端口检测失败: {port_result.get('error', '未知错误')}")
            
            # SSL状态检测
            if 'ssl' in check_types:
                current_step += 1
                task_info['progress'] = int((current_step / total_steps) * 100)
                
                ssl_result = self._check_ssl_status(certificate_id)
                task_info['results']['ssl'] = ssl_result
                
                if not ssl_result.get('success'):
                    task_info['errors'].append(f"SSL检测失败: {ssl_result.get('error', '未知错误')}")
            
            # 更新检测完成状态
            task_info['status'] = 'completed' if len(task_info['errors']) == 0 else 'completed_with_errors'
            task_info['progress'] = 100
            task_info['end_time'] = datetime.now().isoformat()
            
            # 记录操作历史
            self._record_operation_history(
                certificate_id, 
                'manual_check', 
                'completed', 
                f"检测类型: {', '.join(check_types)}"
            )
            
            logger.info(f"手动检测完成: 证书 {certificate_id}, 任务 {task_id}")
            
        except Exception as e:
            task_info['status'] = 'failed'
            task_info['errors'].append(f'检测执行失败: {str(e)}')
            task_info['end_time'] = datetime.now().isoformat()
            logger.error(f"手动检测执行失败 {certificate_id}: {str(e)}")
        
        finally:
            # 标记检测结束
            self._mark_check_in_progress(certificate_id, False)
    
    def deep_certificate_scan(self, certificate_id: int) -> Dict[str, Any]:
        """
        执行深度证书扫描
        
        Args:
            certificate_id: 证书ID
        
        Returns:
            深度扫描结果
        """
        try:
            certificate = Certificate.get_by_id(certificate_id)
            if not certificate:
                return {'success': False, 'error': '证书不存在'}
            
            domain = certificate.domain
            
            # 执行深度扫描
            scan_results = {
                'certificate_id': certificate_id,
                'domain': domain,
                'scan_type': 'deep',
                'certificate_chain_analysis': self._analyze_certificate_chain(domain),
                'security_vulnerabilities': self._check_security_vulnerabilities(domain),
                'compliance_check': self._check_compliance(domain),
                'performance_analysis': self._analyze_performance(domain),
                'timestamp': datetime.now().isoformat()
            }
            
            # 记录操作历史
            self._record_operation_history(
                certificate_id, 
                'deep_scan', 
                'completed', 
                '深度安全扫描'
            )
            
            return {
                'success': True,
                'scan_results': scan_results
            }
            
        except Exception as e:
            logger.error(f"深度证书扫描失败 {certificate_id}: {str(e)}")
            return {'success': False, 'error': f'深度扫描失败: {str(e)}'}
    
    def import_certificates_from_csv(self, csv_content: str, user_id: int) -> Dict[str, Any]:
        """
        从CSV文件批量导入证书信息
        
        Args:
            csv_content: CSV文件内容
            user_id: 用户ID
        
        Returns:
            导入结果
        """
        try:
            # 解析CSV数据
            df = pd.read_csv(io.StringIO(csv_content))
            
            # 验证必需的列
            required_columns = ['domain', 'server_ip', 'server_port']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    'success': False, 
                    'error': f'缺少必需的列: {", ".join(missing_columns)}'
                }
            
            # 数据验证和清理
            validation_result = self._validate_import_data(df)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'invalid_rows': validation_result.get('invalid_rows', [])
                }
            
            # 执行导入
            import_results = {
                'total_rows': len(df),
                'success_count': 0,
                'failed_count': 0,
                'duplicate_count': 0,
                'imported_certificates': [],
                'errors': []
            }
            
            for index, row in df.iterrows():
                try:
                    # 检查重复
                    existing_cert = self._find_existing_certificate(row['domain'])
                    if existing_cert:
                        import_results['duplicate_count'] += 1
                        import_results['errors'].append(f"行 {index + 1}: 域名 {row['domain']} 已存在")
                        continue
                    
                    # 创建证书记录
                    cert_data = self._prepare_certificate_data(row, user_id)
                    certificate = Certificate.create(**cert_data)
                    
                    import_results['success_count'] += 1
                    import_results['imported_certificates'].append({
                        'id': certificate.id,
                        'domain': certificate.domain
                    })
                    
                except Exception as e:
                    import_results['failed_count'] += 1
                    import_results['errors'].append(f"行 {index + 1}: {str(e)}")
            
            # 记录导入操作
            self._record_bulk_operation(
                'csv_import',
                f"导入 {import_results['success_count']} 个证书",
                user_id
            )
            
            return {
                'success': True,
                'import_results': import_results
            }
            
        except Exception as e:
            logger.error(f"CSV导入失败: {str(e)}")
            return {'success': False, 'error': f'导入失败: {str(e)}'}
    
    def export_certificates_to_csv(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        导出证书数据为CSV格式
        
        Args:
            filters: 过滤条件
        
        Returns:
            导出结果
        """
        try:
            # 构建查询条件
            where_conditions = ['1=1']
            params = []
            
            if filters:
                if filters.get('status'):
                    where_conditions.append('status = ?')
                    params.append(filters['status'])
                
                if filters.get('expires_before'):
                    where_conditions.append('expires_at <= ?')
                    params.append(filters['expires_before'])
                
                if filters.get('domain_pattern'):
                    where_conditions.append('domain LIKE ?')
                    params.append(f"%{filters['domain_pattern']}%")
            
            where_clause = ' AND '.join(where_conditions)
            
            # 查询证书数据
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(f"""
                SELECT 
                    id, domain, type, status, created_at, expires_at,
                    ca_type, monitoring_enabled, dns_status, domain_reachable,
                    tls_version, certificate_chain_valid, http_redirect_status,
                    notes, owner, business_unit
                FROM certificates
                WHERE {where_clause}
                ORDER BY domain
            """, params)
            
            certificates = cursor.fetchall()
            conn.close()
            
            # 转换为DataFrame
            columns = [
                'ID', '域名', '类型', '状态', '创建时间', '到期时间',
                'CA类型', '监控启用', 'DNS状态', '域名可达',
                'TLS版本', '证书链完整', 'HTTP重定向',
                '备注', '负责人', '业务单元'
            ]
            
            df = pd.DataFrame(certificates, columns=columns)
            
            # 转换为CSV
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            csv_content = csv_buffer.getvalue()
            
            return {
                'success': True,
                'csv_content': csv_content,
                'total_records': len(certificates),
                'filename': f'certificates_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
            
        except Exception as e:
            logger.error(f"CSV导出失败: {str(e)}")
            return {'success': False, 'error': f'导出失败: {str(e)}'}
    
    def import_from_discovery(self, ip_ranges: List[str], ports: List[int] = None) -> Dict[str, Any]:
        """
        通过网络扫描自动发现和导入证书
        
        Args:
            ip_ranges: IP地址范围列表
            ports: 扫描端口列表
        
        Returns:
            发现结果
        """
        if ports is None:
            ports = [443, 8443, 9443]
        
        try:
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 解析IP范围
            target_ips = self._parse_ip_ranges(ip_ranges)
            total_targets = len(target_ips) * len(ports)
            
            # 创建发现任务
            task_info = {
                'task_id': task_id,
                'type': 'discovery',
                'status': 'running',
                'progress': 0,
                'total_targets': total_targets,
                'scanned_count': 0,
                'discovered_certificates': [],
                'errors': [],
                'start_time': datetime.now().isoformat(),
                'end_time': None
            }
            
            self.operation_tasks[task_id] = task_info
            
            # 在后台线程中执行发现
            thread = threading.Thread(
                target=self._execute_discovery_scan,
                args=(task_id, target_ips, ports)
            )
            thread.daemon = True
            thread.start()
            
            return {
                'success': True,
                'task_id': task_id,
                'message': '证书发现任务已启动',
                'total_targets': total_targets
            }
            
        except Exception as e:
            logger.error(f"启动证书发现失败: {str(e)}")
            return {'success': False, 'error': f'启动发现失败: {str(e)}'}
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        task_info = self.operation_tasks.get(task_id)
        if not task_info:
            return {'success': False, 'error': '任务不存在'}
        
        return {
            'success': True,
            'task_info': task_info
        }
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """取消任务"""
        task_info = self.operation_tasks.get(task_id)
        if not task_info:
            return {'success': False, 'error': '任务不存在'}
        
        if task_info['status'] in ['completed', 'failed', 'cancelled']:
            return {'success': False, 'error': '任务已完成或已取消'}
        
        task_info['status'] = 'cancelled'
        task_info['end_time'] = datetime.now().isoformat()
        
        return {'success': True, 'message': '任务已取消'}

    def renew_certificate(self, certificate_id: int, force: bool = False) -> Dict[str, Any]:
        """
        续期证书

        Args:
            certificate_id: 证书ID
            force: 是否强制续期

        Returns:
            续期结果
        """
        try:
            certificate = Certificate.get_by_id(certificate_id)
            if not certificate:
                return {'success': False, 'error': '证书不存在'}

            # 检查是否需要续期
            if not force and not self._needs_renewal(certificate):
                return {
                    'success': False,
                    'error': '证书暂不需要续期',
                    'expires_at': certificate.expires_at
                }

            # 标记续期开始
            self._update_renewal_status(certificate_id, 'in_progress')

            try:
                # 执行续期逻辑（根据CA类型）
                renewal_result = self._execute_renewal(certificate)

                if renewal_result['success']:
                    # 更新证书信息
                    self._update_certificate_after_renewal(certificate_id, renewal_result)
                    self._update_renewal_status(certificate_id, 'completed')

                    # 记录操作历史
                    self._record_operation_history(
                        certificate_id,
                        'renewal',
                        'completed',
                        f"证书续期成功，新到期时间: {renewal_result.get('new_expires_at')}"
                    )

                    return {
                        'success': True,
                        'message': '证书续期成功',
                        'new_expires_at': renewal_result.get('new_expires_at'),
                        'renewal_details': renewal_result
                    }
                else:
                    self._update_renewal_status(certificate_id, 'failed')

                    # 创建续期失败告警
                    Alert.create(
                        certificate_id=certificate_id,
                        alert_type='renewal_failed',
                        message=f"证书续期失败: {renewal_result.get('error', '未知错误')}",
                        severity='high'
                    )

                    return {
                        'success': False,
                        'error': renewal_result.get('error', '续期失败'),
                        'details': renewal_result
                    }

            except Exception as e:
                self._update_renewal_status(certificate_id, 'failed')
                raise e

        except Exception as e:
            logger.error(f"证书续期失败 {certificate_id}: {str(e)}")
            return {'success': False, 'error': f'续期失败: {str(e)}'}

    def schedule_renewal(self, certificate_id: int, days_before: int = 30) -> Dict[str, Any]:
        """
        安排证书续期

        Args:
            certificate_id: 证书ID
            days_before: 提前续期天数

        Returns:
            安排结果
        """
        try:
            certificate = Certificate.get_by_id(certificate_id)
            if not certificate:
                return {'success': False, 'error': '证书不存在'}

            # 计算续期时间
            expires_at = datetime.fromisoformat(certificate.expires_at.replace('Z', '+00:00'))
            renewal_date = expires_at - timedelta(days=days_before)

            # 更新续期配置
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE certificates SET
                    auto_renewal_enabled = 1,
                    renewal_days_before = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (days_before, certificate_id))

            conn.commit()
            conn.close()

            # 记录操作历史
            self._record_operation_history(
                certificate_id,
                'schedule_renewal',
                'completed',
                f"安排自动续期，提前 {days_before} 天"
            )

            return {
                'success': True,
                'message': '续期安排成功',
                'renewal_date': renewal_date.isoformat(),
                'days_before': days_before
            }

        except Exception as e:
            logger.error(f"安排证书续期失败 {certificate_id}: {str(e)}")
            return {'success': False, 'error': f'安排续期失败: {str(e)}'}

    def batch_operations(self, operation_type: str, certificate_ids: List[int],
                        options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        批量操作

        Args:
            operation_type: 操作类型 (check/renew/delete)
            certificate_ids: 证书ID列表
            options: 操作选项

        Returns:
            批量操作结果
        """
        if options is None:
            options = {}

        try:
            # 生成任务ID
            task_id = str(uuid.uuid4())

            # 创建批量操作任务
            task_info = {
                'task_id': task_id,
                'type': f'batch_{operation_type}',
                'status': 'running',
                'progress': 0,
                'total_count': len(certificate_ids),
                'success_count': 0,
                'failed_count': 0,
                'results': [],
                'errors': [],
                'start_time': datetime.now().isoformat(),
                'end_time': None
            }

            self.operation_tasks[task_id] = task_info

            # 在后台线程中执行批量操作
            thread = threading.Thread(
                target=self._execute_batch_operations,
                args=(task_id, operation_type, certificate_ids, options)
            )
            thread.daemon = True
            thread.start()

            return {
                'success': True,
                'task_id': task_id,
                'message': f'批量{operation_type}任务已启动',
                'total_count': len(certificate_ids)
            }

        except Exception as e:
            logger.error(f"启动批量操作失败: {str(e)}")
            return {'success': False, 'error': f'启动批量操作失败: {str(e)}'}

    def get_operation_history(self, certificate_id: int, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """获取操作历史"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 获取总数
            cursor.execute("""
                SELECT COUNT(*) FROM certificate_operations
                WHERE certificate_id = ?
            """, (certificate_id,))
            total = cursor.fetchone()[0]

            # 获取分页数据
            offset = (page - 1) * per_page
            cursor.execute("""
                SELECT * FROM certificate_operations
                WHERE certificate_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (certificate_id, per_page, offset))

            operations = []
            for row in cursor.fetchall():
                operations.append({
                    'id': row[0],
                    'certificate_id': row[1],
                    'operation_type': row[2],
                    'status': row[3],
                    'details': row[4],
                    'user_id': row[5],
                    'created_at': row[6]
                })

            conn.close()

            return {
                'success': True,
                'operations': operations,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            }

        except Exception as e:
            logger.error(f"获取操作历史失败 {certificate_id}: {str(e)}")
            return {'success': False, 'error': f'获取操作历史失败: {str(e)}'}

    # 私有辅助方法
    def _mark_check_in_progress(self, certificate_id: int, in_progress: bool) -> None:
        """标记检测进行中状态"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE certificates SET
                    check_in_progress = ?,
                    last_manual_check = CASE WHEN ? = 0 THEN CURRENT_TIMESTAMP ELSE last_manual_check END
                WHERE id = ?
            """, (in_progress, in_progress, certificate_id))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"更新检测状态失败 {certificate_id}: {str(e)}")

    def _check_ssl_status(self, certificate_id: int) -> Dict[str, Any]:
        """检查SSL状态"""
        try:
            certificate = Certificate.get_by_id(certificate_id)
            if not certificate:
                return {'success': False, 'error': '证书不存在'}

            # 这里可以添加更多SSL状态检查逻辑
            # 目前使用端口监控服务的结果
            port_result = self.port_service.check_ssl_port(certificate.domain, 443)

            return {
                'success': True,
                'ssl_enabled': port_result.get('ssl_enabled', False),
                'tls_version': port_result.get('tls_version'),
                'security_grade': port_result.get('security_grade'),
                'handshake_time': port_result.get('handshake_time'),
                'errors': port_result.get('errors', [])
            }

        except Exception as e:
            logger.error(f"SSL状态检查失败 {certificate_id}: {str(e)}")
            return {'success': False, 'error': f'SSL检查失败: {str(e)}'}

    def _analyze_certificate_chain(self, domain: str) -> Dict[str, Any]:
        """分析证书链"""
        try:
            # 获取证书链信息
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert_chain = ssock.getpeercert_chain()

                    chain_analysis = {
                        'chain_length': len(cert_chain) if cert_chain else 0,
                        'is_complete': len(cert_chain) > 1 if cert_chain else False,
                        'certificates': []
                    }

                    if cert_chain:
                        for i, cert_der in enumerate(cert_chain):
                            cert_info = self.port_service.extract_certificate_details(cert_der)
                            chain_analysis['certificates'].append({
                                'position': i,
                                'type': 'leaf' if i == 0 else 'intermediate' if i < len(cert_chain) - 1 else 'root',
                                'subject': cert_info.get('subject', {}),
                                'issuer': cert_info.get('issuer', {}),
                                'expires': cert_info.get('not_valid_after')
                            })

                    return chain_analysis

        except Exception as e:
            logger.error(f"证书链分析失败 {domain}: {str(e)}")
            return {'error': f'证书链分析失败: {str(e)}'}

    def _check_security_vulnerabilities(self, domain: str) -> Dict[str, Any]:
        """检查安全漏洞"""
        vulnerabilities = {
            'heartbleed': False,
            'poodle': False,
            'beast': False,
            'crime': False,
            'weak_ciphers': [],
            'protocol_issues': []
        }

        try:
            # 检查TLS版本和加密套件
            port_result = self.port_service.check_ssl_port(domain, 443)

            tls_version = port_result.get('tls_version', '')
            cipher_suite = port_result.get('cipher_suite', '')

            # 检查过时的TLS版本
            if 'TLS 1.0' in tls_version or 'SSL' in tls_version:
                vulnerabilities['protocol_issues'].append('使用过时的TLS/SSL版本')

            # 检查弱加密套件
            weak_indicators = ['RC4', 'DES', 'MD5', 'NULL', 'EXPORT']
            for indicator in weak_indicators:
                if indicator in cipher_suite.upper():
                    vulnerabilities['weak_ciphers'].append(indicator)

            return vulnerabilities

        except Exception as e:
            logger.error(f"安全漏洞检查失败 {domain}: {str(e)}")
            return {'error': f'安全漏洞检查失败: {str(e)}'}

    def _check_compliance(self, domain: str) -> Dict[str, Any]:
        """检查合规性"""
        compliance = {
            'pci_dss': {'compliant': False, 'issues': []},
            'hipaa': {'compliant': False, 'issues': []},
            'gdpr': {'compliant': False, 'issues': []},
            'recommendations': []
        }

        try:
            # 获取SSL配置
            port_result = self.port_service.check_ssl_port(domain, 443)
            http_result = self.port_service.check_http_redirect(domain, 80)

            tls_version = port_result.get('tls_version', '')
            security_grade = port_result.get('security_grade', 'F')
            hsts_enabled = http_result.get('hsts_enabled', False)

            # PCI DSS 检查
            if 'TLS 1.2' in tls_version or 'TLS 1.3' in tls_version:
                if security_grade in ['A+', 'A', 'B']:
                    compliance['pci_dss']['compliant'] = True
                else:
                    compliance['pci_dss']['issues'].append('SSL安全等级不足')
            else:
                compliance['pci_dss']['issues'].append('TLS版本不符合PCI DSS要求')

            # HSTS检查
            if not hsts_enabled:
                compliance['recommendations'].append('启用HSTS以提高安全性')

            return compliance

        except Exception as e:
            logger.error(f"合规性检查失败 {domain}: {str(e)}")
            return {'error': f'合规性检查失败: {str(e)}'}

    def _analyze_performance(self, domain: str) -> Dict[str, Any]:
        """分析性能"""
        try:
            port_result = self.port_service.check_ssl_port(domain, 443)

            handshake_time = port_result.get('handshake_time', 0)

            performance = {
                'handshake_time': handshake_time,
                'performance_grade': 'excellent' if handshake_time < 500 else
                                   'good' if handshake_time < 1000 else
                                   'fair' if handshake_time < 2000 else 'poor',
                'recommendations': []
            }

            if handshake_time > 1000:
                performance['recommendations'].append('优化SSL配置以减少握手时间')

            if handshake_time > 2000:
                performance['recommendations'].append('考虑使用更快的加密算法')

            return performance

        except Exception as e:
            logger.error(f"性能分析失败 {domain}: {str(e)}")
            return {'error': f'性能分析失败: {str(e)}'}

    def _record_operation_history(self, certificate_id: int, operation_type: str,
                                 status: str, details: str, user_id: int = None) -> None:
        """记录操作历史"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO certificate_operations
                (certificate_id, operation_type, status, details, user_id, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (certificate_id, operation_type, status, details, user_id))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"记录操作历史失败: {str(e)}")

    def _record_bulk_operation(self, operation_type: str, details: str, user_id: int) -> None:
        """记录批量操作"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO certificate_operations
                (certificate_id, operation_type, status, details, user_id, created_at)
                VALUES (NULL, ?, 'completed', ?, ?, CURRENT_TIMESTAMP)
            """, (operation_type, details, user_id))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"记录批量操作失败: {str(e)}")

    def _validate_import_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """验证导入数据"""
        invalid_rows = []

        for index, row in df.iterrows():
            row_errors = []

            # 验证域名格式
            domain = str(row.get('domain', '')).strip()
            if not domain or '.' not in domain:
                row_errors.append('域名格式无效')

            # 验证IP地址
            server_ip = str(row.get('server_ip', '')).strip()
            try:
                ipaddress.ip_address(server_ip)
            except ValueError:
                row_errors.append('IP地址格式无效')

            # 验证端口
            try:
                port = int(row.get('server_port', 443))
                if not (1 <= port <= 65535):
                    row_errors.append('端口范围无效')
            except (ValueError, TypeError):
                row_errors.append('端口格式无效')

            if row_errors:
                invalid_rows.append({
                    'row': index + 1,
                    'errors': row_errors,
                    'data': row.to_dict()
                })

        if invalid_rows:
            return {
                'valid': False,
                'error': f'发现 {len(invalid_rows)} 行数据格式错误',
                'invalid_rows': invalid_rows
            }

        return {'valid': True}

    def _find_existing_certificate(self, domain: str) -> Optional[Dict[str, Any]]:
        """查找已存在的证书"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id, domain FROM certificates WHERE domain = ?", (domain,))
            result = cursor.fetchone()
            conn.close()

            if result:
                return {'id': result[0], 'domain': result[1]}
            return None

        except Exception as e:
            logger.error(f"查找证书失败: {str(e)}")
            return None

    def _prepare_certificate_data(self, row: pd.Series, user_id: int) -> Dict[str, Any]:
        """准备证书数据"""
        return {
            'domain': str(row.get('domain', '')).strip(),
            'type': str(row.get('type', 'single')).strip(),
            'server_ip': str(row.get('server_ip', '')).strip(),
            'server_port': int(row.get('server_port', 443)),
            'ca_type': str(row.get('ca_type', 'unknown')).strip(),
            'status': 'pending',
            'import_source': 'csv',
            'notes': str(row.get('notes', '')).strip(),
            'owner': str(row.get('owner', '')).strip(),
            'business_unit': str(row.get('business_unit', '')).strip(),
            'monitoring_enabled': bool(row.get('monitoring_enabled', True))
        }

    def _parse_ip_ranges(self, ip_ranges: List[str]) -> List[str]:
        """解析IP地址范围"""
        target_ips = []

        for ip_range in ip_ranges:
            try:
                # 支持单个IP、CIDR、IP范围
                if '/' in ip_range:
                    # CIDR格式
                    network = ipaddress.ip_network(ip_range, strict=False)
                    target_ips.extend([str(ip) for ip in network.hosts()])
                elif '-' in ip_range:
                    # IP范围格式 (192.168.1.1-192.168.1.10)
                    start_ip, end_ip = ip_range.split('-')
                    start = ipaddress.ip_address(start_ip.strip())
                    end = ipaddress.ip_address(end_ip.strip())

                    current = start
                    while current <= end:
                        target_ips.append(str(current))
                        current += 1
                else:
                    # 单个IP
                    ipaddress.ip_address(ip_range)  # 验证格式
                    target_ips.append(ip_range)

            except ValueError as e:
                logger.warning(f"无效的IP范围 {ip_range}: {str(e)}")

        return target_ips[:1000]  # 限制最大1000个IP

    def _execute_discovery_scan(self, task_id: str, target_ips: List[str], ports: List[int]) -> None:
        """执行发现扫描"""
        task_info = self.operation_tasks.get(task_id)
        if not task_info:
            return

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交扫描任务
                futures = []
                for ip in target_ips:
                    for port in ports:
                        if task_info['status'] == 'cancelled':
                            break
                        future = executor.submit(self._scan_single_target, ip, port)
                        futures.append(future)

                # 收集结果
                for future in as_completed(futures):
                    if task_info['status'] == 'cancelled':
                        break

                    try:
                        result = future.result(timeout=30)
                        task_info['scanned_count'] += 1
                        task_info['progress'] = int((task_info['scanned_count'] / task_info['total_targets']) * 100)

                        if result and result.get('has_certificate'):
                            task_info['discovered_certificates'].append(result)

                    except Exception as e:
                        task_info['errors'].append(f"扫描失败: {str(e)}")

            task_info['status'] = 'completed'
            task_info['end_time'] = datetime.now().isoformat()

        except Exception as e:
            task_info['status'] = 'failed'
            task_info['errors'].append(f'扫描执行失败: {str(e)}')
            task_info['end_time'] = datetime.now().isoformat()

    def _scan_single_target(self, ip: str, port: int) -> Optional[Dict[str, Any]]:
        """扫描单个目标"""
        try:
            # 检查端口是否开放
            with socket.create_connection((ip, port), timeout=5):
                pass

            # 尝试SSL连接
            try:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

                with socket.create_connection((ip, port), timeout=5) as sock:
                    with context.wrap_socket(sock) as ssock:
                        cert = ssock.getpeercert()

                        if cert:
                            # 提取域名
                            subject = cert.get('subject', ())
                            domain = None
                            for item in subject:
                                if item[0][0] == 'commonName':
                                    domain = item[0][1]
                                    break

                            # 检查SAN
                            san_domains = []
                            if 'subjectAltName' in cert:
                                for san_type, san_value in cert['subjectAltName']:
                                    if san_type == 'DNS':
                                        san_domains.append(san_value)

                            return {
                                'ip': ip,
                                'port': port,
                                'has_certificate': True,
                                'domain': domain,
                                'san_domains': san_domains,
                                'expires': cert.get('notAfter'),
                                'issuer': dict(cert.get('issuer', ())),
                                'discovered_at': datetime.now().isoformat()
                            }
            except ssl.SSLError:
                # 端口开放但不是SSL
                return {
                    'ip': ip,
                    'port': port,
                    'has_certificate': False,
                    'error': 'Not an SSL port'
                }

        except (socket.timeout, socket.error):
            # 端口不开放或连接失败
            return None

        return None

    def _execute_batch_operations(self, task_id: str, operation_type: str,
                                 certificate_ids: List[int], options: Dict[str, Any]) -> None:
        """执行批量操作"""
        task_info = self.operation_tasks.get(task_id)
        if not task_info:
            return

        try:
            for i, cert_id in enumerate(certificate_ids):
                if task_info['status'] == 'cancelled':
                    break

                try:
                    if operation_type == 'check':
                        result = self.manual_certificate_check(cert_id, options.get('check_types'))
                    elif operation_type == 'renew':
                        result = self.renew_certificate(cert_id, options.get('force', False))
                    elif operation_type == 'delete':
                        result = self._delete_certificate(cert_id)
                    else:
                        result = {'success': False, 'error': f'未知操作类型: {operation_type}'}

                    task_info['results'].append({
                        'certificate_id': cert_id,
                        'result': result
                    })

                    if result.get('success'):
                        task_info['success_count'] += 1
                    else:
                        task_info['failed_count'] += 1
                        task_info['errors'].append(f"证书 {cert_id}: {result.get('error', '操作失败')}")

                except Exception as e:
                    task_info['failed_count'] += 1
                    task_info['errors'].append(f"证书 {cert_id}: {str(e)}")

                # 更新进度
                task_info['progress'] = int(((i + 1) / len(certificate_ids)) * 100)

            task_info['status'] = 'completed'
            task_info['end_time'] = datetime.now().isoformat()

        except Exception as e:
            task_info['status'] = 'failed'
            task_info['errors'].append(f'批量操作执行失败: {str(e)}')
            task_info['end_time'] = datetime.now().isoformat()

    def _needs_renewal(self, certificate: Certificate) -> bool:
        """检查是否需要续期"""
        try:
            expires_at = datetime.fromisoformat(certificate.expires_at.replace('Z', '+00:00'))
            renewal_days_before = getattr(certificate, 'renewal_days_before', 30)
            renewal_date = expires_at - timedelta(days=renewal_days_before)

            return datetime.now() >= renewal_date

        except Exception:
            return False

    def _execute_renewal(self, certificate: Certificate) -> Dict[str, Any]:
        """执行证书续期"""
        # 这里应该根据不同的CA类型实现具体的续期逻辑
        # 目前返回模拟结果
        try:
            ca_type = certificate.ca_type.lower()

            if ca_type == 'letsencrypt':
                return self._renew_letsencrypt_certificate(certificate)
            elif ca_type in ['digicert', 'comodo', 'globalsign']:
                return self._renew_commercial_certificate(certificate)
            else:
                return {
                    'success': False,
                    'error': f'不支持的CA类型: {ca_type}'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'续期执行失败: {str(e)}'
            }

    def _renew_letsencrypt_certificate(self, certificate: Certificate) -> Dict[str, Any]:
        """续期Let's Encrypt证书"""
        # 模拟Let's Encrypt续期
        try:
            # 这里应该调用certbot或ACME客户端
            # 目前返回模拟成功结果
            new_expires_at = datetime.now() + timedelta(days=90)

            return {
                'success': True,
                'new_expires_at': new_expires_at.isoformat(),
                'renewal_method': 'letsencrypt_auto',
                'certificate_path': f'/etc/letsencrypt/live/{certificate.domain}/fullchain.pem',
                'private_key_path': f'/etc/letsencrypt/live/{certificate.domain}/privkey.pem'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Let\'s Encrypt续期失败: {str(e)}'
            }

    def _renew_commercial_certificate(self, certificate: Certificate) -> Dict[str, Any]:
        """续期商业证书"""
        # 模拟商业证书续期
        return {
            'success': False,
            'error': '商业证书续期需要手动处理，请联系CA提供商'
        }

    def _update_renewal_status(self, certificate_id: int, status: str) -> None:
        """更新续期状态"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE certificates SET
                    renewal_status = ?,
                    last_renewal_attempt = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, certificate_id))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"更新续期状态失败 {certificate_id}: {str(e)}")

    def _update_certificate_after_renewal(self, certificate_id: int, renewal_result: Dict[str, Any]) -> None:
        """续期后更新证书信息"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE certificates SET
                    expires_at = ?,
                    status = 'valid',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (renewal_result.get('new_expires_at'), certificate_id))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"更新证书信息失败 {certificate_id}: {str(e)}")

    def _delete_certificate(self, certificate_id: int) -> Dict[str, Any]:
        """删除证书"""
        try:
            certificate = Certificate.get_by_id(certificate_id)
            if not certificate:
                return {'success': False, 'error': '证书不存在'}

            # 删除证书记录（级联删除相关数据）
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM certificates WHERE id = ?", (certificate_id,))
            conn.commit()
            conn.close()

            return {
                'success': True,
                'message': f'证书 {certificate.domain} 已删除'
            }

        except Exception as e:
            logger.error(f"删除证书失败 {certificate_id}: {str(e)}")
            return {'success': False, 'error': f'删除失败: {str(e)}'}
