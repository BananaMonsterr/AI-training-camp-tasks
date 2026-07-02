"""
数据模型单元测试
"""

import pytest
from datetime import date, datetime, timezone
from uuid import UUID

from models.base import generate_uuid, utc_now
from models.employee import EmployeeModel, EmployeeStatus, EmploymentType
from models.onboarding import OnboardingRequestModel, OnboardingStatus
from models.offboarding import (
    OffboardingRequestModel, OffboardingStatus,
    ResignationType, AssetReturnStatus,
)
from models.approval import ApprovalFlowModel, ApprovalRecordModel, FlowType, RecordStatus
from models.notification import NotificationModel, NotificationType, NotificationChannel
from models.auth import UserModel, RoleType


class TestBaseModel:
    """基础模型测试"""

    def test_generate_uuid(self):
        uid = generate_uuid()
        assert isinstance(uid, str)
        # 验证UUID格式
        UUID(uid)

    def test_utc_now(self):
        now = utc_now()
        assert isinstance(now, datetime)
        assert now.tzinfo is not None

    def test_timestamp_mixin(self, sample_employee_model):
        """测试时间戳混入类"""
        assert sample_employee_model.created_at is not None
        assert sample_employee_model.updated_at is not None

    def test_to_dict(self, sample_employee_model):
        """测试转字典"""
        d = sample_employee_model.to_dict()
        assert isinstance(d, dict)
        assert d["id"] == sample_employee_model.id
        assert d["name"] == "张三"
        # 时间戳应为毫秒数
        assert isinstance(d["created_at"], int)

    def test_update_method(self, sample_employee_model):
        """测试update方法"""
        sample_employee_model.update(position="技术总监")
        assert sample_employee_model.position == "技术总监"


class TestEmployeeModel:
    """员工模型测试"""

    def test_create_employee(self):
        emp = EmployeeModel(
            employee_no="EMP20250001",
            name="张三",
            id_card="110101199001011234",
            email="zhangsan@company.com",
            phone="13800138000",
            department_id="dept-001",
            position="高级工程师",
            hire_date=date(2025, 1, 16),
            employment_type=EmploymentType.FULL_TIME,
        )
        assert emp.id is not None
        assert emp.status == EmployeeStatus.ONBOARDING  # 默认值
        assert emp.is_deleted is False

    def test_employee_to_dict_without_sensitive(self, sample_employee_model):
        """测试不脱敏的to_dict"""
        d = sample_employee_model.to_dict(sensitive=False)
        assert "********" in d["id_card"]
        assert "****" in d["phone"]

    def test_employee_to_dict_with_sensitive(self, sample_employee_model):
        """测试脱敏的to_dict"""
        d = sample_employee_model.to_dict(sensitive=True)
        assert d["id_card"] == "110101199001011234"
        assert d["phone"] == "13800138000"

    def test_employee_status_values(self):
        assert EmployeeStatus.ACTIVE.value == "active"
        assert EmployeeStatus.ONBOARDING.value == "onboarding"
        assert EmployeeStatus.TERMINATED.value == "terminated"

    def test_employment_type_values(self):
        assert EmploymentType.FULL_TIME.value == "full_time"
        assert EmploymentType.INTERN.value == "intern"


class TestOnboardingModel:
    """入职申请模型测试"""

    def test_create_onboarding(self, sample_onboarding_model):
        assert sample_onboarding_model.status == OnboardingStatus.DRAFT
        assert sample_onboarding_model.current_step is None
        assert sample_onboarding_model.submitted_at is None

    def test_status_transition_values(self):
        assert OnboardingStatus.DRAFT.value == "draft"
        assert OnboardingStatus.PENDING_HR_REVIEW.value == "pending_hr_review"
        assert OnboardingStatus.APPROVED.value == "approved"
        assert OnboardingStatus.CANCELLED.value == "cancelled"

    def test_to_dict(self, sample_onboarding_model):
        d = sample_onboarding_model.to_dict()
        assert d["expected_hire_date"] == "2025-02-01"
        assert d["equipment_required"] == ["laptop", "monitor"]


class TestOffboardingModel:
    """离职申请模型测试"""

    def test_create_offboarding(self, sample_offboarding_model):
        assert sample_offboarding_model.status == OffboardingStatus.DRAFT
        assert sample_offboarding_model.asset_return_status == AssetReturnStatus.PENDING

    def test_resignation_type_values(self):
        assert ResignationType.VOLUNTARY.value == "voluntary"
        assert ResignationType.INVOLUNTARY.value == "involuntary"

    def test_asset_return_status_values(self):
        assert AssetReturnStatus.PENDING.value == "pending"
        assert AssetReturnStatus.COMPLETED.value == "completed"


class TestApprovalModel:
    """审批模型测试"""

    def test_create_approval_flow(self):
        flow = ApprovalFlowModel(
            flow_type=FlowType.ONBOARDING,
            name="测试入职流程",
            steps=[
                {"step_key": "hr_review", "step_name": "HR审核", "order": 1}
            ],
        )
        assert flow.is_active is True
        assert flow.version == 1

    def test_create_approval_record(self):
        record = ApprovalRecordModel(
            flow_id="flow-001",
            request_id="req-001",
            request_type="onboarding",
            step_key="hr_review",
            step_name="HR审核",
            assignee_id="user-001",
            assignee_name="王五",
        )
        assert record.status == RecordStatus.PENDING
        assert record.action is None

    def test_record_status_values(self):
        assert RecordStatus.PENDING.value == "pending"
        assert RecordStatus.COMPLETED.value == "completed"
        assert RecordStatus.SKIPPED.value == "skipped"


class TestNotificationModel:
    """通知模型测试"""

    def test_create_notification(self):
        notif = NotificationModel(
            recipient_id="user-001",
            title="测试通知",
            content="这是一条测试通知",
            notification_type=NotificationType.APPROVAL_PENDING,
            channel=NotificationChannel.IN_APP,
        )
        assert notif.is_read is False
        assert notif.read_at is None

    def test_mark_as_read(self):
        notif = NotificationModel(
            recipient_id="user-001",
            title="测试",
            content="内容",
            notification_type=NotificationType.SYSTEM_REMINDER,
            channel=NotificationChannel.EMAIL,
        )
        notif.mark_as_read()
        assert notif.is_read is True
        assert notif.read_at is not None

    def test_notification_type_values(self):
        assert NotificationType.APPROVAL_PENDING.value == "approval_pending"
        assert NotificationType.APPROVAL_APPROVED.value == "approval_approved"


class TestAuthModel:
    """认证模型测试"""

    def test_create_user(self, sample_user_admin):
        assert sample_user_admin.role == RoleType.ADMIN
        assert sample_user_admin.is_active is True

    def test_user_role_values(self):
        assert RoleType.ADMIN.value == "admin"
        assert RoleType.EMPLOYEE.value == "employee"
        assert RoleType.DEPT_MANAGER.value == "dept_manager"


class TestModelEdgeCases:
    """模型边界测试"""

    def test_employee_no_id_card(self):
        """测试身份证为空"""
        emp = EmployeeModel(
            employee_no="EMP99999",
            name="测试",
            id_card="",
            email="test@test.com",
            phone="13800138000",
            department_id="dept-001",
            position="测试",
            hire_date=date(2025, 1, 1),
            employment_type=EmploymentType.FULL_TIME,
        )
        d = emp.to_dict(sensitive=False)
        assert d["id_card"] == ""  # 空字符串不做脱敏

    def test_onboarding_null_equipment(self):
        """测试设备清单为空"""
        req = OnboardingRequestModel(
            employee_id="emp-001",
            applicant_id="user-001",
            offer_letter_url="https://test.com/test.pdf",
            expected_hire_date=date(2025, 2, 1),
            equipment_required=None,
        )
        assert req.to_dict()["equipment_required"] == []

    def test_model_repr(self, sample_employee_model):
        """测试__repr__"""
        rep = repr(sample_employee_model)
        assert "张三" in rep
        assert "EMP20250001" in rep
