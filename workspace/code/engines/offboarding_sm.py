"""
离职申请状态机 - 对应API文档第11.2节
"""

from .state_machine import StateMachine, StateTransition


class OffboardingStateMachine(StateMachine):
    """
    离职申请状态机
    
    状态流转：
    draft -> submit -> pending_dept_review -> approve(Dept) -> pending_hr_review
         -> approve(HR) -> pending_exit_interview -> complete -> pending_asset_return
         -> complete -> approved
    任意pending状态 -> reject -> draft (驳回回到草稿)
    任意pending* -> cancel -> cancelled
    """

    def __init__(self):
        states = [
            "draft",
            "pending_dept_review",
            "pending_hr_review",
            "pending_exit_interview",
            "pending_asset_return",
            "approved",
            "rejected",
            "cancelled",
        ]
        super().__init__(states=states, initial_state="draft")
        self._setup_transitions()

    def _setup_transitions(self):
        """配置所有状态转移规则"""

        # draft 状态
        self.add_transition(StateTransition("draft", "submit", "pending_dept_review"))
        self.add_transition(StateTransition("draft", "update", "draft"))
        self.add_transition(StateTransition("draft", "cancel", "cancelled"))

        # pending_dept_review 状态
        self.add_transition(StateTransition("pending_dept_review", "approve", "pending_hr_review"))
        self.add_transition(StateTransition("pending_dept_review", "reject", "draft"))
        self.add_transition(StateTransition("pending_dept_review", "cancel", "cancelled"))

        # pending_hr_review 状态
        self.add_transition(StateTransition("pending_hr_review", "approve", "pending_exit_interview"))
        self.add_transition(StateTransition("pending_hr_review", "reject", "draft"))
        self.add_transition(StateTransition("pending_hr_review", "cancel", "cancelled"))

        # pending_exit_interview 状态
        self.add_transition(StateTransition("pending_exit_interview", "approve", "pending_asset_return"))
        self.add_transition(StateTransition("pending_exit_interview", "cancel", "cancelled"))

        # pending_asset_return 状态
        self.add_transition(StateTransition("pending_asset_return", "approve", "approved"))
        self.add_transition(StateTransition("pending_asset_return", "cancel", "cancelled"))

        # 终态：approved, rejected, cancelled 无出向转移
