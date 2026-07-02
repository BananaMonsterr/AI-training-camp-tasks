"""
员工管理服务单元测试
"""

import pytest
from datetime import date

from services.employee_service import EmployeeService
from utils.exceptions import (
    ValidationException, EmployeeNotFoundException,
    ResourceAlreadyExistsException, ForbiddenException,
)


class TestCreateEmployee:
    """创建员工测试"""

    def test_create_success(self, employee_service, sample_employee_dict):
        result = employee_service.create_employee(sample_employee_dict, "admin")
        assert result["id"] is not None
        assert result["name"] == "张三"
        assert result["status"] == "onboarding"
        assert result["employee_no"].startswith("EMP")

    def test_create_by_hr_manager(self, employee_service, sample_employee_dict):
        result = employee_service.create_employee(sample_employee_dict, "hr_manager")
        assert result["id"] is not None

    def test_create_by_employee_forbidden(self, employee_service, sample_employee_dict):
        with pytest.raises(ForbiddenException):
            employee_service.create_employee(sample_employee_dict, "employee")

    def test_create_missing_required_field(self, employee_service):
        with pytest.raises(ValidationException, match="缺少必填字段"):
            employee_service.create_employee({"name": "test"}, "admin")

    def test_create_duplicate_id_card(self, employee_service, sample_employee_dict):
        employee_service.create_employee(sample_employee_dict, "admin")
        with pytest.raises(ResourceAlreadyExistsException, match="身份证号已存在"):
            employee_service.create_employee({
                **sample_employee_dict,
                "employee_no": "EMP99999",
                "name": "李四",
            }, "admin")

    def test_auto_generate_employee_no(self, employee_service, sample_employee_dict):
        """测试自动生成工号"""
        r1 = employee_service.create_employee(sample_employee_dict, "admin")
        r2 = employee_service.create_employee({
            **sample_employee_dict,
            "id_card": "220101199001011234",
            "name": "李四",
        }, "admin")
        assert r1["employee_no"] != r2["employee_no"]


class TestGetEmployee:
    """查询员工测试"""

    def test_get_by_admin(self, employee_service, created_employee):
        result = employee_service.get_employee(
            created_employee, "admin", "", "", show_sensitive=False
        )
        assert result["id"] == created_employee
        assert "********" in result["id_card"]

    def test_get_with_sensitive(self, employee_service, created_employee):
        result = employee_service.get_employee(
            created_employee, "admin", "", "", show_sensitive=True
        )
        assert "********" not in result["id_card"]

    def test_get_not_found(self, employee_service):
        with pytest.raises(EmployeeNotFoundException):
            employee_service.get_employee("nonexistent", "admin", "", "")

    def test_get_by_employee_self(self, employee_service, created_employee):
        """员工本人可查看"""
        emp = employee_service.get_employee(
            created_employee, "admin", "", "", show_sensitive=False
        )
        result = employee_service.get_employee(
            created_employee, "employee", emp["id"], emp["department_id"]
        )
        assert result["id"] == created_employee


class TestListEmployees:
    """员工列表测试"""

    def test_list_all(self, employee_service, created_employee):
        result = employee_service.list_employees()
        assert result["total"] >= 1
        assert len(result["items"]) >= 1

    def test_list_with_pagination(self, employee_service, created_employee):
        result = employee_service.list_employees(page=1, page_size=10)
        assert result["page"] == 1
        assert result["page_size"] == 10

    def test_list_with_keyword(self, employee_service, created_employee):
        result = employee_service.list_employees(keyword="李四")
        assert result["total"] >= 1

    def test_list_with_keyword_no_match(self, employee_service):
        result = employee_service.list_employees(keyword="不存在的名字")
        assert result["total"] == 0

    def test_list_filter_by_department(self, employee_service, created_employee):
        result = employee_service.list_employees(department_id="dept-002")
        assert result["total"] >= 1

        result = employee_service.list_employees(department_id="dept-999")
        assert result["total"] == 0

    def test_list_sort_by_name(self, employee_service, created_employee):
        # 创建第二个员工
        employee_service.create_employee({
            "name": "王五",
            "id_card": "330101199001011234",
            "email": "ww@company.com",
            "phone": "13700137000",
            "department_id": "dept-001",
            "position": "设计师",
            "hire_date": "2025-01-15",
        }, "admin")

        result = employee_service.list_employees(sort_by="name", sort_order="asc")
        names = [item["name"] for item in result["items"]]
        assert names == sorted(names)


class TestUpdateEmployee:
    """更新员工测试"""

    def test_update_success(self, employee_service, created_employee):
        result = employee_service.update_employee(
            created_employee, {"position": "技术总监"}, "admin"
        )
        assert result["position"] == "技术总监"

    def test_update_not_found(self, employee_service):
        with pytest.raises(EmployeeNotFoundException):
            employee_service.update_employee("nonexistent", {"name": "test"}, "admin")

    def test_update_by_hr_staff_forbidden(self, employee_service, created_employee):
        with pytest.raises(ForbiddenException):
            employee_service.update_employee(created_employee, {"name": "test"}, "employee")


class TestDeleteEmployee:
    """删除员工测试"""

    def test_delete_success(self, employee_service, created_employee):
        employee_service.delete_employee(created_employee, "admin")
        with pytest.raises(EmployeeNotFoundException):
            employee_service.get_employee(created_employee, "admin", "", "")

    def test_delete_not_found(self, employee_service):
        with pytest.raises(EmployeeNotFoundException):
            employee_service.delete_employee("nonexistent", "admin")

    def test_delete_by_non_admin(self, employee_service, created_employee):
        with pytest.raises(ForbiddenException):
            employee_service.delete_employee(created_employee, "employee")


class TestDepartmentEmployees:
    """部门员工查询测试"""

    def test_get_department_employees(self, employee_service, created_employee):
        result = employee_service.get_department_employees(
            "dept-002", "admin", ""
        )
        assert result["total"] >= 1

    def test_dept_manager_only_own_dept(self, employee_service, created_employee):
        with pytest.raises(ForbiddenException):
            employee_service.get_department_employees(
                "dept-001", "dept_manager", "dept-002"  # 经理管辖dept-002，查dept-001
            )

    def test_dept_manager_own_dept_success(self, employee_service, created_employee):
        result = employee_service.get_department_employees(
            "dept-002", "dept_manager", "dept-002"
        )
        assert result["total"] >= 1


class TestHelperMethods:
    """辅助方法测试"""

    def test_get_by_employee_no(self, employee_service, created_employee):
        emp = employee_service.get_by_employee_no("EMP2025")
        # 工号格式为 EMP20250001
        emp_detail = employee_service.get_employee(
            created_employee, "admin", "", ""
        )
        emp_no = emp_detail["employee_no"]
        emp = employee_service.get_by_employee_no(emp_no)
        assert emp is not None
        assert emp.id == created_employee

    def test_count_by_department(self, employee_service, created_employee):
        count = employee_service.count_by_department("dept-002")
        assert count >= 1

        count = employee_service.count_by_department("dept-999")
        assert count == 0
