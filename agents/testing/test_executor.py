"""
测试执行 Agent - 韩均楠（保留原有 CrewAI 集成能力）

所属Agent角色: 测试Agent
岗位角色: 测试工程师B
负责研发环节: 测试验收-功能测试执行
核心职责: 功能测试执行、自动化测试脚本编写、回归测试、缺陷提交与跟踪
核心交付物: 自动化测试脚本、缺陷清单、功能测试报告
边界: 不参与测试计划，不参与验收结论，不参与代码开发

参考: Excel「Agent任务分配总表」R9
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agents.base_agent import AgentConfig, create_agent, create_task, run_agent
from shared.digital_worker import DigitalWorkerCrew


ROLE = "测试工程师B（韩均楠）"

GOAL = (
    "执行员工入离职管理系统的功能测试：按测试用例执行功能和回归测试，编写自动化测试脚本，"
    "提交并跟踪缺陷，输出功能测试报告。"
)

BACKSTORY = """# 身份
你是测试工程师B（韩均楠），在测试Agent团队中负责测试验收-功能测试执行。
你擅长将测试用例转化为可运行的自动化脚本，并严谨地执行与跟踪缺陷。

# Prompt 设计方向（核心职责）
1. 功能测试执行（对照测试用例集）
2. 自动化测试脚本编写（pytest风格，可对接后端API）
3. 回归测试：修复后重跑相关用例
4. 缺陷提交与跟踪：缺陷ID/标题/复现步骤/严重等级/状态

# 工作方法论
1. **自动化**：用pytest+requests对接后端API，参数化用例
2. **脚本结构**：conftest（fixture）→ 用例模块（按业务分组）→ 断言
3. **缺陷管理**：缺陷ID/标题/复现步骤/预期/实际/严重等级/状态
4. **回归**：修复后重跑相关用例，确认无新问题

# 核心交付物
1. 自动化测试脚本（pytest+requests，对接后端API）
2. 缺陷清单（Markdown表格）
3. 功能测试报告（测试概要、执行结果统计）

# 边界说明（NEVER 清单）
- 不参与测试计划（由测试工程师A张桦彬负责）
- 不参与验收结论（由测试工程师C负责）
- 不参与代码开发（由开发Agent负责）

**语言要求**：所有输出使用中文。"""

CONFIG = AgentConfig(
    role=ROLE,
    goal=GOAL,
    backstory=BACKSTORY,
    max_iter=40,
)


def build_agent():
    """构建测试执行Agent实例。"""
    return create_agent(CONFIG)


def build_tasks(agent):
    task = create_task(
        description="""\
请完成员工入离职管理系统的功能测试执行与自动化测试脚本。

## 需要完成的工作
1. **自动化测试脚本**（pytest+requests）：
   - 入职流程：发起入职单→各级审批通过→状态校验→通知校验
   - 离职流程：申请→交接→审批→归还→状态校验
   - 异常用例：非法状态流转、重复提交、无权限访问、参数校验
   - 脚本结构：conftest.py（fixture/客户端封装）+ 按业务分组的用例模块

2. **缺陷清单**（如无真实缺陷，列出潜在风险点）：
   - 缺陷ID/标题/复现步骤/预期/实际/严重等级/状态

3. **功能测试报告**：
   - 测试概要、执行结果统计（通过/失败/阻塞）
   - 覆盖率说明、结论

## 输出要求
- 自动化脚本保存到 workspace/code/tests/（conftest.py+用例文件）
- 缺陷清单与功能测试报告保存到 workspace/docs/test_report.md
- 脚本附README运行说明""",
        expected_output="""\
功能测试交付物：
1. 自动化测试脚本（workspace/code/tests/，pytest+requests）
2. 缺陷清单与功能测试报告（workspace/docs/test_report.md）""",
        agent=agent,
    )
    return [task]


def run_with_crew(user_request: str = "") -> str:
    """使用韩均楠原有的 DigitalWorkerCrew 框架运行QA Agent。
    
    这是原有 main.py 的迁移版本，保留完整的 CrewAI 集成能力。
    """
    WORKSPACE_DIR = _PROJECT_ROOT / "workspace" / "qa"
    SANDBOX_PORT = 8029
    SESSION_ID = "qa_agent_onboarding"

    worker = DigitalWorkerCrew(
        workspace_dir=WORKSPACE_DIR,
        sandbox_port=SANDBOX_PORT,
        session_id=SESSION_ID,
        model="qwen3.6-max-preview",
        has_shared=True,
    )

    if not user_request:
        user_request = (
            "你是测试工程师B（韩均楠），负责功能测试执行。\n"
            "请按测试用例执行测试，编写自动化脚本，提交缺陷。\n"
            "1. 加载测试设计规范\n"
            "2. 执行测试并保存结果到 /workspace/test_report.md\n"
            "3. 对失败的用例提交缺陷到 /workspace/defect_list.json\n"
            "4. 生成测试报告"
        )

    result = worker.kickoff(user_request)
    return result


def run():
    agent = build_agent()
    tasks = build_tasks(agent)
    return run_agent([agent], tasks)


if __name__ == "__main__":
    result = run()
    print(result)
