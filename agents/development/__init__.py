"""
开发Agent组 - 3个角色

1. 架构师(李兆贵): 系统分析(主责)+技术管理 - 架构设计、技术选型、ER图
2. 后端开发(龚茂林): 系统分析(辅助)+后端全栈开发 - API设计、数据模型、审批流
3. 前端开发(张铃): 代码开发-前端页面&联调 - 页面开发、表单交互、联调
"""
from agents.development import architect
from agents.development import backend_dev
from agents.development import frontend_dev

__all__ = [
    "architect",
    "backend_dev",
    "frontend_dev",
]
