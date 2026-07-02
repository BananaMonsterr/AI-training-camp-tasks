"""
员工管理服务 - 对应API文档第5章
"""

import copy
import time
from datetime import date
from typing import Any, Optional

from models.employee import EmployeeModel, EmployeeStatus, EmploymentType
from utils.exceptions import (
    AppException, EmployeeNotFoundException, ResourceAlreadyExistsException,
    ValidationException, ForbiddenException,
)
from utils.sensitive import auto_mask
from auth.rbac import RBACManager


class EmployeeService:
    """
    员工管理服务
    
    负责员工CRUD操作、部门查询、敏感字段控制
    """

    def __init__(self, rbac_manager: Optional[RBACManager] = None):
        self.rbac = rbac_manager or RBACManager()
        # 模拟数据库存储
        self._store: dict[str, EmployeeModel] = {}
        self._id_counter = 0

    def _next_employee_no(self) -> str:
        """生成下一个工号"""
        self._id_counter += 1
        return f"EMP{time.strftime('%Y')}{self._id_counter:05d}"

    def create_employee(self, data: dict, operator_role: str) -> dict:
        """
        创建员工 - 对应API文档5.2.1
        """
        # 权限检查
        self.rbac.require_permission(operator_role, "employee", "create")

        # 参数校验
        required_fields = ["name", "id_card", "email", "phone",
                           "department_id", "position", "hire_date"]
        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationException(f"缺少必填字段: {field}")

        # 检查唯一性
        for emp in self._store.values():
            if not emp.is_deleted:
                if emp.employee_no == data.get("employee_no"):
                    raise ResourceAlreadyExistsException(f"工号 '{data['employee_no']}' 已存在")
                if emp.id_card == data.get("id_card"):
                    raise ResourceAlreadyExistsException("身份证号已存在")

        # 创建模型
        employee = EmployeeModel(
            employee_no=data.get("employee_no", self._next_employee_no()),
            name=data["name"],
            id_card=data["id_card"],
            email=data["email"],
            phone=data["phone"],
            department_id=data["department_id"],
            position=data["position"],
            hire_date=data["hire_date"] if isinstance(data["hire_date"], date)
                     else date.fromisoformat(data["hire_date"]),
            status=EmployeeStatus.ONBOARDING,
            manager_id=data.get("manager_id"),
            employment_type=EmploymentType(
                data.get("employment_type", "full_time")
            ),
        )

        self._store[employee.id] = employee
        return employee.to_dict(sensitive=False)

    def get_employee(self, employee_id: str, operator_role: str,
                     operator_id: str, operator_dept_id: str,
                     show_sensitive: bool = False) -> dict:
        """
        查询单个员工 - 对应API文档5.2.3
        """
        employee = self._store.get(employee_id)
        if not employee or employee.is_deleted:
            raise EmployeeNotFoundException()

        # 权限检查
        if not self.rbac.can_access_employee(
            operator_role, operator_dept_id, employee.department_id,
            operator_id, employee_id
        ):
            raise ForbiddenException("无权访问该员工信息")

        result = employee.to_dict(sensitive=show_sensitive)
        return result

    def list_employees(self, keyword: Optional[str] = None,
                       department_id: Optional[str] = None,
                       status: Optional[str] = None,
                       employment_type: Optional[str] = None,
                       page: int = 1, page_size: int = 20,
                       sort_by: str = "created_at",
                       sort_order: str = "desc",
                       operator_role: str = "admin",
                       operator_dept_id: Optional[str] = None) -> dict:
        """
        查询员工列表 - 对应API文档5.2.2
        """
        employees = list(self._store.values())

        # 过滤已删除
        employees = [e for e in employees if not e.is_deleted]

        # 部门经理只能看本部门
        if operator_role == "dept_manager" and operator_dept_id:
            employees = [
                e for e in employees if e.department_id == operator_dept_id
            ]

        # 关键词过滤
        if keyword:
            keyword = keyword.lower()
            employees = [
                e for e in employees
                if keyword in e.name.lower()
                or keyword in e.employee_no.lower()
                or keyword in e.email.lower()
            ]

        # 部门过滤
        if department_id:
            employees = [e for e in employees if e.department_id == department_id]

        # 状态过滤
        if status:
            try:
                status_enum = EmployeeStatus(status)
                employees = [e for e in employees if e.status == status_enum]
            except ValueError:
                raise ValidationException(f"无效的员工状态: {status}")

        # 雇佣类型过滤
        if employment_type:
            try:
                emp_type = EmploymentType(employment_type)
                employees = [e for e in employees if e.employment_type == emp_type]
            except ValueError:
                raise ValidationException(f"无效的雇佣类型: {employment_type}")

        # 排序
        reverse = sort_order.lower() == "desc"
        if sort_by == "name":
            employees.sort(key=lambda e: e.name, reverse=reverse)
        elif sort_by == "employee_no":
            employees.sort(key=lambda e: e.employee_no, reverse=reverse)
        else:
            employees.sort(key=lambda e: e.created_at, reverse=reverse)

        # 分页
        total = len(employees)
        start = (page - 1) * page_size
        end = start + page_size
        items = [e.to_dict(sensitive=False) for e in employees[start:end]]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size) if page_size > 0 else 1,
        }

    def update_employee(self, employee_id: str, data: dict,
                        operator_role: str) -> dict:
        """
        更新员工信息 - 对应API文档5.2.4
        """
        self.rbac.require_permission(operator_role, "employee", "update")

        employee = self._store.get(employee_id)
        if not employee or employee.is_deleted:
            raise EmployeeNotFoundException()

        # 更新字段
        updatable_fields = ["name", "email", "phone", "department_id",
                            "position", "manager_id", "employment_type", "status"]
        for field in updatable_fields:
            if field in data and data[field] is not None:
                if field == "status":
                    try:
                        setattr(employee, field, EmployeeStatus(data[field]))
                    except ValueError:
                        raise ValidationException(f"无效的员工状态: {data[field]}")
                elif field == "employment_type":
                    try:
                        setattr(employee, field, EmploymentType(data[field]))
                    except ValueError:
                        raise ValidationException(f"无效的雇佣类型: {data[field]}")
                else:
                    setattr(employee, field, data[field])

        return employee.to_dict(sensitive=False)

    def delete_employee(self, employee_id: str, operator_role: str) -> None:
        """
        删除员工（软删除）- 对应API文档5.2.5
        """
        self.rbac.require_permission(operator_role, "employee", "delete")

        employee = self._store.get(employee_id)
        if not employee or employee.is_deleted:
            raise EmployeeNotFoundException()

        employee.is_deleted = True
        employee.status = EmployeeStatus.TERMINATED

    def get_department_employees(self, department_id: str,
                                 operator_role: str,
                                 operator_dept_id: str,
                                 page: int = 1, page_size: int = 20) -> dict:
        """
        查询部门员工 - 对应API文档5.2.6
        """
        # 部门经理只能查本部门
        if operator_role == "dept_manager" and operator_dept_id != department_id:
            raise ForbiddenException("您只能查看本部门的员工")

        return self.list_employees(
            department_id=department_id,
            page=page,
            page_size=page_size,
            operator_role=operator_role,
            operator_dept_id=operator_dept_id,
        )

    def get_by_employee_no(self, employee_no: str) -> Optional[EmployeeModel]:
        """根据工号查询员工"""
        for emp in self._store.values():
            if emp.employee_no == employee_no and not emp.is_deleted:
                return emp
        return None

    def count_by_department(self, department_id: str) -> int:
        """统计部门员工数"""
        return len([
            e for e in self._store.values()
            if e.department_id == department_id and not e.is_deleted
        ])
