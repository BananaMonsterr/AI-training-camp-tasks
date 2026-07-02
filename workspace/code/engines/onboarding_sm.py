"""
入职申请状态机 - 对应API文档第11.1节
"""

from .state_machine import StateMachine, StateTransition


class OnboardingStateMachine(StateMachine):
    """
    入职申请状态机
    
    状态流转：
    draft -> submit -> pending_hr_review -> approve(HR) -> pending_dept_review 
         -> approve(Dept) -> pending_it_prepare -> complete(IT) -> approved
    任意pending状态 -> reject -> draft (驳回回到草稿)
    任意非终态 -> cancel -> cancelled
    """

    def __init__(self):
        states = [
            "draft",
            "pending_hr_review",
            "pending_dept_review",
            "pending_it_prepare",
            "approved",
            "rejected",
            "cancelled",
        ]
        super().__init__(states=states, initial_state="draft")
        self._setup_transitions()

    def _setup_transitions(self):
        """配置所有状态转移规则"""

        # draft 状态
        self.add_transition(StateTransition("draft", "submit", "pending_hr_review"))
        self.add_transition(StateTransition("draft", "update", "draft"))
        self.add_transition(StateTransition("draft", "cancel", "cancelled"))
        self.add_transition(StateTransition("draft", "delete", "draft"))  # 标记删除

        # pending_hr_review 状态
        self.add_transition(StateTransition("pending_hr_review", "approve", "pending_dept_review"))
        self.add_transition(StateTransition("pending_hr_review", "reject", "draft"))
        self.add_transition(StateTransition("pending_hr_review", "cancel", "cancelled"))

        # pending_dept_review 状态
        self.add_transition(StateTransition("pending_dept_review", "approve", "pending_it_prepare"))
        self.add_transition(StateTransition("pending_dept_review", "reject", "draft"))
        self.add_transition(StateTransition("pending_dept_review", "cancel", "cancelled"))

        # pending_it_prepare 状态
        self.add_transition(StateTransition("pending_it_prepare", "approve", "approved"))
        self.add_transition(StateTransition("pending_it_prepare", "cancel", "cancelled"))

        # 终态：approved, rejected, cancelled 无出向转移
