"""
入职申请数据模型 - 对应API文档第6.1节
"""

import enum
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Date, DateTime, Enum, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, generate_uuid


class OnboardingStatus(str, enum.Enum):
    """入职申请状态"""
    DRAFT = "draft"
    PENDING_HR_REVIEW = "pending_hr_review"
    PENDING_DEPT_REVIEW = "pending_dept_review"
    PENDING_IT_PREPARE = "pending_it_prepare"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class OnboardingRequestModel(Base, TimestampMixin):
    """入职申请模型"""
    __tablename__ = "onboarding_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="关联员工ID"
    )
    applicant_id: Mapped[str] = mapped_column(
        String(36), nullable=False, comment="申请人ID"
    )
    offer_letter_url: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="录用通知书附件URL"
    )
    expected_hire_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="预计入职日期"
    )
    equipment_required: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, default=list, comment="所需设备清单"
    )
    seat_location: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, comment="座位位置"
    )
    status: Mapped[OnboardingStatus] = mapped_column(
        Enum(OnboardingStatus, name="onboarding_status"),
        default=OnboardingStatus.DRAFT,
        nullable=False,
        comment="申请状态",
    )
    current_step: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="当前审批步骤"
    )
    remark: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="备注"
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="提交时间"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["expected_hire_date"] = self.expected_hire_date.isoformat() if self.expected_hire_date else None
        if self.equipment_required is None:
            result["equipment_required"] = []
        return result

    def __repr__(self) -> str:
        return f"<OnboardingRequest(id={self.id}, status={self.status.value})>"
