# -*- coding: utf-8 -*-
"""编排器(Orchestrator) - 多Agent流水线调度 + 产出链式传递"""
from __future__ import annotations
import json, os, sys
from datetime import datetime
from pathlib import Path

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
    "编排器 - 链式流水线调度 + 产出记录"

    def __init__(self, workspace_dir=None):
        self.workspace_dir = Path(workspace_dir) if workspace_dir else _PROJECT_ROOT / "workspace"
        self.docs_dir = self.workspace_dir / "docs"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.results = {}
        self.stage_outputs = {}
        self.manifest = {
            "pipeline_name": "员工入离职管理系统 - 多Agent协作流水线",
            "start_time": datetime.now().isoformat(),
            "stages": [],
            "agents": {},
        }
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

    def _get_upstream_context(self, current_stage_idx):
        parts = []
        for i in range(current_stage_idx):
            sname = PIPELINE_STAGES[i]["name"]
            if sname in self.stage_outputs:
                outputs = self.stage_outputs[sname]
                parts.append("【%s】产出文件:" % sname)
                for role_key, files in outputs.items():
                    for f in files:
                        parts.append("  - %s: %s" % (role_key, f))
        return "\n".join(parts) if parts else ""

    def _scan_output_files(self):
        if not self.docs_dir.exists():
            return []
        files = []
        for f in sorted(self.docs_dir.iterdir()):
            if f.is_file() and f.suffix in (".md", ".json", ".html", ".js", ".css", ".py"):
                if f.name.startswith(".") or f.name == "pipeline_manifest.json":
                    continue
                files.append(str(f.resolve()))
        return files

    def run_agent(self, role_key):
        if role_key not in self._agent_registry:
            raise KeyError("未知角色: %s" % role_key)
        build_fn, build_tasks_fn = self._agent_registry[role_key]
        agent = build_fn()
        tasks = build_tasks_fn(agent)
        print("\n%s" % ("="*60))
        print("  执行 Agent: %s" % role_key)
        result = run_agent([agent], tasks)
        output_files = self._scan_output_files()
        self.manifest["agents"][role_key] = {
            "output_files": output_files,
            "result_preview": result[:500] if result else "",
        }
        self.results[role_key] = result
        return result

    def run_stage(self, stage_name):
        stage_idx, stage = None, None
        for i, s in enumerate(PIPELINE_STAGES):
            if s["name"] == stage_name:
                stage_idx, stage = i, s
                break
        if not stage:
            raise ValueError("未知阶段: %s" % stage_name)
        upstream_ctx = self._get_upstream_context(stage_idx)
        if upstream_ctx:
            print("\n  [上游产出] 以下文件可作为本阶段输入:")
            print(upstream_ctx)
        print("\n%s" % ("="*60))
        print("  阶段: %s" % stage["name"])
        print("  主导角色: %s" % ", ".join(stage["lead_roles"]))
        print("  输入: %s" % stage["inputs"])
        print("  预期产出: %s" % stage["outputs"])
        print("%s" % ("="*60))
        stage_outputs = {}
        for role_key in stage["lead_roles"]:
            self.run_agent(role_key)
            stage_outputs[role_key] = self._scan_output_files()
        self.stage_outputs[stage_name] = stage_outputs
        self.manifest["stages"].append({
            "name": stage_name,
            "agents": stage["lead_roles"],
            "produced_files": [f for files in stage_outputs.values() for f in files],
        })
        self._save_manifest()
        print("\n  [完成] 阶段【%s】执行完成" % stage_name)
        print("  [产出] 文件保存到 workspace/docs/")
        return stage_outputs

    def run_pipeline(self, stages=None):
        if stages is None:
            stages = [s["name"] for s in PIPELINE_STAGES]
        self.manifest["stages_config"] = list(stages)
        print("\n" + "="*60)
        print("  员工入离职管理系统 - 多Agent协作流水线")
        print("  流水线: %s" % " -> ".join(stages))
        print("="*60)
        for i, stage_name in enumerate(stages, 1):
            print("\n" + "="*60)
            print("  [%d/%d] %s" % (i, len(stages), stage_name))
            print("="*60)
            self.run_stage(stage_name)
        self.manifest["end_time"] = datetime.now().isoformat()
        self.manifest["status"] = "completed"
        self._save_manifest()
        return self.get_summary()

    def _save_manifest(self):
        mpath = self.docs_dir / "pipeline_manifest.json"
        try:
            mpath.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print("  [WARN] 保存manifest失败: %s" % e)

    def get_summary(self):
        mpath = self.docs_dir / "pipeline_manifest.json"
        ms = str(mpath) if mpath.exists() else ""
        return {"completed_agents": list(self.results.keys()), "manifest": ms, "docs_dir": str(self.docs_dir)}

def run_pipeline(stages=None):
    return Orchestrator().run_pipeline(stages)

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
        print("完成！")