"""
员工数据模型 - 对应API文档第5.1节
"""

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, generate_uuid, utc_now


class EmployeeStatus(str, enum.Enum):
    """员工在职状态"""
    ACTIVE = "active"
    ONBOARDING = "onboarding"
    OFFBOARDING = "offboarding"
    TERMINATED = "terminated"
    SUSPENDED = "suspended"


class EmploymentType(str, enum.Enum):
    """雇佣类型"""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    INTERN = "intern"
    CONTRACTOR = "contractor"


class EmployeeModel(Base, TimestampMixin):
    """员工模型"""
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    employee_no: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True,
        comment="工号（唯一）"
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="姓名")
    id_card: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="身份证号（加密存储）"
    )
    email: Mapped[str] = mapped_column(String(128), nullable=False, comment="邮箱")
    phone: Mapped[str] = mapped_column(String(20), nullable=False, comment="手机号")
    department_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="所属部门ID"
    )
    position: Mapped[str] = mapped_column(String(64), nullable=False, comment="职位")
    hire_date: Mapped[date] = mapped_column(Date, nullable=False, comment="入职日期")
    status: Mapped[EmployeeStatus] = mapped_column(
        Enum(EmployeeStatus, name="employee_status"),
        default=EmployeeStatus.ONBOARDING,
        nullable=False,
        comment="在职状态",
    )
    manager_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="直属上级ID"
    )
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(EmploymentType, name="employment_type"),
        default=EmploymentType.FULL_TIME,
        nullable=False,
        comment="雇佣类型",
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="逻辑删除标记"
    )

    def to_dict(self, sensitive: bool = False) -> dict:
        """转换为字典，支持敏感字段控制"""
        result = super().to_dict()
        result["hire_date"] = self.hire_date.isoformat() if self.hire_date else None

        if not sensitive:
            # 脱敏处理
            from utils.sensitive import mask_id_card, mask_phone, mask_email
            result["id_card"] = mask_id_card(self.id_card)
            result["phone"] = mask_phone(self.phone)
            result["email"] = mask_email(self.email)

        return result

    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, no={self.employee_no}, name={self.name})>"
