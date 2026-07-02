"""
通知管理器及通知服务单元测试
"""

import pytest

from notifications.notification_manager import (
    NotificationManager, NotificationType, Channel,
)
from notifications.email_provider import EmailProvider
from services.notification_service import NotificationService
from utils.exceptions import NotFoundException, ValidationException, ForbiddenException


class TestEmailProvider:
    """邮件发送器测试"""

    def test_send_email(self, email_provider):
        result = email_provider.send_email(
            to_address="test@company.com",
            subject="测试邮件",
            body="这是一封测试邮件",
        )
        assert result is True
        assert email_provider.get_sent_count() == 1

    def test_send_batch(self, email_provider):
        result = email_provider.send_batch(
            recipients=["a@c.com", "b@c.com"],
            subject="批量测试",
            body="批量发送",
        )
        assert result["total"] == 2
        assert result["success"] == 2
        assert result["failed"] == 0

    def test_send_html(self, email_provider):
        result = email_provider.send_html_email(
            to_address="test@c.com",
            subject="HTML测试",
            html_body="<h1>Hello</h1>",
        )
        assert result is True

    def test_clear_sent(self, email_provider):
        email_provider.send_email("a@c.com", "s", "b")
        email_provider.clear_sent()
        assert email_provider.get_sent_count() == 0


class TestNotificationManager:
    """通知管理器测试"""

    def test_send_in_app(self, notification_manager):
        result = notification_manager.send_notification(
            recipient_id="user-001",
            recipient_email="user@company.com",
            title="测试通知",
            content="这是一条测试",
            notification_type=NotificationType.SYSTEM_REMINDER,
            channel=Channel.IN_APP,
        )
        assert result["id"] is not None
        assert result["is_read"] is False
        assert result["channel"] == "in_app"

    def test_send_email_channel(self, notification_manager):
        result = notification_manager.send_notification(
            recipient_id="user-001",
            recipient_email="user@company.com",
            title="邮件通知",
            content="邮件内容",
            notification_type=NotificationType.APPROVAL_PENDING,
            channel=Channel.EMAIL,
        )
        assert result["channel"] == "email"

    def test_send_both_channels(self, notification_manager):
        result = notification_manager.send_notification(
            recipient_id="user-001",
            recipient_email="user@company.com",
            title="双渠道",
            content="双渠道内容",
            notification_type=NotificationType.APPROVAL_PENDING,
            channel=Channel.BOTH,
        )
        assert result["channel"] == "both"

    def test_get_notifications(self, notification_manager):
        notification_manager.send_notification(
            recipient_id="user-001", recipient_email="u@c.com",
            title="T1", content="C1",
            notification_type=NotificationType.SYSTEM_REMINDER,
        )
        result = notification_manager.get_notifications("user-001")
        assert result["total"] >= 1
        assert result["items"][0]["title"] == "T1"

    def test_filter_unread(self, notification_manager):
        notification_manager.send_notification(
            recipient_id="user-001", recipient_email="u@c.com",
            title="未读", content="测试",
            notification_type=NotificationType.SYSTEM_REMINDER,
        )
        result = notification_manager.get_notifications("user-001", is_read=False)
        assert result["total"] >= 1

        result = notification_manager.get_notifications("user-001", is_read=True)
        assert result["total"] == 0

    def test_mark_as_read(self, notification_manager):
        sent = notification_manager.send_notification(
            recipient_id="user-001", recipient_email="u@c.com",
            title="标记已读", content="test",
            notification_type=NotificationType.APPROVAL_PENDING,
        )
        result = notification_manager.mark_as_read(sent["id"], "user-001")
        assert result["is_read"] is True
        assert result["read_at"] is not None

    def test_mark_as_read_wrong_user(self, notification_manager):
        sent = notification_manager.send_notification(
            recipient_id="user-001", recipient_email="u@c.com",
            title="test", content="test",
            notification_type=NotificationType.SYSTEM_REMINDER,
        )
        result = notification_manager.mark_as_read(sent["id"], "other-user")
        assert result is None

    def test_mark_not_found(self, notification_manager):
        result = notification_manager.mark_as_read("nonexistent", "user-001")
        assert result is None

    def test_batch_mark_as_read(self, notification_manager):
        n1 = notification_manager.send_notification(
            "user-001", "u@c.com", "T1", "C1",
            NotificationType.SYSTEM_REMINDER,
        )
        n2 = notification_manager.send_notification(
            "user-001", "u@c.com", "T2", "C2",
            NotificationType.APPROVAL_PENDING,
        )
        count = notification_manager.batch_mark_as_read(
            [n1["id"], n2["id"]], "user-001"
        )
        assert count == 2

    def test_mark_all_as_read(self, notification_manager):
        for i in range(3):
            notification_manager.send_notification(
                "user-001", "u@c.com", f"T{i}", f"C{i}",
                NotificationType.SYSTEM_REMINDER,
            )
        count = notification_manager.batch_mark_as_read([], "user-001", mark_all=True)
        assert count == 3

    def test_unread_count(self, notification_manager):
        notification_manager.send_notification(
            "user-001", "u@c.com", "T1", "C1",
            NotificationType.APPROVAL_PENDING,
        )
        notification_manager.send_notification(
            "user-001", "u@c.com", "T2", "C2",
            NotificationType.SYSTEM_REMINDER,
        )
        result = notification_manager.get_unread_count("user-001")
        assert result["total_unread"] == 2
        assert "approval_pending" in result["by_type"]

    def test_no_notifications(self, notification_manager):
        result = notification_manager.get_notifications("nonexistent")
        assert result["total"] == 0


class TestApprovalNotification:
    """审批通知快捷发送测试"""

    def test_send_approval_pending(self, notification_manager):
        result = notification_manager.send_approval_notification(
            recipient_id="user-001",
            recipient_email="user@c.com",
            employee_name="张三",
            request_type="onboarding",
            action="pending",
            step_name="HR审核",
        )
        assert result["notification_type"] == "approval_pending"
        assert "张三" in result["content"]

    def test_send_approval_approved(self, notification_manager):
        result = notification_manager.send_approval_notification(
            recipient_id="user-001",
            recipient_email="user@c.com",
            employee_name="张三",
            request_type="onboarding",
            action="approve",
            step_name="HR审核",
        )
        assert result["notification_type"] == "approval_approved"

    def test_send_approval_rejected(self, notification_manager):
        result = notification_manager.send_approval_notification(
            recipient_id="user-001",
            recipient_email="user@c.com",
            employee_name="张三",
            request_type="offboarding",
            action="reject",
            step_name="部门审批",
        )
        assert result["notification_type"] == "approval_rejected"


class TestNotificationService:
    """通知服务测试"""

    def test_send_notification_admin(self, notification_service):
        data = {
            "recipient_id": "user-001",
            "recipient_email": "user@c.com",
            "title": "服务发送",
            "content": "通过服务发送",
            "notification_type": "system_reminder",
            "channel": "in_app",
        }
        result = notification_service.send_notification(data, "admin")
        assert result["title"] == "服务发送"

    def test_send_notification_non_admin(self, notification_service):
        data = {
            "recipient_id": "user-001",
            "recipient_email": "user@c.com",
            "title": "test",
            "content": "test",
            "notification_type": "system_reminder",
        }
        with pytest.raises(ForbiddenException):
            notification_service.send_notification(data, "employee")

    def test_send_missing_fields(self, notification_service):
        with pytest.raises(ValidationException):
            notification_service.send_notification({}, "admin")

    def test_get_unread_count(self, notification_service):
        # 先发一条通知
        notification_service.send_notification({
            "recipient_id": "user-001",
            "recipient_email": "u@c.com",
            "title": "test",
            "content": "test",
            "notification_type": "system_reminder",
        }, "admin")
        result = notification_service.get_unread_count("user-001")
        assert result["total_unread"] >= 1

    def test_mark_nonexistent(self, notification_service):
        with pytest.raises(NotFoundException):
            notification_service.mark_as_read("nonexistent", "user-001")
