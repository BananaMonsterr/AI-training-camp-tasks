"""
基础Agent构建器 - 支持 DeepSeek（文本）/ Qwen（视觉）LLM 切换

遵循 m1l2_agent.py 风格，提供统一的 Agent/Task/Crew 构建接口。
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
from llm.llm_factory import get_llm


@dataclass
class AgentConfig:
    role: str
    goal: str
    backstory: str
    tools: list = field(default_factory=lambda: [FileReadTool(), FileWriterTool()])
    memory: bool = True
    max_iter: int = 40
    model: str | None = None
    temperature: float = 0.3
    llm_type: str = "text"  # "text" -> DeepSeek, "vision" -> Qwen


def create_agent(config: AgentConfig) -> Agent:
    llm = get_llm(llm_type=config.llm_type, temperature=config.temperature)
    if config.model:
        llm = get_llm(llm_type=config.llm_type, temperature=config.temperature)
    return Agent(
        role=config.role,
        goal=config.goal,
        backstory=config.backstory,
        tools=config.tools,
        memory=config.memory,
        max_iter=config.max_iter,
        llm=llm,
        verbose=True,
    )


def create_task(description, expected_output, agent, context_tasks=None):
    task = Task(description=description, expected_output=expected_output, agent=agent)
    if context_tasks:
        task.context = context_tasks
    return task


def run_agent(agents, tasks, verbose=True):
    crew = Crew(agents=agents, tasks=tasks, verbose=verbose)
    result = crew.kickoff()
    return result.raw if hasattr(result, 'raw') else str(result)


def build_backstory(identity, prompt_direction, work_method, deliverables, boundaries):
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