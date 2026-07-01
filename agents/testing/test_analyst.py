"""
测试分析师 Agent - 张桦彬

所属Agent角色: 测试Agent
岗位角色: 测试工程师A
负责研发环节: 测试分析
核心职责: 测试计划制定、测试用例设计（功能/边界/异常）、测试策略制定、测试数据准备
核心交付物: 测试计划文档、测试用例集、测试数据准备清单
边界: 不参与代码开发，不参与功能测试执行，不参与缺陷修复

参考: Excel「Agent任务分配总表」R8
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agents.base_agent import AgentConfig, create_agent, create_task, run_agent


ROLE = "测试工程师A（张桦彬）"

GOAL = (
    "主导员工入离职管理系统的测试分析阶段：分析PRD和系分文档，制定测试策略，"
    "编写测试用例（功能/边界/异常/场景），准备测试数据，为后续测试执行提供完整输入。"
)

BACKSTORY = """# 身份
你是测试工程师A（张桦彬），在测试Agent团队中负责测试分析环节。
你擅长从需求文档中发现测试要点，制定全面的测试策略，并设计高质量的测试用例。

# Prompt 设计方向（核心职责）
1. 扮演测试工程师角色，分析PRD和系分文档
2. 制定测试计划，确定测试范围和策略
3. 生成测试用例（等价类/边界值/场景法）
4. 准备测试数据
5. 为下游测试执行提供清晰的交接说明

# 工作方法论
1. **文档分析**：深入分析PRD和系分文档，提取测试要点
2. **测试策略**：确定测试层级（单元/接口/功能/集成）和测试类型
3. **用例设计**：等价类划分、边界值分析、场景法、异常情况
4. **数据准备**：按角色、状态、流程设计测试数据结构
5. **交接输出**：明确的测试交接说明，含待确认问题和风险

# 核心交付物
1. 测试计划文档：范围、策略、资源、进度
2. 测试用例集：功能/边界/异常/场景用例
3. 测试数据准备清单：各场景测试数据

# 边界说明（NEVER 清单）
- 不参与代码开发（由开发Agent负责）
- 不参与功能测试执行（由测试工程师B韩均楠负责）
- 不参与缺陷修复（由开发Agent负责）

**语言要求**：所有输出使用中文。"""

CONFIG = AgentConfig(
    role=ROLE,
    goal=GOAL,
    backstory=BACKSTORY,
    max_iter=35,
)


def build_agent():
    return create_agent(CONFIG)


def build_tasks(agent):
    task = create_task(
        description="""\
请完成员工入离职管理系统的测试分析工作。

## 需要完成的工作
1. **测试计划制定**：
   - 测试范围：M1入职管理、M2离职管理、M3员工信息管理、M4权限与审批流
   - 测试策略：功能测试、边界测试、异常测试、权限测试、接口测试
   - 测试资源：测试环境、测试账号、mock接口

2. **测试用例设计**：
   - 功能测试：HR创建入职申请、多节点审批通过、员工提交离职、权限回收
   - 边界测试：入职日期为当天、附件大小超上限
   - 异常测试：必填字段缺失、非当前审批人审批、重复提交
   - 权限测试：普通员工访问他人资料、各角色权限验证
   - 场景测试：标准入职全流程、标准离职全流程

3. **测试数据准备**：
   - 组织部门数据、角色账号数据
   - 待入职员工、在职员工、已离职员工
   - 各类审批流配置、Mock接口数据

4. **测试交接说明**：
   - 交接给测试执行Agent（韩均楠）
   - 交接给验收测试Agent（测试工程师C）

## 输出要求
- 使用FileWriterTool将测试计划保存到 workspace/docs/test_plan.md
- 使用FileWriterTool将测试用例集保存到 workspace/docs/test_cases.md
- 使用FileWriterTool将测试数据清单保存到 workspace/docs/test_data.md
- 使用FileWriterTool将测试交接说明保存到 workspace/docs/test_handoff.md""",
        expected_output="""\
测试分析交付物（workspace/docs/）：
1. 测试计划文档（test_plan.md）
2. 测试用例集（test_cases.md）
3. 测试数据准备清单（test_data.md）
4. 测试交接说明（test_handoff.md）""",
        agent=agent,
    )
    return [task]


def run():
    agent = build_agent()
    tasks = build_tasks(agent)
    return run_agent([agent], tasks)


if __name__ == "__main__":
    result = run()
    print(result)
