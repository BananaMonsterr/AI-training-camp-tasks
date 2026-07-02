"""
邮件发送模块（模拟实现）
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmailProvider:
    """
    邮件发送器（模拟实现）
    
    生产环境中应替换为真实的SMTP/邮件服务API调用
    """

    def __init__(self, smtp_host: str = "smtp.company.com",
                 smtp_port: int = 587,
                 from_address: str = "noreply@company.com"):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_address = from_address
        self._sent_emails: list[dict] = []

    def send_email(self, to_address: str, subject: str, body: str,
                   cc: Optional[list[str]] = None,
                   bcc: Optional[list[str]] = None) -> bool:
        """
        发送邮件
        
        模拟实现：仅记录日志和存储发送记录
        """
        email_record = {
            "to": to_address,
            "cc": cc or [],
            "bcc": bcc or [],
            "subject": subject,
            "body": body,
            "from": self.from_address,
        }

        # 模拟发送（成功）
        self._sent_emails.append(email_record)
        logger.info(
            f"[模拟邮件] 至: {to_address}, 主题: {subject}, "
            f"内容长度: {len(body)} 字符"
        )
        return True

    def send_html_email(self, to_address: str, subject: str,
                        html_body: str,
                        cc: Optional[list[str]] = None) -> bool:
        """发送HTML格式邮件"""
        return self.send_email(to_address, subject, html_body, cc)

    def send_batch(self, recipients: list[str], subject: str,
                   body: str) -> dict:
        """批量发送邮件"""
        success_count = 0
        fail_count = 0

        for recipient in recipients:
            if self.send_email(recipient, subject, body):
                success_count += 1
            else:
                fail_count += 1

        return {
            "total": len(recipients),
            "success": success_count,
            "failed": fail_count,
        }

    def get_sent_count(self) -> int:
        """获取已发送邮件数量"""
        return len(self._sent_emails)

    def clear_sent(self) -> None:
        """清空发送记录"""
        self._sent_emails.clear()
