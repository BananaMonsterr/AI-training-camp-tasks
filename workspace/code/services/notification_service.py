"""
通知管理服务 - 对应API文档第9章
"""

from typing import Optional

from notifications.notification_manager import NotificationManager, NotificationType, Channel
from utils.exceptions import NotFoundException, ValidationException


class NotificationService:
    """
    通知管理服务
    
    职责:
    1. 查询通知列表
    2. 标记已读/批量已读
    3. 未读数统计
    4. 发送通知（内部接口）
    """

    def __init__(self, notification_manager: Optional[NotificationManager] = None):
        self.manager = notification_manager or NotificationManager()

    def get_notifications(self, recipient_id: str,
                          is_read: Optional[bool] = None,
                          notification_type: Optional[str] = None,
                          page: int = 1, page_size: int = 20) -> dict:
        """
        查询通知列表 - 对应API文档9.2.1
        """
        return self.manager.get_notifications(
            recipient_id=recipient_id,
            is_read=is_read,
            notification_type=notification_type,
            page=page,
            page_size=page_size,
        )

    def mark_as_read(self, notification_id: str,
                     recipient_id: str) -> dict:
        """
        标记已读 - 对应API文档9.2.2
        """
        result = self.manager.mark_as_read(notification_id, recipient_id)
        if not result:
            raise NotFoundException(f"通知不存在: {notification_id}")
        return result

    def batch_mark_as_read(self, notification_ids: list[str],
                           recipient_id: str,
                           mark_all: bool = False) -> dict:
        """
        批量标记已读 - 对应API文档9.2.3
        """
        count = self.manager.batch_mark_as_read(
            notification_ids=notification_ids,
            recipient_id=recipient_id,
            mark_all=mark_all,
        )
        return {
            "marked_count": count,
            "message": f"已标记 {count} 条通知为已读",
        }

    def get_unread_count(self, recipient_id: str) -> dict:
        """
        查询未读通知数 - 对应API文档9.2.4
        """
        return self.manager.get_unread_count(recipient_id)

    def send_notification(self, data: dict, operator_role: str) -> dict:
        """
        发送通知（内部接口）- 对应API文档9.2.5
        """
        if operator_role != "admin":
            from utils.exceptions import ForbiddenException
            raise ForbiddenException("仅管理员可以手动发送通知")

        required = ["recipient_id", "recipient_email", "title", "content",
                     "notification_type"]
        for field in required:
            if field not in data:
                raise ValidationException(f"缺少必填字段: {field}")

        try:
            notif_type = NotificationType(data["notification_type"])
        except ValueError:
            raise ValidationException(f"无效的通知类型: {data['notification_type']}")

        channel = Channel.IN_APP
        if "channel" in data:
            try:
                channel = Channel(data["channel"])
            except ValueError:
                raise ValidationException(f"无效的通知渠道: {data['channel']}")

        return self.manager.send_notification(
            recipient_id=data["recipient_id"],
            recipient_email=data.get("recipient_email", ""),
            title=data["title"],
            content=data["content"],
            notification_type=notif_type,
            channel=channel,
            reference_type=data.get("reference_type"),
            reference_id=data.get("reference_id"),
        )
