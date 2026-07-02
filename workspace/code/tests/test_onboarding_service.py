"""
入职申请服务单元测试
"""

import pytest

from services.onboarding_service import OnboardingService
from services.employee_service import EmployeeService
from utils.exceptions import (
    ValidationException, StatusConflictException,
    NotFoundException, ForbiddenException,
)


class TestCreateDraft:
    """创建入职申请草稿测试"""

    def test_create_success(self, onboarding_service, created_employee):
        data = {
            "employee_id": created_employee,
            "offer_letter_url": "https://oss.company.com/offer.pdf",
            "expected_hire_date": "2025-02-01",
            "equipment_required": ["laptop", "monitor"],
            "seat_location": "B栋3楼-301",
            "remark": "特批通道",
        }
        result = onboarding_service.create_draft(data, "user-001", "admin")
        assert result["status"] == "draft"
        assert result["employee_id"] == created_employee

    def test_create_by_hr_staff(self, onboarding_service, created_employee):
        data = {
            "employee_id": created_employee,
            "offer_letter_url": "https://oss.company.com/offer.pdf",
            "expected_hire_date": "2025-02-01",
        }
        result = onboarding_service.create_draft(data, "user-001", "hr_staff")
        assert result["status"] == "draft"

    def test_create_missing_required(self, onboarding_service):
        with pytest.raises(ValidationException, match="缺少必填字段"):
            onboarding_service.create_draft({}, "user-001", "admin")

    def test_create_by_employee_forbidden(self, onboarding_service):
        with pytest.raises(ForbiddenException):
            onboarding_service.create_draft({}, "user-001", "employee")


class TestSubmit:
    """提交入职申请测试"""

    def test_submit_success(self, onboarding_service, created_onboarding):
        result = onboarding_service.submit(created_onboarding, "user-001", "admin")
        assert result["status"] == "pending_hr_review"
        assert result["current_step"] == "hr_review"
        assert result["submitted_at"] is not None

    def test_submit_twice_fails(self, onboarding_service, created_onboarding):
        onboarding_service.submit(created_onboarding, "user-001", "admin")
        with pytest.raises(StatusConflictException, match="不允许"):
            onboarding_service.submit(created_onboarding, "user-001", "admin")

    def test_submit_by_unauthorized_user(self, onboarding_service, created_onboarding):
        with pytest.raises(ForbiddenException):
            onboarding_service.submit(created_onboarding, "other-user", "employee")

    def test_submit_nonexistent(self, onboarding_service):
        with pytest.raises(NotFoundException):
            onboarding_service.submit("nonexistent", "user-001", "admin")


class TestQuery:
    """查询入职申请测试"""

    def test_get_request(self, onboarding_service, created_onboarding):
        result = onboarding_service.get_request(created_onboarding, "user-001", "admin")
        assert result["id"] == created_onboarding
        assert result["status"] == "draft"

    def test_get_request_not_found(self, onboarding_service):
        with pytest.raises(NotFoundException):
            onboarding_service.get_request("nonexistent", "user-001", "admin")

    def test_list_requests(self, onboarding_service, created_onboarding):
        result = onboarding_service.list_requests()
        assert result["total"] >= 1

    def test_list_requests_filter_by_status(self, onboarding_service, created_onboarding):
        result = onboarding_service.list_requests(status="draft")
        assert result["total"] >= 1

        result = onboarding_service.list_requests(status="approved")
        assert result["total"] == 0

    def test_list_by_employee_only_own(self, onboarding_service, created_onboarding):
        """普通员工只看自己的"""
        result = onboarding_service.list_requests(
            operator_role="employee", operator_id="user-001"
        )
        assert result["total"] >= 1

        result = onboarding_service.list_requests(
            operator_role="employee", operator_id="other-user"
        )
        assert result["total"] == 0


class TestUpdate:
    """更新入职申请测试"""

    def test_update_draft(self, onboarding_service, created_onboarding):
        result = onboarding_service.update_draft(
            created_onboarding,
            {"remark": "更新备注", "seat_location": "新座位"},
            "user-001", "admin"
        )
        assert result["remark"] == "更新备注"
        assert result["seat_location"] == "新座位"

    def test_update_after_submit_fails(self, onboarding_service, created_onboarding):
        onboarding_service.submit(created_onboarding, "user-001", "admin")
        with pytest.raises(StatusConflictException, match="仅草稿状态可编辑"):
            onboarding_service.update_draft(
                created_onboarding, {"remark": "test"}, "user-001", "admin"
            )


class TestCancel:
    """撤回入职申请测试"""

    def test_cancel_draft(self, onboarding_service, created_onboarding):
        result = onboarding_service.cancel(created_onboarding, "user-001", "admin")
        assert result["status"] == "cancelled"

    def test_cancel_submitted(self, onboarding_service, created_onboarding):
        onboarding_service.submit(created_onboarding, "user-001", "admin")
        result = onboarding_service.cancel(created_onboarding, "user-001", "admin")
        assert result["status"] == "cancelled"

    def test_cancel_approved_fails(self, onboarding_service, created_onboarding):
        onboarding_service.submit(created_onboarding, "user-001", "admin")
        # 模拟审批通过全部步骤
        onboarding_service.approve_step(
            created_onboarding, "hr_review", "approve", "", "user-001", "HR"
        )
        onboarding_service.approve_step(
            created_onboarding, "dept_review", "approve", "", "user-002", "部门经理"
        )
        onboarding_service.approve_step(
            created_onboarding, "it_prepare", "approve", "", "user-003", "IT"
        )
        with pytest.raises(StatusConflictException):
            onboarding_service.cancel(created_onboarding, "user-001", "admin")


class TestDelete:
    """删除入职申请测试"""

    def test_delete_draft(self, onboarding_service, created_onboarding):
        onboarding_service.delete(created_onboarding, "admin")
        with pytest.raises(NotFoundException):
            onboarding_service.get_request(created_onboarding, "user-001", "admin")

    def test_delete_by_non_admin(self, onboarding_service, created_onboarding):
        with pytest.raises(ForbiddenException):
            onboarding_service.delete(created_onboarding, "employee")


class TestApproveStep:
    """审批步骤测试"""

    def test_approve_hr_step(self, onboarding_service, created_onboarding):
        onboarding_service.submit(created_onboarding, "user-001", "admin")
        result = onboarding_service.approve_step(
            created_onboarding, "hr_review", "approve", "同意入职",
            "user-002", "HR经理"
        )
        assert result["status"] == "pending_dept_review"

    def test_reject_hr_step(self, onboarding_service, created_onboarding):
        onboarding_service.submit(created_onboarding, "user-001", "admin")
        result = onboarding_service.approve_step(
            created_onboarding, "hr_review", "reject", "资料不全",
            "user-002", "HR经理"
        )
        assert result["status"] == "draft"

    def test_full_approval_flow(self, onboarding_service, created_onboarding):
        """完整审批流程"""
        onboarding_service.submit(created_onboarding, "user-001", "admin")

        onboarding_service.approve_step(
            created_onboarding, "hr_review", "approve", "", "u1", "HR"
        )
        onboarding_service.approve_step(
            created_onboarding, "dept_review", "approve", "", "u2", "部门经理"
        )
        result = onboarding_service.approve_step(
            created_onboarding, "it_prepare", "approve", "", "u3", "IT"
        )
        assert result["status"] == "approved"


class TestAvailableActions:
    """可用操作测试"""

    def test_draft_actions(self, onboarding_service, created_onboarding):
        actions = onboarding_service.get_available_actions(created_onboarding)
        assert "submit" in actions
        assert "cancel" in actions
        assert "update" in actions

    def test_submitted_actions(self, onboarding_service, created_onboarding):
        onboarding_service.submit(created_onboarding, "user-001", "admin")
        actions = onboarding_service.get_available_actions(created_onboarding)
        assert "approve" in actions
        assert "reject" in actions
        assert "cancel" in actions
