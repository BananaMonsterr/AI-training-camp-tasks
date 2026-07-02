"""
通知数据模型 - 对应API文档第9.1节
"""

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, generate_uuid


class NotificationType(str, enum.Enum):
    """通知类型"""
    APPROVAL_PENDING = "approval_pending"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_TRANSFERRED = "approval_transferred"
    ONBOARDING_COMPLETED = "onboarding_completed"
    OFFBOARDING_COMPLETED = "offboarding_completed"
    SYSTEM_REMINDER = "system_reminder"


class NotificationChannel(str, enum.Enum):
    """通知渠道"""
    IN_APP = "in_app"
    EMAIL = "email"
    BOTH = "both"


class NotificationModel(Base, TimestampMixin):
    """通知模型"""
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    recipient_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="接收人ID"
    )
    title: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="通知标题"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="通知内容"
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"),
        nullable=False,
        comment="通知类型",
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel"),
        default=NotificationChannel.IN_APP,
        nullable=False,
        comment="发送渠道",
    )
    reference_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="关联业务类型"
    )
    reference_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="关联业务ID"
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否已读"
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="读取时间"
    )

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["is_read"] = self.is_read
        result["read_at"] = int(self.read_at.timestamp() * 1000) if self.read_at else None
        return result

    def mark_as_read(self) -> None:
        """标记为已读"""
        from datetime import timezone
        self.is_read = True
        self.read_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, type={self.notification_type.value}, read={self.is_read})>"
