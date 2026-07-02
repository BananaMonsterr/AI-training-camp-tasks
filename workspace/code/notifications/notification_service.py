"""通知服务 - 管理站内通知的创建和发送"""
from typing import Optional, List
from datetime import datetime, timezone
from models import db
from models.notification import Notification, NotificationType, NotificationChannel
from .email_service import EmailService
import logging

logger = logging.getLogger(__name__)


class NotificationServiceError(Exception):
    """通知服务异常"""
    pass


class NotificationService:
    """
    通知服务 - 站内通知 + 邮件通知
    支持11种自动触发事件
    """

    def __init__(self):
        self.email_service = EmailService()

    # ----------------------------------------------------------------
    # 创建通知
    # ----------------------------------------------------------------

    def _create_notification(self, recipient_id: int, recipient_name: str,
                             title: str, content: str = None,
                             notification_type: str = NotificationType.SYSTEM.value,
                             channel: str = NotificationChannel.APP.value,
                             ref_type: str = None, ref_id: int = None,
                             recipient_email: str = None) -> Notification:
        """创建站内通知记录"""
        notif = Notification(
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            title=title,
            content=content,
            notification_type=notification_type,
            channel=channel,
            ref_type=ref_type,
            ref_id=ref_id,
        )
        db.session.add(notif)
        db.session.flush()

        # 如果是邮件渠道，尝试发送邮件
        if channel == NotificationChannel.EMAIL.value and recipient_email:
            try:
                self.email_service.sender.send(
                    to_email=recipient_email,
                    subject=title,
                    body=content or '',
                )
                notif.mark_as_sent()
            except Exception as e:
                notif.send_error = str(e)
                logger.error(f'邮件发送失败: {e}')

        return notif

    def notify_approval_task(self, recipient_id: int, recipient_name: str,
                              ref_type: str, ref_id: int,
                              title: str, content: str = None) -> Notification:
        """通知审批人处理审批任务（事件1、2）"""
        return self._create_notification(
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            title=title,
            content=content,
            notification_type=NotificationType.APPROVAL_TASK.value,
            channel=NotificationChannel.APP.value,
            ref_type=ref_type,
            ref_id=ref_id,
        )

    def notify_approval_result(self, recipient_id: int, recipient_name: str,
                                ref_type: str, ref_id: int,
                                title: str, content: str = None) -> Notification:
        """通知申请人审批结果（事件3、4）"""
        return self._create_notification(
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            title=title,
            content=content,
            notification_type=NotificationType.APPROVAL_RESULT.value,
            channel=NotificationChannel.APP.value,
            ref_type=ref_type,
            ref_id=ref_id,
        )

    def notify_system(self, recipient_id: int, recipient_name: str,
                       title: str, content: str = None,
                       ref_type: str = None, ref_id: int = None) -> Notification:
        """发送系统通知"""
        return self._create_notification(
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            title=title,
            content=content,
            notification_type=NotificationType.SYSTEM.value,
            channel=NotificationChannel.APP.value,
            ref_type=ref_type,
            ref_id=ref_id,
        )

    def notify_onboarding_reminder(self, recipient_id: int, recipient_name: str,
                                    candidate_name: str, hire_date: str) -> Notification:
        """入职提醒通知"""
        return self._create_notification(
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            title=f'【入职提醒】{candidate_name} 将于 {hire_date} 入职',
            content=f'请提前准备好工位、IT设备等入职物资。',
            notification_type=NotificationType.ONBOARDING_REMINDER.value,
            channel=NotificationChannel.APP.value,
            ref_type='onboarding',
        )

    # ----------------------------------------------------------------
    # 查询通知
    # ----------------------------------------------------------------

    def list_notifications(self, user_id: int, page: int = 1, page_size: int = 20,
                            unread_only: bool = False) -> dict:
        """查询用户通知列表"""
        query = Notification.query.filter(
            Notification.recipient_id == user_id
        )
        if unread_only:
            query = query.filter(Notification.is_read == False)

        total = query.count()
        items = query.order_by(Notification.created_at.desc()).offset(
            (page - 1) * page_size).limit(page_size).all()

        return {
            'items': [n.to_dict() for n in items],
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': (total + page_size - 1) // page_size,
            }
        }

    def get_unread_count(self, user_id: int) -> int:
        """获取未读通知数"""
        return Notification.query.filter(
            Notification.recipient_id == user_id,
            Notification.is_read == False
        ).count()

    def mark_as_read(self, notification_id: int, user_id: int) -> Notification:
        """标记通知已读"""
        notif = Notification.query.get(notification_id)
        if not notif:
            raise NotificationServiceError(f'通知不存在: id={notification_id}')
        if notif.recipient_id != user_id:
            raise NotificationServiceError('只能标记自己的通知')
        notif.mark_as_read()
        db.session.commit()
        return notif

    def mark_batch_as_read(self, notification_ids: List[int], user_id: int) -> int:
        """批量标记已读，返回成功标记数"""
        count = 0
        for nid in notification_ids:
            try:
                self.mark_as_read(nid, user_id)
                count += 1
            except NotificationServiceError:
                continue
        return count
