"""
产品Agent组 - 3个角色

1. 需求分析师(徐意): 需求分析(主责) - 用户调研、竞品分析、需求收集
2. 业务设计师(张梦晴): 需求分析(辅助)+业务流程设计+原型设计
3. 方案设计师(刘紫璇): PRD/方案设计 - 功能架构、交互流程、验收标准
"""
from agents.product import requirement_analyst
from agents.product import business_designer
from agents.product import solution_designer

__all__ = [
    "requirement_analyst",
    "business_designer",
    "solution_designer",
]
