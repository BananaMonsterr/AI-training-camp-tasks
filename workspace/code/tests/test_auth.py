"""权限控制模块单元测试"""
import pytest
from ..models import db
from ..models.employee import Employee, Department
from ..models.auth import RoleAssignment, RoleType, Permission, ROLE_PERMISSIONS
from ..auth.role_manager import RoleManager, RoleManagerError
from ..auth.permission_checker import PermissionChecker, PermissionDeniedError


class TestRoleManager:
    """角色管理器测试"""

    @pytest.fixture(autouse=True)
    def setup(self, app):
        with app.app_context():
            dept = Department(name='权限测试部', code='DEPT_AUTH')
            db.session.add(dept)
            db.session.flush()

            emp = Employee(
                employee_no='EMP_AUTH_001',
                name='权限用户',
                email='auth@test.com',
                department_id=dept.id,
            )
            db.session.add(emp)
            db.session.commit()

            self.employee_id = emp.id
            self.manager = RoleManager()

    def test_assign_role(self, app):
        with app.app_context():
            ra = self.manager.assign_role(
                employee_id=self.employee_id,
                role_type=RoleType.EMPLOYEE.value,
                assigned_by=1,
            )
            assert ra.id is not None
            assert ra.role_type == 'EMPLOYEE'
            assert ra.is_active is True

    def test_assign_duplicate_role(self, app):
        with app.app_context():
            self.manager.assign_role(self.employee_id, RoleType.EMPLOYEE.value, 1)
            with pytest.raises(RoleManagerError) as exc:
                self.manager.assign_role(self.employee_id, RoleType.EMPLOYEE.value, 1)
            assert '已有此角色' in str(exc.value)

    def test_assign_invalid_role(self, app):
        with app.app_context():
            with pytest.raises(RoleManagerError) as exc:
                self.manager.assign_role(self.employee_id, 'INVALID_ROLE', 1)
            assert '非法角色类型' in str(exc.value)

    def test_assign_role_to_nonexistent_employee(self, app):
        with app.app_context():
            with pytest.raises(RoleManagerError) as exc:
                self.manager.assign_role(99999, RoleType.EMPLOYEE.value, 1)
            assert '不存在' in str(exc.value)

    def test_revoke_role(self, app):
        with app.app_context():
            ra = self.manager.assign_role(self.employee_id, RoleType.HR_MANAGER.value, 1)
            self.manager.revoke_role(ra.id)
            assert ra.is_active is False

    def test_get_user_roles(self, app):
        with app.app_context():
            self.manager.assign_role(self.employee_id, RoleType.DEPARTMENT_HEAD.value, 1)
            self.manager.assign_role(self.employee_id, RoleType.TEAM_LEADER.value, 1)

            roles = self.manager.get_user_roles(self.employee_id)
            assert len(roles) == 2

    def test_get_user_role_types(self, app):
        with app.app_context():
            self.manager.assign_role(self.employee_id, RoleType.HR_MANAGER.value, 1)
            role_types = self.manager.get_user_role_types(self.employee_id)
            assert 'HR_MANAGER' in role_types

    def test_has_permission_true(self, app):
        with app.app_context():
            self.manager.assign_role(self.employee_id, RoleType.HR_MANAGER.value, 1)
            assert self.manager.has_permission(self.employee_id, 'employee:read') is True
            assert self.manager.has_permission(self.employee_id, 'employee:list') is True

    def test_has_permission_false(self, app):
        with app.app_context():
            self.manager.assign_role(self.employee_id, RoleType.EMPLOYEE.value, 1)
            # 普通员工没有删除权限
            assert self.manager.has_permission(self.employee_id, 'employee:delete') is False

    def test_super_admin_has_all(self, app):
        with app.app_context():
            self.manager.assign_role(self.employee_id, RoleType.SUPER_ADMIN.value, 1)
            # 超级管理员应有所有权限
            assert self.manager.has_permission(self.employee_id, 'employee:delete') is True
            assert self.manager.has_permission(self.employee_id, 'approval:batch') is True
            assert self.manager.has_permission(self.employee_id, 'hr:sync') is True

    def test_has_any_permission(self, app):
        with app.app_context():
            self.manager.assign_role(self.employee_id, RoleType.EMPLOYEE.value, 1)
            assert self.manager.has_any_permission(self.employee_id, [
                'employee:read', 'employee:delete'
            ]) is True
            assert self.manager.has_any_permission(self.employee_id, [
                'employee:delete', 'employee:create'
            ]) is False

    def test_has_all_permissions(self, app):
        with app.app_context():
            self.manager.assign_role(self.employee_id, RoleType.HR_MANAGER.value, 1)
            assert self.manager.has_all_permissions(self.employee_id, [
                'employee:read', 'employee:list', 'employee:create'
            ]) is True
            assert self.manager.has_all_permissions(self.employee_id, [
                'employee:delete',  # HR没有删除权限
            ]) is False

    def test_no_role_assigned(self, app):
        with app.app_context():
            # 未分配角色的用户
            assert self.manager.has_permission(self.employee_id, 'employee:read') is False
            assert len(self.manager.get_user_permissions(self.employee_id)) == 0


class TestPermissionChecker:
    """权限检查器测试"""

    @pytest.fixture(autouse=True)
    def setup(self, app):
        with app.app_context():
            dept = Department(name='检查器测试', code='DEPT_CHECK')
            db.session.add(dept)
            db.session.flush()

            emp = Employee(
                employee_no='EMP_CHECK',
                name='检查用户',
                email='check@test.com',
                department_id=dept.id,
            )
            db.session.add(emp)
            db.session.commit()

            # 分配HR角色
            RoleManager().assign_role(emp.id, RoleType.HR_MANAGER.value, 1)
            self.employee_id = emp.id
            self.checker = PermissionChecker()

    def test_check_pass(self):
        result = self.checker.check(self.employee_id, 'employee:read')
        assert result is True

    def test_check_fail(self):
        with pytest.raises(PermissionDeniedError) as exc:
            self.checker.check(self.employee_id, 'employee:delete')
        assert '权限不足' in str(exc.value)

    def test_check_or_fail_true(self):
        assert self.checker.check_or_fail(self.employee_id, 'employee:read') is True

    def test_check_or_fail_false(self):
        assert self.checker.check_or_fail(self.employee_id, 'employee:delete') is False
