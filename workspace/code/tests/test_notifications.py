"""通知模块单元测试"""
import pytest
from ..models import db
from ..models.notification import Notification, NotificationType
from ..notifications.notification_service import NotificationService, NotificationServiceError
from ..notifications.email_service import EmailSender, EmailService


class TestEmailSender:
    """邮件发送器测试"""

    def setup_method(self):
        self.sender = EmailSender()

    def test_send_email(self):
        result = self.sender.send(
            to_email='test@test.com',
            subject='测试主题',
            body='测试内容',
        )
        assert result is True

    def test_send_with_cc(self):
        result = self.sender.send(
            to_email='test@test.com',
            subject='抄送测试',
            body='内容',
            cc=['cc@test.com'],
        )
        assert result is True

    def test_sent_records(self):
        self.sender.clear_sent_emails()
        self.sender.send('a@test.com', '主题A', '内容A')
        self.sender.send('b@test.com', '主题B', '内容B')

        records = self.sender.get_sent_emails()
        assert len(records) == 2
        assert records[0]['subject'] == '主题A'
        assert records[1]['to'] == 'b@test.com'

    def test_batch_send(self):
        self.sender.clear_sent_emails()
        results = self.sender.send_batch(
            recipients=['a@test.com', 'b@test.com'],
            subject='批量',
            body='批量内容',
        )
        assert len(results) == 2
        assert all(results)


class TestNotificationService:
    """通知服务测试"""

    @pytest.fixture(autouse=True)
    def setup(self, app):
        with app.app_context():
            self.service = NotificationService()

    def test_create_system_notification(self, app):
        with app.app_context():
            notif = self.service.notify_system(
                recipient_id=1,
                recipient_name='接收人',
                title='系统通知',
                content='系统通知内容',
            )

            assert notif.id is not None
            assert notif.title == '系统通知'
            assert notif.notification_type == 'SYSTEM'
            assert notif.is_read is False

    def test_create_approval_task_notification(self, app):
        with app.app_context():
            notif = self.service.notify_approval_task(
                recipient_id=2,
                recipient_name='审批人',
                ref_type='onboarding',
                ref_id=100,
                title='请审批入职申请',
                content='候选人张三的入职申请待审批',
            )

            assert notif.notification_type == 'APPROVAL_TASK'
            assert notif.ref_type == 'onboarding'
            assert notif.ref_id == 100

    def test_create_approval_result_notification(self, app):
        with app.app_context():
            notif = self.service.notify_approval_result(
                recipient_id=1,
                recipient_name='申请人',
                ref_type='onboarding',
                ref_id=100,
                title='审批通过',
                content='您的入职申请已通过',
            )

            assert notif.notification_type == 'APPROVAL_RESULT'

    def test_onboarding_reminder(self, app):
        with app.app_context():
            notif = self.service.notify_onboarding_reminder(
                recipient_id=3,
                recipient_name='HR',
                candidate_name='新员工',
                hire_date='2024-08-01',
            )

            assert '入职提醒' in notif.title
            assert notif.notification_type == 'ONBOARDING_REMINDER'

    def test_list_notifications(self, app):
        with app.app_context():
            # 创建测试数据
            for i in range(3):
                self.service.notify_system(
                    recipient_id=10,
                    recipient_name='测试用户',
                    title=f'通知{i}',
                    content=f'内容{i}',
                )

            result = self.service.list_notifications(user_id=10)
            assert result['pagination']['total'] >= 3
            assert len(result['items']) >= 3

    def test_unread_count(self, app):
        with app.app_context():
            # 先清除可能的通知
            Notification.query.filter_by(recipient_id=20).delete()
            db.session.commit()

            for i in range(5):
                self.service.notify_system(
                    recipient_id=20,
                    recipient_name='未读测试',
                    title=f'未读通知{i}',
                )

            count = self.service.get_unread_count(20)
            assert count >= 5

    def test_mark_as_read(self, app):
        with app.app_context():
            notif = self.service.notify_system(
                recipient_id=30,
                recipient_name='已读测试',
                title='待阅读',
            )

            marked = self.service.mark_as_read(notif.id, 30)
            assert marked.is_read is True
            assert marked.read_at is not None

    def test_mark_others_notification(self, app):
        with app.app_context():
            notif = self.service.notify_system(
                recipient_id=40,
                recipient_name='用户A',
                title='A的通知',
            )

            with pytest.raises(NotificationServiceError) as exc:
                self.service.mark_as_read(notif.id, 99)  # 不是接收人
            assert '只能标记自己的通知' in str(exc.value)

    def test_mark_nonexistent(self, app):
        with app.app_context():
            with pytest.raises(NotificationServiceError) as exc:
                self.service.mark_as_read(99999, 1)
            assert '不存在' in str(exc.value)

    def test_batch_mark_as_read(self, app):
        with app.app_context():
            ids = []
            for i in range(3):
                n = self.service.notify_system(
                    recipient_id=50,
                    recipient_name='批量测试',
                    title=f'批量{i}',
                )
                ids.append(n.id)

            count = self.service.mark_batch_as_read(ids, 50)
            assert count == 3

            # 验证全部已读
            unread = self.service.get_unread_count(50)
            assert unread == 0

    def test_notification_with_email_channel(self, app):
        with app.app_context():
            from ..models.notification import NotificationChannel
            notif = self.service._create_notification(
                recipient_id=60,
                recipient_name='邮件测试',
                title='邮件通知',
                content='这是邮件内容',
                channel=NotificationChannel.EMAIL.value,
                recipient_email='email@test.com',
            )
            assert notif.id is not None
