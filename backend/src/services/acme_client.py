"""
ACME协议客户端实现
支持Let's Encrypt、ZeroSSL等CA的证书自动申请、续期和部署
"""

import os
import json
import time
import logging
import hashlib
import base64
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from acme import client, messages, challenges, crypto_util
from acme.client import ClientV2
import josepy as jose
import requests
import dns.resolver
import dns.exception
from .dns_providers import DNSManager

# 导入新的异常处理
try:
    from utils.exceptions import (
        ErrorCode, ACMEError, CertificateError,
        BaseAPIException, ValidationError
    )
except ImportError:
    # 兼容性处理，如果新的异常模块不存在，使用旧的
    class ErrorCode:
        ACME_CLIENT_ERROR = 1301
        ACME_NETWORK_ERROR = 1306
        ACME_TIMEOUT = 1308
        ACME_INVALID_DOMAIN = 1309
        ACME_RATE_LIMIT = 1305
        ACME_ORDER_FAILED = 1304
        ACME_CHALLENGE_FAILED = 1303
        ACME_ACCOUNT_ERROR = 1302
        CERTIFICATE_REQUEST_FAILED = 1205

    class ACMEError(Exception):
        def __init__(self, error_code, message, acme_details=None):
            self.error_code = error_code
            self.message = message
            self.acme_details = acme_details
            super().__init__(message)

    class CertificateError(Exception):
        def __init__(self, error_code, message, domain=None):
            self.error_code = error_code
            self.message = message
            self.domain = domain
            super().__init__(message)

    class ValidationError(Exception):
        pass

# 配置日志
logger = logging.getLogger(__name__)


class ACMEClientError(ACMEError):
    """ACME客户端异常 - 兼容旧代码"""
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.ACME_CLIENT_ERROR):
        super().__init__(error_code=error_code, message=message)


class CertificateAuthority:
    """证书颁发机构配置"""
    
    LETS_ENCRYPT_PROD = {
        'name': 'Let\'s Encrypt',
        'directory_url': 'https://acme-v02.api.letsencrypt.org/directory',
        'staging_url': 'https://acme-staging-v02.api.letsencrypt.org/directory',
        'rate_limits': {
            'certificates_per_week': 50,
            'duplicate_certificates_per_week': 5
        }
    }
    
    ZEROSSL = {
        'name': 'ZeroSSL',
        'directory_url': 'https://acme.zerossl.com/v2/DV90',
        'staging_url': 'https://acme.zerossl.com/v2/DV90',  # ZeroSSL没有staging环境
        'rate_limits': {
            'certificates_per_week': 100,
            'duplicate_certificates_per_week': 10
        }
    }
    
    BUYPASS = {
        'name': 'Buypass',
        'directory_url': 'https://api.buypass.com/acme/directory',
        'staging_url': 'https://api.test4.buypass.no/acme/directory',
        'rate_limits': {
            'certificates_per_week': 200,
            'duplicate_certificates_per_week': 20
        }
    }


class ACMEClient:
    """ACME协议客户端"""
    
    def __init__(self, ca_config: Dict[str, Any], email: str, staging: bool = False):
        """
        初始化ACME客户端
        
        Args:
            ca_config: CA配置信息
            email: 联系邮箱
            staging: 是否使用staging环境
        """
        self.ca_config = ca_config
        self.email = email
        self.staging = staging
        self.directory_url = ca_config['staging_url'] if staging else ca_config['directory_url']
        
        # 初始化客户端
        self.account_key = None
        self.client = None
        self.account = None
        
        # 存储路径
        self.storage_path = os.getenv('CERT_STORAGE_PATH', 'certs/')
        os.makedirs(self.storage_path, exist_ok=True)

        # DNS管理器
        self.dns_manager = DNSManager()

        logger.info(f"初始化ACME客户端: {ca_config['name']}, staging={staging}")
    
    def _generate_account_key(self) -> jose.JWKRSA:
        """生成账户私钥"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        return jose.JWKRSA(key=private_key)
    
    def _load_or_create_account_key(self) -> jose.JWKRSA:
        """加载或创建账户私钥"""
        key_file = os.path.join(self.storage_path, f"account_key_{self.ca_config['name'].lower().replace(' ', '_')}.pem")
        
        if os.path.exists(key_file):
            try:
                with open(key_file, 'rb') as f:
                    private_key = serialization.load_pem_private_key(f.read(), password=None)
                return jose.JWKRSA(key=private_key)
            except Exception as e:
                logger.warning(f"加载账户私钥失败: {e}, 将生成新的私钥")
        
        # 生成新的私钥
        account_key = self._generate_account_key()
        
        # 保存私钥
        try:
            private_key_pem = account_key.key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(key_file, 'wb') as f:
                f.write(private_key_pem)
            logger.info(f"账户私钥已保存到: {key_file}")
        except Exception as e:
            logger.error(f"保存账户私钥失败: {e}")
        
        return account_key
    
    def initialize(self) -> bool:
        """初始化ACME客户端和账户"""
        try:
            # 加载或生成账户私钥
            self.account_key = self._load_or_create_account_key()

            # 创建ACME客户端
            net = client.ClientNetwork(self.account_key, user_agent='SSL-Cert-Manager/1.0')

            try:
                directory = client.ClientV2.get_directory(self.directory_url, net)
            except requests.exceptions.ConnectionError as e:
                logger.error(f"无法连接到ACME服务器: {self.directory_url}")
                raise ACMEError(
                    error_code=ErrorCode.ACME_NETWORK_ERROR,
                    message=f"无法连接到ACME服务器: {self.directory_url}",
                    acme_details={'directory_url': self.directory_url, 'error': str(e)}
                )
            except requests.exceptions.Timeout as e:
                logger.error(f"连接ACME服务器超时: {self.directory_url}")
                raise ACMEError(
                    error_code=ErrorCode.ACME_TIMEOUT,
                    message=f"连接ACME服务器超时: {self.directory_url}",
                    acme_details={'directory_url': self.directory_url, 'timeout': True}
                )

            self.client = ClientV2(directory, net=net)

            # 注册或获取账户
            self.account = self._register_or_get_account()

            logger.info("ACME客户端初始化成功")
            return True

        except ACMEError:
            # 重新抛出ACME错误
            raise
        except Exception as e:
            logger.error(f"ACME客户端初始化失败: {e}")
            raise ACMEError(
                error_code=ErrorCode.ACME_CLIENT_ERROR,
                message=f"ACME客户端初始化失败: {str(e)}",
                acme_details={'error_type': type(e).__name__}
            )
    
    def _register_or_get_account(self):
        """注册或获取ACME账户"""
        try:
            # 尝试获取现有账户
            account = self.client.query_registration(
                messages.Registration.from_data(email=self.email)
            )
            logger.info("使用现有ACME账户")
            return account

        except Exception:
            # 注册新账户
            try:
                new_account = messages.NewRegistration.from_data(
                    email=self.email,
                    terms_of_service_agreed=True
                )
                account = self.client.new_account(new_account)
                logger.info("注册新ACME账户成功")
                return account

            except messages.Error as e:
                logger.error(f"ACME账户注册失败: {e}")
                if 'rate limit' in str(e).lower():
                    raise ACMEError(
                        error_code=ErrorCode.ACME_RATE_LIMIT,
                        message="ACME账户注册频率超限",
                        acme_details={'email': self.email, 'error': str(e)}
                    )
                else:
                    raise ACMEError(
                        error_code=ErrorCode.ACME_ACCOUNT_ERROR,
                        message=f"ACME账户注册失败: {str(e)}",
                        acme_details={'email': self.email, 'error': str(e)}
                    )
            except Exception as e:
                logger.error(f"注册ACME账户失败: {e}")
                raise ACMEError(
                    error_code=ErrorCode.ACME_ACCOUNT_ERROR,
                    message=f"ACME账户注册失败: {str(e)}",
                    acme_details={'email': self.email, 'error_type': type(e).__name__}
                )
    
    def generate_csr(self, domains: List[str], key_size: int = 2048) -> Tuple[bytes, bytes]:
        """
        生成证书签名请求(CSR)和私钥
        
        Args:
            domains: 域名列表
            key_size: 私钥长度
            
        Returns:
            Tuple[bytes, bytes]: (CSR, 私钥)
        """
        # 生成私钥
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )
        
        # 构建主题名称
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, domains[0])
        ])
        
        # 构建CSR
        builder = x509.CertificateSigningRequestBuilder()
        builder = builder.subject_name(subject)
        
        # 添加SAN扩展
        if len(domains) > 1:
            san_list = [x509.DNSName(domain) for domain in domains]
            builder = builder.add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False
            )
        
        # 签名CSR
        csr = builder.sign(private_key, hashes.SHA256())
        
        # 序列化
        csr_pem = csr.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return csr_pem, key_pem

    def _validate_domain_format(self, domain: str) -> bool:
        """验证域名格式"""
        import re
        if not isinstance(domain, str):
            return False

        # 基本域名格式验证
        pattern = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        if not re.match(pattern, domain):
            return False

        # 长度检查
        if len(domain) > 253:
            return False

        # 通配符域名检查
        if domain.startswith('*.'):
            # 通配符只能在最前面
            if domain.count('*') > 1:
                return False
            # 验证通配符后的域名部分
            return self._validate_domain_format(domain[2:])

        return True

    def request_certificate(self, domains: List[str], validation_method: str = 'http') -> Dict[str, Any]:
        """
        申请证书
        
        Args:
            domains: 域名列表
            validation_method: 验证方式 ('http' 或 'dns')
            
        Returns:
            Dict: 证书申请结果
        """
        if not self.client or not self.account:
            raise ACMEError(
                error_code=ErrorCode.ACME_CLIENT_ERROR,
                message="ACME客户端未初始化"
            )

        # 验证输入参数
        if not domains:
            raise ValidationError("域名列表不能为空")

        # 验证域名格式
        for domain in domains:
            if not self._validate_domain_format(domain):
                raise ACMEError(
                    error_code=ErrorCode.ACME_INVALID_DOMAIN,
                    message=f"域名格式无效: {domain}",
                    acme_details={'invalid_domain': domain, 'domains': domains}
                )

        try:
            logger.info(f"开始申请证书: {domains}, 验证方式: {validation_method}")

            # 生成CSR和私钥
            csr_pem, key_pem = self.generate_csr(domains)

            # 创建订单
            try:
                order = self.client.new_order(csr_pem)
                logger.info(f"创建订单成功: {order.uri}")
            except messages.Error as e:
                if 'rate limit' in str(e).lower():
                    raise ACMEError(
                        error_code=ErrorCode.ACME_RATE_LIMIT,
                        message="证书申请频率超限",
                        acme_details={'domains': domains, 'error': str(e)}
                    )
                else:
                    raise ACMEError(
                        error_code=ErrorCode.ACME_ORDER_FAILED,
                        message=f"创建ACME订单失败: {str(e)}",
                        acme_details={'domains': domains, 'error': str(e)}
                    )
            except requests.exceptions.RequestException as e:
                raise ACMEError(
                    error_code=ErrorCode.ACME_NETWORK_ERROR,
                    message=f"网络请求失败: {str(e)}",
                    acme_details={'domains': domains, 'error': str(e)}
                )

            # 处理授权验证
            for authorization in order.authorizations:
                self._process_authorization(authorization, validation_method)

            # 等待验证完成
            order = self._wait_for_order_ready(order)

            # 完成订单
            order = self.client.finalize_order(order, datetime.now() + timedelta(seconds=90))

            # 获取证书
            certificate_pem = order.fullchain_pem

            # 清理验证记录
            for domain in domains:
                self._cleanup_challenge(domain)

            # 保存证书和私钥
            cert_info = self._save_certificate(domains[0], certificate_pem, key_pem)

            logger.info(f"证书申请成功: {domains[0]}")

            return {
                'success': True,
                'certificate': certificate_pem,
                'private_key': key_pem.decode('utf-8'),
                'domains': domains,
                'cert_info': cert_info
            }

        except ACMEError:
            # 重新抛出ACME错误
            raise
        except Exception as e:
            logger.error(f"证书申请失败: {e}")
            raise CertificateError(
                error_code=ErrorCode.CERTIFICATE_REQUEST_FAILED,
                message=f"证书申请失败: {str(e)}",
                domain=domains[0] if domains else None
            )
    
    def _process_authorization(self, authorization, validation_method: str):
        """处理域名授权验证"""
        domain = authorization.body.identifier.value
        logger.info(f"处理域名授权: {domain}, 方法: {validation_method}")
        
        # 选择验证方式
        if validation_method == 'http':
            challenge = self._get_http_challenge(authorization)
            self._setup_http_challenge(challenge, domain)
        elif validation_method == 'dns':
            challenge = self._get_dns_challenge(authorization)
            self._setup_dns_challenge(challenge, domain)
        else:
            raise ACMEClientError(f"不支持的验证方式: {validation_method}")
        
        # 响应验证
        self.client.answer_challenge(challenge, challenge.response(self.account_key))
        
        # 等待验证完成
        self._wait_for_challenge_completion(challenge)
    
    def _get_http_challenge(self, authorization):
        """获取HTTP验证挑战"""
        for challenge in authorization.body.challenges:
            if isinstance(challenge.chall, challenges.HTTP01):
                return challenge
        raise ACMEClientError("未找到HTTP-01验证挑战")
    
    def _get_dns_challenge(self, authorization):
        """获取DNS验证挑战"""
        for challenge in authorization.body.challenges:
            if isinstance(challenge.chall, challenges.DNS01):
                return challenge
        raise ACMEClientError("未找到DNS-01验证挑战")
    
    def _setup_http_challenge(self, challenge, domain: str):
        """设置HTTP验证"""
        token = challenge.chall.token
        key_authorization = challenge.chall.key_authorization(self.account_key)
        
        # 创建验证文件目录
        well_known_path = os.path.join(self.storage_path, '.well-known', 'acme-challenge')
        os.makedirs(well_known_path, exist_ok=True)
        
        # 写入验证文件
        challenge_file = os.path.join(well_known_path, token)
        with open(challenge_file, 'w') as f:
            f.write(key_authorization)
        
        logger.info(f"HTTP验证文件已创建: {challenge_file}")
        logger.info(f"请确保 http://{domain}/.well-known/acme-challenge/{token} 可访问")
    
    def _setup_dns_challenge(self, challenge, domain: str):
        """设置DNS验证"""
        key_authorization = challenge.chall.key_authorization(self.account_key)
        dns_value = base64.urlsafe_b64encode(
            hashlib.sha256(key_authorization.encode()).digest()
        ).decode().rstrip('=')

        logger.info(f"设置DNS验证记录: {domain}")

        # 尝试自动添加DNS记录
        if self.dns_manager.add_acme_challenge(domain, dns_value):
            logger.info(f"DNS验证记录自动添加成功: {domain}")
            # 存储验证信息，用于后续清理
            self._store_challenge_info(domain, dns_value)
        else:
            # 如果自动添加失败，提供手动添加的信息
            dns_name = f"_acme-challenge.{domain}"
            logger.warning(f"DNS验证记录自动添加失败，请手动添加:")
            logger.info(f"名称: {dns_name}")
            logger.info(f"值: {dns_value}")
            logger.info("添加完成后按回车继续...")
            input("等待DNS记录添加...")

    def _store_challenge_info(self, domain: str, dns_value: str):
        """存储验证信息"""
        challenge_file = os.path.join(self.storage_path, f".challenge_{domain}.json")
        challenge_info = {
            'domain': domain,
            'dns_value': dns_value,
            'timestamp': time.time()
        }

        try:
            with open(challenge_file, 'w') as f:
                json.dump(challenge_info, f)
        except Exception as e:
            logger.error(f"存储验证信息失败: {e}")

    def _cleanup_challenge(self, domain: str):
        """清理验证记录"""
        challenge_file = os.path.join(self.storage_path, f".challenge_{domain}.json")

        if os.path.exists(challenge_file):
            try:
                with open(challenge_file, 'r') as f:
                    challenge_info = json.load(f)

                # 删除DNS记录
                self.dns_manager.remove_acme_challenge(
                    challenge_info['domain'],
                    challenge_info['dns_value']
                )

                # 删除临时文件
                os.remove(challenge_file)
                logger.info(f"验证记录清理完成: {domain}")

            except Exception as e:
                logger.error(f"清理验证记录失败: {e}")
    
    def _wait_for_challenge_completion(self, challenge, timeout: int = 300):
        """等待验证完成"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                challenge = self.client.poll(challenge)
                if challenge.status == messages.STATUS_VALID:
                    logger.info("验证成功")
                    return
                elif challenge.status == messages.STATUS_INVALID:
                    error_detail = str(challenge.error) if challenge.error else "未知错误"
                    raise ACMEError(
                        error_code=ErrorCode.ACME_CHALLENGE_FAILED,
                        message=f"ACME验证失败: {error_detail}",
                        acme_details={'challenge_error': error_detail}
                    )

                time.sleep(5)

            except ACMEError:
                # 重新抛出ACME错误
                raise
            except requests.exceptions.RequestException as e:
                logger.warning(f"验证状态检查网络错误: {e}")
                time.sleep(5)
            except Exception as e:
                logger.error(f"验证状态检查失败: {e}")
                time.sleep(5)

        raise ACMEError(
            error_code=ErrorCode.ACME_TIMEOUT,
            message="ACME验证超时",
            acme_details={'timeout_seconds': timeout}
        )
    
    def _wait_for_order_ready(self, order, timeout: int = 300):
        """等待订单就绪"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                order = self.client.poll(order)
                if order.status == messages.STATUS_READY:
                    logger.info("订单就绪")
                    return order
                elif order.status == messages.STATUS_INVALID:
                    error_detail = str(order.error) if order.error else "未知错误"
                    raise ACMEError(
                        error_code=ErrorCode.ACME_ORDER_FAILED,
                        message=f"ACME订单失败: {error_detail}",
                        acme_details={'order_error': error_detail}
                    )

                time.sleep(5)

            except ACMEError:
                # 重新抛出ACME错误
                raise
            except requests.exceptions.RequestException as e:
                logger.warning(f"订单状态检查网络错误: {e}")
                time.sleep(5)
            except Exception as e:
                logger.error(f"订单状态检查失败: {e}")
                time.sleep(5)

        raise ACMEError(
            error_code=ErrorCode.ACME_TIMEOUT,
            message="ACME订单超时",
            acme_details={'timeout_seconds': timeout}
        )
    
    def _save_certificate(self, domain: str, certificate_pem: str, key_pem: bytes) -> Dict[str, Any]:
        """保存证书和私钥"""
        # 创建域名目录
        domain_path = os.path.join(self.storage_path, domain)
        os.makedirs(domain_path, exist_ok=True)
        
        # 保存证书
        cert_file = os.path.join(domain_path, 'cert.pem')
        with open(cert_file, 'w') as f:
            f.write(certificate_pem)
        
        # 保存私钥
        key_file = os.path.join(domain_path, 'privkey.pem')
        with open(key_file, 'wb') as f:
            f.write(key_pem)
        
        # 解析证书信息
        cert_info = self._parse_certificate_info(certificate_pem)
        
        # 保存证书信息
        info_file = os.path.join(domain_path, 'info.json')
        with open(info_file, 'w') as f:
            json.dump(cert_info, f, indent=2, default=str)
        
        logger.info(f"证书已保存到: {domain_path}")
        
        return cert_info
    
    def _parse_certificate_info(self, certificate_pem: str) -> Dict[str, Any]:
        """解析证书信息"""
        try:
            cert = x509.load_pem_x509_certificate(certificate_pem.encode())
            
            return {
                'subject': cert.subject.rfc4514_string(),
                'issuer': cert.issuer.rfc4514_string(),
                'serial_number': str(cert.serial_number),
                'not_valid_before': cert.not_valid_before,
                'not_valid_after': cert.not_valid_after,
                'signature_algorithm': cert.signature_algorithm_oid._name,
                'public_key_size': cert.public_key().key_size,
                'domains': self._extract_domains_from_cert(cert)
            }
            
        except Exception as e:
            logger.error(f"解析证书信息失败: {e}")
            return {}
    
    def _extract_domains_from_cert(self, cert) -> List[str]:
        """从证书中提取域名"""
        domains = []
        
        # 从CN获取主域名
        try:
            cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            domains.append(cn)
        except (IndexError, AttributeError):
            pass
        
        # 从SAN扩展获取所有域名
        try:
            san_ext = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            for name in san_ext.value:
                if isinstance(name, x509.DNSName):
                    if name.value not in domains:
                        domains.append(name.value)
        except x509.ExtensionNotFound:
            pass
        
        return domains

    def renew_certificate(self, domain: str, validation_method: str = 'http') -> Dict[str, Any]:
        """
        续期证书

        Args:
            domain: 主域名
            validation_method: 验证方式

        Returns:
            Dict: 续期结果
        """
        try:
            logger.info(f"开始续期证书: {domain}")

            # 检查现有证书
            cert_info = self._load_certificate_info(domain)
            if not cert_info:
                raise ACMEClientError(f"未找到域名 {domain} 的证书信息")

            # 检查是否需要续期
            if not self._should_renew_certificate(cert_info):
                logger.info(f"证书 {domain} 暂不需要续期")
                return {
                    'success': True,
                    'renewed': False,
                    'message': '证书暂不需要续期',
                    'expires_at': cert_info.get('not_valid_after')
                }

            # 获取原证书的域名列表
            domains = cert_info.get('domains', [domain])

            # 申请新证书
            result = self.request_certificate(domains, validation_method)

            if result['success']:
                logger.info(f"证书续期成功: {domain}")
                return {
                    'success': True,
                    'renewed': True,
                    'message': '证书续期成功',
                    'cert_info': result['cert_info']
                }
            else:
                raise ACMEClientError(f"证书续期失败: {result.get('error')}")

        except Exception as e:
            logger.error(f"证书续期失败: {e}")
            return {
                'success': False,
                'renewed': False,
                'error': str(e)
            }

    def _load_certificate_info(self, domain: str) -> Optional[Dict[str, Any]]:
        """加载证书信息"""
        info_file = os.path.join(self.storage_path, domain, 'info.json')

        if not os.path.exists(info_file):
            return None

        try:
            with open(info_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载证书信息失败: {e}")
            return None

    def _should_renew_certificate(self, cert_info: Dict[str, Any], days_before: int = 30) -> bool:
        """检查是否需要续期证书"""
        try:
            expires_at = cert_info.get('not_valid_after')
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            elif not isinstance(expires_at, datetime):
                return True  # 无法确定过期时间，建议续期

            renewal_time = expires_at - timedelta(days=days_before)
            return datetime.now() >= renewal_time

        except Exception as e:
            logger.error(f"检查证书续期状态失败: {e}")
            return True  # 出错时建议续期

    def revoke_certificate(self, domain: str, reason: int = 0) -> Dict[str, Any]:
        """
        撤销证书

        Args:
            domain: 域名
            reason: 撤销原因代码

        Returns:
            Dict: 撤销结果
        """
        try:
            logger.info(f"开始撤销证书: {domain}")

            # 加载证书
            cert_file = os.path.join(self.storage_path, domain, 'cert.pem')
            if not os.path.exists(cert_file):
                raise ACMEClientError(f"未找到证书文件: {cert_file}")

            with open(cert_file, 'r') as f:
                cert_pem = f.read()

            cert = x509.load_pem_x509_certificate(cert_pem.encode())

            # 撤销证书
            self.client.revoke(jose.ComparableX509(cert), reason)

            logger.info(f"证书撤销成功: {domain}")

            return {
                'success': True,
                'message': '证书撤销成功'
            }

        except Exception as e:
            logger.error(f"证书撤销失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_certificate_status(self, domain: str) -> Dict[str, Any]:
        """
        获取证书状态

        Args:
            domain: 域名

        Returns:
            Dict: 证书状态信息
        """
        try:
            cert_info = self._load_certificate_info(domain)
            if not cert_info:
                return {
                    'exists': False,
                    'message': '证书不存在'
                }

            expires_at = cert_info.get('not_valid_after')
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))

            now = datetime.now()
            days_until_expiry = (expires_at - now).days if expires_at else 0

            # 确定证书状态
            if days_until_expiry < 0:
                status = 'expired'
            elif days_until_expiry <= 7:
                status = 'critical'
            elif days_until_expiry <= 30:
                status = 'warning'
            else:
                status = 'valid'

            return {
                'exists': True,
                'status': status,
                'expires_at': expires_at,
                'days_until_expiry': days_until_expiry,
                'should_renew': self._should_renew_certificate(cert_info),
                'cert_info': cert_info
            }

        except Exception as e:
            logger.error(f"获取证书状态失败: {e}")
            return {
                'exists': False,
                'error': str(e)
            }

    def list_certificates(self) -> List[Dict[str, Any]]:
        """列出所有证书"""
        certificates = []

        try:
            if not os.path.exists(self.storage_path):
                return certificates

            for item in os.listdir(self.storage_path):
                item_path = os.path.join(self.storage_path, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    cert_status = self.get_certificate_status(item)
                    if cert_status.get('exists'):
                        certificates.append({
                            'domain': item,
                            **cert_status
                        })

            return certificates

        except Exception as e:
            logger.error(f"列出证书失败: {e}")
            return certificates


class ACMEManager:
    """ACME管理器 - 管理多个CA客户端"""

    def __init__(self, email: str, staging: bool = False, auto_initialize: bool = True):
        """
        初始化ACME管理器

        Args:
            email: 联系邮箱
            staging: 是否使用staging环境
            auto_initialize: 是否自动初始化客户端
        """
        self.email = email
        self.staging = staging
        self.clients = {}

        # 只在需要时初始化支持的CA
        if auto_initialize:
            self._initialize_clients()

    def _initialize_clients(self):
        """初始化CA客户端"""
        ca_configs = {
            'letsencrypt': CertificateAuthority.LETS_ENCRYPT_PROD,
            'zerossl': CertificateAuthority.ZEROSSL,
            'buypass': CertificateAuthority.BUYPASS
        }

        for ca_name, ca_config in ca_configs.items():
            try:
                client = ACMEClient(ca_config, self.email, self.staging)
                client.initialize()
                self.clients[ca_name] = client
                logger.info(f"CA客户端初始化成功: {ca_name}")
            except Exception as e:
                logger.error(f"CA客户端初始化失败 {ca_name}: {e}")

    def get_client(self, ca_name: str = 'letsencrypt') -> Optional[ACMEClient]:
        """获取指定CA的客户端"""
        return self.clients.get(ca_name)

    def request_certificate(self, domains: List[str], ca_name: str = 'letsencrypt',
                          validation_method: str = 'http') -> Dict[str, Any]:
        """申请证书"""
        client = self.get_client(ca_name)
        if not client:
            return {
                'success': False,
                'error': f'不支持的CA: {ca_name}'
            }

        return client.request_certificate(domains, validation_method)

    def renew_certificate(self, domain: str, ca_name: str = 'letsencrypt',
                         validation_method: str = 'http') -> Dict[str, Any]:
        """续期证书"""
        client = self.get_client(ca_name)
        if not client:
            return {
                'success': False,
                'error': f'不支持的CA: {ca_name}'
            }

        return client.renew_certificate(domain, validation_method)

    def auto_renew_certificates(self, ca_name: str = 'letsencrypt') -> Dict[str, Any]:
        """自动续期所有需要续期的证书"""
        client = self.get_client(ca_name)
        if not client:
            return {
                'success': False,
                'error': f'不支持的CA: {ca_name}'
            }

        results = {
            'success': True,
            'renewed': [],
            'failed': [],
            'skipped': []
        }

        try:
            certificates = client.list_certificates()

            for cert in certificates:
                domain = cert['domain']

                if cert.get('should_renew'):
                    logger.info(f"自动续期证书: {domain}")
                    result = client.renew_certificate(domain)

                    if result['success'] and result.get('renewed'):
                        results['renewed'].append(domain)
                    elif result['success']:
                        results['skipped'].append(domain)
                    else:
                        results['failed'].append({
                            'domain': domain,
                            'error': result.get('error')
                        })
                else:
                    results['skipped'].append(domain)

            logger.info(f"自动续期完成: 续期 {len(results['renewed'])}, "
                       f"跳过 {len(results['skipped'])}, 失败 {len(results['failed'])}")

        except Exception as e:
            logger.error(f"自动续期失败: {e}")
            results['success'] = False
            results['error'] = str(e)

        return results

    def get_supported_cas(self) -> List[Dict[str, Any]]:
        """获取支持的CA列表"""
        return [
            {
                'name': 'letsencrypt',
                'display_name': 'Let\'s Encrypt',
                'available': 'letsencrypt' in self.clients,
                'rate_limits': CertificateAuthority.LETS_ENCRYPT_PROD['rate_limits']
            },
            {
                'name': 'zerossl',
                'display_name': 'ZeroSSL',
                'available': 'zerossl' in self.clients,
                'rate_limits': CertificateAuthority.ZEROSSL['rate_limits']
            },
            {
                'name': 'buypass',
                'display_name': 'Buypass',
                'available': 'buypass' in self.clients,
                'rate_limits': CertificateAuthority.BUYPASS['rate_limits']
            }
        ]
