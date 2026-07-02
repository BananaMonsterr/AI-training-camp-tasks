"""数据模型包"""
from .base import Base, TimestampMixin
from .employee import EmployeeModel
from .onboarding import OnboardingRequestModel
from .offboarding import OffboardingRequestModel
from .approval import ApprovalFlowModel, ApprovalRecordModel
from .notification import NotificationModel
from .auth import UserModel, RoleModel, UserRoleModel


# ─── 模拟数据库 Session（避免 SQLAlchemy 依赖）───
class _MockSession:
    """模拟 SQLAlchemy session，实际使用各 Service 的内存存储"""
    def add(self, obj):
        pass
    def commit(self):
        pass
    def flush(self):
        pass
    def rollback(self):
        pass


class _MockDB:
    session = _MockSession()


db = _MockDB()
# ────────────────────────────────────────────────────


__all__ = [
    "Base", "TimestampMixin", "db",
    "EmployeeModel",
    "OnboardingRequestModel",
    "OffboardingRequestModel",
    "ApprovalFlowModel", "ApprovalRecordModel",
    "NotificationModel",
    "UserModel", "RoleModel", "UserRoleModel",
]
