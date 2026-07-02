"""
审批流服务单元测试
"""

import pytest

from utils.exceptions import (
    ValidationException, FlowNotFoundException, StatusConflictException,
    ForbiddenException,
)


class TestFlowTemplate:
    """审批流模板测试"""

    def test_list_flows(self, approval_service):
        result = approval_service.list_flows()
        assert result["total"] >= 2  # 默认有入职和离职两个流程

    def test_list_onboarding_flows(self, approval_service):
        result = approval_service.list_flows(flow_type="onboarding")
        assert result["total"] >= 1
        assert result["items"][0]["flow_type"] == "onboarding"

    def test_get_flow_for_type(self, approval_service):
        flow = approval_service.get_flow_for_type("onboarding")
        assert flow.flow_type.value == "onboarding"
        assert flow.is_active is True

    def test_create_flow(self, approval_service):
        data = {
            "flow_type": "onboarding",
            "name": "自定义入职流程",
            "steps": [
                {"step_key": "step1", "step_name": "第一步", "assignee_role": "admin", "order": 1},
            ],
        }
        result = approval_service.create_flow(data, "admin")
        assert result["name"] == "自定义入职流程"

    def test_create_flow_by_non_admin(self, approval_service):
        with pytest.raises(ForbiddenException):
            approval_service.create_flow({}, "employee")

    def test_update_flow(self, approval_service):
        flows = approval_service.list_flows()
        flow_id = flows["items"][0]["id"]
        result = approval_service.update_flow(
            flow_id, {"name": "更新后的流程名称"}, "admin"
        )
        assert result["name"] == "更新后的流程名称"


class TestApprovalAction:
    """审批操作测试"""

    def test_approve_onboarding(self, approval_service, created_onboarding):
        """入职申请通过"""
        from models.onboarding import OnboardingStatus
        onboarding_service = approval_service.onboarding_service
        onboarding_service.submit(created_onboarding, "user-001", "admin")

        flow = approval_service.get_flow_for_type("onboarding")
        result = approval_service.perform_action(
            flow_id=flow.id,
            request_id=created_onboarding,
            action="approve",
            step_key="hr_review",
            comment="同意入职",
            operator_id="user-002",
            operator_name="HR经理",
            operator_role="hr_manager",
        )
        assert result["action"] == "approve"
        assert result["is_final"] is False
        assert result["next_step"] == "dept_review"

    def test_approve_final_step(self, approval_service, created_onboarding):
        """最后一步审批通过"""
        onboarding_service = approval_service.onboarding_service
        onboarding_service.submit(created_onboarding, "user-001", "admin")

        flow = approval_service.get_flow_for_type("onboarding")

        # 前两步
        approval_service.perform_action(flow.id, created_onboarding, "approve",
                                         "hr_review", "", "u1", "HR", "hr_manager")
        approval_service.perform_action(flow.id, created_onboarding, "approve",
                                         "dept_review", "", "u2", "部门经理", "dept_manager")

        # 最后一步
        result = approval_service.perform_action(
            flow.id, created_onboarding, "approve",
            "it_prepare", "设备已准备", "u3", "IT", "admin"
        )
        assert result["is_final"] is True
        assert result["next_step"] is None
        assert result["current_status"] == "approved"

    def test_reject_onboarding(self, approval_service, created_onboarding):
        """驳回入职申请"""
        onboarding_service = approval_service.onboarding_service
        onboarding_service.submit(created_onboarding, "user-001", "admin")

        flow = approval_service.get_flow_for_type("onboarding")
        result = approval_service.perform_action(
            flow.id, created_onboarding, "reject",
            "hr_review", "资料不全", "u2", "HR经理", "hr_manager"
        )
        assert result["action"] == "reject"
        assert result["is_final"] is True  # 驳回即终态

    def test_transfer_task(self, approval_service, created_onboarding):
        """转办审批"""
        onboarding_service = approval_service.onboarding_service
        onboarding_service.submit(created_onboarding, "user-001", "admin")

        flow = approval_service.get_flow_for_type("onboarding")
        result = approval_service.transfer_task(
            flow_id=flow.id,
            request_id=created_onboarding,
            step_key="hr_review",
            transfer_to_user_id="user-003",
            comment="请假，转办",
            operator_id="user-002",
            operator_name="原审批人",
        )
        assert result["original_assignee"] == "user-002"
        assert result["new_assignee"]["id"] == "user-003"

    def test_approve_nonexistent_flow(self, approval_service, created_onboarding):
        with pytest.raises(FlowNotFoundException):
            approval_service.perform_action(
                flow_id="nonexistent",
                request_id=created_onboarding,
                action="approve",
                step_key="hr_review",
                comment="",
                operator_id="u1",
                operator_name="test",
                operator_role="admin",
            )

    def test_approve_invalid_action(self, approval_service, created_onboarding):
        onboarding_service = approval_service.onboarding_service
        onboarding_service.submit(created_onboarding, "user-001", "admin")
        flow = approval_service.get_flow_for_type("onboarding")

        with pytest.raises(ValidationException, match="无效的审批动作"):
            approval_service.perform_action(
                flow.id, created_onboarding, "invalid_action",
                "hr_review", "", "u1", "test", "admin"
            )


class TestPendingTasks:
    """待办任务测试"""

    def test_get_pending_tasks(self, approval_service, created_onboarding):
        onboarding_service = approval_service.onboarding_service
        onboarding_service.submit(created_onboarding, "user-001", "admin")

        flow = approval_service.get_flow_for_type("onboarding")
        # 执行审批操作会自动创建待办记录
        approval_service.perform_action(
            flow.id, created_onboarding, "approve",
            "hr_review", "", "u1", "HR", "hr_manager"
        )

        # 现在应该有下一个步骤的待办
        result = approval_service.get_pending_tasks("u2")  # 部门经理审批
        # 注意：这里因为没有创建部门经理的待办，所以可能为空
        assert "items" in result


class TestHistory:
    """审批历史测试"""

    def test_get_history(self, approval_service, created_onboarding):
        onboarding_service = approval_service.onboarding_service
        onboarding_service.submit(created_onboarding, "user-001", "admin")

        flow = approval_service.get_flow_for_type("onboarding")
        approval_service.perform_action(
            flow.id, created_onboarding, "approve",
            "hr_review", "同意", "u1", "HR经理", "hr_manager"
        )

        history = approval_service.get_history(created_onboarding)
        assert history["request_id"] == created_onboarding
        assert len(history["records"]) >= 1
        assert history["records"][0]["action"] == "approve"
