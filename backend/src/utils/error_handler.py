"""
统一错误处理模块
提供API错误处理装饰器和中间件
"""
import logging
import traceback
import functools
from typing import Dict, Any, Callable
from flask import Flask, request, jsonify, g

from .exceptions import (
    BaseAPIException, ErrorCode, ValidationError, 
    AuthenticationError, AuthorizationError,
    ResourceNotFoundError, ResourceConflictError
)

logger = logging.getLogger(__name__)


def handle_api_errors(app: Flask):
    """注册全局错误处理器"""
    
    @app.errorhandler(BaseAPIException)
    def handle_api_exception(error: BaseAPIException):
        """处理API业务异常"""
        logger.warning(f"API业务异常: {error.error_code.name} - {error.message}")
        response_data = error.to_dict()
        return jsonify(response_data), error.http_status
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """处理404错误"""
        return jsonify({
            'code': ErrorCode.NOT_FOUND.value,
            'message': '请求的资源不存在',
            'data': None,
            'suggestions': '请检查URL路径是否正确'
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """处理方法不允许错误"""
        return jsonify({
            'code': ErrorCode.METHOD_NOT_ALLOWED.value,
            'message': f'方法 {request.method} 不被允许',
            'data': None,
            'details': {'allowed_methods': list(error.valid_methods)},
            'suggestions': f'请使用以下方法之一: {", ".join(error.valid_methods)}'
        }), 405
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """处理服务器内部错误"""
        error_id = getattr(g, 'request_id', 'unknown')
        logger.error(f"服务器内部错误 (ID: {error_id}): {str(error)}")
        
        return jsonify({
            'code': ErrorCode.INTERNAL_ERROR.value,
            'message': '服务器内部错误',
            'data': None,
            'details': {'error_id': error_id},
            'suggestions': '请稍后重试，如果问题持续存在请联系技术支持'
        }), 500


def api_error_handler(func: Callable) -> Callable:
    """API错误处理装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BaseAPIException:
            # 重新抛出API异常，由全局处理器处理
            raise
        except ValueError as e:
            # 转换为验证错误
            raise ValidationError(f"参数值错误: {str(e)}")
        except KeyError as e:
            # 转换为验证错误
            raise ValidationError(f"缺少必需参数: {str(e)}")
        except Exception as e:
            # 记录详细错误信息
            logger.error(f"API处理异常: {func.__name__} - {str(e)}")
            # 重新抛出，由全局处理器处理
            raise
    
    return wrapper


def validate_json_request(required_fields: list = None, optional_fields: list = None):
    """JSON请求验证装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                raise ValidationError("请求必须是JSON格式")
            
            try:
                data = request.get_json()
                if data is None:
                    raise ValidationError("请求体不能为空")
            except Exception:
                raise ValidationError("JSON格式错误")
            
            # 验证必需字段
            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field not in data or data[field] is None:
                        missing_fields.append(field)
                
                if missing_fields:
                    raise ValidationError(
                        f"缺少必需字段: {', '.join(missing_fields)}",
                        field_errors={field: "此字段为必需" for field in missing_fields}
                    )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def create_error_response(error_code: ErrorCode, 
                         message: str = None, 
                         details: Dict[str, Any] = None,
                         suggestions: str = None) -> Dict[str, Any]:
    """创建标准错误响应"""
    from .exceptions import ERROR_MESSAGES
    
    return {
        'code': error_code.value,
        'message': message or ERROR_MESSAGES.get(error_code, "未知错误"),
        'data': None,
        'details': details,
        'suggestions': suggestions
    }
