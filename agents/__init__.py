"""
Agent 模块 - 员工入离职管理系统 多Agent协作框架

遵循标准研发流程：需求分析 → 方案设计 → 系统分析 → 代码开发 → 测试分析 → 测试验收
包含 3 个 Agent 组（产品/开发/测试），共 9 个角色。

参考代码风格：https://github.com/kid0317/crewai_mas_demo/blob/main/m1l2/m1l2_agent.py
"""
from agents.base_agent import (
    create_agent,
    create_task,
    run_agent,
    AgentConfig,
)
from agents.orchestrator import Orchestrator, PIPELINE_STAGES
from agents.product import (
    requirement_analyst,
    business_designer,
    solution_designer,
)
from agents.development import (
    architect,
    backend_dev,
    frontend_dev,
)
from agents.testing import (
    test_analyst,
    test_executor,
    acceptance_tester,
)

__all__ = [
    "create_agent", "create_task", "run_agent", "AgentConfig",
    "Orchestrator", "PIPELINE_STAGES",
    "requirement_analyst", "business_designer", "solution_designer",
    "architect", "backend_dev", "frontend_dev",
    "test_analyst", "test_executor", "acceptance_tester",
]
