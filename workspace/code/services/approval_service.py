"""
审批流服务 - 对应API文档第8章
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from models.approval import (
    ApprovalFlowModel, ApprovalRecordModel,
    FlowType, ApprovalAction, RecordStatus,
)
from utils.exceptions import (
    ValidationException, NotFoundException, FlowNotFoundException,
    StatusConflictException, ForbiddenException,
)


class ApprovalService:
    """
    审批流服务
    
    职责:
    1. 审批流模板管理（CRUD）
    2. 审批操作（通过/驳回/转办）
    3. 待办任务查询
    4. 审批历史查询
    """

    def __init__(self, onboarding_service=None, offboarding_service=None):
        self.onboarding_service = onboarding_service
        self.offboarding_service = offboarding_service
        self._flow_store: dict[str, ApprovalFlowModel] = {}
        self._record_store: dict[str, ApprovalRecordModel] = {}

        # 初始化默认审批流模板
        self._init_default_flows()

    def _init_default_flows(self):
        """初始化默认审批流模板"""
        onboarding_flow = ApprovalFlowModel(
            flow_type=FlowType.ONBOARDING,
            name="标准入职审批流程",
            steps=[
                {
                    "step_key": "hr_review",
                    "step_name": "HR审核",
                    "assignee_role": "hr_manager",
                    "order": 1,
                    "allow_skip": False,
                },
                {
                    "step_key": "dept_review",
                    "step_name": "部门审批",
                    "assignee_role": "dept_manager",
                    "order": 2,
                    "allow_skip": False,
                },
                {
                    "step_key": "it_prepare",
                    "step_name": "IT设备准备",
                    "assignee_role": "it_staff",
                    "order": 3,
                    "allow_skip": True,
                },
            ],
            is_active=True,
            version=1,
        )
        self._flow_store[onboarding_flow.id] = onboarding_flow

        offboarding_flow = ApprovalFlowModel(
            flow_type=FlowType.OFFBOARDING,
            name="标准离职审批流程",
            steps=[
                {
                    "step_key": "dept_manager_review",
                    "step_name": "部门审批",
                    "assignee_role": "dept_manager",
                    "order": 1,
                    "allow_skip": False,
                },
                {
                    "step_key": "hr_review",
                    "step_name": "HR审批",
                    "assignee_role": "hr_manager",
                    "order": 2,
                    "allow_skip": False,
                },
                {
                    "step_key": "exit_interview",
                    "step_name": "离职面谈",
                    "assignee_role": "hr_manager",
                    "order": 3,
                    "allow_skip": False,
                },
                {
                    "step_key": "asset_return",
                    "step_name": "资产归还",
                    "assignee_role": "admin",
                    "order": 4,
                    "allow_skip": False,
                },
            ],
            is_active=True,
            version=1,
        )
        self._flow_store[offboarding_flow.id] = offboarding_flow

    def get_flow_for_type(self, flow_type: str) -> ApprovalFlowModel:
        """根据流程类型获取激活的审批流模板"""
        for flow in self._flow_store.values():
            if flow.flow_type.value == flow_type and flow.is_active:
                return flow
        raise FlowNotFoundException(f"未找到类型为'{flow_type}'的审批流模板")

    def list_flows(self, flow_type: Optional[str] = None,
                   page: int = 1, page_size: int = 20) -> dict:
        """查询审批流模板列表 - 对应API文档8.2.1"""
        flows = list(self._flow_store.values())

        if flow_type:
            flows = [f for f in flows if f.flow_type.value == flow_type]

        flows.sort(key=lambda f: f.created_at, reverse=True)

        total = len(flows)
        start = (page - 1) * page_size
        end = start + page_size
        items = [f.to_dict() for f in flows[start:end]]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size) if page_size > 0 else 1,
        }

    def create_flow(self, data: dict, operator_role: str) -> dict:
        """创建审批流模板 - 对应API文档8.2.2"""
        if operator_role != "admin":
            raise ForbiddenException("仅管理员可以创建审批流模板")

        required = ["flow_type", "name", "steps"]
        for field in required:
            if field not in data:
                raise ValidationException(f"缺少必填字段: {field}")

        flow = ApprovalFlowModel(
            flow_type=FlowType(data["flow_type"]),
            name=data["name"],
            steps=data["steps"],
            is_active=data.get("is_active", True),
            version=data.get("version", 1),
        )

        self._flow_store[flow.id] = flow
        return flow.to_dict()

    def update_flow(self, flow_id: str, data: dict,
                    operator_role: str) -> dict:
        """更新审批流模板"""
        if operator_role != "admin":
            raise ForbiddenException("仅管理员可以更新审批流模板")

        flow = self._flow_store.get(flow_id)
        if not flow:
            raise FlowNotFoundException()

        updatable = ["name", "steps", "is_active", "version"]
        for field in updatable:
            if field in data:
                if field == "flow_type":
                    setattr(flow, field, FlowType(data[field]))
                else:
                    setattr(flow, field, data[field])

        return flow.to_dict()

    def get_flow(self, flow_id: str) -> dict:
        """获取单个审批流模板"""
        flow = self._flow_store.get(flow_id)
        if not flow:
            raise FlowNotFoundException()
        return flow.to_dict()

    def perform_action(self, flow_id: str, request_id: str,
                       action: str, step_key: str, comment: str,
                       operator_id: str, operator_name: str,
                       operator_role: str) -> dict:
        """
        执行审批操作 - 对应API文档8.2.3
        
        统一处理 approve/reject/transfer 操作
        """
        flow = self._flow_store.get(flow_id)
        if not flow:
            raise FlowNotFoundException()

        # 校验审批动作
        try:
            approval_action = ApprovalAction(action)
        except ValueError:
            raise ValidationException(f"无效的审批动作: {action}")

        # 获取步骤定义
        step_def = self._find_step(flow, step_key)
        if not step_def:
            raise ValidationException(f"流程中未找到步骤: {step_key}")

        # 检查当前步骤的待审批记录
        pending_records = [
            r for r in self._record_store.values()
            if r.flow_id == flow_id
            and r.request_id == request_id
            and r.step_key == step_key
            and r.status == RecordStatus.PENDING
        ]

        if not pending_records:
            # 自动创建审批记录（首次审批）
            record = ApprovalRecordModel(
                flow_id=flow_id,
                request_id=request_id,
                request_type=flow.flow_type.value,
                step_key=step_key,
                step_name=step_def["step_name"],
                assignee_id=operator_id,
                assignee_name=operator_name,
                status=RecordStatus.PENDING,
            )
            self._record_store[record.id] = record
            pending_records = [record]

        # 执行审批
        record = pending_records[0]
        record.action = approval_action
        record.comment = comment
        record.operated_at = datetime.now(timezone.utc)

        # 转办处理
        if action == "transfer":
            record.status = RecordStatus.COMPLETED
            return self._handle_transfer(flow, record, step_key, operator_id)

        # 通过/驳回
        record.status = RecordStatus.COMPLETED

        # 调用对应业务服务的状态更新
        if flow.flow_type == FlowType.ONBOARDING and self.onboarding_service:
            result = self.onboarding_service.approve_step(
                request_id, step_key, action, comment,
                operator_id, operator_name
            )
        elif flow.flow_type == FlowType.OFFBOARDING and self.offboarding_service:
            result = self.offboarding_service.approve_step(
                request_id, step_key, action, comment,
                operator_id, operator_name
            )
        else:
            result = {}

        # 判断是否最终步骤
        is_final = self._is_final_step(flow, step_key, action)
        next_step = self._get_next_step(flow, step_key)

        response_data = {
            "record_id": record.id,
            "request_id": request_id,
            "request_type": flow.flow_type.value,
            "action": action,
            "step_key": step_key,
            "previous_status": result.get("status") if action == "reject" else None,
            "current_status": result.get("status"),
            "is_final": is_final,
            "next_step": next_step["step_key"] if next_step else None,
            "next_assignee": {
                "id": step_def.get("assignee_role", ""),
                "name": step_def.get("step_name", ""),
            } if next_step else None,
        }

        return response_data

    def transfer_task(self, flow_id: str, request_id: str,
                      step_key: str, transfer_to_user_id: str,
                      comment: str,
                      operator_id: str, operator_name: str) -> dict:
        """
        转办审批 - 对应API文档8.2.4
        """
        flow = self._flow_store.get(flow_id)
        if not flow:
            raise FlowNotFoundException()

        # 查找当前待审批记录
        pending_records = [
            r for r in self._record_store.values()
            if r.flow_id == flow_id
            and r.request_id == request_id
            and r.step_key == step_key
            and r.status == RecordStatus.PENDING
        ]

        if not pending_records:
            raise StatusConflictException("该步骤没有待审批的记录")

        record = pending_records[0]
        record.action = ApprovalAction.TRANSFER
        record.comment = comment
        record.operated_at = datetime.now(timezone.utc)
        record.status = RecordStatus.COMPLETED
        record.transfer_from_id = operator_id

        # 创建新的待审批记录给接收人
        new_record = ApprovalRecordModel(
            flow_id=flow_id,
            request_id=request_id,
            request_type=flow.flow_type.value,
            step_key=step_key,
            step_name=record.step_name,
            assignee_id=transfer_to_user_id,
            assignee_name=f"User({transfer_to_user_id[:8]})",
            status=RecordStatus.PENDING,
            transfer_from_id=operator_id,
        )
        self._record_store[new_record.id] = new_record

        return {
            "record_id": record.id,
            "original_assignee": operator_id,
            "new_assignee": {
                "id": transfer_to_user_id,
                "name": f"User({transfer_to_user_id[:8]})",
            },
            "step_key": step_key,
        }

    def get_pending_tasks(self, user_id: str,
                          request_type: Optional[str] = None,
                          page: int = 1, page_size: int = 20) -> dict:
        """
        查询待办审批列表 - 对应API文档8.2.5
        """
        records = [
            r for r in self._record_store.values()
            if r.assignee_id == user_id
            and r.status == RecordStatus.PENDING
        ]

        if request_type:
            records = [r for r in records if r.request_type == request_type]

        records.sort(key=lambda r: r.created_at, reverse=True)

        total = len(records)
        start = (page - 1) * page_size
        end = start + page_size
        items = [r.to_dict() for r in records[start:end]]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size) if page_size > 0 else 1,
        }

    def get_history(self, request_id: str) -> dict:
        """
        查询审批历史 - 对应API文档8.2.6
        """
        records = [
            r for r in self._record_store.values()
            if r.request_id == request_id
        ]

        # 获取流程信息
        flow = None
        if records:
            flow = self._flow_store.get(records[0].flow_id)

        records.sort(key=lambda r: r.created_at)

        return {
            "request_id": request_id,
            "request_type": records[0].request_type if records else None,
            "flow_name": flow.name if flow else None,
            "records": [r.to_dict() for r in records],
        }

    def _find_step(self, flow: ApprovalFlowModel, step_key: str) -> Optional[dict]:
        """在流程定义中查找步骤"""
        for step in flow.steps:
            if step["step_key"] == step_key:
                return step
        return None

    def _is_final_step(self, flow: ApprovalFlowModel, step_key: str,
                       action: str) -> bool:
        """判断是否为最终步骤"""
        if action == "reject":
            return True  # 驳回即终态

        steps = sorted(flow.steps, key=lambda s: s.get("order", 0))
        return steps[-1]["step_key"] == step_key if steps else True

    def _get_next_step(self, flow: ApprovalFlowModel,
                       current_step_key: str) -> Optional[dict]:
        """获取下一个步骤"""
        steps = sorted(flow.steps, key=lambda s: s.get("order", 0))
        for i, step in enumerate(steps):
            if step["step_key"] == current_step_key and i + 1 < len(steps):
                return steps[i + 1]
        return None

    def _handle_transfer(self, flow: ApprovalFlowModel, record: ApprovalRecordModel,
                         step_key: str, new_assignee_id: str) -> dict:
        """处理转办逻辑"""
        new_record = ApprovalRecordModel(
            flow_id=record.flow_id,
            request_id=record.request_id,
            request_type=record.request_type,
            step_key=step_key,
            step_name=record.step_name,
            assignee_id=new_assignee_id,
            assignee_name=f"User({new_assignee_id[:8]})",
            status=RecordStatus.PENDING,
            transfer_from_id=record.assignee_id,
        )
        self._record_store[new_record.id] = new_record

        return {
            "record_id": record.id,
            "original_assignee": record.assignee_id,
            "new_assignee": {
                "id": new_assignee_id,
                "name": f"User({new_assignee_id[:8]})",
            },
            "step_key": step_key,
        }
