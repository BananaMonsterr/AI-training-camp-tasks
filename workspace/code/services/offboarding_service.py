"""
离职申请服务 - 对应API文档第7章
"""

from datetime import date, datetime, timezone
from typing import Any, Optional

from models.offboarding import (
    OffboardingRequestModel, OffboardingStatus,
    ResignationType, AssetReturnStatus,
)
from models.employee import EmployeeModel, EmployeeStatus
from engines.offboarding_sm import OffboardingStateMachine
from utils.exceptions import (
    ValidationException, StatusConflictException, EmployeeNotFoundException,
    NotFoundException, ForbiddenException,
)
from auth.rbac import RBACManager


class OffboardingService:
    """
    离职申请服务
    
    职责:
    1. 离职申请的CRUD
    2. 提交/撤回/删除
    3. 状态机驱动的流程流转
    """

    def __init__(self, rbac_manager: Optional[RBACManager] = None,
                 employee_service=None, notification_service=None):
        self.rbac = rbac_manager or RBACManager()
        self.state_machine = OffboardingStateMachine()
        self.employee_service = employee_service
        self.notification_service = notification_service
        self._store: dict[str, OffboardingRequestModel] = {}

    def create_draft(self, data: dict, applicant_id: str,
                     operator_role: str) -> dict:
        """
        创建离职申请草稿 - 对应API文档7.3.1
        """
        self.rbac.require_permission(operator_role, "offboarding", "create")

        required = ["employee_id", "resignation_type", "reason",
                     "expected_last_work_date"]
        for field in required:
            if field not in data or not data[field]:
                raise ValidationException(f"缺少必填字段: {field}")

        # 校验员工存在
        if self.employee_service:
            try:
                emp = self.employee_service.get_employee(
                    data["employee_id"], "admin", "", "", show_sensitive=False
                )
            except EmployeeNotFoundException:
                raise EmployeeNotFoundException("关联员工不存在")

        # 解析枚举
        try:
            res_type = ResignationType(data["resignation_type"])
        except ValueError:
            raise ValidationException(
                f"无效的离职类型: {data['resignation_type']}"
            )

        request = OffboardingRequestModel(
            employee_id=data["employee_id"],
            applicant_id=applicant_id,
            resignation_type=res_type,
            reason=data["reason"],
            expected_last_work_date=self._parse_date(data["expected_last_work_date"]),
            handover_note=data.get("handover_note"),
            asset_return_status=AssetReturnStatus.PENDING,
            status=OffboardingStatus.DRAFT,
        )

        self._store[request.id] = request
        return request.to_dict()

    def submit(self, request_id: str, operator_id: str,
               operator_role: str) -> dict:
        """提交离职申请 - 对应API文档7.3.2"""
        request = self._get_request(request_id)

        if operator_role not in ("admin",) and request.applicant_id != operator_id:
            raise ForbiddenException("只有申请人或管理员可以提交")

        if request.status != OffboardingStatus.DRAFT:
            raise StatusConflictException(
                f"当前状态 '{request.status.value}' 不允许提交"
            )

        try:
            new_state = self.state_machine.transition(
                request.status.value, "submit"
            )
            request.status = OffboardingStatus(new_state)
            request.current_step = "dept_manager_review"
            request.submitted_at = datetime.now(timezone.utc)
        except ValueError as e:
            raise StatusConflictException(str(e))

        return {
            "id": request.id,
            "status": request.status.value,
            "current_step": request.current_step,
            "submitted_at": int(request.submitted_at.timestamp() * 1000) if request.submitted_at else None,
        }

    def get_request(self, request_id: str, operator_id: str,
                    operator_role: str) -> dict:
        """查询单个离职申请 - 对应API文档7.3.4"""
        request = self._get_request(request_id)

        if operator_role not in ("admin", "hr_manager") and request.applicant_id != operator_id:
            raise ForbiddenException("无权查看该离职申请")

        return request.to_dict()

    def list_requests(self, status: Optional[str] = None,
                      employee_id: Optional[str] = None,
                      applicant_id: Optional[str] = None,
                      date_from: Optional[str] = None,
                      date_to: Optional[str] = None,
                      page: int = 1, page_size: int = 20,
                      operator_id: Optional[str] = None,
                      operator_role: str = "admin") -> dict:
        """查询离职申请列表 - 对应API文档7.3.3"""
        requests = list(self._store.values())

        if operator_role == "employee" and operator_id:
            requests = [r for r in requests if r.applicant_id == operator_id]

        if status:
            try:
                s = OffboardingStatus(status)
                requests = [r for r in requests if r.status == s]
            except ValueError:
                raise ValidationException(f"无效的状态: {status}")

        if employee_id:
            requests = [r for r in requests if r.employee_id == employee_id]
        if applicant_id:
            requests = [r for r in requests if r.applicant_id == applicant_id]

        if date_from:
            from_dt = date.fromisoformat(date_from)
            requests = [r for r in requests if r.created_at.date() >= from_dt]
        if date_to:
            to_dt = date.fromisoformat(date_to)
            requests = [r for r in requests if r.created_at.date() <= to_dt]

        requests.sort(key=lambda r: r.created_at, reverse=True)

        total = len(requests)
        start = (page - 1) * page_size
        end = start + page_size
        items = [r.to_dict() for r in requests[start:end]]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size) if page_size > 0 else 1,
        }

    def update_draft(self, request_id: str, data: dict,
                     operator_id: str, operator_role: str) -> dict:
        """更新离职申请草稿 - 对应API文档7.3.5"""
        request = self._get_request(request_id)

        if operator_role not in ("admin",) and request.applicant_id != operator_id:
            raise ForbiddenException("无权修改该离职申请")

        if request.status != OffboardingStatus.DRAFT:
            raise StatusConflictException("仅草稿状态可编辑")

        updatable = ["resignation_type", "reason", "expected_last_work_date",
                     "handover_note"]
        for field in updatable:
            if field in data:
                if field == "resignation_type":
                    try:
                        setattr(request, field, ResignationType(data[field]))
                    except ValueError:
                        raise ValidationException(f"无效的离职类型: {data[field]}")
                elif field == "expected_last_work_date":
                    setattr(request, field, self._parse_date(data[field]))
                else:
                    setattr(request, field, data[field])

        return request.to_dict()

    def cancel(self, request_id: str, operator_id: str,
               operator_role: str) -> dict:
        """撤回离职申请"""
        request = self._get_request(request_id)

        if operator_role not in ("admin",) and request.applicant_id != operator_id:
            raise ForbiddenException("只有申请人或管理员可以撤回")

        if request.status in (OffboardingStatus.APPROVED,
                              OffboardingStatus.REJECTED,
                              OffboardingStatus.CANCELLED):
            raise StatusConflictException(f"当前状态 '{request.status.value}' 不可撤回")

        try:
            new_state = self.state_machine.transition(
                request.status.value, "cancel"
            )
            request.status = OffboardingStatus(new_state)
        except ValueError as e:
            raise StatusConflictException(str(e))

        return {"id": request.id, "status": request.status.value}

    def delete(self, request_id: str, operator_role: str) -> None:
        """删除离职申请"""
        if operator_role != "admin":
            raise ForbiddenException("仅管理员可以删除")

        request = self._get_request(request_id)
        if request.status not in (OffboardingStatus.DRAFT, OffboardingStatus.CANCELLED):
            raise StatusConflictException("仅草稿或已撤销的申请可删除")

        del self._store[request_id]

    def approve_step(self, request_id: str, step_key: str,
                     action: str, comment: str,
                     operator_id: str, operator_name: str) -> dict:
        """审批步骤操作"""
        request = self._get_request(request_id)
        status_map = {
            "dept_manager_review": OffboardingStatus.PENDING_DEPT_REVIEW,
            "hr_review": OffboardingStatus.PENDING_HR_REVIEW,
            "exit_interview": OffboardingStatus.PENDING_EXIT_INTERVIEW,
            "asset_return": OffboardingStatus.PENDING_ASSET_RETURN,
        }

        expected_status = status_map.get(step_key)
        if expected_status and request.status != expected_status:
            raise StatusConflictException(
                f"当前状态 '{request.status.value}' 与步骤 '{step_key}' 不匹配"
            )

        if action == "approve":
            new_state = self.state_machine.transition(
                request.status.value, "approve"
            )
            request.status = OffboardingStatus(new_state)

            step_order = ["dept_manager_review", "hr_review",
                          "exit_interview", "asset_return"]
            if step_key in step_order:
                idx = step_order.index(step_key)
                if idx + 1 < len(step_order):
                    request.current_step = step_order[idx + 1]
                else:
                    request.current_step = None
                    request.completed_at = datetime.now(timezone.utc)

            # 离职最终通过，修改员工状态
            if request.status == OffboardingStatus.APPROVED:
                if self.employee_service:
                    self.employee_service.update_employee(
                        request.employee_id,
                        {"status": "terminated"},
                        "admin"
                    )

        elif action == "reject":
            new_state = self.state_machine.transition(
                request.status.value, "reject"
            )
            request.status = OffboardingStatus(new_state)
            request.current_step = None

        return request.to_dict()

    def _get_request(self, request_id: str) -> OffboardingRequestModel:
        request = self._store.get(request_id)
        if not request:
            raise NotFoundException(f"离职申请不存在: {request_id}")
        return request

    def _parse_date(self, date_str: Any) -> date:
        if isinstance(date_str, date):
            return date_str
        if isinstance(date_str, str):
            return date.fromisoformat(date_str)
        raise ValidationException(f"无效的日期格式: {date_str}")

    def get_available_actions(self, request_id: str) -> list[str]:
        """获取当前状态下可用的操作"""
        request = self._get_request(request_id)
        return self.state_machine.get_available_actions(request.status.value)
