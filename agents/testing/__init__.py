"""
测试Agent组 - 3个角色

1. 测试分析师(张桦彬): 测试分析 - 测试计划、用例设计、测试数据
2. 测试执行(韩均楠): 功能测试执行 - 自动化脚本、回归测试、缺陷跟踪
3. 验收测试(测试工程师C): 验收测试&报告 - 验收执行、全流程冒烟、测试报告
"""
from agents.testing import test_analyst
from agents.testing import test_executor
from agents.testing import acceptance_tester

__all__ = [
    "test_analyst",
    "test_executor",
    "acceptance_tester",
]
