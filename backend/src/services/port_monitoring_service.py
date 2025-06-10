"""
SSL证书端口监控服务
提供SSL端口检查、TLS协议检测、证书链验证等功能
"""

import ssl
import socket
import time
import logging
import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID
import requests

from models.certificate import Certificate
from models.database import Database
from models.alert import Alert

logger = logging.getLogger(__name__)

class PortMonitoringService:
    """端口监控服务"""
    
    def __init__(self):
        self.db = Database()
        # 默认监控端口
        self.default_ports = [80, 443]
        # SSL/TLS配置
        self.ssl_timeout = 10.0
        self.socket_timeout = 5.0
        self.max_workers = 5
        
        # TLS协议版本映射
        self.tls_versions = {
            ssl.PROTOCOL_TLS: 'TLS',
            ssl.PROTOCOL_TLSv1: 'TLS 1.0',
            ssl.PROTOCOL_TLSv1_1: 'TLS 1.1',
            ssl.PROTOCOL_TLSv1_2: 'TLS 1.2',
        }
        
        # 弱加密套件列表
        self.weak_ciphers = [
            'RC4', 'DES', '3DES', 'MD5', 'SHA1', 'NULL', 'EXPORT', 'ADH', 'AECDH'
        ]
    
    def check_ssl_port(self, domain: str, port: int = 443) -> Dict[str, Any]:
        """
        检查SSL端口状态
        
        Args:
            domain: 域名
            port: 端口号，默认443
        
        Returns:
            SSL端口检查结果
        """
        start_time = time.time()
        result = {
            'domain': domain,
            'port': port,
            'ssl_enabled': False,
            'handshake_time': 0,
            'tls_version': None,
            'cipher_suite': None,
            'certificate_details': {},
            'certificate_chain_valid': False,
            'security_grade': 'F',
            'errors': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # 创建SSL上下文
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # 建立SSL连接
            with socket.create_connection((domain, port), timeout=self.socket_timeout) as sock:
                handshake_start = time.time()
                
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    handshake_time = int((time.time() - handshake_start) * 1000)
                    result['handshake_time'] = handshake_time
                    result['ssl_enabled'] = True
                    
                    # 获取TLS版本
                    result['tls_version'] = ssock.version()
                    
                    # 获取加密套件
                    result['cipher_suite'] = ssock.cipher()[0] if ssock.cipher() else None
                    
                    # 获取证书
                    cert_der = ssock.getpeercert_chain()[0] if ssock.getpeercert_chain() else None
                    if cert_der:
                        result['certificate_details'] = self.extract_certificate_details(cert_der)
                        result['certificate_chain_valid'] = self._validate_certificate_chain(ssock)
                    
                    # 计算安全等级
                    result['security_grade'] = self._calculate_security_grade(result)
            
        except ssl.SSLError as e:
            result['errors'].append(f'SSL错误: {str(e)}')
            logger.warning(f"SSL连接失败 {domain}:{port} - {str(e)}")
            
        except socket.timeout:
            result['errors'].append('连接超时')
            logger.warning(f"连接超时 {domain}:{port}")
            
        except socket.gaierror as e:
            result['errors'].append(f'域名解析失败: {str(e)}')
            logger.warning(f"域名解析失败 {domain}:{port} - {str(e)}")
            
        except Exception as e:
            result['errors'].append(f'连接失败: {str(e)}')
            logger.error(f"端口检查失败 {domain}:{port} - {str(e)}")
        
        finally:
            result['response_time'] = int((time.time() - start_time) * 1000)
        
        return result
    
    def check_http_redirect(self, domain: str, port: int = 80) -> Dict[str, Any]:
        """
        检查HTTP到HTTPS重定向
        
        Args:
            domain: 域名
            port: HTTP端口，默认80
        
        Returns:
            HTTP重定向检查结果
        """
        result = {
            'domain': domain,
            'port': port,
            'redirect_enabled': False,
            'redirect_target': None,
            'redirect_status_code': None,
            'redirect_type': None,  # permanent/temporary
            'hsts_enabled': False,
            'hsts_max_age': None,
            'errors': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            url = f"http://{domain}:{port}" if port != 80 else f"http://{domain}"
            
            response = requests.get(
                url,
                timeout=self.ssl_timeout,
                allow_redirects=False,
                headers={'User-Agent': 'SSL-Certificate-Manager/1.0 (Port Monitor)'}
            )
            
            result['redirect_status_code'] = response.status_code
            
            # 检查重定向
            if response.status_code in [301, 302, 303, 307, 308]:
                location = response.headers.get('Location', '')
                if location.startswith('https://'):
                    result['redirect_enabled'] = True
                    result['redirect_target'] = location
                    result['redirect_type'] = 'permanent' if response.status_code in [301, 308] else 'temporary'
            
            # 检查HSTS头
            hsts_header = response.headers.get('Strict-Transport-Security')
            if hsts_header:
                result['hsts_enabled'] = True
                # 解析max-age
                for directive in hsts_header.split(';'):
                    directive = directive.strip()
                    if directive.startswith('max-age='):
                        try:
                            result['hsts_max_age'] = int(directive.split('=')[1])
                        except (ValueError, IndexError):
                            pass
            
        except requests.exceptions.Timeout:
            result['errors'].append('HTTP请求超时')
            
        except requests.exceptions.ConnectionError as e:
            result['errors'].append(f'HTTP连接失败: {str(e)}')
            
        except Exception as e:
            result['errors'].append(f'HTTP检查失败: {str(e)}')
            logger.error(f"HTTP重定向检查失败 {domain}:{port} - {str(e)}")
        
        return result
    
    def extract_certificate_details(self, cert_der: bytes) -> Dict[str, Any]:
        """
        从DER格式证书中提取详细信息
        
        Args:
            cert_der: DER格式的证书数据
        
        Returns:
            证书详细信息
        """
        try:
            cert = x509.load_der_x509_certificate(cert_der, default_backend())
            
            # 基本信息
            subject = cert.subject
            issuer = cert.issuer
            
            # 提取主题信息
            subject_dict = {}
            for attribute in subject:
                oid_name = attribute.oid._name
                subject_dict[oid_name] = attribute.value
            
            # 提取颁发者信息
            issuer_dict = {}
            for attribute in issuer:
                oid_name = attribute.oid._name
                issuer_dict[oid_name] = attribute.value
            
            # SAN扩展
            san_list = []
            try:
                san_ext = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                san_list = [name.value for name in san_ext.value]
            except x509.ExtensionNotFound:
                pass
            
            # 计算指纹
            sha1_fingerprint = hashlib.sha1(cert_der).hexdigest().upper()
            sha256_fingerprint = hashlib.sha256(cert_der).hexdigest().upper()
            
            # 密钥信息
            public_key = cert.public_key()
            key_size = public_key.key_size if hasattr(public_key, 'key_size') else None
            key_type = type(public_key).__name__
            
            return {
                'subject': subject_dict,
                'issuer': issuer_dict,
                'serial_number': str(cert.serial_number),
                'not_valid_before': cert.not_valid_before.isoformat(),
                'not_valid_after': cert.not_valid_after.isoformat(),
                'signature_algorithm': cert.signature_algorithm_oid._name,
                'public_key_type': key_type,
                'public_key_size': key_size,
                'san_list': san_list,
                'sha1_fingerprint': sha1_fingerprint,
                'sha256_fingerprint': sha256_fingerprint,
                'version': cert.version.name
            }
            
        except Exception as e:
            logger.error(f"证书详细信息提取失败: {str(e)}")
            return {'error': f'证书解析失败: {str(e)}'}
    
    def check_custom_ports(self, domain: str, ports: List[int]) -> Dict[str, Any]:
        """
        检查自定义端口列表
        
        Args:
            domain: 域名
            ports: 端口列表
        
        Returns:
            自定义端口检查结果
        """
        result = {
            'domain': domain,
            'ports_checked': len(ports),
            'ssl_ports': [],
            'non_ssl_ports': [],
            'failed_ports': [],
            'port_details': {},
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(ports))) as executor:
                # 提交检查任务
                future_to_port = {
                    executor.submit(self._check_single_port, domain, port): port
                    for port in ports
                }
                
                # 收集结果
                for future in as_completed(future_to_port):
                    port = future_to_port[future]
                    try:
                        port_result = future.result(timeout=15)
                        result['port_details'][port] = port_result
                        
                        if port_result.get('ssl_enabled'):
                            result['ssl_ports'].append(port)
                        elif port_result.get('errors'):
                            result['failed_ports'].append(port)
                        else:
                            result['non_ssl_ports'].append(port)
                            
                    except Exception as e:
                        result['failed_ports'].append(port)
                        result['port_details'][port] = {
                            'port': port,
                            'ssl_enabled': False,
                            'errors': [f'检查失败: {str(e)}']
                        }
                        logger.error(f"端口 {port} 检查失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"自定义端口检查失败 {domain}: {str(e)}")
            result['error'] = f'批量检查失败: {str(e)}'
        
        return result
    
    def _check_single_port(self, domain: str, port: int) -> Dict[str, Any]:
        """检查单个端口"""
        # 首先检查端口是否开放
        try:
            with socket.create_connection((domain, port), timeout=self.socket_timeout):
                pass
        except (socket.timeout, socket.error):
            return {
                'port': port,
                'ssl_enabled': False,
                'errors': ['端口不可达']
            }
        
        # 如果是HTTP端口，检查重定向
        if port in [80, 8080]:
            return self.check_http_redirect(domain, port)
        
        # 否则尝试SSL连接
        return self.check_ssl_port(domain, port)

    def _validate_certificate_chain(self, ssl_socket) -> bool:
        """验证证书链完整性"""
        try:
            cert_chain = ssl_socket.getpeercert_chain()
            return len(cert_chain) > 1  # 至少有服务器证书和中间证书
        except Exception:
            return False

    def _calculate_security_grade(self, ssl_result: Dict[str, Any]) -> str:
        """
        计算SSL安全等级

        Args:
            ssl_result: SSL检查结果

        Returns:
            安全等级 (A+, A, B, C, D, F)
        """
        if not ssl_result.get('ssl_enabled'):
            return 'F'

        score = 100

        # TLS版本评分
        tls_version = ssl_result.get('tls_version', '')
        if 'TLS 1.3' in tls_version:
            score += 0  # 最高分
        elif 'TLS 1.2' in tls_version:
            score -= 5
        elif 'TLS 1.1' in tls_version:
            score -= 20
        elif 'TLS 1.0' in tls_version:
            score -= 30
        else:
            score -= 50

        # 加密套件评分
        cipher_suite = ssl_result.get('cipher_suite', '')
        if any(weak in cipher_suite.upper() for weak in self.weak_ciphers):
            score -= 30

        # 证书链评分
        if not ssl_result.get('certificate_chain_valid'):
            score -= 20

        # 握手时间评分
        handshake_time = ssl_result.get('handshake_time', 0)
        if handshake_time > 3000:  # 3秒
            score -= 10
        elif handshake_time > 1000:  # 1秒
            score -= 5

        # 转换为等级
        if score >= 95:
            return 'A+'
        elif score >= 85:
            return 'A'
        elif score >= 75:
            return 'B'
        elif score >= 65:
            return 'C'
        elif score >= 50:
            return 'D'
        else:
            return 'F'

    def perform_comprehensive_port_check(self, certificate_id: int) -> Dict[str, Any]:
        """
        对证书执行综合端口检查

        Args:
            certificate_id: 证书ID

        Returns:
            综合端口检查结果
        """
        try:
            # 获取证书信息
            certificate = Certificate.get_by_id(certificate_id)
            if not certificate:
                return {'success': False, 'error': '证书不存在'}

            domain = certificate.domain

            # 获取监控端口列表
            monitored_ports = self._get_monitored_ports(certificate_id)

            # 检查SSL端口
            ssl_results = {}
            for port in monitored_ports:
                if port != 80:  # 80端口单独处理
                    ssl_results[port] = self.check_ssl_port(domain, port)

            # 检查HTTP重定向
            http_redirect_result = self.check_http_redirect(domain, 80)

            # 更新数据库
            self._update_certificate_port_status(certificate_id, ssl_results, http_redirect_result)

            # 检查并创建告警
            self._check_and_create_port_alerts(certificate_id, ssl_results, http_redirect_result)

            # 综合结果
            result = {
                'success': True,
                'certificate_id': certificate_id,
                'domain': domain,
                'ssl_checks': ssl_results,
                'http_redirect_check': http_redirect_result,
                'monitored_ports': monitored_ports,
                'overall_security_grade': self._calculate_overall_security_grade(ssl_results),
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"端口综合检查完成: {domain} - {result['overall_security_grade']}")
            return result

        except Exception as e:
            logger.error(f"端口综合检查失败 {certificate_id}: {str(e)}")
            return {'success': False, 'error': f'检查失败: {str(e)}'}

    def _get_monitored_ports(self, certificate_id: int) -> List[int]:
        """获取证书的监控端口列表"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT monitored_ports FROM certificates WHERE id = ?
            """, (certificate_id,))

            result = cursor.fetchone()
            if result and result[0]:
                try:
                    return json.loads(result[0])
                except (json.JSONDecodeError, TypeError):
                    pass

            # 返回默认端口
            return self.default_ports

        except Exception as e:
            logger.error(f"获取监控端口失败 {certificate_id}: {str(e)}")
            return self.default_ports
        finally:
            if 'conn' in locals():
                conn.close()

    def configure_monitored_ports(self, certificate_id: int, ports: List[int]) -> Dict[str, Any]:
        """
        配置证书的监控端口

        Args:
            certificate_id: 证书ID
            ports: 端口列表

        Returns:
            配置结果
        """
        try:
            # 验证端口范围
            valid_ports = [port for port in ports if 1 <= port <= 65535]
            if len(valid_ports) != len(ports):
                return {'success': False, 'error': '端口范围必须在1-65535之间'}

            # 限制端口数量
            if len(valid_ports) > 20:
                return {'success': False, 'error': '监控端口数量不能超过20个'}

            conn = self.db.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE certificates SET
                    monitored_ports = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (json.dumps(valid_ports), certificate_id))

            conn.commit()

            logger.info(f"更新证书 {certificate_id} 监控端口: {valid_ports}")

            return {
                'success': True,
                'message': '监控端口配置成功',
                'monitored_ports': valid_ports
            }

        except Exception as e:
            logger.error(f"配置监控端口失败 {certificate_id}: {str(e)}")
            return {'success': False, 'error': f'配置失败: {str(e)}'}
        finally:
            if 'conn' in locals():
                conn.close()

    def batch_check_ports(self, certificate_ids: List[int], max_concurrent: int = 3) -> Dict[str, Any]:
        """
        批量检查证书端口

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
                    executor.submit(self.perform_comprehensive_port_check, cert_id): cert_id
                    for cert_id in certificate_ids
                }

                # 收集结果
                for future in as_completed(future_to_cert_id):
                    cert_id = future_to_cert_id[future]
                    try:
                        result = future.result(timeout=60)  # 60秒超时
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
                        logger.error(f"批量端口检查失败 {cert_id}: {str(e)}")

            logger.info(f"批量端口检查完成: 成功 {results['success_count']}, 失败 {results['failed_count']}")

        except Exception as e:
            results['success'] = False
            results['errors'].append(f"批量检查失败: {str(e)}")
            logger.error(f"批量端口检查失败: {str(e)}")

        return results

    def _calculate_overall_security_grade(self, ssl_results: Dict[int, Dict[str, Any]]) -> str:
        """计算整体安全等级"""
        if not ssl_results:
            return 'F'

        grades = [result.get('security_grade', 'F') for result in ssl_results.values()]
        grade_scores = {'A+': 100, 'A': 90, 'B': 80, 'C': 70, 'D': 60, 'F': 0}

        # 计算平均分
        total_score = sum(grade_scores.get(grade, 0) for grade in grades)
        avg_score = total_score / len(grades)

        # 转换回等级
        for grade, score in sorted(grade_scores.items(), key=lambda x: x[1], reverse=True):
            if avg_score >= score:
                return grade
        return 'F'

    def _update_certificate_port_status(self, certificate_id: int, ssl_results: Dict[int, Dict[str, Any]],
                                       http_redirect_result: Dict[str, Any]) -> None:
        """更新证书的端口状态信息"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 提取主要SSL端口(443)的信息
            main_ssl_result = ssl_results.get(443, {})

            cursor.execute("""
                UPDATE certificates SET
                    ssl_handshake_time = ?,
                    tls_version = ?,
                    cipher_suite = ?,
                    certificate_chain_valid = ?,
                    http_redirect_status = ?,
                    last_port_check = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                main_ssl_result.get('handshake_time'),
                main_ssl_result.get('tls_version'),
                main_ssl_result.get('cipher_suite'),
                main_ssl_result.get('certificate_chain_valid'),
                'enabled' if http_redirect_result.get('redirect_enabled') else 'disabled',
                certificate_id
            ))

            conn.commit()

        except Exception as e:
            logger.error(f"更新证书端口状态失败 {certificate_id}: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'conn' in locals():
                conn.close()

    def _check_and_create_port_alerts(self, certificate_id: int, ssl_results: Dict[int, Dict[str, Any]],
                                     http_redirect_result: Dict[str, Any]) -> None:
        """检查并创建端口相关告警"""
        try:
            # 检查SSL端口不可达告警
            for port, result in ssl_results.items():
                if not result.get('ssl_enabled') and result.get('errors'):
                    self._create_port_unreachable_alert(certificate_id, port, result['errors'])

            # 检查TLS版本过时告警
            for port, result in ssl_results.items():
                tls_version = result.get('tls_version', '')
                if 'TLS 1.0' in tls_version or 'TLS 1.1' in tls_version:
                    self._create_outdated_tls_alert(certificate_id, port, tls_version)

            # 检查弱加密套件告警
            for port, result in ssl_results.items():
                cipher_suite = result.get('cipher_suite', '')
                if any(weak in cipher_suite.upper() for weak in self.weak_ciphers):
                    self._create_weak_cipher_alert(certificate_id, port, cipher_suite)

            # 检查证书链不完整告警
            for port, result in ssl_results.items():
                if result.get('ssl_enabled') and not result.get('certificate_chain_valid'):
                    self._create_incomplete_chain_alert(certificate_id, port)

            # 检查HTTP重定向告警
            if not http_redirect_result.get('redirect_enabled'):
                self._create_no_https_redirect_alert(certificate_id)

        except Exception as e:
            logger.error(f"创建端口告警失败 {certificate_id}: {str(e)}")

    def _create_port_unreachable_alert(self, certificate_id: int, port: int, errors: List[str]) -> None:
        """创建端口不可达告警"""
        try:
            existing_alert = self._get_active_alert(certificate_id, f'port_unreachable_{port}')
            if existing_alert:
                return

            message = f"端口 {port} 不可达: {', '.join(errors)}"
            Alert.create(
                certificate_id=certificate_id,
                alert_type=f'port_unreachable_{port}',
                message=message,
                severity='high'
            )
            logger.warning(f"创建端口不可达告警: 证书 {certificate_id}, 端口 {port}")

        except Exception as e:
            logger.error(f"创建端口不可达告警失败: {str(e)}")

    def _create_outdated_tls_alert(self, certificate_id: int, port: int, tls_version: str) -> None:
        """创建TLS版本过时告警"""
        try:
            existing_alert = self._get_active_alert(certificate_id, f'outdated_tls_{port}')
            if existing_alert:
                return

            message = f"端口 {port} 使用过时的TLS版本: {tls_version}"
            Alert.create(
                certificate_id=certificate_id,
                alert_type=f'outdated_tls_{port}',
                message=message,
                severity='medium'
            )
            logger.warning(f"创建TLS版本过时告警: 证书 {certificate_id}, 端口 {port}")

        except Exception as e:
            logger.error(f"创建TLS版本过时告警失败: {str(e)}")

    def _create_weak_cipher_alert(self, certificate_id: int, port: int, cipher_suite: str) -> None:
        """创建弱加密套件告警"""
        try:
            existing_alert = self._get_active_alert(certificate_id, f'weak_cipher_{port}')
            if existing_alert:
                return

            message = f"端口 {port} 使用弱加密套件: {cipher_suite}"
            Alert.create(
                certificate_id=certificate_id,
                alert_type=f'weak_cipher_{port}',
                message=message,
                severity='medium'
            )
            logger.warning(f"创建弱加密套件告警: 证书 {certificate_id}, 端口 {port}")

        except Exception as e:
            logger.error(f"创建弱加密套件告警失败: {str(e)}")

    def _create_incomplete_chain_alert(self, certificate_id: int, port: int) -> None:
        """创建证书链不完整告警"""
        try:
            existing_alert = self._get_active_alert(certificate_id, f'incomplete_chain_{port}')
            if existing_alert:
                return

            message = f"端口 {port} 证书链不完整"
            Alert.create(
                certificate_id=certificate_id,
                alert_type=f'incomplete_chain_{port}',
                message=message,
                severity='medium'
            )
            logger.warning(f"创建证书链不完整告警: 证书 {certificate_id}, 端口 {port}")

        except Exception as e:
            logger.error(f"创建证书链不完整告警失败: {str(e)}")

    def _create_no_https_redirect_alert(self, certificate_id: int) -> None:
        """创建无HTTPS重定向告警"""
        try:
            existing_alert = self._get_active_alert(certificate_id, 'no_https_redirect')
            if existing_alert:
                return

            message = "HTTP未配置到HTTPS的重定向"
            Alert.create(
                certificate_id=certificate_id,
                alert_type='no_https_redirect',
                message=message,
                severity='low'
            )
            logger.info(f"创建无HTTPS重定向告警: 证书 {certificate_id}")

        except Exception as e:
            logger.error(f"创建无HTTPS重定向告警失败: {str(e)}")

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

    def get_port_monitoring_statistics(self) -> Dict[str, Any]:
        """获取端口监控统计信息"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 统计TLS版本分布
            cursor.execute("""
                SELECT
                    tls_version,
                    COUNT(*) as count
                FROM certificates
                WHERE tls_version IS NOT NULL
                GROUP BY tls_version
            """)
            tls_stats = {row[0]: row[1] for row in cursor.fetchall()}

            # 统计安全等级分布
            cursor.execute("""
                SELECT
                    certificate_chain_valid,
                    COUNT(*) as count
                FROM certificates
                WHERE certificate_chain_valid IS NOT NULL
                GROUP BY certificate_chain_valid
            """)
            chain_stats = cursor.fetchall()

            # 统计平均握手时间
            cursor.execute("""
                SELECT
                    AVG(ssl_handshake_time) as avg_handshake_time,
                    COUNT(CASE WHEN ssl_handshake_time > 1000 THEN 1 END) as slow_handshakes
                FROM certificates
                WHERE ssl_handshake_time IS NOT NULL
            """)
            timing_stats = cursor.fetchone()

            # 统计HTTP重定向状态
            cursor.execute("""
                SELECT
                    http_redirect_status,
                    COUNT(*) as count
                FROM certificates
                WHERE http_redirect_status IS NOT NULL
                GROUP BY http_redirect_status
            """)
            redirect_stats = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                'success': True,
                'statistics': {
                    'tls_version_distribution': tls_stats,
                    'certificate_chain_valid_count': sum(1 for row in chain_stats if row[0] == 1),
                    'certificate_chain_invalid_count': sum(1 for row in chain_stats if row[0] == 0),
                    'average_handshake_time': round(timing_stats[0] or 0, 2),
                    'slow_handshakes_count': timing_stats[1] or 0,
                    'http_redirect_distribution': redirect_stats
                }
            }

        except Exception as e:
            logger.error(f"获取端口监控统计失败: {str(e)}")
            return {'success': False, 'error': f'获取统计失败: {str(e)}'}
        finally:
            if 'conn' in locals():
                conn.close()

    def generate_security_report(self, certificate_id: int = None) -> Dict[str, Any]:
        """生成安全评估报告"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 构建查询条件
            where_clause = "WHERE 1=1"
            params = []
            if certificate_id:
                where_clause += " AND id = ?"
                params.append(certificate_id)

            # 获取证书安全信息
            cursor.execute(f"""
                SELECT
                    id, domain, tls_version, cipher_suite,
                    certificate_chain_valid, ssl_handshake_time,
                    http_redirect_status
                FROM certificates
                {where_clause}
            """, params)

            certificates = cursor.fetchall()

            # 分析安全状况
            security_issues = []
            recommendations = []

            for cert in certificates:
                cert_id, domain, tls_version, cipher_suite, chain_valid, handshake_time, redirect_status = cert

                # 检查TLS版本
                if tls_version and ('TLS 1.0' in tls_version or 'TLS 1.1' in tls_version):
                    security_issues.append({
                        'certificate_id': cert_id,
                        'domain': domain,
                        'issue': f'使用过时的TLS版本: {tls_version}',
                        'severity': 'high',
                        'recommendation': '升级到TLS 1.2或TLS 1.3'
                    })

                # 检查加密套件
                if cipher_suite and any(weak in cipher_suite.upper() for weak in self.weak_ciphers):
                    security_issues.append({
                        'certificate_id': cert_id,
                        'domain': domain,
                        'issue': f'使用弱加密套件: {cipher_suite}',
                        'severity': 'medium',
                        'recommendation': '配置更强的加密套件'
                    })

                # 检查证书链
                if chain_valid == 0:
                    security_issues.append({
                        'certificate_id': cert_id,
                        'domain': domain,
                        'issue': '证书链不完整',
                        'severity': 'medium',
                        'recommendation': '配置完整的证书链，包括中间证书'
                    })

                # 检查握手时间
                if handshake_time and handshake_time > 3000:
                    security_issues.append({
                        'certificate_id': cert_id,
                        'domain': domain,
                        'issue': f'SSL握手时间过长: {handshake_time}ms',
                        'severity': 'low',
                        'recommendation': '优化服务器配置以减少握手时间'
                    })

                # 检查HTTP重定向
                if redirect_status != 'enabled':
                    security_issues.append({
                        'certificate_id': cert_id,
                        'domain': domain,
                        'issue': 'HTTP未重定向到HTTPS',
                        'severity': 'low',
                        'recommendation': '配置HTTP到HTTPS的自动重定向'
                    })

            # 生成通用建议
            if not certificate_id:  # 全局报告
                recommendations.extend([
                    '定期更新SSL/TLS配置以支持最新的安全标准',
                    '禁用过时的TLS协议版本（TLS 1.0/1.1）',
                    '使用强加密套件，避免弱加密算法',
                    '确保证书链完整，包括所有中间证书',
                    '配置HSTS头以增强安全性',
                    '定期监控SSL配置的安全性'
                ])

            return {
                'success': True,
                'report': {
                    'certificate_id': certificate_id,
                    'generated_at': datetime.now().isoformat(),
                    'total_certificates': len(certificates),
                    'security_issues': security_issues,
                    'issues_count': len(security_issues),
                    'recommendations': recommendations
                }
            }

        except Exception as e:
            logger.error(f"生成安全报告失败: {str(e)}")
            return {'success': False, 'error': f'生成报告失败: {str(e)}'}
        finally:
            if 'conn' in locals():
                conn.close()
