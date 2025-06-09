"""
速率限制模块
提供API请求频率限制功能，防止滥用和DDoS攻击
"""
import time
import json
from typing import Dict, List, Optional, Tuple, Callable
from functools import wraps
from collections import defaultdict, deque
from flask import Flask, request, jsonify, g
from utils.exceptions import ValidationError, ErrorCode
from utils.logging_config import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.storage = defaultdict(lambda: defaultdict(deque))
        self.rules = {}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """初始化应用"""
        self.app = app
        
        # 配置默认限制规则
        app.config.setdefault('RATE_LIMIT_STORAGE_URL', 'memory://')
        app.config.setdefault('RATE_LIMIT_STRATEGY', 'fixed-window')
        
        # 注册请求处理器
        app.before_request(self._before_request)
        
        logger.info("速率限制器已初始化")
    
    def _before_request(self):
        """请求前处理"""
        # 清理过期的记录
        self._cleanup_expired_records()
    
    def _cleanup_expired_records(self):
        """清理过期的记录"""
        current_time = time.time()
        
        # 每100次请求清理一次
        if hasattr(g, 'cleanup_counter'):
            g.cleanup_counter += 1
        else:
            g.cleanup_counter = 1
        
        if g.cleanup_counter % 100 == 0:
            for client_id in list(self.storage.keys()):
                for rule_key in list(self.storage[client_id].keys()):
                    window = self.storage[client_id][rule_key]
                    # 清理1小时前的记录
                    while window and window[0] < current_time - 3600:
                        window.popleft()
                    
                    # 如果窗口为空，删除该规则
                    if not window:
                        del self.storage[client_id][rule_key]
                
                # 如果客户端没有任何记录，删除该客户端
                if not self.storage[client_id]:
                    del self.storage[client_id]
    
    def _get_client_id(self) -> str:
        """获取客户端标识"""
        # 优先使用用户ID
        if hasattr(g, 'user') and g.user:
            return f"user:{g.user.id}"
        
        # 使用IP地址
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if client_ip:
            # 处理多个IP的情况
            client_ip = client_ip.split(',')[0].strip()
        
        return f"ip:{client_ip}"
    
    def _get_rule_key(self, endpoint: str, method: str) -> str:
        """获取规则键"""
        return f"{method}:{endpoint}"
    
    def is_allowed(self, rule_key: str, limit: int, window: int) -> Tuple[bool, Dict]:
        """检查是否允许请求"""
        client_id = self._get_client_id()
        current_time = time.time()
        
        # 获取客户端的请求记录
        requests = self.storage[client_id][rule_key]
        
        # 清理窗口外的请求
        window_start = current_time - window
        while requests and requests[0] < window_start:
            requests.popleft()
        
        # 检查是否超过限制
        current_count = len(requests)
        allowed = current_count < limit
        
        if allowed:
            # 记录当前请求
            requests.append(current_time)
        
        # 计算重置时间
        reset_time = int(current_time + window)
        if requests:
            # 使用最早请求的时间计算重置时间
            reset_time = int(requests[0] + window)
        
        return allowed, {
            'limit': limit,
            'remaining': max(0, limit - current_count - (1 if allowed else 0)),
            'reset': reset_time,
            'retry_after': max(0, reset_time - int(current_time)) if not allowed else 0
        }
    
    def limit(self, rate: str, per: int = 60, key_func: Optional[Callable] = None):
        """速率限制装饰器
        
        Args:
            rate: 限制速率，如 "10/minute", "100/hour"
            per: 时间窗口（秒），默认60秒
            key_func: 自定义键函数
        """
        # 解析速率字符串
        if isinstance(rate, str) and '/' in rate:
            limit_str, period_str = rate.split('/')
            limit = int(limit_str)
            
            period_map = {
                'second': 1,
                'minute': 60,
                'hour': 3600,
                'day': 86400
            }
            
            per = period_map.get(period_str, per)
        else:
            limit = int(rate)
        
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # 获取规则键
                if key_func:
                    rule_key = key_func()
                else:
                    rule_key = self._get_rule_key(request.endpoint or 'unknown', request.method)
                
                # 检查是否允许请求
                allowed, info = self.is_allowed(rule_key, limit, per)
                
                if not allowed:
                    logger.warning(
                        f"速率限制触发 - 客户端: {self._get_client_id()}, "
                        f"规则: {rule_key}, 限制: {limit}/{per}s"
                    )
                    
                    response = jsonify({
                        'code': 429,
                        'message': '请求过于频繁，请稍后再试',
                        'data': {
                            'rate_limit': info
                        }
                    })
                    response.status_code = 429
                    response.headers['X-RateLimit-Limit'] = str(info['limit'])
                    response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
                    response.headers['X-RateLimit-Reset'] = str(info['reset'])
                    response.headers['Retry-After'] = str(info['retry_after'])
                    
                    return response
                
                # 执行原函数
                response = f(*args, **kwargs)
                
                # 添加速率限制头
                if hasattr(response, 'headers'):
                    response.headers['X-RateLimit-Limit'] = str(info['limit'])
                    response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
                    response.headers['X-RateLimit-Reset'] = str(info['reset'])
                
                return response
            
            return decorated_function
        return decorator


# 全局速率限制器实例
rate_limiter = RateLimiter()


def init_rate_limiter(app: Flask):
    """初始化速率限制器"""
    rate_limiter.init_app(app)


def rate_limit(rate: str, per: int = 60, key_func: Optional[Callable] = None):
    """速率限制装饰器"""
    return rate_limiter.limit(rate, per, key_func)


# 预定义的限制级别
def strict_rate_limit(f):
    """严格限流：每分钟5次，每小时20次"""
    @rate_limit("5/minute")
    @rate_limit("20/hour")
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


def moderate_rate_limit(f):
    """中等限流：每分钟20次，每小时100次"""
    @rate_limit("20/minute")
    @rate_limit("100/hour")
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


def loose_rate_limit(f):
    """宽松限流：每分钟60次，每小时500次"""
    @rate_limit("60/minute")
    @rate_limit("500/hour")
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function


def api_rate_limit(f):
    """API限流：每分钟30次，每小时200次"""
    @rate_limit("30/minute")
    @rate_limit("200/hour")
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function
