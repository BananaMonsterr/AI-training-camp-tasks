"""
RBAC权限控制单元测试
"""

import pytest

from auth.rbac import RBACManager, Resource, Permission, Role
from utils.exceptions import ForbiddenException, RoleRequiredException


class TestRBACManager:
    """RBAC管理器测试"""

    def test_admin_has_all_permissions(self, rbac_manager):
        """管理员有所有权限"""
        resources = ["employee", "onboarding", "offboarding", "approval", "notification"]
        actions = ["create", "read", "update", "delete"]
        for r in resources:
            for a in actions:
                assert rbac_manager.check_permission("admin", r, a), f"admin 应有权 {r}.{a}"

    def test_hr_manager_permissions(self, rbac_manager):
        """HR经理权限"""
        assert rbac_manager.check_permission("hr_manager", "employee", "create")
        assert rbac_manager.check_permission("hr_manager", "employee", "read")
        assert rbac_manager.check_permission("hr_manager", "employee", "update")
        assert not rbac_manager.check_permission("hr_manager", "employee", "delete")
        assert rbac_manager.check_permission("hr_manager", "approval", "approve")
        assert rbac_manager.check_permission("hr_manager", "approval", "transfer")

    def test_hr_staff_permissions(self, rbac_manager):
        """HR专员权限"""
        assert rbac_manager.check_permission("hr_staff", "employee", "create")
        assert rbac_manager.check_permission("hr_staff", "employee", "read")
        assert not rbac_manager.check_permission("hr_staff", "approval", "approve")
        assert not rbac_manager.check_permission("hr_staff", "notification", "delete")

    def test_dept_manager_permissions(self, rbac_manager):
        """部门经理权限"""
        assert rbac_manager.check_permission("dept_manager", "employee", "read")
        assert not rbac_manager.check_permission("dept_manager", "employee", "create")
        assert rbac_manager.check_permission("dept_manager", "onboarding", "approve")
        assert rbac_manager.check_permission("dept_manager", "offboarding", "approve")

    def test_employee_permissions(self, rbac_manager):
        """普通员工权限"""
        assert rbac_manager.check_permission("employee", "employee", "read")
        assert not rbac_manager.check_permission("employee", "employee", "create")
        assert rbac_manager.check_permission("employee", "onboarding", "create")
        assert rbac_manager.check_permission("employee", "onboarding", "submit")
        assert not rbac_manager.check_permission("employee", "onboarding", "approve")

    def test_unknown_role(self, rbac_manager):
        assert not rbac_manager.check_permission("unknown_role", "employee", "read")

    def test_unknown_resource(self, rbac_manager):
        assert not rbac_manager.check_permission("admin", "unknown_resource", "read")


class TestRequirePermission:
    """权限校验测试"""

    def test_require_pass(self, rbac_manager):
        # 不应抛出异常
        rbac_manager.require_permission("admin", "employee", "delete")

    def test_require_fail(self, rbac_manager):
        with pytest.raises(ForbiddenException, match="没有"):
            rbac_manager.require_permission("employee", "employee", "delete")

    def test_require_roles_pass(self, rbac_manager):
        rbac_manager.require_roles("admin", ["admin", "hr_manager"])

    def test_require_roles_fail(self, rbac_manager):
        with pytest.raises(RoleRequiredException, match="需要角色"):
            rbac_manager.require_roles("employee", ["admin", "hr_manager"])


class TestHelperMethods:
    """辅助方法测试"""

    def test_is_admin(self, rbac_manager):
        assert rbac_manager.is_admin("admin") is True
        assert rbac_manager.is_admin("employee") is False

    def test_is_hr(self, rbac_manager):
        assert rbac_manager.is_hr("admin") is True
        assert rbac_manager.is_hr("hr_manager") is True
        assert rbac_manager.is_hr("hr_staff") is True
        assert rbac_manager.is_hr("employee") is False

    def test_can_access_employee_admin(self, rbac_manager):
        assert rbac_manager.can_access_employee("admin", "", "", "", "") is True

    def test_can_access_employee_hr(self, rbac_manager):
        assert rbac_manager.can_access_employee("hr_manager", "", "", "", "") is True

    def test_can_access_employee_dept_manager(self, rbac_manager):
        assert rbac_manager.can_access_employee(
            "dept_manager", "dept-001", "dept-001", "user-001", "emp-001"
        ) is True
        assert rbac_manager.can_access_employee(
            "dept_manager", "dept-001", "dept-002", "user-001", "emp-001"
        ) is False

    def test_can_access_employee_self(self, rbac_manager):
        assert rbac_manager.can_access_employee(
            "employee", "dept-001", "dept-001", "user-001", "user-001"
        ) is True
        assert rbac_manager.can_access_employee(
            "employee", "dept-001", "dept-001", "user-001", "emp-other"
        ) is False


class TestCustomRole:
    """自定义角色测试"""

    def test_register_custom_role(self, rbac_manager):
        role = Role(
            name="审计员",
            code="auditor",
            permissions={
                "employee": ["read"],
                "approval": ["read"],
            }
        )
        rbac_manager.register_role(role)
        assert rbac_manager.check_permission("auditor", "employee", "read") is True
        assert rbac_manager.check_permission("auditor", "employee", "create") is False

    def test_get_role(self, rbac_manager):
        role = rbac_manager.get_role("admin")
        assert role is not None
        assert role.name == "系统管理员"

    def test_get_nonexistent_role(self, rbac_manager):
        role = rbac_manager.get_role("nonexistent")
        assert role is None
