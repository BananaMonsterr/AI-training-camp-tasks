"""邮件发送服务（模拟实现）"""
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件发送器 - 模拟实现，仅记录日志"""

    def __init__(self, smtp_host: str = 'mock.smtp.com', smtp_port: int = 587):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self._sent_emails: List[dict] = []

    def send(self, to_email: str, subject: str, body: str,
             cc: Optional[List[str]] = None) -> bool:
        """
        发送邮件
        模拟实现：记录日志并返回成功
        """
        email_record = {
            'to': to_email,
            'subject': subject,
            'body': body,
            'cc': cc or [],
            'status': 'sent',
        }
        self._sent_emails.append(email_record)
        logger.info(
            f'[邮件 Mock] 发送邮件 -> {to_email} | '
            f'主题: {subject} | 长度: {len(body)}字'
        )
        return True

    def send_batch(self, recipients: List[str], subject: str, body: str) -> List[bool]:
        """批量发送邮件"""
        results = []
        for email in recipients:
            result = self.send(email, subject, body)
            results.append(result)
        return results

    def get_sent_emails(self) -> List[dict]:
        """获取已发送的邮件记录（用于测试）"""
        return self._sent_emails

    def clear_sent_emails(self):
        """清空发送记录"""
        self._sent_emails.clear()


class EmailService:
    """邮件服务 - 单例模式"""

    _instance = None
    _sender = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._sender = EmailSender()
        return cls._instance

    @property
    def sender(self) -> EmailSender:
        return self._sender

    def send_approval_notification(self, to_email: str, approver_name: str,
                                    request_type: str, candidate_name: str) -> bool:
        """发送审批任务通知邮件"""
        subject = f'【审批通知】{request_type}申请待审批'
        body = (
            f'{approver_name}您好，\n\n'
            f'您有一项{candidate_name}的{request_type}申请待审批，请及时处理。\n\n'
            f'请登录系统查看详情。\n'
            f'此邮件由系统自动发送，请勿回复。'
        )
        return self._sender.send(to_email, subject, body)

    def send_approval_result_email(self, to_email: str, name: str,
                                    request_type: str, result: str,
                                    comment: str = None) -> bool:
        """发送审批结果通知邮件"""
        result_text = '已通过' if result == 'approved' else '被驳回'
        subject = f'【审批结果】{request_type}申请{result_text}'
        body = (
            f'{name}您好，\n\n'
            f'您的{request_type}申请已{result_text}。\n'
        )
        if comment:
            body += f'审批意见: {comment}\n'
        body += '\n请登录系统查看详情。\n此邮件由系统自动发送，请勿回复。'

        return self._sender.send(to_email, subject, body)
