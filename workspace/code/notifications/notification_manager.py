"""
通知管理器 - 统一的内部通知+邮件通知调度
对应API文档第9章
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from .email_provider import EmailProvider

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """通知类型"""
    APPROVAL_PENDING = "approval_pending"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_TRANSFERRED = "approval_transferred"
    ONBOARDING_COMPLETED = "onboarding_completed"
    OFFBOARDING_COMPLETED = "offboarding_completed"
    SYSTEM_REMINDER = "system_reminder"


class Channel(str, Enum):
    """通知渠道"""
    IN_APP = "in_app"
    EMAIL = "email"
    BOTH = "both"


@dataclass
class NotificationRecord:
    """通知记录"""
    id: str
    recipient_id: str
    recipient_email: str
    title: str
    content: str
    notification_type: NotificationType
    channel: Channel
    reference_type: Optional[str]
    reference_id: Optional[str]
    is_read: bool = False
    read_at: Optional[int] = None
    created_at: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "recipient_id": self.recipient_id,
            "title": self.title,
            "content": self.content,
            "notification_type": self.notification_type.value,
            "channel": self.channel.value,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "is_read": self.is_read,
            "read_at": self.read_at,
            "created_at": self.created_at,
        }


class NotificationManager:
    """
    通知管理器
    
    负责:
    1. 创建站内通知 (in_app)
    2. 发送邮件通知 (email)
    3. 查看/标记已读
    """

    def __init__(self, email_provider: Optional[EmailProvider] = None):
        self.email_provider = email_provider or EmailProvider()
        self._notifications: dict[str, NotificationRecord] = {}

        # 类型到标题模板的映射
        self._title_templates = {
            NotificationType.APPROVAL_PENDING: "待审批通知",
            NotificationType.APPROVAL_APPROVED: "审批通过通知",
            NotificationType.APPROVAL_REJECTED: "审批驳回通知",
            NotificationType.APPROVAL_TRANSFERRED: "审批转办通知",
            NotificationType.ONBOARDING_COMPLETED: "入职完成通知",
            NotificationType.OFFBOARDING_COMPLETED: "离职完成通知",
            NotificationType.SYSTEM_REMINDER: "系统提醒",
        }

    def send_notification(
        self,
        recipient_id: str,
        recipient_email: str,
        title: str,
        content: str,
        notification_type: NotificationType,
        channel: Channel = Channel.IN_APP,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> dict:
        """
        发送通知
        返回创建的通知记录
        """
        record = NotificationRecord(
            id=str(uuid.uuid4()),
            recipient_id=recipient_id,
            recipient_email=recipient_email,
            title=title,
            content=content,
            notification_type=notification_type,
            channel=channel,
            reference_type=reference_type,
            reference_id=reference_id,
            created_at=int(time.time() * 1000),
        )

        # 保存站内通知
        self._notifications[record.id] = record

        # 如果需要发送邮件
        if channel in (Channel.EMAIL, Channel.BOTH):
            email_body = self._build_email_body(record)
            self.email_provider.send_email(
                to_address=recipient_email,
                subject=title,
                body=email_body,
            )

        logger.info(
            f"通知已发送: {record.id} -> {recipient_id} "
            f"(类型: {notification_type.value}, 渠道: {channel.value})"
        )

        return record.to_dict()

    def send_approval_notification(self, recipient_id: str, recipient_email: str,
                                   employee_name: str, request_type: str,
                                   action: str, step_name: str,
                                   channel: Channel = Channel.BOTH) -> dict:
        """
        快捷发送审批相关通知
        """
        notif_type = NotificationType.APPROVAL_PENDING
        if action == "approve":
            notif_type = NotificationType.APPROVAL_APPROVED
        elif action == "reject":
            notif_type = NotificationType.APPROVAL_REJECTED
        elif action == "transfer":
            notif_type = NotificationType.APPROVAL_TRANSFERRED

        title = self._title_templates.get(notif_type, "审批通知")
        content = f"员工{employee_name}的{self._get_type_name(request_type)}申请已在'{step_name}'步骤{self._get_action_desc(action)}"

        return self.send_notification(
            recipient_id=recipient_id,
            recipient_email=recipient_email,
            title=title,
            content=content,
            notification_type=notif_type,
            channel=channel,
            reference_type=request_type,
        )

    def get_notifications(self, recipient_id: str,
                          is_read: Optional[bool] = None,
                          notification_type: Optional[str] = None,
                          page: int = 1, page_size: int = 20) -> dict:
        """
        查询通知列表
        """
        notifications = list(self._notifications.values())

        # 过滤接收人
        notifications = [n for n in notifications if n.recipient_id == recipient_id]

        # 过滤已读/未读
        if is_read is not None:
            notifications = [n for n in notifications if n.is_read == is_read]

        # 过滤类型
        if notification_type:
            notifications = [
                n for n in notifications
                if n.notification_type.value == notification_type
            ]

        # 按创建时间倒序
        notifications.sort(key=lambda n: n.created_at, reverse=True)

        unread_count = len([n for n in notifications if not n.is_read])
        total = len(notifications)
        start = (page - 1) * page_size
        end = start + page_size
        items = notifications[start:end]

        return {
            "items": [n.to_dict() for n in items],
            "total": total,
            "unread_count": unread_count,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size) if page_size > 0 else 1,
        }

    def mark_as_read(self, notification_id: str, recipient_id: str) -> Optional[dict]:
        """
        标记通知为已读
        """
        record = self._notifications.get(notification_id)
        if not record:
            return None

        if record.recipient_id != recipient_id:
            return None

        record.is_read = True
        record.read_at = int(time.time() * 1000)
        return record.to_dict()

    def batch_mark_as_read(self, notification_ids: list[str],
                           recipient_id: str,
                           mark_all: bool = False) -> int:
        """
        批量标记已读
        """
        count = 0

        if mark_all:
            for record in self._notifications.values():
                if record.recipient_id == recipient_id and not record.is_read:
                    record.is_read = True
                    record.read_at = int(time.time() * 1000)
                    count += 1
            return count

        for nid in notification_ids:
            record = self._notifications.get(nid)
            if record and record.recipient_id == recipient_id and not record.is_read:
                record.is_read = True
                record.read_at = int(time.time() * 1000)
                count += 1

        return count

    def get_unread_count(self, recipient_id: str) -> dict:
        """
        获取未读通知数
        """
        notifications = [
            n for n in self._notifications.values()
            if n.recipient_id == recipient_id and not n.is_read
        ]

        total_unread = len(notifications)
        by_type: dict[str, int] = {}
        for n in notifications:
            t = n.notification_type.value
            by_type[t] = by_type.get(t, 0) + 1

        return {
            "total_unread": total_unread,
            "by_type": by_type,
        }

    def get_notification_by_id(self, notification_id: str) -> Optional[dict]:
        """根据ID获取通知"""
        record = self._notifications.get(notification_id)
        return record.to_dict() if record else None

    def _build_email_body(self, record: NotificationRecord) -> str:
        """构建邮件正文"""
        return (
            f"标题: {record.title}\n"
            f"内容: {record.content}\n"
            f"类型: {record.notification_type.value}\n"
            f"时间: {datetime.fromtimestamp(record.created_at / 1000, tz=timezone.utc)}\n"
        )

    def _get_type_name(self, request_type: str) -> str:
        return "入职" if request_type == "onboarding" else "离职"

    def _get_action_desc(self, action: str) -> str:
        desc_map = {
            "approve": "已通过",
            "reject": "已驳回",
            "transfer": "已转办",
            "pending": "待处理",
        }
        return desc_map.get(action, action)
