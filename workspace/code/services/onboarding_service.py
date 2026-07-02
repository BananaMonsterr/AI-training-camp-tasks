"""
入职申请服务 - 对应API文档第6章
"""

from datetime import date, datetime, timezone
from typing import Any, Optional

from models.onboarding import OnboardingRequestModel, OnboardingStatus
from models.employee import EmployeeModel, EmployeeStatus
from engines.onboarding_sm import OnboardingStateMachine
from utils.exceptions import (
    ValidationException, StatusConflictException, EmployeeNotFoundException,
    NotFoundException, ForbiddenException,
)
from auth.rbac import RBACManager


class OnboardingService:
    """
    入职申请服务
    
    职责:
    1. 入职申请的CRUD
    2. 提交/撤回/删除
    3. 状态机驱动的流程流转
    """

    def __init__(self, rbac_manager: Optional[RBACManager] = None,
                 employee_service=None, notification_service=None):
        self.rbac = rbac_manager or RBACManager()
        self.state_machine = OnboardingStateMachine()
        self.employee_service = employee_service
        self.notification_service = notification_service
        self._store: dict[str, OnboardingRequestModel] = {}

    def create_draft(self, data: dict, applicant_id: str,
                     operator_role: str) -> dict:
        """
        创建入职申请草稿 - 对应API文档6.3.1
        """
        self.rbac.require_permission(operator_role, "onboarding", "create")

        # 校验必填字段
        required = ["employee_id", "offer_letter_url", "expected_hire_date"]
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

        # 创建申请
        request = OnboardingRequestModel(
            employee_id=data["employee_id"],
            applicant_id=applicant_id,
            offer_letter_url=data["offer_letter_url"],
            expected_hire_date=self._parse_date(data["expected_hire_date"]),
            equipment_required=data.get("equipment_required", []),
            seat_location=data.get("seat_location"),
            remark=data.get("remark"),
            status=OnboardingStatus.DRAFT,
        )

        self._store[request.id] = request
        return request.to_dict()

    def submit(self, request_id: str, operator_id: str,
               operator_role: str) -> dict:
        """
        提交入职申请 - 对应API文档6.3.2
        """
        request = self._get_request(request_id)

        # 权限检查：本人或admin/hr_manager
        if operator_role not in ("admin", "hr_manager") and request.applicant_id != operator_id:
            raise ForbiddenException("只有申请人或管理员可以提交")

        # 状态机检查
        if request.status != OnboardingStatus.DRAFT:
            raise StatusConflictException(
                f"当前状态 '{request.status.value}' 不允许提交，仅草稿可提交"
            )

        # 执行状态转移
        try:
            new_state = self.state_machine.transition(
                request.status.value, "submit"
            )
            request.status = OnboardingStatus(new_state)
            request.current_step = "hr_review"
            request.submitted_at = datetime.now(timezone.utc)
        except ValueError as e:
            raise StatusConflictException(str(e))

        # 发送通知
        if self.notification_service:
            self._send_approval_notifications(request, "pending")

        return {
            "id": request.id,
            "status": request.status.value,
            "current_step": request.current_step,
            "submitted_at": int(request.submitted_at.timestamp() * 1000) if request.submitted_at else None,
        }

    def get_request(self, request_id: str, operator_id: str,
                    operator_role: str) -> dict:
        """查询单个入职申请 - 对应API文档6.3.4"""
        request = self._get_request(request_id)

        # 权限检查
        if operator_role not in ("admin", "hr_manager") and request.applicant_id != operator_id:
            raise ForbiddenException("无权查看该入职申请")

        result = request.to_dict()
        return result

    def list_requests(self, status: Optional[str] = None,
                      employee_id: Optional[str] = None,
                      applicant_id: Optional[str] = None,
                      date_from: Optional[str] = None,
                      date_to: Optional[str] = None,
                      page: int = 1, page_size: int = 20,
                      operator_id: Optional[str] = None,
                      operator_role: str = "admin") -> dict:
        """查询入职申请列表 - 对应API文档6.3.3"""
        requests = list(self._store.values())

        # 普通员工只看自己的
        if operator_role == "employee" and operator_id:
            requests = [r for r in requests if r.applicant_id == operator_id]

        # 过滤
        if status:
            try:
                s = OnboardingStatus(status)
                requests = [r for r in requests if r.status == s]
            except ValueError:
                raise ValidationException(f"无效的状态: {status}")

        if employee_id:
            requests = [r for r in requests if r.employee_id == employee_id]
        if applicant_id:
            requests = [r for r in requests if r.applicant_id == applicant_id]

        # 日期过滤
        if date_from:
            from_dt = date.fromisoformat(date_from)
            requests = [r for r in requests if r.created_at.date() >= from_dt]
        if date_to:
            to_dt = date.fromisoformat(date_to)
            requests = [r for r in requests if r.created_at.date() <= to_dt]

        # 排序
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
        """更新入职申请草稿 - 对应API文档6.3.5"""
        request = self._get_request(request_id)

        if operator_role not in ("admin", "hr_manager") and request.applicant_id != operator_id:
            raise ForbiddenException("无权修改该入职申请")

        if request.status != OnboardingStatus.DRAFT:
            raise StatusConflictException("仅草稿状态可编辑")

        # 更新字段
        updatable = ["offer_letter_url", "expected_hire_date",
                     "equipment_required", "seat_location", "remark"]
        for field in updatable:
            if field in data:
                if field == "expected_hire_date":
                    setattr(request, field, self._parse_date(data[field]))
                else:
                    setattr(request, field, data[field])

        return request.to_dict()

    def cancel(self, request_id: str, operator_id: str,
               operator_role: str) -> dict:
        """撤回入职申请 - 对应API文档6.3.6"""
        request = self._get_request(request_id)

        if operator_role not in ("admin",) and request.applicant_id != operator_id:
            raise ForbiddenException("只有申请人或管理员可以撤回")

        if request.status in (OnboardingStatus.APPROVED,
                              OnboardingStatus.REJECTED,
                              OnboardingStatus.CANCELLED):
            raise StatusConflictException(f"当前状态 '{request.status.value}' 不可撤回")

        try:
            new_state = self.state_machine.transition(
                request.status.value, "cancel"
            )
            request.status = OnboardingStatus(new_state)
        except ValueError as e:
            raise StatusConflictException(str(e))

        return {"id": request.id, "status": request.status.value}

    def delete(self, request_id: str, operator_role: str) -> None:
        """删除入职申请 - 对应API文档6.3.7"""
        if operator_role != "admin":
            raise ForbiddenException("仅管理员可以删除")

        request = self._get_request(request_id)
        if request.status not in (OnboardingStatus.DRAFT, OnboardingStatus.CANCELLED):
            raise StatusConflictException("仅草稿或已撤销的申请可删除")

        del self._store[request_id]

    def approve_step(self, request_id: str, step_key: str,
                     action: str, comment: str,
                     operator_id: str, operator_name: str) -> dict:
        """
        审批步骤操作
        由ApprovalService调用，这里做状态更新
        """
        request = self._get_request(request_id)
        status_map = {
            "hr_review": OnboardingStatus.PENDING_HR_REVIEW,
            "dept_review": OnboardingStatus.PENDING_DEPT_REVIEW,
            "it_prepare": OnboardingStatus.PENDING_IT_PREPARE,
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
            request.status = OnboardingStatus(new_state)

            # 更新下一步
            step_order = ["hr_review", "dept_review", "it_prepare"]
            if step_key in step_order:
                idx = step_order.index(step_key)
                if idx + 1 < len(step_order):
                    request.current_step = step_order[idx + 1]
                else:
                    request.current_step = None
                    request.completed_at = datetime.now(timezone.utc)

            # 如果是最后一步(IT准备)，修改员工状态为active
            if request.status == OnboardingStatus.APPROVED:
                if self.employee_service:
                    self.employee_service.update_employee(
                        request.employee_id,
                        {"status": "active"},
                        "admin"
                    )

        elif action == "reject":
            new_state = self.state_machine.transition(
                request.status.value, "reject"
            )
            request.status = OnboardingStatus(new_state)
            request.current_step = None

        return request.to_dict()

    def _get_request(self, request_id: str) -> OnboardingRequestModel:
        """获取申请，不存在的抛异常"""
        request = self._store.get(request_id)
        if not request:
            raise NotFoundException(f"入职申请不存在: {request_id}")
        return request

    def _parse_date(self, date_str: Any) -> date:
        """解析日期"""
        if isinstance(date_str, date):
            return date_str
        if isinstance(date_str, str):
            return date.fromisoformat(date_str)
        raise ValidationException(f"无效的日期格式: {date_str}")

    def _send_approval_notifications(self, request: OnboardingRequestModel,
                                     action: str) -> None:
        """发送审批通知"""
        if not self.notification_service:
            return
        # 这里简化处理，实际应根据流程步骤发给对应审批人
        pass

    def get_available_actions(self, request_id: str) -> list[str]:
        """获取当前状态下可用的操作"""
        request = self._get_request(request_id)
        return self.state_machine.get_available_actions(request.status.value)
