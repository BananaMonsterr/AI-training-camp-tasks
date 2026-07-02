"""
状态机引擎单元测试
"""

import pytest

from engines.state_machine import StateMachine, StateTransition, StateMachineEngine
from engines.onboarding_sm import OnboardingStateMachine
from engines.offboarding_sm import OffboardingStateMachine


class TestStateMachineCore:
    """状态机核心功能测试"""

    def test_create_state_machine(self):
        sm = StateMachine(states=["draft", "active", "done"], initial_state="draft")
        assert sm.initial_state == "draft"
        assert len(sm.states) == 3

    def test_add_transition(self):
        sm = StateMachine(states=["draft", "active"], initial_state="draft")
        sm.add_transition(StateTransition("draft", "start", "active"))
        assert "draft" in sm.transitions
        assert len(sm.transitions["draft"]) == 1

    def test_get_available_actions(self):
        sm = StateMachine(states=["draft", "active", "done"], initial_state="draft")
        sm.add_transition(StateTransition("draft", "start", "active"))
        sm.add_transition(StateTransition("draft", "cancel", "done"))
        actions = sm.get_available_actions("draft")
        assert "start" in actions
        assert "cancel" in actions
        assert len(actions) == 2

    def test_get_available_actions_empty(self):
        sm = StateMachine(states=["draft"], initial_state="draft")
        actions = sm.get_available_actions("draft")
        assert actions == []

    def test_can_transition_true(self):
        sm = StateMachine(states=["draft", "active"], initial_state="draft")
        sm.add_transition(StateTransition("draft", "start", "active"))
        assert sm.can_transition("draft", "start") is True

    def test_can_transition_false(self):
        sm = StateMachine(states=["draft", "active"], initial_state="draft")
        sm.add_transition(StateTransition("draft", "start", "active"))
        assert sm.can_transition("draft", "stop") is False

    def test_transition_success(self):
        sm = StateMachine(states=["draft", "active"], initial_state="draft")
        sm.add_transition(StateTransition("draft", "start", "active"))
        new_state = sm.transition("draft", "start")
        assert new_state == "active"

    def test_transition_failure(self):
        sm = StateMachine(states=["draft", "active"], initial_state="draft")
        sm.add_transition(StateTransition("draft", "start", "active"))
        with pytest.raises(ValueError, match="不允许操作"):  # noqa
            sm.transition("draft", "stop")

    def test_transition_with_condition_passed(self):
        """带条件的转移"""
        def check_age(ctx):
            return ctx.get("age", 0) >= 18

        sm = StateMachine(states=["child", "adult"], initial_state="child")
        sm.add_transition(StateTransition("child", "grow", "adult", condition=check_age))

        assert sm.can_transition("child", "grow", {"age": 18}) is True
        assert sm.can_transition("child", "grow", {"age": 15}) is False

        with pytest.raises(ValueError):
            sm.transition("child", "grow", {"age": 15})

        new_state = sm.transition("child", "grow", {"age": 20})
        assert new_state == "adult"

    def test_transition_with_hooks(self):
        """测试钩子函数"""
        calls = []

        def before(ctx):
            calls.append("before")

        def after(ctx):
            calls.append("after")

        sm = StateMachine(states=["draft", "active"], initial_state="draft")
        sm.add_transition(StateTransition("draft", "start", "active",
                                           before_hook=before, after_hook=after))
        sm.transition("draft", "start")
        assert calls == ["before", "after"]


class TestOnboardingStateMachine:
    """入职状态机测试"""

    def test_initial_state(self):
        sm = OnboardingStateMachine()
        assert sm.initial_state == "draft"

    def test_happy_path(self):
        """正常流程测试"""
        sm = OnboardingStateMachine()
        state = sm.transition("draft", "submit")
        assert state == "pending_hr_review"

        state = sm.transition(state, "approve")
        assert state == "pending_dept_review"

        state = sm.transition(state, "approve")
        assert state == "pending_it_prepare"

        state = sm.transition(state, "approve")
        assert state == "approved"

    def test_reject_path(self):
        """驳回流程测试"""
        sm = OnboardingStateMachine()
        state = sm.transition("draft", "submit")
        assert state == "pending_hr_review"

        state = sm.transition(state, "reject")
        assert state == "draft"  # 驳回回到草稿

    def test_cancel_from_pending(self):
        """从待审状态取消"""
        sm = OnboardingStateMachine()
        state = sm.transition("draft", "submit")
        state = sm.transition(state, "cancel")
        assert state == "cancelled"

    def test_cancel_from_draft(self):
        sm = OnboardingStateMachine()
        state = sm.transition("draft", "cancel")
        assert state == "cancelled"

    def test_invalid_transition(self):
        """非法状态转移"""
        sm = OnboardingStateMachine()
        with pytest.raises(ValueError):
            sm.transition("draft", "approve")  # 草稿不能审批

    def test_terminal_state_no_outgoing(self):
        """终态不能转移"""
        sm = OnboardingStateMachine()
        with pytest.raises(ValueError):
            sm.transition("approved", "submit")

    def test_update_draft_remains_draft(self):
        sm = OnboardingStateMachine()
        state = sm.transition("draft", "update")
        assert state == "draft"

    def test_all_available_actions_draft(self):
        sm = OnboardingStateMachine()
        actions = sm.get_available_actions("draft")
        assert set(actions) == {"submit", "update", "cancel", "delete"}

    def test_all_available_actions_pending(self):
        sm = OnboardingStateMachine()
        actions = sm.get_available_actions("pending_hr_review")
        assert set(actions) == {"approve", "reject", "cancel"}

    def test_all_states(self):
        """验证所有已定义状态的完整性"""
        sm = OnboardingStateMachine()
        expected_states = {
            "draft", "pending_hr_review", "pending_dept_review",
            "pending_it_prepare", "approved", "rejected", "cancelled",
        }
        assert set(sm.states) == expected_states


class TestOffboardingStateMachine:
    """离职状态机测试"""

    def test_initial_state(self):
        sm = OffboardingStateMachine()
        assert sm.initial_state == "draft"

    def test_happy_path(self):
        """正常流程"""
        sm = OffboardingStateMachine()
        state = sm.transition("draft", "submit")
        assert state == "pending_dept_review"

        state = sm.transition(state, "approve")
        assert state == "pending_hr_review"

        state = sm.transition(state, "approve")
        assert state == "pending_exit_interview"

        state = sm.transition(state, "approve")
        assert state == "pending_asset_return"

        state = sm.transition(state, "approve")
        assert state == "approved"

    def test_reject_from_dept(self):
        """部门驳回"""
        sm = OffboardingStateMachine()
        state = sm.transition("draft", "submit")
        state = sm.transition(state, "reject")
        assert state == "draft"

    def test_reject_from_hr(self):
        """HR驳回"""
        sm = OffboardingStateMachine()
        state = sm.transition("draft", "submit")
        state = sm.transition(state, "approve")  # 部门通过
        state = sm.transition(state, "reject")   # HR驳回
        assert state == "draft"

    def test_cancel_from_any_pending(self):
        """从任意待审状态取消"""
        sm = OffboardingStateMachine()
        # 测试从pending_dept_review取消
        state = sm.transition("draft", "submit")
        state = sm.transition(state, "cancel")
        assert state == "cancelled"

    def test_invalid_transition(self):
        sm = OffboardingStateMachine()
        with pytest.raises(ValueError):
            sm.transition("draft", "approve")

    def test_all_states(self):
        sm = OffboardingStateMachine()
        expected_states = {
            "draft", "pending_dept_review", "pending_hr_review",
            "pending_exit_interview", "pending_asset_return",
            "approved", "rejected", "cancelled",
        }
        assert set(sm.states) == expected_states


class TestStateMachineEngine:
    """状态机引擎测试"""

    def test_register_machine(self):
        engine = StateMachineEngine()
        engine.register_machine("onboarding", OnboardingStateMachine())
        engine.register_machine("offboarding", OffboardingStateMachine())
        assert engine.get_machine("onboarding") is not None
        assert engine.get_machine("offboarding") is not None

    def test_get_machine_not_found(self):
        engine = StateMachineEngine()
        with pytest.raises(ValueError, match="未注册"):  # noqa
            engine.get_machine("nonexistent")

    def test_validate_action(self, state_machine_engine):
        assert state_machine_engine.validate_action("onboarding", "draft", "submit") is True
        assert state_machine_engine.validate_action("onboarding", "draft", "approve") is False

    def test_execute_action(self, state_machine_engine):
        new_state = state_machine_engine.execute_action("onboarding", "draft", "submit")
        assert new_state == "pending_hr_review"

    def test_get_available_actions(self, state_machine_engine):
        actions = state_machine_engine.get_available_actions("onboarding", "draft")
        assert "submit" in actions
        assert "cancel" in actions


class TestEdgeCases:
    """边界情况测试"""

    def test_state_machine_with_unknown_state(self):
        sm = StateMachine(states=["a", "b"], initial_state="a")
        with pytest.raises(AssertionError):
            sm.add_transition(StateTransition("a", "go", "c"))  # c不在状态列表中

    def test_engine_double_register(self):
        engine = StateMachineEngine()
        sm = OnboardingStateMachine()
        engine.register_machine("test", sm)
        engine.register_machine("test", sm)  # 覆盖注册，不报错
        assert engine.get_machine("test") is sm

    def test_terminal_state_actions(self):
        """终态没有操作"""
        sm = OnboardingStateMachine()
        approved_actions = sm.get_available_actions("approved")
        assert approved_actions == []

        rejected_actions = sm.get_available_actions("rejected")
        assert rejected_actions == []

        cancelled_actions = sm.get_available_actions("cancelled")
        assert cancelled_actions == []
