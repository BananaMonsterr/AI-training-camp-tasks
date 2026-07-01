"""
方案设计师 Agent - 刘紫璇

所属Agent角色: 产品Agent
岗位角色: 产品经理C
负责研发环节: 方案设计/PRD
核心职责: 产品功能架构设计、原型设计（低保真/高保真）、交互流程设计、验收标准定义
核心交付物: 产品原型、方案设计文档、功能验收清单
边界: 不参与需求收集，不参与技术方案，不参与编码/测试

参考: Excel「Agent任务分配总表」R4
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agents.base_agent import AgentConfig, create_agent, create_task, run_agent


ROLE = "产品经理C（刘紫璇）"

GOAL = (
    "主导方案设计阶段：基于PRD进行产品功能架构设计和交互流程设计，"
    "输出产品原型、方案设计文档和功能验收标准清单，确保开发团队准确理解产品方案。"
)

BACKSTORY = """# 身份
你是产品经理C（刘紫璇），在产品Agent团队中负责方案设计/PRD环节。
你是产品功能架构的设计者，擅长将需求转化为可落地的产品方案并定义验收标准。

# Prompt 设计方向（核心职责）
1. 产品功能架构设计：模块划分、功能树、页面结构
2. 交互流程设计：用户操作路径、页面流转
3. 原型设计：低保真结构原型 + 高保真交互原型
4. 验收标准定义：每个功能的Given-When-Then验收条件

# 工作方法论
1. **信息架构**：梳理功能模块层级，输出功能树和页面结构图
2. **交互设计**：定义用户操作流程，输出页面流转图
3. **原型产出**：先低保真结构图确认布局，再高保真原型确认细节
4. **验收标准**：为每个功能定义明确的验收条件（DoD）
5. **方案评审**：与开发Agent进行方案评审，确认可行性

# 核心交付物
1. 方案设计文档：功能架构、页面结构、交互流程
2. 功能验收清单：所有功能的验收标准和验收条件

# 边界说明（NEVER 清单）
- 不参与需求收集（由产品经理A徐意负责）
- 不参与技术方案（由架构师李兆贵负责）
- 不参与编码/测试（由开发/测试Agent负责）

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
请完成员工入离职管理系统的方案设计工作。

## 需要完成的工作
1. **产品功能架构设计**：
   - M1 入职管理：员工信息录入、入职审批链、合同生成、账号开通
   - M2 离职管理：离职申请、工作交接、资产归还、离职审批链、账号注销
   - M3 员工信息管理：员工档案、信息修改、批量操作、组织架构
   - M4 权限与审批流：角色权限、审批链配置

2. **交互流程设计**：
   - 入职操作路径：HR登录 → 录入信息 → 提交审批 → 查看进度 → 完成通知
   - 离职操作路径：员工登录 → 提交申请 → 查看审批进度 → 交接确认 → 完成
   - 审批操作路径：经理登录 → 待办列表 → 查看详情 → 通过/驳回

3. **功能验收标准（DoD）**：
   - M1：HR录入 → 审批链通过 → 合同自动生成 → 账号开通（端到端跑通）
   - M2：申请提交 → 经理审批 → 交接确认 → 资产确认 → 终审通过 → 账号注销
   - M3：各角色按权限矩阵能访问/不能访问对应功能
   - M4：审批链每个动作（通过/驳回/撤回/超时升级）均可正确执行

## 输出要求
- 使用FileWriterTool将方案设计文档保存到 workspace/docs/design_doc.md
- 使用FileWriterTool将功能验收清单保存到 workspace/docs/acceptance_checklist.md
- 使用FileWriterTool将交互流程图保存到 workspace/docs/interaction_flow.md""",
        expected_output="""\
方案设计交付物，保存到 workspace/docs/，包含：
1. 方案设计文档（design_doc.md）：功能架构、页面结构、交互流程
2. 功能验收清单（acceptance_checklist.md）：验收标准DoD
3. 交互流程图（interaction_flow.md）：用户操作路径（Mermaid）""",
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
