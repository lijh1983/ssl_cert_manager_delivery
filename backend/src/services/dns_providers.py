"""
DNS提供商集成模块
支持自动化DNS验证记录的添加和删除
"""

import os
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import requests
import dns.resolver
import dns.exception

logger = logging.getLogger(__name__)


class DNSProviderError(Exception):
    """DNS提供商异常"""
    pass


class DNSProvider(ABC):
    """DNS提供商抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化DNS提供商
        
        Args:
            config: 配置信息
        """
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def add_txt_record(self, domain: str, name: str, value: str, ttl: int = 300) -> bool:
        """
        添加TXT记录
        
        Args:
            domain: 域名
            name: 记录名称
            value: 记录值
            ttl: TTL值
            
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    def delete_txt_record(self, domain: str, name: str, value: str) -> bool:
        """
        删除TXT记录
        
        Args:
            domain: 域名
            name: 记录名称
            value: 记录值
            
        Returns:
            bool: 是否成功
        """
        pass
    
    def verify_txt_record(self, name: str, value: str, timeout: int = 300) -> bool:
        """
        验证TXT记录是否生效
        
        Args:
            name: 记录名称
            value: 期望的记录值
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否验证成功
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                answers = dns.resolver.resolve(name, 'TXT')
                for answer in answers:
                    txt_value = answer.to_text().strip('"')
                    if txt_value == value:
                        logger.info(f"TXT记录验证成功: {name} = {value}")
                        return True
                
                logger.debug(f"TXT记录尚未生效: {name}")
                time.sleep(10)
                
            except dns.exception.DNSException as e:
                logger.debug(f"DNS查询失败: {e}")
                time.sleep(10)
            except Exception as e:
                logger.error(f"验证TXT记录时发生错误: {e}")
                time.sleep(10)
        
        logger.error(f"TXT记录验证超时: {name}")
        return False


class CloudflareDNS(DNSProvider):
    """Cloudflare DNS提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Cloudflare DNS
        
        Args:
            config: 包含api_token或email+api_key的配置
        """
        super().__init__(config)
        self.api_token = config.get('api_token')
        self.email = config.get('email')
        self.api_key = config.get('api_key')
        self.base_url = 'https://api.cloudflare.com/client/v4'
        
        if not self.api_token and not (self.email and self.api_key):
            raise DNSProviderError("需要提供api_token或email+api_key")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        if self.api_token:
            return {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
        else:
            return {
                'X-Auth-Email': self.email,
                'X-Auth-Key': self.api_key,
                'Content-Type': 'application/json'
            }
    
    def _get_zone_id(self, domain: str) -> Optional[str]:
        """获取域名的Zone ID"""
        # 尝试获取根域名
        parts = domain.split('.')
        for i in range(len(parts)):
            zone_name = '.'.join(parts[i:])
            
            url = f"{self.base_url}/zones"
            params = {'name': zone_name}
            
            try:
                response = requests.get(url, headers=self._get_headers(), params=params)
                response.raise_for_status()
                
                data = response.json()
                if data['success'] and data['result']:
                    return data['result'][0]['id']
                    
            except Exception as e:
                logger.debug(f"获取Zone ID失败 {zone_name}: {e}")
                continue
        
        return None
    
    def add_txt_record(self, domain: str, name: str, value: str, ttl: int = 300) -> bool:
        """添加TXT记录"""
        try:
            zone_id = self._get_zone_id(domain)
            if not zone_id:
                raise DNSProviderError(f"未找到域名 {domain} 的Zone ID")
            
            url = f"{self.base_url}/zones/{zone_id}/dns_records"
            data = {
                'type': 'TXT',
                'name': name,
                'content': value,
                'ttl': ttl
            }
            
            response = requests.post(url, headers=self._get_headers(), json=data)
            response.raise_for_status()
            
            result = response.json()
            if result['success']:
                logger.info(f"Cloudflare TXT记录添加成功: {name}")
                return True
            else:
                logger.error(f"Cloudflare TXT记录添加失败: {result.get('errors')}")
                return False
                
        except Exception as e:
            logger.error(f"Cloudflare添加TXT记录失败: {e}")
            return False
    
    def delete_txt_record(self, domain: str, name: str, value: str) -> bool:
        """删除TXT记录"""
        try:
            zone_id = self._get_zone_id(domain)
            if not zone_id:
                raise DNSProviderError(f"未找到域名 {domain} 的Zone ID")
            
            # 查找记录ID
            url = f"{self.base_url}/zones/{zone_id}/dns_records"
            params = {'type': 'TXT', 'name': name, 'content': value}
            
            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            
            data = response.json()
            if not data['success'] or not data['result']:
                logger.warning(f"未找到要删除的TXT记录: {name}")
                return True
            
            # 删除记录
            record_id = data['result'][0]['id']
            delete_url = f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}"
            
            response = requests.delete(delete_url, headers=self._get_headers())
            response.raise_for_status()
            
            result = response.json()
            if result['success']:
                logger.info(f"Cloudflare TXT记录删除成功: {name}")
                return True
            else:
                logger.error(f"Cloudflare TXT记录删除失败: {result.get('errors')}")
                return False
                
        except Exception as e:
            logger.error(f"Cloudflare删除TXT记录失败: {e}")
            return False


class AliDNS(DNSProvider):
    """阿里云DNS提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化阿里云DNS
        
        Args:
            config: 包含access_key_id和access_key_secret的配置
        """
        super().__init__(config)
        self.access_key_id = config.get('access_key_id')
        self.access_key_secret = config.get('access_key_secret')
        self.endpoint = config.get('endpoint', 'https://alidns.cn-hangzhou.aliyuncs.com')
        
        if not self.access_key_id or not self.access_key_secret:
            raise DNSProviderError("需要提供access_key_id和access_key_secret")
    
    def add_txt_record(self, domain: str, name: str, value: str, ttl: int = 300) -> bool:
        """添加TXT记录"""
        # 这里需要实现阿里云DNS API调用
        # 由于阿里云API比较复杂，这里提供一个简化的示例
        logger.warning("阿里云DNS集成尚未完全实现")
        return False
    
    def delete_txt_record(self, domain: str, name: str, value: str) -> bool:
        """删除TXT记录"""
        logger.warning("阿里云DNS集成尚未完全实现")
        return False


class DNSPodProvider(DNSProvider):
    """DNSPod DNS提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化DNSPod
        
        Args:
            config: 包含token的配置
        """
        super().__init__(config)
        self.token = config.get('token')
        self.base_url = 'https://dnsapi.cn'
        
        if not self.token:
            raise DNSProviderError("需要提供token")
    
    def add_txt_record(self, domain: str, name: str, value: str, ttl: int = 300) -> bool:
        """添加TXT记录"""
        # 这里需要实现DNSPod API调用
        logger.warning("DNSPod集成尚未完全实现")
        return False
    
    def delete_txt_record(self, domain: str, name: str, value: str) -> bool:
        """删除TXT记录"""
        logger.warning("DNSPod集成尚未完全实现")
        return False


class DNSManager:
    """DNS管理器"""
    
    def __init__(self):
        """初始化DNS管理器"""
        self.providers = {}
        self._load_providers()
    
    def _load_providers(self):
        """加载DNS提供商配置"""
        # 从环境变量或配置文件加载DNS提供商配置
        
        # Cloudflare
        cf_token = os.getenv('CLOUDFLARE_API_TOKEN')
        cf_email = os.getenv('CLOUDFLARE_EMAIL')
        cf_key = os.getenv('CLOUDFLARE_API_KEY')
        
        if cf_token or (cf_email and cf_key):
            try:
                config = {}
                if cf_token:
                    config['api_token'] = cf_token
                else:
                    config['email'] = cf_email
                    config['api_key'] = cf_key
                
                self.providers['cloudflare'] = CloudflareDNS(config)
                logger.info("Cloudflare DNS提供商已加载")
            except Exception as e:
                logger.error(f"加载Cloudflare DNS提供商失败: {e}")
        
        # 阿里云DNS
        ali_key_id = os.getenv('ALIYUN_ACCESS_KEY_ID')
        ali_key_secret = os.getenv('ALIYUN_ACCESS_KEY_SECRET')
        
        if ali_key_id and ali_key_secret:
            try:
                config = {
                    'access_key_id': ali_key_id,
                    'access_key_secret': ali_key_secret
                }
                self.providers['aliyun'] = AliDNS(config)
                logger.info("阿里云DNS提供商已加载")
            except Exception as e:
                logger.error(f"加载阿里云DNS提供商失败: {e}")
        
        # DNSPod
        dnspod_token = os.getenv('DNSPOD_TOKEN')
        if dnspod_token:
            try:
                config = {'token': dnspod_token}
                self.providers['dnspod'] = DNSPodProvider(config)
                logger.info("DNSPod提供商已加载")
            except Exception as e:
                logger.error(f"加载DNSPod提供商失败: {e}")
    
    def get_provider(self, provider_name: str) -> Optional[DNSProvider]:
        """获取DNS提供商"""
        return self.providers.get(provider_name)
    
    def add_acme_challenge(self, domain: str, challenge_value: str, 
                          provider_name: str = None) -> bool:
        """
        添加ACME验证记录
        
        Args:
            domain: 域名
            challenge_value: 验证值
            provider_name: DNS提供商名称
            
        Returns:
            bool: 是否成功
        """
        record_name = f"_acme-challenge.{domain}"
        
        # 如果没有指定提供商，尝试所有可用的提供商
        if provider_name:
            providers = [provider_name]
        else:
            providers = list(self.providers.keys())
        
        for prov_name in providers:
            provider = self.get_provider(prov_name)
            if provider:
                try:
                    if provider.add_txt_record(domain, record_name, challenge_value):
                        # 验证记录是否生效
                        if provider.verify_txt_record(record_name, challenge_value):
                            logger.info(f"ACME验证记录添加成功: {record_name}")
                            return True
                except Exception as e:
                    logger.error(f"使用 {prov_name} 添加ACME验证记录失败: {e}")
                    continue
        
        logger.error(f"所有DNS提供商都无法添加ACME验证记录: {record_name}")
        return False
    
    def remove_acme_challenge(self, domain: str, challenge_value: str,
                             provider_name: str = None) -> bool:
        """
        删除ACME验证记录
        
        Args:
            domain: 域名
            challenge_value: 验证值
            provider_name: DNS提供商名称
            
        Returns:
            bool: 是否成功
        """
        record_name = f"_acme-challenge.{domain}"
        
        # 如果没有指定提供商，尝试所有可用的提供商
        if provider_name:
            providers = [provider_name]
        else:
            providers = list(self.providers.keys())
        
        success = False
        for prov_name in providers:
            provider = self.get_provider(prov_name)
            if provider:
                try:
                    if provider.delete_txt_record(domain, record_name, challenge_value):
                        success = True
                        logger.info(f"使用 {prov_name} 删除ACME验证记录成功: {record_name}")
                except Exception as e:
                    logger.error(f"使用 {prov_name} 删除ACME验证记录失败: {e}")
        
        return success
    
    def get_available_providers(self) -> List[str]:
        """获取可用的DNS提供商列表"""
        return list(self.providers.keys())
