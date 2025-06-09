"""
统一日志配置模块
提供结构化日志记录功能
"""
import os
import sys
import json
import logging
import logging.config
from datetime import datetime
from typing import Dict, Any, Optional
from flask import g, request, has_request_context


class JSONFormatter(logging.Formatter):
    """JSON格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为JSON"""
        # 基础日志信息
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # 添加请求上下文信息
        if has_request_context():
            try:
                log_data.update({
                    'request_id': getattr(g, 'request_id', None),
                    'user_id': getattr(g, 'user_id', None),
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'url': request.url,
                    'remote_addr': request.remote_addr,
                })
            except RuntimeError:
                # 在应用上下文之外，忽略请求信息
                pass
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # 添加额外字段
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log_with_extra(self, level: int, message: str, **kwargs):
        """带额外字段的日志记录"""
        extra_fields = {}
        
        # 提取标准字段
        for key, value in kwargs.items():
            if key in ['user_id', 'request_id', 'operation', 'resource_type', 
                      'resource_id', 'error_code', 'duration', 'status_code']:
                extra_fields[key] = value
        
        # 创建LogRecord并添加额外字段
        if extra_fields:
            self.logger._log(level, message, (), extra={'extra_fields': extra_fields})
        else:
            self.logger._log(level, message, ())
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._log_with_extra(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self._log_with_extra(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._log_with_extra(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        self._log_with_extra(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self._log_with_extra(logging.CRITICAL, message, **kwargs)
    
    def audit(self, action: str, resource_type: str, resource_id: Any = None, 
             result: str = 'success', **kwargs):
        """审计日志"""
        audit_data = {
            'audit': True,
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'result': result,
            **kwargs
        }
        self._log_with_extra(logging.INFO, f"审计: {action} {resource_type}", **audit_data)
    
    def performance(self, operation: str, duration: float, **kwargs):
        """性能日志"""
        perf_data = {
            'performance': True,
            'operation': operation,
            'duration': duration,
            **kwargs
        }
        self._log_with_extra(logging.INFO, f"性能: {operation} 耗时 {duration:.3f}s", **perf_data)
    
    def security(self, event: str, severity: str = 'medium', **kwargs):
        """安全日志"""
        security_data = {
            'security': True,
            'event': event,
            'severity': severity,
            **kwargs
        }
        self._log_with_extra(logging.WARNING, f"安全事件: {event}", **security_data)


def setup_logging(app_name: str = 'ssl_cert_manager', 
                 log_level: str = None, 
                 log_file: str = None,
                 enable_console: bool = True) -> None:
    """
    设置应用日志配置
    """
    # 确定日志级别
    if log_level is None:
        log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # 确定日志文件路径
    if log_file is None:
        log_dir = os.environ.get('LOG_DIR', '/tmp/logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'{app_name}.log')
    
    # 创建日志目录
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # 日志配置
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': JSONFormatter,
            },
            'simple': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        },
        'handlers': {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': log_file,
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 5,
                'formatter': 'json',
                'level': log_level,
            }
        },
        'loggers': {
            app_name: {
                'level': log_level,
                'handlers': ['file'],
                'propagate': False
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['file']
        }
    }
    
    # 添加控制台处理器
    if enable_console:
        config['handlers']['console'] = {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'simple',
            'level': log_level,
        }
        
        # 为所有日志器添加控制台处理器
        for logger_config in config['loggers'].values():
            logger_config['handlers'].append('console')
        config['root']['handlers'].append('console')
    
    # 应用配置
    logging.config.dictConfig(config)


def get_logger(name: str) -> StructuredLogger:
    """获取结构化日志记录器"""
    return StructuredLogger(name)


def init_logging_middleware(app):
    """初始化日志中间件"""
    @app.before_request
    def add_request_id():
        """为每个请求添加唯一ID"""
        import uuid
        if not hasattr(g, 'request_id'):
            g.request_id = str(uuid.uuid4())[:8]
    
    @app.after_request
    def log_response_info(response):
        """记录响应信息"""
        logger = get_logger('response')
        logger.info(
            f"Response {response.status_code}",
            request_id=getattr(g, 'request_id', None),
            status_code=response.status_code
        )
        return response
