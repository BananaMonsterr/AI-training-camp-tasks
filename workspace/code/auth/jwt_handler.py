"""
JWT Token 处理器 - 对应API文档第4.3节
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from pydantic import BaseModel

from utils.exceptions import TokenExpiredException, UnauthorizedException


# 默认密钥（生产环境应从环境变量读取）
SECRET_KEY = "change-me-in-production-use-env-var-please"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2小时


class TokenPayload(BaseModel):
    """JWT Token 载荷 - 对应API文档4.3节"""
    sub: str           # 用户UUID
    employee_id: str   # 员工ID
    role: str          # 角色
    department_id: str # 部门ID
    username: str      # 用户名
    display_name: str  # 显示名称
    exp: int           # 过期时间戳(秒)
    tenant_id: str = "default"


class JWTHandler:
    """JWT 令牌处理器"""

    def __init__(self, secret_key: str = SECRET_KEY, algorithm: str = ALGORITHM,
                 expire_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def create_token(self, user_id: str, employee_id: str, role: str,
                     department_id: str, username: str, display_name: str,
                     tenant_id: str = "default") -> str:
        """
        创建JWT Token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.expire_minutes)

        payload = {
            "sub": user_id,
            "employee_id": employee_id,
            "role": role,
            "department_id": department_id,
            "username": username,
            "display_name": display_name,
            "tenant_id": tenant_id,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> TokenPayload:
        """
        解码并验证Token
        """
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )
            return TokenPayload(**payload)
        except JWTError as e:
            error_msg = str(e)
            if "expired" in error_msg.lower():
                raise TokenExpiredException()
            raise UnauthorizedException(f"Token无效: {error_msg}")

    def refresh_token(self, token: str) -> str:
        """
        刷新Token（延长有效期）
        """
        payload = self.decode_token(token)
        return self.create_token(
            user_id=payload.sub,
            employee_id=payload.employee_id,
            role=payload.role,
            department_id=payload.department_id,
            username=payload.username,
            display_name=payload.display_name,
            tenant_id=payload.tenant_id,
        )

    def get_current_user(self, token: str) -> TokenPayload:
        """获取当前用户信息（别名）"""
        return self.decode_token(token)
