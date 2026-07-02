"""
审批流数据模型 - 对应API文档第8.1节
"""

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, generate_uuid


class FlowType(str, enum.Enum):
    """流程类型"""
    ONBOARDING = "onboarding"
    OFFBOARDING = "offboarding"


class ApprovalAction(str, enum.Enum):
    """审批动作"""
    APPROVE = "approve"
    REJECT = "reject"
    TRANSFER = "transfer"
    SKIP = "skip"


class RecordStatus(str, enum.Enum):
    """审批记录状态"""
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class ApprovalFlowModel(Base, TimestampMixin):
    """审批流模板模型"""
    __tablename__ = "approval_flows"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    flow_type: Mapped[FlowType] = mapped_column(
        Enum(FlowType, name="flow_type"),
        nullable=False,
        comment="流程类型",
    )
    name: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="流程名称"
    )
    steps: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list, comment="审批步骤定义"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否启用"
    )
    version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="版本号"
    )

    def to_dict(self) -> dict[str, Any]:
        return super().to_dict()

    def __repr__(self) -> str:
        return f"<ApprovalFlow(id={self.id}, name={self.name}, type={self.flow_type.value})>"


class ApprovalRecordModel(Base, TimestampMixin):
    """审批记录模型"""
    __tablename__ = "approval_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    flow_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="关联流程ID"
    )
    request_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="关联申请ID"
    )
    request_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="申请类型: onboarding/offboarding"
    )
    step_key: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="步骤标识"
    )
    step_name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="步骤名称"
    )
    assignee_id: Mapped[str] = mapped_column(
        String(36), nullable=False, comment="审批人ID"
    )
    assignee_name: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="审批人姓名"
    )
    action: Mapped[Optional[ApprovalAction]] = mapped_column(
        Enum(ApprovalAction, name="approval_action"),
        nullable=True,
        comment="审批动作",
    )
    comment: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="审批意见"
    )
    operated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="操作时间"
    )
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status"),
        default=RecordStatus.PENDING,
        nullable=False,
        comment="记录状态",
    )
    transfer_from_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="转办来源人ID"
    )

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["action"] = self.action.value if self.action else None
        result["status"] = self.status.value
        return result

    def __repr__(self) -> str:
        return (
            f"<ApprovalRecord(id={self.id}, step={self.step_key}, "
            f"status={self.status.value})>"
        )
