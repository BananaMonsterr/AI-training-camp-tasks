"""
状态机引擎核心 - 支持审批流的状态流转
对应API文档第11章状态机定义
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class StateTransition:
    """状态转移定义"""
    from_state: str
    action: str
    to_state: str
    condition: Optional[Callable[[dict], bool]] = None  # 条件函数
    before_hook: Optional[Callable[[dict], None]] = None  # 转移前钩子
    after_hook: Optional[Callable[[dict], None]] = None   # 转移后钩子


class StateMachine:
    """状态机基类"""

    def __init__(self, states: list[str], initial_state: str):
        self.states = states
        self.initial_state = initial_state
        self.transitions: dict[str, list[StateTransition]] = {}  # from_state -> [transitions]

    def add_transition(self, transition: StateTransition) -> None:
        """添加状态转移规则"""
        assert transition.from_state in self.states, f"源状态 {transition.from_state} 不在状态列表中"
        assert transition.to_state in self.states, f"目标状态 {transition.to_state} 不在状态列表中"

        if transition.from_state not in self.transitions:
            self.transitions[transition.from_state] = []
        self.transitions[transition.from_state].append(transition)

    def get_available_actions(self, current_state: str) -> list[str]:
        """获取当前状态下可用的操作列表"""
        transitions = self.transitions.get(current_state, [])
        return [t.action for t in transitions]

    def can_transition(self, current_state: str, action: str, context: dict = None) -> bool:
        """检查是否可以从当前状态通过指定操作转移"""
        transitions = self.transitions.get(current_state, [])
        for t in transitions:
            if t.action == action:
                if t.condition and context is not None:
                    return t.condition(context)
                return True
        return False

    def transition(self, current_state: str, action: str, context: dict = None) -> str:
        """
        执行状态转移
        返回转移后的状态
        """
        transitions = self.transitions.get(current_state, [])
        for t in transitions:
            if t.action == action:
                # 检查条件
                if t.condition and context is not None:
                    if not t.condition(context):
                        raise ValueError(f"条件不满足，无法执行操作 '{action}'")

                # 执行前钩子
                if t.before_hook and context is not None:
                    t.before_hook(context)

                # 执行后钩子
                if t.after_hook and context is not None:
                    t.after_hook(context)

                return t.to_state

        available = self.get_available_actions(current_state)
        raise ValueError(
            f"状态 '{current_state}' 不允许操作 '{action}'，"
            f"可用操作: {available}"
        )


class StateMachineEngine:
    """
    状态机引擎 - 管理多个状态机实例
    提供统一的状态查询和转移接口
    """

    def __init__(self):
        self._machines: dict[str, StateMachine] = {}

    def register_machine(self, name: str, machine: StateMachine) -> None:
        """注册状态机"""
        self._machines[name] = machine

    def get_machine(self, name: str) -> StateMachine:
        """获取状态机"""
        if name not in self._machines:
            raise ValueError(f"状态机 '{name}' 未注册")
        return self._machines[name]

    def validate_action(self, machine_name: str, current_state: str,
                        action: str, context: dict = None) -> bool:
        """校验操作是否合法"""
        machine = self.get_machine(machine_name)
        return machine.can_transition(current_state, action, context)

    def execute_action(self, machine_name: str, current_state: str,
                       action: str, context: dict = None) -> str:
        """
        执行状态转移
        :return: 新状态
        """
        machine = self.get_machine(machine_name)
        return machine.transition(current_state, action, context)

    def get_available_actions(self, machine_name: str, current_state: str) -> list[str]:
        """获取当前状态下所有可用操作"""
        machine = self.get_machine(machine_name)
        return machine.get_available_actions(current_state)
