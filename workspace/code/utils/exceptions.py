"""
自定义异常体系 - 与API设计文档第3章错误码一一对应
"""

from typing import Any, Optional


class AppException(Exception):
    """基础业务异常"""

    def __init__(self, code: int, message: str, status_code: int = 400,
                 details: Optional[dict] = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# ─── 4xx 客户端错误 ─────────────────────────────────

class BadRequestException(AppException):
    """40000 请求格式错误"""
    def __init__(self, message: str = "请求格式错误", details: Optional[dict] = None):
        super().__init__(40000, message, 400, details)


class ValidationException(AppException):
    """40001 参数校验失败"""
    def __init__(self, message: str = "参数校验失败", details: Optional[dict] = None):
        super().__init__(40001, message, 400, details)


class InvalidEnumValueException(AppException):
    """40002 枚举值无效"""
    def __init__(self, message: str = "枚举值无效", details: Optional[dict] = None):
        super().__init__(40002, message, 400, details)


class InvalidDateFormatException(AppException):
    """40003 日期格式错误"""
    def __init__(self, message: str = "日期格式错误", details: Optional[dict] = None):
        super().__init__(40003, message, 400, details)


class ResourceAlreadyExistsException(AppException):
    """40004 资源已存在"""
    def __init__(self, message: str = "资源已存在", details: Optional[dict] = None):
        super().__init__(40004, message, 409, details)


class UnauthorizedException(AppException):
    """40100 未认证"""
    def __init__(self, message: str = "未认证，Token缺失或无效"):
        super().__init__(40100, message, 401)


class TokenExpiredException(AppException):
    """40101 Token已过期"""
    def __init__(self, message: str = "Token已过期"):
        super().__init__(40101, message, 401)


class ForbiddenException(AppException):
    """40300 无权限访问"""
    def __init__(self, message: str = "无权限访问"):
        super().__init__(40300, message, 403)


class RoleRequiredException(AppException):
    """40301 需要特定角色"""
    def __init__(self, message: str = "需要特定角色才能执行此操作"):
        super().__init__(40301, message, 403)


class NotFoundException(AppException):
    """40400 资源不存在"""
    def __init__(self, message: str = "资源不存在", details: Optional[dict] = None):
        super().__init__(40400, message, 404, details)


class EmployeeNotFoundException(AppException):
    """40401 员工不存在"""
    def __init__(self, message: str = "员工不存在"):
        super().__init__(40401, message, 404)


class FlowNotFoundException(AppException):
    """40402 审批流不存在"""
    def __init__(self, message: str = "审批流不存在"):
        super().__init__(40402, message, 404)


class ConflictException(AppException):
    """40900 资源冲突"""
    def __init__(self, message: str = "资源冲突", details: Optional[dict] = None):
        super().__init__(40900, message, 409, details)


class StatusConflictException(AppException):
    """40901 当前状态不允许该操作"""
    def __init__(self, message: str = "当前状态不允许该操作"):
        super().__init__(40901, message, 409)


class UnprocessableEntityException(AppException):
    """42200 业务逻辑校验失败"""
    def __init__(self, message: str = "业务逻辑校验失败", details: Optional[dict] = None):
        super().__init__(42200, message, 422, details)


class RateLimitExceededException(AppException):
    """42900 请求频率超限"""
    def __init__(self, message: str = "请求频率超限"):
        super().__init__(42900, message, 429)


class InternalException(AppException):
    """50000 服务器内部错误"""
    def __init__(self, message: str = "服务器内部错误", details: Optional[dict] = None):
        super().__init__(50000, message, 500, details)
