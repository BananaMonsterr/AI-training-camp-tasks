"""审批流引擎单元测试"""
import pytest
from datetime import date, datetime
from ..models import db
from ..models.employee import Employee, Department
from ..models.onboarding import OnboardingRequest, OnboardingStatus
from ..models.offboarding import OffboardingRequest, OffboardingStatus
from ..models.approval import ApprovalNode, NodeStatus
from ..models.notification import Notification
from ..engines.state_machine import (
    StateMachine, StateMachineError,
    create_onboarding_state_machine, create_offboarding_state_machine
)
from ..engines.approval_engine import ApprovalEngine, ApprovalEngineError


class TestStateMachine:
    """状态机引擎测试"""

    def setup_method(self):
        self.sm = StateMachine('test')
        self.sm.add_transition('DRAFT', 'PENDING_APPROVAL', 'submit')
        self.sm.add_transition('PENDING_APPROVAL', 'APPROVED', 'approve')
        self.sm.add_transition('PENDING_APPROVAL', 'REJECTED', 'reject')
        self.sm.add_transition('DRAFT', 'CANCELLED', 'cancel')

    def test_valid_transition(self):
        result = self.sm.fire('DRAFT', 'submit')
        assert result == 'PENDING_APPROVAL'

    def test_full_approval_flow(self):
        """测试完整审批流转：提交->通过"""
        state = self.sm.fire('DRAFT', 'submit')
        assert state == 'PENDING_APPROVAL'

        state = self.sm.fire(state, 'approve')
        assert state == 'APPROVED'

    def test_reject_flow(self):
        """测试驳回流程：提交->驳回"""
        state = self.sm.fire('DRAFT', 'submit')
        state = self.sm.fire(state, 'reject')
        assert state == 'REJECTED'

    def test_invalid_transition(self):
        """测试非法状态转换"""
        with pytest.raises(StateMachineError) as exc:
            self.sm.fire('DRAFT', 'approve')  # 草稿不能直接通过
        assert '不允许状态转换' in str(exc.value)

    def test_invalid_action(self):
        """测试不存在的动作"""
        with pytest.raises(StateMachineError):
            self.sm.fire('DRAFT', 'unknown_action')

    def test_can_fire(self):
        """测试can_fire方法"""
        assert self.sm.can_fire('DRAFT', 'submit') is True
        assert self.sm.can_fire('DRAFT', 'approve') is False
        assert self.sm.can_fire('DRAFT', 'unknown') is False

    def test_get_valid_actions(self):
        """测试获取合法动作"""
        actions = self.sm.get_valid_actions('DRAFT')
        action_names = [a['action'] for a in actions]
        assert 'submit' in action_names
        assert 'cancel' in action_names
        assert 'approve' not in action_names

    def test_get_valid_actions_pending(self):
        """待审批状态下的合法动作"""
        actions = self.sm.get_valid_actions('PENDING_APPROVAL')
        action_names = [a['action'] for a in actions]
        assert 'approve' in action_names
        assert 'reject' in action_names

    def test_conditional_transition(self):
        """测试带条件的转换"""
        sm = StateMachine('conditional')
        sm.add_transition('DRAFT', 'APPROVED', 'fast_approve',
                          condition=lambda ctx: ctx.get('is_admin', False))

        # 条件不满足
        with pytest.raises(StateMachineError):
            sm.fire('DRAFT', 'fast_approve', {'is_admin': False})

        # 条件满足
        result = sm.fire('DRAFT', 'fast_approve', {'is_admin': True})
        assert result == 'APPROVED'

    def test_before_after_hooks(self):
        """测试前置/后置钩子"""
        calls = []
        sm = StateMachine('hooks')

        def before(ctx):
            calls.append('before')

        def after(ctx):
            calls.append('after')

        sm.add_transition('A', 'B', 'go', before=before, after=after)
        sm.fire('A', 'go')
        assert calls == ['before', 'after']

    def test_onboarding_state_machine(self):
        """测试入职状态机所有合法转换"""
        sm = create_onboarding_state_machine()

        # 主流程
        assert sm.fire('DRAFT', 'submit') == 'PENDING_APPROVAL'
        assert sm.fire('PENDING_APPROVAL', 'approve') == 'APPROVED'
        assert sm.fire('APPROVED', 'complete') == 'ONBOARDING_DONE'

        # 驳回
        assert sm.fire('DRAFT', 'submit') == 'PENDING_APPROVAL'
        assert sm.fire('PENDING_APPROVAL', 'reject') == 'REJECTED'

        # 取消/撤回
        assert sm.fire('DRAFT', 'cancel') == 'CANCELLED'

    def test_offboarding_state_machine(self):
        """测试离职状态机所有合法转换"""
        sm = create_offboarding_state_machine()

        # 主流程
        assert sm.fire('DRAFT', 'submit') == 'PENDING_APPROVAL'
        assert sm.fire('PENDING_APPROVAL', 'approve') == 'APPROVED'
        assert sm.fire('APPROVED', 'complete') == 'OFFBOARDING_COMPLETED'

        # 驳回
        assert sm.fire('DRAFT', 'submit') == 'PENDING_APPROVAL'
        assert sm.fire('PENDING_APPROVAL', 'reject') == 'REJECTED'

        # 撤回
        assert sm.fire('PENDING_APPROVAL', 'withdraw') == 'WITHDRAWN'


class TestApprovalEngine:
    """审批流引擎集成测试"""

    @pytest.fixture(autouse=True)
    def setup_data(self, app):
        """准备测试数据"""
        with app.app_context():
            # 创建部门
            dept = Department(name='测试部', code='DEPT_TEST')
            db.session.add(dept)
            db.session.flush()
            self.dept_id = dept.id

            # 创建申请人
            applicant = Employee(
                employee_no='EMP_APP',
                name='申请人',
                email='applicant@test.com',
                department_id=dept.id,
            )
            db.session.add(applicant)
            db.session.flush()
            self.applicant_id = applicant.id

            # 创建审批人（模拟）
            approver = Employee(
                employee_no='EMP_APV',
                name='审批人',
                email='approver@test.com',
                department_id=dept.id,
            )
            db.session.add(approver)
            db.session.flush()
            self.approver_id = approver.id

            # 创建入职申请
            req = OnboardingRequest(
                applicant_id=self.applicant_id,
                applicant_name='申请人',
                department_id=self.dept_id,
                department_name='测试部',
                position='测试工程师',
                candidate_name='候选人',
                candidate_email='candidate@test.com',
                expected_hire_date=date(2024, 7, 1),
                status=OnboardingStatus.DRAFT.value,
            )
            db.session.add(req)
            db.session.commit()
            self.onboarding_req_id = req.id

            # 创建离职申请
            off_req = OffboardingRequest(
                employee_id=self.applicant_id,
                employee_name='申请人',
                employee_no='EMP_APP',
                department_id=self.dept_id,
                department_name='测试部',
                offboarding_type='RESIGNATION',
                reason='测试离职',
                expected_last_date=date(2024, 6, 30),
                status=OffboardingStatus.DRAFT.value,
            )
            db.session.add(off_req)
            db.session.commit()
            self.offboarding_req_id = off_req.id

    def test_submit_onboarding(self, app):
        """测试提交入职审批"""
        with app.app_context():
            engine = ApprovalEngine()
            req = engine.submit_onboarding(self.onboarding_req_id, self.applicant_id)

            assert req.status == 'PENDING_APPROVAL'
            assert req.current_approver_id is not None

            # 验证审批节点已创建
            nodes = ApprovalNode.query.filter_by(
                onboarding_request_id=self.onboarding_req_id
            ).all()
            assert len(nodes) == 2  # 部门审批 + HR审批
            assert nodes[0].status == 'PENDING'
            assert nodes[1].status == 'PENDING'

    def test_approve_full_flow(self, app):
        """测试完整的审批通过流程"""
        with app.app_context():
            engine = ApprovalEngine()

            # 1. 提交
            req = engine.submit_onboarding(self.onboarding_req_id, self.applicant_id)
            assert req.status == 'PENDING_APPROVAL'

            # 2. 获取第一个节点并审批通过
            nodes = ApprovalNode.query.filter_by(
                onboarding_request_id=self.onboarding_req_id,
                status='PENDING'
            ).order_by(ApprovalNode.node_order).all()
            assert len(nodes) > 0

            # 第一个节点通过
            result = engine.approve(nodes[0].id, nodes[0].approver_id, '同意')
            assert result['action'] == 'approve'

            # 第二个节点通过
            if len(nodes) > 1:
                result = engine.approve(nodes[1].id, nodes[1].approver_id, '同意')

            # 3. 验证申请状态
            req = OnboardingRequest.query.get(self.onboarding_req_id)
            assert req.status == 'APPROVED'
            assert req.final_approver_id is not None

    def test_reject_flow(self, app):
        """测试审批驳回流程"""
        with app.app_context():
            engine = ApprovalEngine()

            # 1. 提交
            req = engine.submit_onboarding(self.onboarding_req_id, self.applicant_id)

            # 2. 获取第一个节点并驳回
            node = ApprovalNode.query.filter_by(
                onboarding_request_id=self.onboarding_req_id,
                status='PENDING'
            ).first()

            result = engine.reject(node.id, node.approver_id, '不符合要求')
            assert result['action'] == 'reject'

            # 3. 验证状态
            req = OnboardingRequest.query.get(self.onboarding_req_id)
            assert req.status == 'REJECTED'
            assert req.reject_reason == '不符合要求'

    def test_withdraw_onboarding(self, app):
        """测试撤回申请"""
        with app.app_context():
            engine = ApprovalEngine()

            # 1. 提交
            engine.submit_onboarding(self.onboarding_req_id, self.applicant_id)

            # 2. 撤回
            result = engine.withdraw('onboarding', self.onboarding_req_id, self.applicant_id)
            assert result['status'] == 'WITHDRAWN'

    def test_cancel_draft(self, app):
        """测试取消草稿"""
        with app.app_context():
            engine = ApprovalEngine()

            result = engine.cancel('onboarding', self.onboarding_req_id, self.applicant_id)
            assert result['status'] == 'CANCELLED'

    def test_complete_onboarding(self, app):
        """测试完成入职"""
        with app.app_context():
            engine = ApprovalEngine()

            # 先提交并审批通过
            engine.submit_onboarding(self.onboarding_req_id, self.applicant_id)
            nodes = ApprovalNode.query.filter_by(
                onboarding_request_id=self.onboarding_req_id
            ).order_by(ApprovalNode.node_order).all()
            for node in nodes:
                engine.approve(node.id, node.approver_id, '同意')

            # 完成入职
            req = engine.complete_onboarding(self.onboarding_req_id, self.applicant_id)
            assert req.status == 'ONBOARDING_DONE'

    def test_submit_offboarding(self, app):
        """测试提交离职审批"""
        with app.app_context():
            engine = ApprovalEngine()
            req = engine.submit_offboarding(self.offboarding_req_id, self.applicant_id)

            assert req.status == 'PENDING_APPROVAL'

            nodes = ApprovalNode.query.filter_by(
                offboarding_request_id=self.offboarding_req_id
            ).all()
            assert len(nodes) == 3  # 直属上级 + 部门负责人 + HR

    def test_approve_nonexistent_node(self, app):
        """测试审批不存在的节点"""
        with app.app_context():
            engine = ApprovalEngine()
            with pytest.raises(ApprovalEngineError) as exc:
                engine.approve(99999, 1, 'test')
            assert '不存在' in str(exc.value)

    def test_approve_wrong_approver(self, app):
        """测试非审批人操作"""
        with app.app_context():
            engine = ApprovalEngine()
            engine.submit_onboarding(self.onboarding_req_id, self.applicant_id)

            node = ApprovalNode.query.filter_by(
                onboarding_request_id=self.onboarding_req_id
            ).first()

            with pytest.raises(ApprovalEngineError) as exc:
                engine.approve(node.id, 99999, 'test')
            assert '不是此节点的审批人' in str(exc.value)

    def test_double_approve(self, app):
        """测试重复审批"""
        with app.app_context():
            engine = ApprovalEngine()
            engine.submit_onboarding(self.onboarding_req_id, self.applicant_id)

            node = ApprovalNode.query.filter_by(
                onboarding_request_id=self.onboarding_req_id
            ).first()

            engine.approve(node.id, node.approver_id, '同意')

            with pytest.raises(ApprovalEngineError) as exc:
                engine.approve(node.id, node.approver_id, '再次同意')
            assert '不是待审批' in str(exc.value)

    def test_get_pending_approvals(self, app):
        """测试获取待审批列表"""
        with app.app_context():
            engine = ApprovalEngine()
            engine.submit_onboarding(self.onboarding_req_id, self.applicant_id)

            node = ApprovalNode.query.filter_by(
                onboarding_request_id=self.onboarding_req_id
            ).first()

            result = engine.get_pending_approvals(node.approver_id)
            assert result['pagination']['total'] >= 1
            assert len(result['items']) >= 1

    def test_batch_approve(self, app):
        """测试批量审批"""
        with app.app_context():
            engine = ApprovalEngine()
            engine.submit_onboarding(self.onboarding_req_id, self.applicant_id)

            nodes = ApprovalNode.query.filter_by(
                onboarding_request_id=self.onboarding_req_id
            ).all()
            node_ids = [n.id for n in nodes]

            results = engine.batch_approve(node_ids, nodes[0].approver_id, 'approve', '批量同意')
            assert len(results) == len(node_ids)
