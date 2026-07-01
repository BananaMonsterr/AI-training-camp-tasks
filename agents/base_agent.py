"""
基础Agent构建器 - 遵循 m1l2_agent.py 代码风格

提供统一的 Agent/Task 构建接口，所有 9 个角色通过此模块创建。
遵循 CrewAI 的 Agent/Task/Crew 模式：
  - Agent: 定义角色、目标、背景故事、工具、LLM
  - Task: 定义任务描述、期望输出、绑定的Agent
  - Crew: 组合 Agent 和 Task 执行

使用方式:
    agent = create_agent(config)
    task = create_task(description, expected_output, agent)
    result = run_agent([agent], [task])
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from crewai import Agent, Crew, Task
from crewai_tools import FileReadTool, FileWriterTool
from llm import aliyun_llm


@dataclass
class AgentConfig:
    """Agent 配置，遵循 m1l2_agent.py 风格的人设工程三要素。"""
    role: str
    goal: str
    backstory: str
    tools: list = field(default_factory=lambda: [FileReadTool(), FileWriterTool()])
    memory: bool = True
    max_iter: int = 40
    model: str | None = None
    temperature: float = 0.3


def create_agent(config: AgentConfig) -> Agent:
    """统一构建 Agent 实例，遵循 m1l2_agent.py 风格。"""
    return Agent(
        role=config.role,
        goal=config.goal,
        backstory=config.backstory,
        tools=config.tools,
        memory=config.memory,
        max_iter=config.max_iter,
        llm=aliyun_llm.AliyunLLM(
            model=config.model or os.getenv("AGENT_MODEL", "qwen3.6-max-preview"),
            temperature=config.temperature,
        ),
        verbose=True,
    )


def create_task(
    description: str,
    expected_output: str,
    agent: Agent,
    context_tasks: list[Task] | None = None,
) -> Task:
    """统一构建 Task 实例。"""
    task = Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
    )
    if context_tasks:
        task.context = context_tasks
    return task


def run_agent(
    agents: list[Agent],
    tasks: list[Task],
    verbose: bool = True,
) -> str:
    """运行单个或多个 Agent 组成的 Crew，返回执行结果。"""
    crew = Crew(
        agents=agents,
        tasks=tasks,
        verbose=verbose,
    )
    result = crew.kickoff()
    return result.raw if hasattr(result, 'raw') else str(result)


def build_backstory(
    identity: str,
    prompt_direction: str,
    work_method: str,
    deliverables: str,
    boundaries: str,
) -> str:
    """统一构建 Backstory 模板，确保 Prompt 设计方向一致。"""
    return f"""# 身份
{identity}

# Prompt 设计方向（核心职责）
{prompt_direction}

# 工作方法论
{work_method}

# 核心交付物
{deliverables}

# 边界说明（NEVER 清单）
{boundaries}

**语言要求**：所有输出使用中文。"""
