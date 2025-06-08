"""
证书服务模块
提供证书申请、续期、管理等高级功能
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .acme_client import ACMEManager
from models.certificate import Certificate
from models.server import Server
from models.user import User

logger = logging.getLogger(__name__)


class CertificateService:
    """证书服务"""
    
    def __init__(self):
        """初始化证书服务"""
        self.acme_email = os.getenv('ACME_EMAIL', 'admin@example.com')
        self.staging = os.getenv('FLASK_ENV') == 'development'
        self.acme_manager = ACMEManager(self.acme_email, self.staging)
        
        logger.info(f"证书服务初始化完成, staging={self.staging}")
    
    def request_certificate(self, user_id: int, domains: List[str], server_id: int,
                          ca_type: str = 'letsencrypt', validation_method: str = 'http',
                          auto_renew: bool = True) -> Dict[str, Any]:
        """
        申请证书
        
        Args:
            user_id: 用户ID
            domains: 域名列表
            server_id: 服务器ID
            ca_type: CA类型
            validation_method: 验证方式
            auto_renew: 是否自动续期
            
        Returns:
            Dict: 申请结果
        """
        try:
            logger.info(f"用户 {user_id} 申请证书: {domains}")
            
            # 验证用户权限
            user = User.get_by_id(user_id)
            if not user:
                return {
                    'success': False,
                    'error': '用户不存在'
                }
            
            # 验证服务器权限
            server = Server.get_by_id(server_id)
            if not server or (server.user_id != user_id and user.role != 'admin'):
                return {
                    'success': False,
                    'error': '服务器不存在或无权限'
                }
            
            # 检查域名是否已存在证书
            existing_cert = Certificate.get_by_domain(domains[0])
            if existing_cert and existing_cert.status == 'valid':
                return {
                    'success': False,
                    'error': f'域名 {domains[0]} 已存在有效证书'
                }
            
            # 使用ACME客户端申请证书
            result = self.acme_manager.request_certificate(
                domains, ca_type, validation_method
            )
            
            if result['success']:
                # 保存证书信息到数据库
                cert_info = result['cert_info']
                certificate = Certificate.create(
                    domain=domains[0],
                    domains=','.join(domains),
                    server_id=server_id,
                    user_id=user_id,
                    ca_type=ca_type,
                    validation_method=validation_method,
                    auto_renew=auto_renew,
                    status='valid',
                    expires_at=cert_info.get('not_valid_after'),
                    certificate_path=f"{domains[0]}/cert.pem",
                    private_key_path=f"{domains[0]}/privkey.pem"
                )
                
                logger.info(f"证书申请成功并保存到数据库: {certificate.id}")
                
                return {
                    'success': True,
                    'certificate_id': certificate.id,
                    'domains': domains,
                    'expires_at': cert_info.get('not_valid_after'),
                    'message': '证书申请成功'
                }
            else:
                logger.error(f"证书申请失败: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error', '证书申请失败')
                }
                
        except Exception as e:
            logger.error(f"证书申请异常: {e}")
            return {
                'success': False,
                'error': f'证书申请异常: {str(e)}'
            }
    
    def renew_certificate(self, certificate_id: int, user_id: int) -> Dict[str, Any]:
        """
        续期证书
        
        Args:
            certificate_id: 证书ID
            user_id: 用户ID
            
        Returns:
            Dict: 续期结果
        """
        try:
            logger.info(f"用户 {user_id} 续期证书: {certificate_id}")
            
            # 获取证书信息
            certificate = Certificate.get_by_id(certificate_id)
            if not certificate:
                return {
                    'success': False,
                    'error': '证书不存在'
                }
            
            # 验证权限
            user = User.get_by_id(user_id)
            if not user or (certificate.user_id != user_id and user.role != 'admin'):
                return {
                    'success': False,
                    'error': '无权限操作此证书'
                }
            
            # 使用ACME客户端续期证书
            domains = certificate.domains.split(',') if certificate.domains else [certificate.domain]
            result = self.acme_manager.renew_certificate(
                certificate.domain, certificate.ca_type, certificate.validation_method
            )
            
            if result['success'] and result.get('renewed'):
                # 更新数据库中的证书信息
                cert_info = result.get('cert_info', {})
                certificate.update(
                    status='valid',
                    expires_at=cert_info.get('not_valid_after'),
                    renewed_at=datetime.now()
                )
                
                logger.info(f"证书续期成功: {certificate_id}")
                
                return {
                    'success': True,
                    'renewed': True,
                    'expires_at': cert_info.get('not_valid_after'),
                    'message': '证书续期成功'
                }
            elif result['success']:
                return {
                    'success': True,
                    'renewed': False,
                    'message': '证书暂不需要续期'
                }
            else:
                logger.error(f"证书续期失败: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error', '证书续期失败')
                }
                
        except Exception as e:
            logger.error(f"证书续期异常: {e}")
            return {
                'success': False,
                'error': f'证书续期异常: {str(e)}'
            }
    
    def revoke_certificate(self, certificate_id: int, user_id: int, reason: int = 0) -> Dict[str, Any]:
        """
        撤销证书
        
        Args:
            certificate_id: 证书ID
            user_id: 用户ID
            reason: 撤销原因
            
        Returns:
            Dict: 撤销结果
        """
        try:
            logger.info(f"用户 {user_id} 撤销证书: {certificate_id}")
            
            # 获取证书信息
            certificate = Certificate.get_by_id(certificate_id)
            if not certificate:
                return {
                    'success': False,
                    'error': '证书不存在'
                }
            
            # 验证权限
            user = User.get_by_id(user_id)
            if not user or (certificate.user_id != user_id and user.role != 'admin'):
                return {
                    'success': False,
                    'error': '无权限操作此证书'
                }
            
            # 使用ACME客户端撤销证书
            client = self.acme_manager.get_client(certificate.ca_type)
            if not client:
                return {
                    'success': False,
                    'error': f'不支持的CA类型: {certificate.ca_type}'
                }
            
            result = client.revoke_certificate(certificate.domain, reason)
            
            if result['success']:
                # 更新数据库中的证书状态
                certificate.update(
                    status='revoked',
                    revoked_at=datetime.now()
                )
                
                logger.info(f"证书撤销成功: {certificate_id}")
                
                return {
                    'success': True,
                    'message': '证书撤销成功'
                }
            else:
                logger.error(f"证书撤销失败: {result.get('error')}")
                return {
                    'success': False,
                    'error': result.get('error', '证书撤销失败')
                }
                
        except Exception as e:
            logger.error(f"证书撤销异常: {e}")
            return {
                'success': False,
                'error': f'证书撤销异常: {str(e)}'
            }
    
    def auto_renew_certificates(self) -> Dict[str, Any]:
        """
        自动续期所有需要续期的证书
        
        Returns:
            Dict: 续期结果统计
        """
        try:
            logger.info("开始自动续期证书")
            
            # 获取需要续期的证书
            renewal_days = int(os.getenv('CERT_RENEWAL_DAYS', '30'))
            renewal_date = datetime.now() + timedelta(days=renewal_days)
            
            certificates = Certificate.get_expiring_certificates(renewal_date)
            
            results = {
                'success': True,
                'total': len(certificates),
                'renewed': [],
                'failed': [],
                'skipped': []
            }
            
            for certificate in certificates:
                if not certificate.auto_renew:
                    results['skipped'].append({
                        'id': certificate.id,
                        'domain': certificate.domain,
                        'reason': '未启用自动续期'
                    })
                    continue
                
                # 续期证书
                result = self.renew_certificate(certificate.id, certificate.user_id)
                
                if result['success'] and result.get('renewed'):
                    results['renewed'].append({
                        'id': certificate.id,
                        'domain': certificate.domain,
                        'expires_at': result.get('expires_at')
                    })
                elif result['success']:
                    results['skipped'].append({
                        'id': certificate.id,
                        'domain': certificate.domain,
                        'reason': '暂不需要续期'
                    })
                else:
                    results['failed'].append({
                        'id': certificate.id,
                        'domain': certificate.domain,
                        'error': result.get('error')
                    })
            
            logger.info(f"自动续期完成: 总计 {results['total']}, "
                       f"续期 {len(results['renewed'])}, "
                       f"跳过 {len(results['skipped'])}, "
                       f"失败 {len(results['failed'])}")
            
            return results
            
        except Exception as e:
            logger.error(f"自动续期异常: {e}")
            return {
                'success': False,
                'error': f'自动续期异常: {str(e)}'
            }
    
    def get_certificate_status(self, certificate_id: int) -> Dict[str, Any]:
        """
        获取证书状态
        
        Args:
            certificate_id: 证书ID
            
        Returns:
            Dict: 证书状态信息
        """
        try:
            certificate = Certificate.get_by_id(certificate_id)
            if not certificate:
                return {
                    'success': False,
                    'error': '证书不存在'
                }
            
            # 获取ACME客户端状态
            client = self.acme_manager.get_client(certificate.ca_type)
            if client:
                acme_status = client.get_certificate_status(certificate.domain)
            else:
                acme_status = {'exists': False}
            
            # 计算过期时间
            now = datetime.now()
            if certificate.expires_at:
                days_until_expiry = (certificate.expires_at - now).days
            else:
                days_until_expiry = 0
            
            # 确定状态
            if certificate.status == 'revoked':
                status = 'revoked'
            elif days_until_expiry < 0:
                status = 'expired'
            elif days_until_expiry <= 7:
                status = 'critical'
            elif days_until_expiry <= 30:
                status = 'warning'
            else:
                status = 'valid'
            
            return {
                'success': True,
                'certificate': {
                    'id': certificate.id,
                    'domain': certificate.domain,
                    'status': status,
                    'expires_at': certificate.expires_at,
                    'days_until_expiry': days_until_expiry,
                    'auto_renew': certificate.auto_renew,
                    'ca_type': certificate.ca_type,
                    'validation_method': certificate.validation_method
                },
                'acme_status': acme_status
            }
            
        except Exception as e:
            logger.error(f"获取证书状态异常: {e}")
            return {
                'success': False,
                'error': f'获取证书状态异常: {str(e)}'
            }
    
    def get_supported_cas(self) -> List[Dict[str, Any]]:
        """获取支持的CA列表"""
        return self.acme_manager.get_supported_cas()


# 全局证书服务实例
certificate_service = CertificateService()
