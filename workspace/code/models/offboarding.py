"""
离职申请数据模型 - 对应API文档第7.1节
"""

import enum
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Date, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, generate_uuid


class OffboardingStatus(str, enum.Enum):
    """离职申请状态"""
    DRAFT = "draft"
    PENDING_DEPT_REVIEW = "pending_dept_review"
    PENDING_HR_REVIEW = "pending_hr_review"
    PENDING_EXIT_INTERVIEW = "pending_exit_interview"
    PENDING_ASSET_RETURN = "pending_asset_return"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ResignationType(str, enum.Enum):
    """离职类型"""
    VOLUNTARY = "voluntary"
    INVOLUNTARY = "involuntary"
    RETIREMENT = "retirement"
    CONTRACT_END = "contract_end"


class AssetReturnStatus(str, enum.Enum):
    """资产归还状态"""
    PENDING = "pending"
    PARTIAL = "partial"
    COMPLETED = "completed"


class OffboardingRequestModel(Base, TimestampMixin):
    """离职申请模型"""
    __tablename__ = "offboarding_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="关联员工ID"
    )
    applicant_id: Mapped[str] = mapped_column(
        String(36), nullable=False, comment="申请人ID"
    )
    resignation_type: Mapped[ResignationType] = mapped_column(
        Enum(ResignationType, name="resignation_type"),
        nullable=False,
        comment="离职类型",
    )
    reason: Mapped[str] = mapped_column(
        Text, nullable=False, comment="离职原因"
    )
    expected_last_work_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="预计最后工作日"
    )
    handover_note: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="交接说明"
    )
    asset_return_status: Mapped[AssetReturnStatus] = mapped_column(
        Enum(AssetReturnStatus, name="asset_return_status"),
        default=AssetReturnStatus.PENDING,
        nullable=False,
        comment="资产归还状态",
    )
    status: Mapped[OffboardingStatus] = mapped_column(
        Enum(OffboardingStatus, name="offboarding_status"),
        default=OffboardingStatus.DRAFT,
        nullable=False,
        comment="申请状态",
    )
    current_step: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="当前审批步骤"
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="提交时间"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["expected_last_work_date"] = (
            self.expected_last_work_date.isoformat()
            if self.expected_last_work_date else None
        )
        return result

    def __repr__(self) -> str:
        return f"<OffboardingRequest(id={self.id}, status={self.status.value})>"
