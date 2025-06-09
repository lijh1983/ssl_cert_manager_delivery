"""
统一异常处理模块
定义系统中所有的异常类型和错误码
"""
from typing import Dict, Any, Optional
from enum import Enum


class ErrorCode(Enum):
    """错误码枚举"""
    # 成功
    SUCCESS = 200
    
    # 客户端错误 (4xx)
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    VALIDATION_ERROR = 422
    RATE_LIMIT_EXCEEDED = 429
    
    # 服务器错误 (5xx)
    INTERNAL_ERROR = 500
    NOT_IMPLEMENTED = 501
    SERVICE_UNAVAILABLE = 503
    
    # 业务错误 (1xxx)
    # 用户认证相关 (10xx)
    USER_NOT_FOUND = 1001
    INVALID_CREDENTIALS = 1002
    TOKEN_EXPIRED = 1003
    TOKEN_INVALID = 1004
    PERMISSION_DENIED = 1005
    ACCOUNT_LOCKED = 1006
    PASSWORD_TOO_WEAK = 1007
    
    # 服务器管理相关 (11xx)
    SERVER_NOT_FOUND = 1101
    SERVER_ALREADY_EXISTS = 1102
    SERVER_OFFLINE = 1103
    SERVER_CONNECTION_FAILED = 1104
    SERVER_REGISTRATION_FAILED = 1105
    INVALID_SERVER_TOKEN = 1106
    SERVER_QUOTA_EXCEEDED = 1107
    
    # 证书管理相关 (12xx)
    CERTIFICATE_NOT_FOUND = 1201
    CERTIFICATE_ALREADY_EXISTS = 1202
    CERTIFICATE_EXPIRED = 1203
    CERTIFICATE_INVALID = 1204
    CERTIFICATE_REQUEST_FAILED = 1205
    CERTIFICATE_RENEWAL_FAILED = 1206
    CERTIFICATE_REVOCATION_FAILED = 1207
    CERTIFICATE_DEPLOYMENT_FAILED = 1208
    CERTIFICATE_VALIDATION_FAILED = 1209
    CERTIFICATE_QUOTA_EXCEEDED = 1210
    
    # ACME协议相关 (13xx)
    ACME_CLIENT_ERROR = 1301
    ACME_ACCOUNT_ERROR = 1302
    ACME_CHALLENGE_FAILED = 1303
    ACME_ORDER_FAILED = 1304
    ACME_RATE_LIMIT = 1305
    ACME_NETWORK_ERROR = 1306
    ACME_DNS_ERROR = 1307
    ACME_TIMEOUT = 1308
    ACME_INVALID_DOMAIN = 1309
    ACME_CA_UNAVAILABLE = 1310

    # 安全相关 (14xx)
    CSRF_TOKEN_MISSING = 1401
    CSRF_TOKEN_INVALID = 1402


class BaseAPIException(Exception):
    """API异常基类"""
    
    def __init__(self, 
                 error_code: ErrorCode, 
                 message: str = None, 
                 details: Dict[str, Any] = None,
                 suggestions: str = None,
                 http_status: int = None):
        self.error_code = error_code
        self.message = message or self._get_default_message()
        self.details = details or {}
        self.suggestions = suggestions
        self.http_status = http_status or self._get_default_http_status()
        super().__init__(self.message)
    
    def _get_default_message(self) -> str:
        """获取默认错误消息"""
        return ERROR_MESSAGES.get(self.error_code, "未知错误")
    
    def _get_default_http_status(self) -> int:
        """获取默认HTTP状态码"""
        code_value = self.error_code.value
        if code_value < 1000:
            return code_value
        elif 1000 <= code_value < 2000:
            return 400  # 业务错误默认返回400
        else:
            return 500
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'code': self.error_code.value,
            'message': self.message,
            'data': None
        }
        
        if self.details:
            result['details'] = self.details
        
        if self.suggestions:
            result['suggestions'] = self.suggestions
            
        return result


# 具体异常类
class ValidationError(BaseAPIException):
    """数据验证异常"""
    def __init__(self, message: str = None, field_errors: Dict[str, str] = None):
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message or "数据验证失败",
            details={'field_errors': field_errors} if field_errors else None,
            suggestions="请检查输入数据的格式和内容"
        )


class AuthenticationError(BaseAPIException):
    """认证异常"""
    def __init__(self, error_code: ErrorCode = ErrorCode.UNAUTHORIZED, message: str = None):
        super().__init__(
            error_code=error_code,
            message=message,
            suggestions="请检查用户名和密码，或重新登录"
        )


class AuthorizationError(BaseAPIException):
    """授权异常"""
    def __init__(self, message: str = None):
        super().__init__(
            error_code=ErrorCode.PERMISSION_DENIED,
            message=message or "权限不足",
            suggestions="请联系管理员获取相应权限"
        )


class ResourceNotFoundError(BaseAPIException):
    """资源不存在异常"""
    def __init__(self, resource_type: str, resource_id: Any = None):
        message = f"{resource_type}不存在"
        if resource_id:
            message += f" (ID: {resource_id})"
        
        super().__init__(
            error_code=ErrorCode.NOT_FOUND,
            message=message,
            details={'resource_type': resource_type, 'resource_id': resource_id},
            suggestions="请检查资源ID是否正确"
        )


class ResourceConflictError(BaseAPIException):
    """资源冲突异常"""
    def __init__(self, resource_type: str, conflict_field: str = None):
        message = f"{resource_type}已存在"
        if conflict_field:
            message += f" ({conflict_field}冲突)"
        
        super().__init__(
            error_code=ErrorCode.CONFLICT,
            message=message,
            details={'resource_type': resource_type, 'conflict_field': conflict_field},
            suggestions="请使用不同的标识符或检查是否重复创建"
        )


class ACMEError(BaseAPIException):
    """ACME协议相关异常"""
    def __init__(self, error_code: ErrorCode, message: str = None, acme_details: Dict[str, Any] = None):
        super().__init__(
            error_code=error_code,
            message=message,
            details=acme_details,
            suggestions=self._get_acme_suggestions(error_code)
        )
    
    def _get_acme_suggestions(self, error_code: ErrorCode) -> str:
        """获取ACME错误的解决建议"""
        suggestions_map = {
            ErrorCode.ACME_DNS_ERROR: "请检查域名DNS配置是否正确",
            ErrorCode.ACME_CHALLENGE_FAILED: "请确保域名可以正常访问，并检查防火墙设置",
            ErrorCode.ACME_RATE_LIMIT: "请等待一段时间后重试，或考虑使用其他CA",
            ErrorCode.ACME_NETWORK_ERROR: "请检查网络连接和防火墙设置",
            ErrorCode.ACME_TIMEOUT: "请检查网络连接，或稍后重试",
            ErrorCode.ACME_INVALID_DOMAIN: "请检查域名格式是否正确",
        }
        return suggestions_map.get(error_code, "请查看详细错误信息并联系技术支持")


class CertificateError(BaseAPIException):
    """证书相关异常"""
    def __init__(self, error_code: ErrorCode, message: str = None, domain: str = None):
        details = {'domain': domain} if domain else None
        super().__init__(
            error_code=error_code,
            message=message,
            details=details,
            suggestions=self._get_certificate_suggestions(error_code)
        )
    
    def _get_certificate_suggestions(self, error_code: ErrorCode) -> str:
        """获取证书错误的解决建议"""
        suggestions_map = {
            ErrorCode.CERTIFICATE_REQUEST_FAILED: "请检查域名配置和网络连接",
            ErrorCode.CERTIFICATE_RENEWAL_FAILED: "请检查证书状态和域名配置",
            ErrorCode.CERTIFICATE_DEPLOYMENT_FAILED: "请检查服务器连接和权限配置",
            ErrorCode.CERTIFICATE_EXPIRED: "请及时续期证书",
            ErrorCode.CERTIFICATE_INVALID: "请重新申请证书",
        }
        return suggestions_map.get(error_code, "请查看证书详细信息并联系技术支持")


# 错误消息映射
ERROR_MESSAGES = {
    # HTTP状态码
    ErrorCode.BAD_REQUEST: "请求参数错误",
    ErrorCode.UNAUTHORIZED: "未认证或认证失败",
    ErrorCode.FORBIDDEN: "权限不足",
    ErrorCode.NOT_FOUND: "请求的资源不存在",
    ErrorCode.METHOD_NOT_ALLOWED: "请求方法不被允许",
    ErrorCode.CONFLICT: "资源冲突",
    ErrorCode.VALIDATION_ERROR: "数据验证失败",
    ErrorCode.RATE_LIMIT_EXCEEDED: "请求频率超限",
    ErrorCode.INTERNAL_ERROR: "服务器内部错误",
    ErrorCode.NOT_IMPLEMENTED: "功能未实现",
    ErrorCode.SERVICE_UNAVAILABLE: "服务暂时不可用",
    
    # 用户认证相关
    ErrorCode.USER_NOT_FOUND: "用户不存在",
    ErrorCode.INVALID_CREDENTIALS: "用户名或密码错误",
    ErrorCode.TOKEN_EXPIRED: "登录令牌已过期",
    ErrorCode.TOKEN_INVALID: "登录令牌无效",
    ErrorCode.PERMISSION_DENIED: "权限不足",
    ErrorCode.ACCOUNT_LOCKED: "账户已被锁定",
    ErrorCode.PASSWORD_TOO_WEAK: "密码强度不足",
    
    # 服务器管理相关
    ErrorCode.SERVER_NOT_FOUND: "服务器不存在",
    ErrorCode.SERVER_ALREADY_EXISTS: "服务器已存在",
    ErrorCode.SERVER_OFFLINE: "服务器离线",
    ErrorCode.SERVER_CONNECTION_FAILED: "服务器连接失败",
    ErrorCode.SERVER_REGISTRATION_FAILED: "服务器注册失败",
    ErrorCode.INVALID_SERVER_TOKEN: "服务器令牌无效",
    ErrorCode.SERVER_QUOTA_EXCEEDED: "服务器数量超出限制",
    
    # 证书管理相关
    ErrorCode.CERTIFICATE_NOT_FOUND: "证书不存在",
    ErrorCode.CERTIFICATE_ALREADY_EXISTS: "证书已存在",
    ErrorCode.CERTIFICATE_EXPIRED: "证书已过期",
    ErrorCode.CERTIFICATE_INVALID: "证书无效",
    ErrorCode.CERTIFICATE_REQUEST_FAILED: "证书申请失败",
    ErrorCode.CERTIFICATE_RENEWAL_FAILED: "证书续期失败",
    ErrorCode.CERTIFICATE_REVOCATION_FAILED: "证书撤销失败",
    ErrorCode.CERTIFICATE_DEPLOYMENT_FAILED: "证书部署失败",
    ErrorCode.CERTIFICATE_VALIDATION_FAILED: "证书验证失败",
    ErrorCode.CERTIFICATE_QUOTA_EXCEEDED: "证书数量超出限制",
    
    # ACME协议相关
    ErrorCode.ACME_CLIENT_ERROR: "ACME客户端错误",
    ErrorCode.ACME_ACCOUNT_ERROR: "ACME账户错误",
    ErrorCode.ACME_CHALLENGE_FAILED: "ACME验证失败",
    ErrorCode.ACME_ORDER_FAILED: "ACME订单失败",
    ErrorCode.ACME_RATE_LIMIT: "ACME请求频率超限",
    ErrorCode.ACME_NETWORK_ERROR: "ACME网络错误",
    ErrorCode.ACME_DNS_ERROR: "DNS解析错误",
    ErrorCode.ACME_TIMEOUT: "ACME请求超时",
    ErrorCode.ACME_INVALID_DOMAIN: "域名格式无效",
    ErrorCode.ACME_CA_UNAVAILABLE: "CA服务不可用",

    # 安全相关
    ErrorCode.CSRF_TOKEN_MISSING: "CSRF令牌缺失",
    ErrorCode.CSRF_TOKEN_INVALID: "CSRF令牌无效",
}
