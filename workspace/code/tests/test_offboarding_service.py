"""
离职申请服务单元测试
"""

import pytest

from utils.exceptions import (
    ValidationException, StatusConflictException,
    NotFoundException, ForbiddenException,
)


class TestCreateDraft:
    """创建离职申请草稿测试"""

    def test_create_success(self, offboarding_service, created_employee):
        data = {
            "employee_id": created_employee,
            "resignation_type": "voluntary",
            "reason": "个人职业发展",
            "expected_last_work_date": "2025-03-01",
            "handover_note": "已与同事完成交接",
        }
        result = offboarding_service.create_draft(data, "user-001", "admin")
        assert result["status"] == "draft"
        assert result["resignation_type"] == "voluntary"

    def test_create_by_employee_self(self, offboarding_service, created_employee):
        """员工为自己创建离职申请"""
        data = {
            "employee_id": created_employee,
            "resignation_type": "voluntary",
            "reason": "个人发展",
            "expected_last_work_date": "2025-03-01",
        }
        result = offboarding_service.create_draft(data, "user-001", "employee")
        assert result["status"] == "draft"

    def test_create_missing_required(self, offboarding_service):
        with pytest.raises(ValidationException, match="缺少必填字段"):
            offboarding_service.create_draft({}, "user-001", "admin")

    def test_create_invalid_resignation_type(self, offboarding_service, created_employee):
        with pytest.raises(ValidationException, match="无效的离职类型"):
            offboarding_service.create_draft({
                "employee_id": created_employee,
                "resignation_type": "invalid_type",
                "reason": "test",
                "expected_last_work_date": "2025-03-01",
            }, "user-001", "admin")


class TestSubmit:
    """提交离职申请测试"""

    def test_submit_success(self, offboarding_service, created_employee):
        draft = offboarding_service.create_draft({
            "employee_id": created_employee,
            "resignation_type": "voluntary",
            "reason": "个人发展",
            "expected_last_work_date": "2025-03-01",
        }, "user-001", "admin")

        result = offboarding_service.submit(draft["id"], "user-001", "admin")
        assert result["status"] == "pending_dept_review"
        assert result["current_step"] == "dept_manager_review"

    def test_submit_twice_fails(self, offboarding_service, created_employee):
        draft = offboarding_service.create_draft({
            "employee_id": created_employee,
            "resignation_type": "voluntary",
            "reason": "test",
            "expected_last_work_date": "2025-03-01",
        }, "user-001", "admin")

        offboarding_service.submit(draft["id"], "user-001", "admin")
        with pytest.raises(StatusConflictException):
            offboarding_service.submit(draft["id"], "user-001", "admin")


class TestFullFlow:
    """完整审批流程测试"""

    def test_full_approval_flow(self, offboarding_service, created_employee):
        draft = offboarding_service.create_draft({
            "employee_id": created_employee,
            "resignation_type": "voluntary",
            "reason": "个人发展",
            "expected_last_work_date": "2025-03-01",
        }, "user-001", "admin")

        offboarding_service.submit(draft["id"], "user-001", "admin")

        # 部门审批
        offboarding_service.approve_step(
            draft["id"], "dept_manager_review", "approve", "", "u1", "部门经理"
        )
        # HR审批
        offboarding_service.approve_step(
            draft["id"], "hr_review", "approve", "", "u2", "HR"
        )
        # 离职面谈
        offboarding_service.approve_step(
            draft["id"], "exit_interview", "approve", "", "u3", "HR"
        )
        # 资产归还
        result = offboarding_service.approve_step(
            draft["id"], "asset_return", "approve", "", "u4", "Admin"
        )
        assert result["status"] == "approved"

    def test_reject_from_dept(self, offboarding_service, created_employee):
        draft = offboarding_service.create_draft({
            "employee_id": created_employee,
            "resignation_type": "voluntary",
            "reason": "test",
            "expected_last_work_date": "2025-03-01",
        }, "user-001", "admin")

        offboarding_service.submit(draft["id"], "user-001", "admin")
        result = offboarding_service.approve_step(
            draft["id"], "dept_manager_review", "reject", "不同意", "u1", "部门经理"
        )
        assert result["status"] == "draft"

    def test_cancel_submitted(self, offboarding_service, created_employee):
        draft = offboarding_service.create_draft({
            "employee_id": created_employee,
            "resignation_type": "voluntary",
            "reason": "test",
            "expected_last_work_date": "2025-03-01",
        }, "user-001", "admin")

        offboarding_service.submit(draft["id"], "user-001", "admin")
        result = offboarding_service.cancel(draft["id"], "user-001", "admin")
        assert result["status"] == "cancelled"


class TestListAndGet:
    """查询测试"""

    def test_list_and_filter(self, offboarding_service, created_employee):
        # 先创建一个
        draft = offboarding_service.create_draft({
            "employee_id": created_employee,
            "resignation_type": "voluntary",
            "reason": "test",
            "expected_last_work_date": "2025-03-01",
        }, "user-001", "admin")

        result = offboarding_service.list_requests()
        assert result["total"] >= 1

        result = offboarding_service.list_requests(status="draft")
        assert result["total"] >= 1

    def test_get_not_found(self, offboarding_service):
        with pytest.raises(NotFoundException):
            offboarding_service.get_request("nonexistent", "user-001", "admin")
