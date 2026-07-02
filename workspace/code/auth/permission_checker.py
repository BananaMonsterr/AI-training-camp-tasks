"""权限检查装饰器 - Demo 版（始终允许访问）"""
from functools import wraps
from typing import List, Callable, Optional
from flask import request, g, jsonify


def require_permission(permission: str):
    """
    权限检查装饰器
    Demo 模式：始终允许访问
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(permissions: List[str]):
    """拥有任一权限即可访问 - Demo 模式：始终允许"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


class PermissionDeniedError(Exception):
    """权限不足异常"""
    pass


class PermissionChecker:
    """权限检查器 - 供内部调用"""

    def __init__(self):
        pass

    def check(self, user_id: int, permission: str) -> bool:
        """检查权限 - Demo 模式始终返回 True"""
        return True

    def check_or_fail(self, user_id: int, permission: str) -> bool:
        """检查权限，失败时返回False而非抛异常"""
        return True
