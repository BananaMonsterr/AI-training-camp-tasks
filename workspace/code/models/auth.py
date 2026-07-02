"""
用户认证与角色模型
"""

import enum
from typing import Optional

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, generate_uuid


class RoleType(str, enum.Enum):
    """角色类型 - 对应API文档第4.2节权限矩阵"""
    ADMIN = "admin"
    HR_MANAGER = "hr_manager"
    HR_STAFF = "hr_staff"
    DEPT_MANAGER = "dept_manager"
    EMPLOYEE = "employee"


class UserModel(Base, TimestampMixin):
    """用户模型"""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    username: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, comment="用户名"
    )
    password_hash: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="密码哈希"
    )
    employee_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="关联员工ID"
    )
    role: Mapped[RoleType] = mapped_column(
        Enum(RoleType, name="user_role"),
        default=RoleType.EMPLOYEE,
        nullable=False,
        comment="用户角色",
    )
    department_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="所属部门ID"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否激活"
    )
    display_name: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="显示名称"
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="邮箱"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role.value})>"


class RoleModel(Base, TimestampMixin):
    """角色权限模型（细粒度权限控制）"""
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    name: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="角色名称"
    )
    code: Mapped[RoleType] = mapped_column(
        Enum(RoleType, name="role_code"),
        unique=True,
        nullable=False,
        comment="角色编码",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="角色描述"
    )
    permissions: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="权限列表(JSON格式)"
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, code={self.code.value})>"


class UserRoleModel(Base, TimestampMixin):
    """用户-角色关联模型（支持多角色）"""
    __tablename__ = "user_roles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    user_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="用户ID"
    )
    role_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="角色ID"
    )

    def __repr__(self) -> str:
        return f"<UserRole(user={self.user_id}, role={self.role_id})>"
