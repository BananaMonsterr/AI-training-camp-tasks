"""
基于角色的访问控制 - 对应API文档第4.2节权限矩阵
"""

import enum
from dataclasses import dataclass, field
from typing import Optional

from utils.exceptions import ForbiddenException, RoleRequiredException


class Resource(str, enum.Enum):
    """资源类型"""
    EMPLOYEE = "employee"
    ONBOARDING = "onboarding"
    OFFBOARDING = "offboarding"
    APPROVAL = "approval"
    NOTIFICATION = "notification"
    HR_INTEGRATION = "hr_integration"


class Permission(str, enum.Enum):
    """操作权限"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    REJECT = "reject"
    TRANSFER = "transfer"
    SUBMIT = "submit"
    CANCEL = "cancel"
    EXPORT = "export"


@dataclass
class Role:
    """角色定义"""
    name: str
    code: str
    permissions: dict[str, list[str]] = field(default_factory=dict)

    def has_permission(self, resource: str, action: str) -> bool:
        """检查是否有指定资源的操作权限"""
        if resource not in self.permissions:
            return False
        return action in self.permissions[resource]


class RBACManager:
    """
    RBAC 权限管理器
    
    权限矩阵（API文档4.2节）：
    | 角色 | Employee | Onboarding | Offboarding | Approval | Notification |
    |------|----------|------------|-------------|----------|--------------|
    | admin | CRUD | CRUD | CRUD | 全部操作 | 全部操作 |
    | hr_manager | 读+写 | 审批+管理 | 审批+管理 | 审批+转办 | 读+写 |
    | hr_staff | 读+写 | 读+写 | 读+写 | 仅查看 | 读 |
    | dept_manager | 读(本部门) | 审批 | 审批 | 审批+转办 | 读 |
    | employee | 仅查看本人 | 创建+查看 | 创建+查看 | 仅查看本人相关 | 读本人 |
    """

    def __init__(self):
        self._roles: dict[str, Role] = {}
        self._init_default_roles()

    def _init_default_roles(self):
        """初始化默认角色权限"""

        # admin - 全部权限
        admin_permissions = {
            Resource.EMPLOYEE.value: ["create", "read", "update", "delete"],
            Resource.ONBOARDING.value: ["create", "read", "update", "delete",
                                        "approve", "reject", "submit", "cancel"],
            Resource.OFFBOARDING.value: ["create", "read", "update", "delete",
                                         "approve", "reject", "submit", "cancel"],
            Resource.APPROVAL.value: ["create", "read", "update", "delete",
                                      "approve", "reject", "transfer"],
            Resource.NOTIFICATION.value: ["create", "read", "update", "delete"],
            Resource.HR_INTEGRATION.value: ["create", "read", "update", "delete"],
        }
        self.register_role(Role("系统管理员", "admin", admin_permissions))

        # hr_manager - HR经理
        hr_manager_permissions = {
            Resource.EMPLOYEE.value: ["create", "read", "update"],
            Resource.ONBOARDING.value: ["create", "read", "update",
                                        "approve", "reject", "submit", "cancel"],
            Resource.OFFBOARDING.value: ["create", "read", "update",
                                         "approve", "reject", "submit", "cancel"],
            Resource.APPROVAL.value: ["read", "approve", "reject", "transfer"],
            Resource.NOTIFICATION.value: ["create", "read", "update"],
        }
        self.register_role(Role("HR经理", "hr_manager", hr_manager_permissions))

        # hr_staff - HR专员
        hr_staff_permissions = {
            Resource.EMPLOYEE.value: ["create", "read", "update"],
            Resource.ONBOARDING.value: ["create", "read", "update"],
            Resource.OFFBOARDING.value: ["create", "read", "update"],
            Resource.APPROVAL.value: ["read"],
            Resource.NOTIFICATION.value: ["read"],
        }
        self.register_role(Role("HR专员", "hr_staff", hr_staff_permissions))

        # dept_manager - 部门经理
        dept_manager_permissions = {
            Resource.EMPLOYEE.value: ["read"],  # 仅本部门
            Resource.ONBOARDING.value: ["read", "approve", "reject"],
            Resource.OFFBOARDING.value: ["read", "approve", "reject"],
            Resource.APPROVAL.value: ["read", "approve", "reject", "transfer"],
            Resource.NOTIFICATION.value: ["read"],
        }
        self.register_role(Role("部门经理", "dept_manager", dept_manager_permissions))

        # employee - 普通员工
        employee_permissions = {
            Resource.EMPLOYEE.value: ["read"],  # 仅本人
            Resource.ONBOARDING.value: ["create", "read", "submit", "cancel"],
            Resource.OFFBOARDING.value: ["create", "read", "submit", "cancel"],
            Resource.APPROVAL.value: ["read"],  # 仅本人相关
            Resource.NOTIFICATION.value: ["read"],  # 仅本人
        }
        self.register_role(Role("普通员工", "employee", employee_permissions))

    def register_role(self, role: Role) -> None:
        """注册角色"""
        self._roles[role.code] = role

    def get_role(self, role_code: str) -> Optional[Role]:
        """获取角色"""
        return self._roles.get(role_code)

    def check_permission(self, role_code: str, resource: str, action: str) -> bool:
        """
        检查角色是否有指定资源的操作权限
        """
        role = self.get_role(role_code)
        if not role:
            return False
        return role.has_permission(resource, action)

    def require_permission(self, role_code: str, resource: str, action: str) -> None:
        """
        要求具备指定权限，否则抛出异常
        """
        if not self.check_permission(role_code, resource, action):
            role = self.get_role(role_code)
            role_name = role.name if role else "未知"
            raise ForbiddenException(
                f"角色'{role_name}'没有资源'{resource}'的'{action}'权限"
            )

    def require_roles(self, user_role: str, allowed_roles: list[str]) -> None:
        """
        要求用户属于指定角色之一
        """
        if user_role not in allowed_roles:
            raise RoleRequiredException(
                f"需要角色{'/'.join(allowed_roles)}才能执行此操作"
            )

    def is_admin(self, role_code: str) -> bool:
        """是否为管理员"""
        return role_code == "admin"

    def is_hr(self, role_code: str) -> bool:
        """是否为HR角色（经理或专员）"""
        return role_code in ("hr_manager", "hr_staff", "admin")

    def can_access_employee(self, user_role: str, user_dept_id: str,
                            target_dept_id: str, user_id: str,
                            target_employee_id: str) -> bool:
        """
        检查是否可以访问员工信息
        - admin/hr可以访问全部
        - dept_manager仅本部门
        - employee仅本人
        """
        if user_role in ("admin", "hr_manager", "hr_staff"):
            return True
        if user_role == "dept_manager" and user_dept_id == target_dept_id:
            return True
        if user_role == "employee" and user_id == target_employee_id:
            return True
        return False
