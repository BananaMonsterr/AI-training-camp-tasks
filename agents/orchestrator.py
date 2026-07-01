# -*- coding: utf-8 -*-
"""编排器（Orchestrator）- 多Agent流水线调度"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agents.base_agent import run_agent
from agents.product import requirement_analyst, business_designer, solution_designer
from agents.development import architect, backend_dev, frontend_dev
from agents.testing import test_analyst, test_executor, acceptance_tester

PIPELINE_STAGES = [
    {"name": "需求分析", "lead_roles": ["requirement_analyst", "business_designer"],
     "description": "用户调研、竞品分析、需求收集、业务流程设计",
     "inputs": "业务需求文档、现有流程说明",
     "outputs": "PRD文档、业务流程图、用户故事地图"},
    {"name": "方案设计", "lead_roles": ["solution_designer"],
     "description": "产品功能架构设计、交互流程设计、验收标准定义",
     "inputs": "PRD文档、业务流程图",
     "outputs": "方案设计文档、功能验收标准清单"},
    {"name": "系统分析", "lead_roles": ["architect", "backend_dev"],
     "description": "系统架构设计、技术选型、ER图设计、API接口设计",
     "inputs": "方案设计文档、产品原型",
     "outputs": "系统架构图、技术方案文档、ER图、API文档"},
    {"name": "代码开发", "lead_roles": ["backend_dev", "frontend_dev"],
     "description": "后端数据模型/业务逻辑/API开发 + 前端页面/交互/联调",
     "inputs": "技术方案文档、API接口文档、原型设计",
     "outputs": "后端代码、前端代码、单元测试、部署脚本"},
    {"name": "测试分析", "lead_roles": ["test_analyst"],
     "description": "制定测试策略、编写测试用例、准备测试数据",
     "inputs": "PRD文档、系分文档、API文档",
     "outputs": "测试计划文档、测试用例集、测试数据"},
    {"name": "测试验收", "lead_roles": ["test_executor", "acceptance_tester"],
     "description": "功能测试执行、自动化回归、验收测试、缺陷跟踪、测试报告",
     "inputs": "测试用例、测试数据、验收标准清单",
     "outputs": "缺陷清单、功能测试报告、验收测试报告、验收结论"},
]

class Orchestrator:
    def __init__(self, workspace_dir=None):
        self.workspace_dir = Path(workspace_dir) if workspace_dir else _PROJECT_ROOT / "workspace"
        self.results = {}
        self._agent_registry = {
            "requirement_analyst": (requirement_analyst.build_agent, requirement_analyst.build_tasks),
            "business_designer": (business_designer.build_agent, business_designer.build_tasks),
            "solution_designer": (solution_designer.build_agent, solution_designer.build_tasks),
            "architect": (architect.build_agent, architect.build_tasks),
            "backend_dev": (backend_dev.build_agent, backend_dev.build_tasks),
            "frontend_dev": (frontend_dev.build_agent, frontend_dev.build_tasks),
            "test_analyst": (test_analyst.build_agent, test_analyst.build_tasks),
            "test_executor": (test_executor.build_agent, test_executor.build_tasks),
            "acceptance_tester": (acceptance_tester.build_agent, acceptance_tester.build_tasks),
        }

    def run_agent(self, role_key):
        if role_key not in self._agent_registry:
            raise KeyError("未知角色: {0}".format(role_key))
        build_fn, build_tasks_fn = self._agent_registry[role_key]
        agent = build_fn()
        tasks = build_tasks_fn(agent)
        print("\n{0}".format("="*60))
        print("  执行 Agent: {0}".format(role_key))
        print("{0}".format("="*60))
        result = run_agent([agent], tasks)
        self.results[role_key] = result
        return result

    def run_stage(self, stage_name):
        stage = next((s for s in PIPELINE_STAGES if s["name"] == stage_name), None)
        if not stage:
            raise ValueError("未知阶段: {0}".format(stage_name))
        print("\n{0}".format("="*60))
        print("  阶段: {0}".format(stage["name"]))
        print("  主导角色: {0}".format(", ".join(stage["lead_roles"])))
        print("{0}".format("="*60))
        stage_results = {}
        for role_key in stage["lead_roles"]:
            result = self.run_agent(role_key)
            stage_results[role_key] = result
        print("\n  [完成] 阶段 [{0}] 执行完成".format(stage_name))
        self.results["stage:{0}".format(stage_name)] = str(stage_results)
        return stage_results

    def run_pipeline(self, stages=None):
        if stages is None:
            stages = [s["name"] for s in PIPELINE_STAGES]
        print("\n{0}".format("="*60))
        print("  员工入离职管理系统 - 多Agent协作流水线")
        print("  流水线: {0}".format(" -> ".join(stages)))
        print("{0}".format("="*60))
        for i, stage_name in enumerate(stages, 1):
            print("\n{0}".format("="*60))
            print("  [{0}/{1}] {2}".format(i, len(stages), stage_name))
            print("{0}".format("="*60))
            self.run_stage(stage_name)
        return self.get_summary()

    def get_summary(self):
        return {"completed_agents": list(self.results.keys()), "results": self.results}

def run_pipeline(stages=None):
    orch = Orchestrator()
    return orch.run_pipeline(stages)

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if not args:
        print("用法: python agents/orchestrator.py [agent_key|stage_name|--all]")
        sys.exit(1)
    orch = Orchestrator()
    if args[0] == "--all":
        orch.run_pipeline()
    elif any(args[0] == s["name"] for s in PIPELINE_STAGES):
        orch.run_stage(args[0])
    else:
        orch.run_agent(args[0])
        print("\n结果: {0}".format(list(orch.results.keys())))
    print("完成！")
