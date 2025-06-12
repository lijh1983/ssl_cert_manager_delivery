"""
SSL证书域名监控服务
提供DNS解析状态检查、域名可达性监控等功能
"""

import dns.resolver
import requests
import socket
import time
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from models.certificate import Certificate
from models.database import Database
from models.alert import Alert

logger = logging.getLogger(__name__)

class DomainMonitoringService:
    """域名监控服务"""
    
    def __init__(self):
        self.db = Database()
        # DNS服务器列表
        self.dns_servers = [
            '8.8.8.8',      # Google DNS
            '1.1.1.1',      # Cloudflare DNS
            '223.5.5.5',    # 阿里云DNS
            '114.114.114.114'  # 114 DNS
        ]
        # 默认超时设置
        self.dns_timeout = 5.0
        self.http_timeout = 10.0
        self.max_workers = 10
    
    def check_domain_resolution(self, domain: str, record_types: List[str] = None) -> Dict[str, Any]:
        """
        检查域名DNS解析状态
        
        Args:
            domain: 域名
            record_types: 记录类型列表，默认为['A', 'AAAA', 'CNAME']
        
        Returns:
            包含解析结果的字典
        """
        if record_types is None:
            record_types = ['A', 'AAAA', 'CNAME']
        
        start_time = time.time()
        result = {
            'domain': domain,
            'status': 'unknown',
            'response_time': 0,
            'records': {},
            'errors': [],
            'dns_server_used': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # 尝试不同的DNS服务器
            for dns_server in self.dns_servers:
                try:
                    resolver = dns.resolver.Resolver()
                    resolver.nameservers = [dns_server]
                    resolver.timeout = self.dns_timeout
                    resolver.lifetime = self.dns_timeout
                    
                    # 检查各种记录类型
                    for record_type in record_types:
                        try:
                            answers = resolver.resolve(domain, record_type)
                            result['records'][record_type] = [str(rdata) for rdata in answers]
                        except dns.resolver.NoAnswer:
                            result['records'][record_type] = []
                        except dns.resolver.NXDOMAIN:
                            result['errors'].append(f'{record_type}: Domain does not exist')
                        except Exception as e:
                            result['errors'].append(f'{record_type}: {str(e)}')
                    
                    # 如果成功解析到任何记录，标记为成功
                    if any(result['records'].values()):
                        result['status'] = 'resolved'
                        result['dns_server_used'] = dns_server
                        break
                    
                except Exception as e:
                    result['errors'].append(f'DNS Server {dns_server}: {str(e)}')
                    continue
            
            # 如果所有DNS服务器都失败
            if result['status'] == 'unknown':
                result['status'] = 'failed'
            
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(f'General error: {str(e)}')
            logger.error(f"DNS解析失败 {domain}: {str(e)}")
        
        finally:
            result['response_time'] = int((time.time() - start_time) * 1000)  # 毫秒
        
        return result
    
    def validate_dns_configuration(self, domain: str) -> Dict[str, Any]:
        """
        验证DNS配置的正确性
        
        Args:
            domain: 域名
        
        Returns:
            DNS配置验证结果
        """
        result = {
            'domain': domain,
            'valid': False,
            'issues': [],
            'recommendations': [],
            'details': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # 检查A记录
            dns_result = self.check_domain_resolution(domain, ['A', 'AAAA', 'CNAME', 'MX', 'NS'])
            result['details'] = dns_result
            
            # 验证A记录
            if 'A' in dns_result['records'] and dns_result['records']['A']:
                result['valid'] = True
                # 检查A记录数量
                if len(dns_result['records']['A']) > 5:
                    result['issues'].append('A记录数量过多，可能影响解析性能')
            else:
                result['issues'].append('缺少A记录，域名无法解析到IPv4地址')
            
            # 检查AAAA记录（IPv6）
            if 'AAAA' in dns_result['records'] and dns_result['records']['AAAA']:
                result['recommendations'].append('已配置IPv6支持，有助于提高可访问性')
            else:
                result['recommendations'].append('建议配置AAAA记录以支持IPv6')
            
            # 检查CNAME记录
            if 'CNAME' in dns_result['records'] and dns_result['records']['CNAME']:
                if 'A' in dns_result['records'] and dns_result['records']['A']:
                    result['issues'].append('同时存在A记录和CNAME记录，可能导致解析冲突')
            
            # 检查NS记录
            if 'NS' in dns_result['records'] and dns_result['records']['NS']:
                ns_count = len(dns_result['records']['NS'])
                if ns_count < 2:
                    result['issues'].append('NS记录数量不足，建议至少配置2个权威DNS服务器')
                elif ns_count > 10:
                    result['issues'].append('NS记录数量过多，可能影响解析效率')
            
            # 检查解析时间
            if dns_result['response_time'] > 2000:  # 2秒
                result['issues'].append(f'DNS解析时间过长({dns_result["response_time"]}ms)，建议优化DNS配置')
            
        except Exception as e:
            result['issues'].append(f'DNS配置验证失败: {str(e)}')
            logger.error(f"DNS配置验证失败 {domain}: {str(e)}")
        
        return result
    
    def check_domain_reachability(self, domain: str, ports: List[int] = None, 
                                 protocols: List[str] = None) -> Dict[str, Any]:
        """
        检查域名可达性
        
        Args:
            domain: 域名
            ports: 端口列表，默认为[80, 443]
            protocols: 协议列表，默认为['http', 'https']
        
        Returns:
            可达性检查结果
        """
        if ports is None:
            ports = [80, 443]
        if protocols is None:
            protocols = ['http', 'https']
        
        start_time = time.time()
        result = {
            'domain': domain,
            'reachable': False,
            'response_time': 0,
            'http_checks': {},
            'port_checks': {},
            'ssl_info': {},
            'errors': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # HTTP/HTTPS可达性检查
            for protocol in protocols:
                url = f"{protocol}://{domain}"
                try:
                    response = requests.get(
                        url,
                        timeout=self.http_timeout,
                        allow_redirects=True,
                        verify=True if protocol == 'https' else False,
                        headers={
                            'User-Agent': 'SSL-Certificate-Manager/1.0 (Domain Monitor)'
                        }
                    )
                    
                    result['http_checks'][protocol] = {
                        'status_code': response.status_code,
                        'response_time': int(response.elapsed.total_seconds() * 1000),
                        'headers': dict(response.headers),
                        'final_url': response.url,
                        'success': 200 <= response.status_code < 400
                    }
                    
                    if result['http_checks'][protocol]['success']:
                        result['reachable'] = True
                    
                except requests.exceptions.SSLError as e:
                    result['http_checks'][protocol] = {
                        'error': f'SSL错误: {str(e)}',
                        'success': False
                    }
                    result['errors'].append(f'{protocol.upper()} SSL错误: {str(e)}')
                    
                except requests.exceptions.Timeout:
                    result['http_checks'][protocol] = {
                        'error': '请求超时',
                        'success': False
                    }
                    result['errors'].append(f'{protocol.upper()} 请求超时')
                    
                except Exception as e:
                    result['http_checks'][protocol] = {
                        'error': str(e),
                        'success': False
                    }
                    result['errors'].append(f'{protocol.upper()} 错误: {str(e)}')
            
            # 端口可达性检查
            for port in ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5.0)
                    port_start_time = time.time()
                    
                    connection_result = sock.connect_ex((domain, port))
                    port_response_time = int((time.time() - port_start_time) * 1000)
                    
                    result['port_checks'][port] = {
                        'open': connection_result == 0,
                        'response_time': port_response_time
                    }
                    
                    sock.close()
                    
                except Exception as e:
                    result['port_checks'][port] = {
                        'open': False,
                        'error': str(e)
                    }
            
        except Exception as e:
            result['errors'].append(f'可达性检查失败: {str(e)}')
            logger.error(f"域名可达性检查失败 {domain}: {str(e)}")
        
        finally:
            result['response_time'] = int((time.time() - start_time) * 1000)

        return result

    def perform_comprehensive_domain_check(self, certificate_id: int) -> Dict[str, Any]:
        """
        对证书域名执行综合检查

        Args:
            certificate_id: 证书ID

        Returns:
            综合检查结果
        """
        try:
            # 获取证书信息
            certificate = Certificate.get_by_id(certificate_id)
            if not certificate:
                return {'success': False, 'error': '证书不存在'}

            domain = certificate.domain

            # 执行DNS解析检查
            dns_result = self.check_domain_resolution(domain)

            # 执行DNS配置验证
            dns_validation = self.validate_dns_configuration(domain)

            # 执行可达性检查
            reachability_result = self.check_domain_reachability(domain)

            # 更新数据库
            self._update_certificate_domain_status(certificate_id, dns_result, reachability_result)

            # 检查并创建告警
            self._check_and_create_alerts(certificate_id, dns_result, reachability_result)

            # 综合结果
            result = {
                'success': True,
                'certificate_id': certificate_id,
                'domain': domain,
                'dns_check': dns_result,
                'dns_validation': dns_validation,
                'reachability_check': reachability_result,
                'overall_status': self._determine_overall_status(dns_result, reachability_result),
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"域名综合检查完成: {domain} - {result['overall_status']}")
            return result

        except Exception as e:
            logger.error(f"域名综合检查失败 {certificate_id}: {str(e)}")
            return {'success': False, 'error': f'检查失败: {str(e)}'}

    def batch_check_domains(self, certificate_ids: List[int], max_concurrent: int = 5) -> Dict[str, Any]:
        """
        批量检查域名状态

        Args:
            certificate_ids: 证书ID列表
            max_concurrent: 最大并发数

        Returns:
            批量检查结果
        """
        results = {
            'success': True,
            'total_count': len(certificate_ids),
            'success_count': 0,
            'failed_count': 0,
            'results': [],
            'errors': [],
            'timestamp': datetime.now().isoformat()
        }

        try:
            with ThreadPoolExecutor(max_workers=min(max_concurrent, self.max_workers)) as executor:
                # 提交所有任务
                future_to_cert_id = {
                    executor.submit(self.perform_comprehensive_domain_check, cert_id): cert_id
                    for cert_id in certificate_ids
                }

                # 收集结果
                for future in as_completed(future_to_cert_id):
                    cert_id = future_to_cert_id[future]
                    try:
                        result = future.result(timeout=30)  # 30秒超时
                        results['results'].append(result)

                        if result['success']:
                            results['success_count'] += 1
                        else:
                            results['failed_count'] += 1
                            results['errors'].append(f"证书 {cert_id}: {result['error']}")

                    except Exception as e:
                        results['failed_count'] += 1
                        error_msg = f"证书 {cert_id}: {str(e)}"
                        results['errors'].append(error_msg)
                        logger.error(f"批量检查失败 {cert_id}: {str(e)}")

            logger.info(f"批量域名检查完成: 成功 {results['success_count']}, 失败 {results['failed_count']}")

        except Exception as e:
            results['success'] = False
            results['errors'].append(f"批量检查失败: {str(e)}")
            logger.error(f"批量域名检查失败: {str(e)}")

        return results

    def get_domain_monitoring_statistics(self) -> Dict[str, Any]:
        """获取域名监控统计信息"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 统计DNS状态
            cursor.execute("""
                SELECT
                    dns_status,
                    COUNT(*) as count
                FROM certificates
                WHERE dns_status IS NOT NULL
                GROUP BY dns_status
            """)
            dns_stats = {row[0]: row[1] for row in cursor.fetchall()}

            # 统计可达性状态
            cursor.execute("""
                SELECT
                    domain_reachable,
                    COUNT(*) as count
                FROM certificates
                WHERE domain_reachable IS NOT NULL
                GROUP BY domain_reachable
            """)
            reachability_stats = cursor.fetchall()

            # 统计平均响应时间
            cursor.execute("""
                SELECT
                    AVG(dns_response_time) as avg_dns_time,
                    AVG(CASE WHEN http_status_code BETWEEN 200 AND 299 THEN dns_response_time END) as avg_success_time
                FROM certificates
                WHERE dns_response_time IS NOT NULL
            """)
            timing_stats = cursor.fetchone()

            # 统计最近检查时间
            cursor.execute("""
                SELECT
                    COUNT(CASE WHEN last_dns_check > datetime('now', '-1 hour') THEN 1 END) as recent_dns_checks,
                    COUNT(CASE WHEN last_reachability_check > datetime('now', '-1 hour') THEN 1 END) as recent_reachability_checks
                FROM certificates
            """)
            recent_stats = cursor.fetchone()

            return {
                'success': True,
                'statistics': {
                    'dns_status_distribution': dns_stats,
                    'reachability_distribution': {
                        'reachable': sum(1 for row in reachability_stats if row[0] == 1),
                        'unreachable': sum(1 for row in reachability_stats if row[0] == 0)
                    },
                    'average_dns_response_time': round(timing_stats[0] or 0, 2),
                    'average_success_response_time': round(timing_stats[1] or 0, 2),
                    'recent_checks': {
                        'dns_checks_last_hour': recent_stats[0],
                        'reachability_checks_last_hour': recent_stats[1]
                    }
                }
            }

        except Exception as e:
            logger.error(f"获取域名监控统计失败: {str(e)}")
            return {'success': False, 'error': f'获取统计失败: {str(e)}'}
        finally:
            if 'conn' in locals():
                conn.close()

    def _update_certificate_domain_status(self, certificate_id: int, dns_result: Dict[str, Any],
                                         reachability_result: Dict[str, Any]) -> None:
        """更新证书的域名状态信息"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 确定HTTP状态码
            http_status_code = None
            if 'http_checks' in reachability_result:
                for protocol, check in reachability_result['http_checks'].items():
                    if 'status_code' in check:
                        http_status_code = check['status_code']
                        break

            cursor.execute("""
                UPDATE certificates SET
                    dns_status = ?,
                    dns_response_time = ?,
                    domain_reachable = ?,
                    http_status_code = ?,
                    last_dns_check = CURRENT_TIMESTAMP,
                    last_reachability_check = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                dns_result['status'],
                dns_result['response_time'],
                reachability_result['reachable'],
                http_status_code,
                certificate_id
            ))

            conn.commit()

        except Exception as e:
            logger.error(f"更新证书域名状态失败 {certificate_id}: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'conn' in locals():
                conn.close()

    def _determine_overall_status(self, dns_result: Dict[str, Any],
                                 reachability_result: Dict[str, Any]) -> str:
        """确定整体状态"""
        if dns_result['status'] == 'resolved' and reachability_result['reachable']:
            return 'healthy'
        elif dns_result['status'] == 'resolved' and not reachability_result['reachable']:
            return 'dns_ok_unreachable'
        elif dns_result['status'] != 'resolved' and reachability_result['reachable']:
            return 'dns_failed_reachable'
        else:
            return 'unhealthy'

    def _check_and_create_alerts(self, certificate_id: int, dns_result: Dict[str, Any],
                                reachability_result: Dict[str, Any]) -> None:
        """检查并创建告警"""
        try:
            # 检查DNS解析失败告警
            if dns_result['status'] != 'resolved':
                self._create_dns_failure_alert(certificate_id, dns_result)

            # 检查域名不可达告警
            if not reachability_result['reachable']:
                self._create_unreachable_alert(certificate_id, reachability_result)

            # 检查响应时间告警
            if dns_result.get('response_time', 0) > 5000:  # 5秒阈值
                self._create_slow_response_alert(certificate_id, dns_result['response_time'])

        except Exception as e:
            logger.error(f"创建域名监控告警失败 {certificate_id}: {str(e)}")

    def _create_dns_failure_alert(self, certificate_id: int, dns_result: Dict[str, Any]) -> None:
        """创建DNS解析失败告警"""
        try:
            # 检查是否已存在相同类型的活跃告警
            existing_alert = self._get_active_alert(certificate_id, 'dns_failure')
            if existing_alert:
                return  # 已存在告警，不重复创建

            # 构建告警消息
            errors = ', '.join(dns_result.get('errors', []))
            message = f"DNS解析失败: {dns_result['status']}"
            if errors:
                message += f" - {errors}"

            # 创建告警
            alert = Alert.create(
                certificate_id=certificate_id,
                alert_type='dns_failure',
                message=message,
                severity='high'
            )

            logger.warning(f"创建DNS解析失败告警: 证书 {certificate_id}")

        except Exception as e:
            logger.error(f"创建DNS解析失败告警失败 {certificate_id}: {str(e)}")

    def _create_unreachable_alert(self, certificate_id: int, reachability_result: Dict[str, Any]) -> None:
        """创建域名不可达告警"""
        try:
            # 检查是否已存在相同类型的活跃告警
            existing_alert = self._get_active_alert(certificate_id, 'domain_unreachable')
            if existing_alert:
                return  # 已存在告警，不重复创建

            # 构建告警消息
            errors = ', '.join(reachability_result.get('errors', []))
            message = "域名不可达"
            if errors:
                message += f": {errors}"

            # 创建告警
            alert = Alert.create(
                certificate_id=certificate_id,
                alert_type='domain_unreachable',
                message=message,
                severity='high'
            )

            logger.warning(f"创建域名不可达告警: 证书 {certificate_id}")

        except Exception as e:
            logger.error(f"创建域名不可达告警失败 {certificate_id}: {str(e)}")

    def _create_slow_response_alert(self, certificate_id: int, response_time: int) -> None:
        """创建响应时间过慢告警"""
        try:
            # 检查是否已存在相同类型的活跃告警
            existing_alert = self._get_active_alert(certificate_id, 'slow_response')
            if existing_alert:
                return  # 已存在告警，不重复创建

            # 创建告警
            alert = Alert.create(
                certificate_id=certificate_id,
                alert_type='slow_response',
                message=f"DNS响应时间过慢: {response_time}ms",
                severity='medium'
            )

            logger.warning(f"创建响应时间过慢告警: 证书 {certificate_id}, 响应时间 {response_time}ms")

        except Exception as e:
            logger.error(f"创建响应时间过慢告警失败 {certificate_id}: {str(e)}")

    def _get_active_alert(self, certificate_id: int, alert_type: str) -> Optional[Dict[str, Any]]:
        """获取活跃的告警"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, type, message, severity, status, created_at
                FROM alerts
                WHERE certificate_id = ? AND type = ? AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
            """, (certificate_id, alert_type))

            result = cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'type': result[1],
                    'message': result[2],
                    'severity': result[3],
                    'status': result[4],
                    'created_at': result[5]
                }

            return None

        except Exception as e:
            logger.error(f"获取活跃告警失败 {certificate_id}: {str(e)}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    def resolve_domain_alerts(self, certificate_id: int) -> None:
        """解决域名相关告警"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 将域名相关的活跃告警标记为已解决
            cursor.execute("""
                UPDATE alerts SET
                    status = 'resolved',
                    updated_at = CURRENT_TIMESTAMP
                WHERE certificate_id = ?
                AND type IN ('dns_failure', 'domain_unreachable', 'slow_response')
                AND status = 'active'
            """, (certificate_id,))

            conn.commit()
            logger.info(f"解决证书 {certificate_id} 的域名相关告警")

        except Exception as e:
            logger.error(f"解决域名告警失败 {certificate_id}: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'conn' in locals():
                conn.close()

    def get_monitoring_list(self, page: int = 1, limit: int = 20,
                          keyword: str = None, status: str = None,
                          user_id: int = None) -> Dict[str, Any]:
        """获取监控列表"""
        try:
            # 模拟数据
            mock_data = [
                {
                    'id': 1,
                    'domain': 'example.com',
                    'cert_level': 'DV',
                    'encryption_type': 'RSA',
                    'port': 443,
                    'ip_type': 'IPv4',
                    'ip_address': '192.168.1.100',
                    'status': 'normal',
                    'days_left': 45,
                    'monitoring_enabled': True,
                    'description': '主站点监控',
                    'user_id': 1,
                    'created_at': '2025-01-01 10:00:00',
                    'updated_at': '2025-01-10 10:00:00'
                },
                {
                    'id': 2,
                    'domain': 'api.example.com',
                    'cert_level': 'OV',
                    'encryption_type': 'ECC',
                    'port': 443,
                    'ip_type': 'IPv4',
                    'ip_address': '192.168.1.101',
                    'status': 'warning',
                    'days_left': 10,
                    'monitoring_enabled': True,
                    'description': 'API接口监控',
                    'user_id': 1,
                    'created_at': '2025-01-01 10:00:00',
                    'updated_at': '2025-01-10 10:00:00'
                }
            ]

            # 过滤数据
            filtered_data = mock_data
            if keyword:
                filtered_data = [item for item in filtered_data
                               if keyword.lower() in item['domain'].lower()]
            if status:
                filtered_data = [item for item in filtered_data
                               if item['status'] == status]
            if user_id:
                filtered_data = [item for item in filtered_data
                               if item['user_id'] == user_id]

            # 分页
            start = (page - 1) * limit
            end = start + limit
            items = filtered_data[start:end]

            return {
                'total': len(filtered_data),
                'items': items
            }

        except Exception as e:
            logger.error(f"获取监控列表失败: {e}")
            raise

    def create_monitoring_config(self, domain: str, port: int = 443,
                               ip_type: str = 'ipv4', ip_address: str = None,
                               monitoring_enabled: bool = True,
                               description: str = '', user_id: int = None) -> Dict[str, Any]:
        """创建监控配置"""
        try:
            # 验证域名格式
            if not self._validate_domain_format(domain):
                return {
                    'success': False,
                    'error': '域名格式不正确'
                }

            # 检查域名是否已存在
            existing = self._check_domain_exists_for_user(domain, user_id)
            if existing:
                return {
                    'success': False,
                    'error': '该域名已存在监控配置'
                }

            # 创建监控配置
            monitoring_config = {
                'id': 3,  # 模拟新ID
                'domain': domain,
                'port': port,
                'ip_type': ip_type,
                'ip_address': ip_address,
                'monitoring_enabled': monitoring_enabled,
                'description': description,
                'user_id': user_id,
                'status': 'unknown',
                'days_left': 0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }

            # 如果启用监控，立即执行一次检测
            if monitoring_enabled:
                check_result = self._perform_ssl_check_simple(domain, port)
                monitoring_config.update({
                    'status': check_result['status'],
                    'days_left': check_result['days_left'],
                    'cert_level': check_result.get('cert_level', 'DV'),
                    'encryption_type': check_result.get('encryption_type', 'RSA')
                })

            return {
                'success': True,
                'monitoring_config': monitoring_config
            }

        except Exception as e:
            logger.error(f"创建监控配置失败: {e}")
            return {
                'success': False,
                'error': f'创建监控配置失败: {str(e)}'
            }

    def get_monitoring_detail(self, monitoring_id: int) -> Dict[str, Any]:
        """获取监控详情"""
        try:
            # 模拟获取详情
            if monitoring_id == 1:
                monitoring_config = {
                    'id': 1,
                    'domain': 'example.com',
                    'cert_level': 'DV',
                    'encryption_type': 'RSA',
                    'port': 443,
                    'ip_type': 'IPv4',
                    'ip_address': '192.168.1.100',
                    'status': 'normal',
                    'days_left': 45,
                    'monitoring_enabled': True,
                    'description': '主站点监控',
                    'user_id': 1,
                    'created_at': '2025-01-01 10:00:00',
                    'updated_at': '2025-01-10 10:00:00'
                }
                return {
                    'success': True,
                    'monitoring_config': monitoring_config
                }
            else:
                return {
                    'success': False,
                    'error': '监控配置不存在'
                }

        except Exception as e:
            logger.error(f"获取监控详情失败: {e}")
            return {
                'success': False,
                'error': f'获取监控详情失败: {str(e)}'
            }

    def update_monitoring_config(self, monitoring_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新监控配置"""
        try:
            # 模拟更新
            monitoring_config = {
                'id': monitoring_id,
                'domain': 'example.com',
                'monitoring_enabled': data.get('monitoring_enabled', True),
                'description': data.get('description', ''),
                'updated_at': datetime.now().isoformat()
            }

            return {
                'success': True,
                'monitoring_config': monitoring_config
            }

        except Exception as e:
            logger.error(f"更新监控配置失败: {e}")
            return {
                'success': False,
                'error': f'更新监控配置失败: {str(e)}'
            }

    def delete_monitoring_config(self, monitoring_id: int) -> Dict[str, Any]:
        """删除监控配置"""
        try:
            # 模拟删除
            return {
                'success': True,
                'message': '监控配置已删除'
            }

        except Exception as e:
            logger.error(f"删除监控配置失败: {e}")
            return {
                'success': False,
                'error': f'删除监控配置失败: {str(e)}'
            }

    def perform_immediate_check(self, monitoring_id: int) -> Dict[str, Any]:
        """执行立即检测"""
        try:
            # 获取监控配置
            detail_result = self.get_monitoring_detail(monitoring_id)
            if not detail_result['success']:
                return detail_result

            monitoring_config = detail_result['monitoring_config']
            domain = monitoring_config['domain']
            port = monitoring_config['port']

            # 执行SSL检测
            check_result = self._perform_ssl_check_simple(domain, port)

            return {
                'success': True,
                'check_result': check_result
            }

        except Exception as e:
            logger.error(f"立即检测失败: {e}")
            return {
                'success': False,
                'error': f'立即检测失败: {str(e)}'
            }

    def get_monitoring_history(self, monitoring_id: int, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """获取监控历史"""
        try:
            # 模拟历史数据
            mock_history = [
                {
                    'id': 1,
                    'check_time': '2025-01-10 10:00:00',
                    'status': 'normal',
                    'days_left': 45,
                    'response_time': 120,
                    'ssl_version': 'TLSv1.3',
                    'message': '证书正常'
                },
                {
                    'id': 2,
                    'check_time': '2025-01-09 10:00:00',
                    'status': 'normal',
                    'days_left': 46,
                    'response_time': 115,
                    'ssl_version': 'TLSv1.3',
                    'message': '证书正常'
                },
                {
                    'id': 3,
                    'check_time': '2025-01-08 10:00:00',
                    'status': 'warning',
                    'days_left': 47,
                    'response_time': 200,
                    'ssl_version': 'TLSv1.2',
                    'message': '响应时间较慢'
                }
            ]

            # 分页
            start = (page - 1) * limit
            end = start + limit
            items = mock_history[start:end]

            return {
                'success': True,
                'total': len(mock_history),
                'history': items
            }

        except Exception as e:
            logger.error(f"获取监控历史失败: {e}")
            return {
                'success': False,
                'error': f'获取监控历史失败: {str(e)}'
            }

    def _validate_domain_format(self, domain: str) -> bool:
        """验证域名格式"""
        import re
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(pattern, domain))

    def _check_domain_exists_for_user(self, domain: str, user_id: int) -> bool:
        """检查域名是否已存在"""
        # 模拟检查
        return False

    def _perform_ssl_check_simple(self, domain: str, port: int) -> Dict[str, Any]:
        """执行简单的SSL检测"""
        try:
            import random

            # 模拟SSL检测
            statuses = ['normal', 'warning', 'error']
            status = random.choice(statuses)

            if status == 'normal':
                days_left = random.randint(30, 90)
            elif status == 'warning':
                days_left = random.randint(7, 29)
            else:
                days_left = random.randint(0, 6)

            return {
                'status': status,
                'days_left': days_left,
                'response_time': random.randint(50, 300),
                'ssl_version': random.choice(['TLSv1.2', 'TLSv1.3']),
                'cert_level': random.choice(['DV', 'OV', 'EV']),
                'encryption_type': random.choice(['RSA', 'ECC']),
                'message': '证书检测完成'
            }

        except Exception as e:
            logger.error(f"SSL检测失败: {e}")
            return {
                'status': 'error',
                'days_left': 0,
                'response_time': 0,
                'ssl_version': 'unknown',
                'message': f'检测失败: {str(e)}'
            }


# 全局域名监控服务实例
domain_monitoring_service = DomainMonitoringService()
