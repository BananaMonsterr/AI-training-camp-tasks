"""
审批流引擎 - 基于状态机的审批流程编排

职责：
1. 提交审批 -> 创建审批节点链 + 状态机转换
2. 审批操作（同意/驳回）-> 更新节点 + 状态机转换
3. 完成流程 -> 最终状态转换
4. 批量审批支持
5. 审批人自动指派
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from models import db
from models.employee import EmployeeModel as Employee
from models.onboarding import OnboardingRequestModel as OnboardingRequest, OnboardingStatus
from models.offboarding import OffboardingRequestModel as OffboardingRequest, OffboardingStatus
from models.approval import ApprovalNode, NodeStatus
from .state_machine import StateMachine, create_onboarding_state_machine, create_offboarding_state_machine
from notifications.notification_service import NotificationService


class ApprovalEngineError(Exception):
    """审批流引擎异常"""
    pass


class ApprovalEngine:
    """
    审批流引擎 - 核心业务编排
    """

    def __init__(self):
        self.onboarding_sm = create_onboarding_state_machine()
        self.offboarding_sm = create_offboarding_state_machine()
        self.notification_service = NotificationService()

    # ----------------------------------------------------------------
    # 提交审批
    # ----------------------------------------------------------------

    def submit_onboarding(self, request_id: int, user_id: int) -> OnboardingRequest:
        """提交入职申请审批"""
        req = OnboardingRequest.query.get(request_id)
        if not req:
            raise ApprovalEngineError(f'入职申请不存在: id={request_id}')
        if req.applicant_id != user_id:
            raise ApprovalEngineError('只有申请人才能提交审批')

        # 状态机转换: DRAFT -> PENDING_APPROVAL
        req.status = self.onboarding_sm.fire(req.status, 'submit', {
            'user_id': user_id, 'request_id': request_id
        })

        # 自动生成审批节点
        self._create_onboarding_approval_nodes(req, user_id)

        # 更新当前审批人（取第一个节点）
        first_node = ApprovalNode.query.filter_by(
            onboarding_request_id=request_id,
            status=NodeStatus.PENDING.value
        ).order_by(ApprovalNode.node_order).first()
        if first_node:
            req.current_approver_id = first_node.approver_id
            req.current_approver_name = first_node.approver_name

        db.session.commit()

        # 发送通知给审批人
        self.notification_service.notify_approval_task(
            recipient_id=req.current_approver_id,
            recipient_name=req.current_approver_name or '',
            ref_type='onboarding',
            ref_id=req.id,
            title=f'【入职审批】{req.candidate_name} 的入职申请待审批',
            content=f'候选人 {req.candidate_name} 申请入职 {req.position}，'
                    f'预计入职日期: {req.expected_hire_date}',
        )

        return req

    def submit_offboarding(self, request_id: int, user_id: int) -> OffboardingRequest:
        """提交离职申请审批"""
        req = OffboardingRequest.query.get(request_id)
        if not req:
            raise ApprovalEngineError(f'离职申请不存在: id={request_id}')

        # 状态机转换: DRAFT -> PENDING_APPROVAL
        req.status = self.offboarding_sm.fire(req.status, 'submit', {
            'user_id': user_id, 'request_id': request_id
        })

        # 自动生成审批节点
        self._create_offboarding_approval_nodes(req, user_id)

        # 更新当前审批人
        first_node = ApprovalNode.query.filter_by(
            offboarding_request_id=request_id,
            status=NodeStatus.PENDING.value
        ).order_by(ApprovalNode.node_order).first()
        if first_node:
            req.current_approver_id = first_node.approver_id
            req.current_approver_name = first_node.approver_name

        db.session.commit()

        # 发送通知
        self.notification_service.notify_approval_task(
            recipient_id=req.current_approver_id,
            recipient_name=req.current_approver_name or '',
            ref_type='offboarding',
            ref_id=req.id,
            title=f'【离职审批】{req.employee_name} 的离职申请待审批',
            content=f'员工 {req.employee_name} 申请离职，类型: {req.offboarding_type}，'
                    f'预计最后工作日: {req.expected_last_date}',
        )

        return req

    # ----------------------------------------------------------------
    # 审批操作
    # ----------------------------------------------------------------

    def approve(self, node_id: int, user_id: int, comment: str = None) -> dict:
        """
        审批通过
        Returns: 包含更新后的申请主信息
        """
        node = ApprovalNode.query.get(node_id)
        if not node:
            raise ApprovalEngineError(f'审批节点不存在: id={node_id}')
        if node.approver_id != user_id:
            raise ApprovalEngineError('您不是此节点的审批人')
        if node.status != NodeStatus.PENDING.value:
            raise ApprovalEngineError(f'节点状态不是待审批: {node.status}')

        now = datetime.now(timezone.utc)

        # 更新节点
        node.status = NodeStatus.APPROVED.value
        node.comment = comment
        node.operated_at = now
        db.session.flush()

        result = {
            'node_id': node.id,
            'node_name': node.node_name,
            'action': 'approve',
            'comment': comment,
        }

        # 判断是入职还是离职
        req = None
        req_type = None

        if node.onboarding_request_id:
            req = OnboardingRequest.query.get(node.onboarding_request_id)
            req_type = 'onboarding'
        elif node.offboarding_request_id:
            req = OffboardingRequest.query.get(node.offboarding_request_id)
            req_type = 'offboarding'

        if not req:
            raise ApprovalEngineError('关联的申请记录不存在')

        # 检查是否还有下一个节点
        next_node = ApprovalNode.query.filter(
            ((ApprovalNode.onboarding_request_id == node.onboarding_request_id) |
             (ApprovalNode.offboarding_request_id == node.offboarding_request_id)) &
            (ApprovalNode.node_order > node.node_order) &
            (ApprovalNode.status == NodeStatus.PENDING.value) &
            (ApprovalNode.id != node.id)
        ).order_by(ApprovalNode.node_order).first()

        if next_node:
            # 流转到下一节点
            req.current_approver_id = next_node.approver_id
            req.current_approver_name = next_node.approver_name
            db.session.flush()

            # 通知下一审批人
            self.notification_service.notify_approval_task(
                recipient_id=next_node.approver_id,
                recipient_name=next_node.approver_name or '',
                ref_type=req_type,
                ref_id=req.id,
                title=f'【审批流转】{self._get_req_title(req, req_type)} 已流转到您',
                content=f'请及时处理审批',
            )

            result['next_approver'] = next_node.approver_name
        else:
            # 所有节点通过，申请通过
            sm = self.onboarding_sm if req_type == 'onboarding' else self.offboarding_sm
            try:
                req.status = sm.fire(req.status, 'approve', {
                    'user_id': user_id,
                    'request_id': req.id
                })
            except Exception as e:
                raise ApprovalEngineError(f'状态流转失败: {str(e)}')

            req.current_approver_id = None
            req.current_approver_name = None
            req.final_approver_id = user_id
            req.approved_at = now
            db.session.flush()

            # 通知申请人审批通过
            self._notify_approval_result(req, req_type, 'approved')

            result['final_status'] = req.status

        db.session.commit()
        result['request_status'] = req.status
        return result

    def reject(self, node_id: int, user_id: int, comment: str = None) -> dict:
        """
        驳回审批
        """
        node = ApprovalNode.query.get(node_id)
        if not node:
            raise ApprovalEngineError(f'审批节点不存在: id={node_id}')
        if node.approver_id != user_id:
            raise ApprovalEngineError('您不是此节点的审批人')
        if node.status != NodeStatus.PENDING.value:
            raise ApprovalEngineError(f'节点状态不是待审批: {node.status}')

        now = datetime.now(timezone.utc)

        # 更新当前节点
        node.status = NodeStatus.REJECTED.value
        node.comment = comment
        node.operated_at = now
        db.session.flush()

        # 判断是入职还是离职
        req = None
        req_type = None

        if node.onboarding_request_id:
            req = OnboardingRequest.query.get(node.onboarding_request_id)
            req_type = 'onboarding'
        elif node.offboarding_request_id:
            req = OffboardingRequest.query.get(node.offboarding_request_id)
            req_type = 'offboarding'

        if not req:
            raise ApprovalEngineError('关联的申请记录不存在')

        # 将所有后续待审批节点标记为已跳过
        pending_nodes = ApprovalNode.query.filter(
            ((ApprovalNode.onboarding_request_id == node.onboarding_request_id) |
             (ApprovalNode.offboarding_request_id == node.offboarding_request_id)) &
            (ApprovalNode.node_order > node.node_order) &
            (ApprovalNode.status == NodeStatus.PENDING.value)
        ).all()

        for pn in pending_nodes:
            pn.status = NodeStatus.SKIPPED.value
            pn.operated_at = now
        db.session.flush()

        # 状态转换: PENDING_APPROVAL -> REJECTED
        sm = self.onboarding_sm if req_type == 'onboarding' else self.offboarding_sm
        try:
            req.status = sm.fire(req.status, 'reject', {
                'user_id': user_id,
                'request_id': req.id,
                'comment': comment,
            })
        except Exception as e:
            raise ApprovalEngineError(f'状态流转失败: {str(e)}')

        req.current_approver_id = None
        req.current_approver_name = None
        req.reject_reason = comment
        db.session.flush()

        # 通知申请人被驳回
        self._notify_approval_result(req, req_type, 'rejected', comment)

        db.session.commit()

        return {
            'node_id': node.id,
            'action': 'reject',
            'comment': comment,
            'request_status': req.status,
        }

    # ----------------------------------------------------------------
    # 撤回/取消
    # ----------------------------------------------------------------

    def withdraw(self, request_type: str, request_id: int, user_id: int) -> dict:
        """撤回申请（在待审批状态下）"""
        if request_type == 'onboarding':
            req = OnboardingRequest.query.get(request_id)
            sm = self.onboarding_sm
        else:
            req = OffboardingRequest.query.get(request_id)
            sm = self.offboarding_sm

        if not req:
            raise ApprovalEngineError(f'{request_type}申请不存在')

        req.status = sm.fire(req.status, 'withdraw', {
            'user_id': user_id, 'request_id': request_id
        })
        req.current_approver_id = None
        req.current_approver_name = None

        # 将待审批节点标记为已跳过
        pending_nodes = ApprovalNode.query.filter(
            ((ApprovalNode.onboarding_request_id == request_id) |
             (ApprovalNode.offboarding_request_id == request_id)) &
            (ApprovalNode.status == NodeStatus.PENDING.value)
        ).all()
        now = datetime.now(timezone.utc)
        for pn in pending_nodes:
            pn.status = NodeStatus.SKIPPED.value
            pn.operated_at = now

        db.session.commit()
        return {'request_id': req.id, 'status': req.status}

    def cancel(self, request_type: str, request_id: int, user_id: int) -> dict:
        """取消申请（在草稿状态下）"""
        if request_type == 'onboarding':
            req = OnboardingRequest.query.get(request_id)
            sm = self.onboarding_sm
        else:
            req = OffboardingRequest.query.get(request_id)
            sm = self.offboarding_sm

        if not req:
            raise ApprovalEngineError(f'{request_type}申请不存在')

        req.status = sm.fire(req.status, 'cancel', {
            'user_id': user_id, 'request_id': request_id
        })
        db.session.commit()
        return {'request_id': req.id, 'status': req.status}

    # ----------------------------------------------------------------
    # 完成流程
    # ----------------------------------------------------------------

    def complete_onboarding(self, request_id: int, user_id: int) -> OnboardingRequest:
        """完成入职"""
        req = OnboardingRequest.query.get(request_id)
        if not req:
            raise ApprovalEngineError(f'入职申请不存在: id={request_id}')
        if req.status != OnboardingStatus.APPROVED.value:
            raise ApprovalEngineError(f'入职申请状态不是已通过: {req.status}')

        req.status = self.onboarding_sm.fire(req.status, 'complete', {
            'user_id': user_id, 'request_id': request_id
        })

        # 更新员工记录
        employee = Employee.query.filter_by(email=req.candidate_email).first()
        if employee:
            employee.status = 'ACTIVE'
            employee.hire_date = req.expected_hire_date
            employee.department_id = req.department_id
            employee.department_name = req.department_name
            employee.position = req.position

        db.session.commit()

        # 通知相关人员
        self.notification_service.notify_system(
            recipient_id=req.applicant_id,
            recipient_name=req.applicant_name,
            title='【入职完成】入职流程已完成',
            content=f'{req.candidate_name} 的入职流程已完成',
        )

        return req

    def complete_offboarding(self, request_id: int, user_id: int) -> OffboardingRequest:
        """完成离职"""
        req = OffboardingRequest.query.get(request_id)
        if not req:
            raise ApprovalEngineError(f'离职申请不存在: id={request_id}')
        if req.status != OffboardingStatus.APPROVED.value:
            raise ApprovalEngineError(f'离职申请状态不是已通过: {req.status}')

        from datetime import date
        req.status = self.offboarding_sm.fire(req.status, 'complete', {
            'user_id': user_id, 'request_id': request_id
        })
        req.actual_last_date = date.today()

        # 更新员工状态
        employee = Employee.query.get(req.employee_id)
        if employee:
            employee.status = 'TERMINATED'
            employee.termination_date = date.today()

        db.session.commit()

        # 通知
        self.notification_service.notify_system(
            recipient_id=req.employee_id,
            recipient_name=req.employee_name,
            title='【离职完成】离职流程已完成',
            content=f'{req.employee_name} 的离职流程已完成，最后工作日: {req.actual_last_date}',
        )

        return req

    # ----------------------------------------------------------------
    # 查询
    # ----------------------------------------------------------------

    def get_pending_approvals(self, user_id: int, page: int = 1, page_size: int = 20) -> dict:
        """获取用户的待审批列表"""
        nodes = ApprovalNode.query.filter(
            ApprovalNode.approver_id == user_id,
            ApprovalNode.status == NodeStatus.PENDING.value
        ).order_by(ApprovalNode.created_at.desc())

        total = nodes.count()
        items = nodes.offset((page - 1) * page_size).limit(page_size).all()

        results = []
        for node in items:
            item = node.to_dict()
            # 关联请求信息
            if node.onboarding_request_id:
                req = OnboardingRequest.query.get(node.onboarding_request_id)
                if req:
                    item['request'] = req.to_dict()
            elif node.offboarding_request_id:
                req = OffboardingRequest.query.get(node.offboarding_request_id)
                if req:
                    item['request'] = req.to_dict()
            results.append(item)

        return {
            'items': results,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': (total + page_size - 1) // page_size,
            }
        }

    def get_processed_approvals(self, user_id: int, page: int = 1, page_size: int = 20) -> dict:
        """获取用户的已办审批列表"""
        nodes = ApprovalNode.query.filter(
            ApprovalNode.approver_id == user_id,
            ApprovalNode.status.in_([NodeStatus.APPROVED.value, NodeStatus.REJECTED.value])
        ).order_by(ApprovalNode.operated_at.desc())

        total = nodes.count()
        items = nodes.offset((page - 1) * page_size).limit(page_size).all()

        results = []
        for node in items:
            item = node.to_dict()
            if node.onboarding_request_id:
                req = OnboardingRequest.query.get(node.onboarding_request_id)
                if req:
                    item['request'] = req.to_dict()
            elif node.offboarding_request_id:
                req = OffboardingRequest.query.get(node.offboarding_request_id)
                if req:
                    item['request'] = req.to_dict()
            results.append(item)

        return {
            'items': results,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': (total + page_size - 1) // page_size,
            }
        }

    def batch_approve(self, node_ids: List[int], user_id: int, action: str,
                      comment: str = None) -> List[dict]:
        """批量审批"""
        results = []
        for node_id in node_ids:
            try:
                if action == 'approve':
                    result = self.approve(node_id, user_id, comment)
                elif action == 'reject':
                    result = self.reject(node_id, user_id, comment)
                else:
                    result = {'node_id': node_id, 'error': f'不支持的操作: {action}'}
                result['node_id'] = node_id
                results.append(result)
            except ApprovalEngineError as e:
                results.append({'node_id': node_id, 'error': str(e)})
        return results

    # ----------------------------------------------------------------
    # 内部方法
    # ----------------------------------------------------------------

    def _create_onboarding_approval_nodes(self, req: OnboardingRequest, user_id: int):
        """创建入职审批节点链"""
        nodes_data = [
            {'name': '部门负责人审批', 'order': 1, 'type': 'department_head'},
            {'name': 'HR审批', 'order': 2, 'type': 'hr_manager'},
        ]

        for i, node_data in enumerate(nodes_data):
            approver_id, approver_name = self._resolve_approver(req, node_data['type'])
            node = ApprovalNode(
                onboarding_request_id=req.id,
                node_name=node_data['name'],
                node_order=node_data['order'],
                approver_id=approver_id,
                approver_name=approver_name,
                status=NodeStatus.PENDING.value,
            )
            db.session.add(node)

    def _create_offboarding_approval_nodes(self, req: OffboardingRequest, user_id: int):
        """创建离职审批节点链"""
        nodes_data = [
            {'name': '直属上级审批', 'order': 1, 'type': 'team_leader'},
            {'name': '部门负责人审批', 'order': 2, 'type': 'department_head'},
            {'name': 'HR审批', 'order': 3, 'type': 'hr_manager'},
        ]

        for i, node_data in enumerate(nodes_data):
            approver_id, approver_name = self._resolve_approver(req, node_data['type'])
            node = ApprovalNode(
                offboarding_request_id=req.id,
                node_name=node_data['name'],
                node_order=node_data['order'],
                approver_id=approver_id,
                approver_name=approver_name,
                status=NodeStatus.PENDING.value,
            )
            db.session.add(node)

    def _resolve_approver(self, req, approver_type: str):
        """
        解析审批人
        实际项目中此处应查询部门/上级/HR角色配置
        这里使用模拟数据
        """
        # 模拟: 根据类型返回不同的审批人
        mock_approvers = {
            'department_head': (2, '张经理'),
            'hr_manager': (3, '李HR'),
            'team_leader': (4, '王主管'),
        }
        return mock_approvers.get(approver_type, (1, '系统管理员'))

    def _get_req_title(self, req, req_type: str) -> str:
        """获取申请标题摘要"""
        if req_type == 'onboarding':
            return f'入职申请-{req.candidate_name}'
        return f'离职申请-{req.employee_name}'

    def _notify_approval_result(self, req, req_type: str, result: str, comment: str = None):
        """通知申请人审批结果"""
        if req_type == 'onboarding':
            title = '【审批通过】入职申请已通过' if result == 'approved' else '【审批驳回】入职申请被驳回'
            content = f'您的入职申请（{req.candidate_name}）已{("通过" if result == "approved" else "驳回")}'
            recipient_id = req.applicant_id
            recipient_name = req.applicant_name
        else:
            title = '【审批通过】离职申请已通过' if result == 'approved' else '【审批驳回】离职申请被驳回'
            content = f'您的离职申请（{req.employee_name}）已{("通过" if result == "approved" else "驳回")}'
            recipient_id = req.employee_id
            recipient_name = req.employee_name

        if comment:
            content += f'，审批意见: {comment}'

        self.notification_service.notify_system(
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            title=title,
            content=content,
            ref_type=req_type,
            ref_id=req.id,
        )
