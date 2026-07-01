"""基础Agent构建器 - 支持 DeepSeek（文本）/ Qwen VL（识图）/ Qwen Image（生图）

遵循 m1l2_agent.py 风格，提供统一的 Agent/Task/Crew 构建接口。
llm_type 取值:
  - "text"      : DeepSeek v4 flash（纯文本，默认）
  - "vision"    : Qwen3 VL plus（识图）
  - "image_gen" : DeepSeek 文本 + QwenImageLLM 生图工具
"""
from __future__ import annotations
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Type

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
    llm_type: str = "text"  # "text" | "vision" | "image_gen"


def _build_image_gen_tool():
    """构建 CrewAI 兼容的生图工具。"""
    try:
        from crewai.tools import BaseTool
    except ImportError:
        from crewai_tools import BaseTool
    from pydantic import BaseModel, Field
    from llm.qwen_image_llm import QwenImageLLM

    class ImageGenInput(BaseModel):
        prompt: str = Field(description="图片描述提示词")
        size: str = Field(default="1024*1024", description="图片尺寸，如1024*1024")

    class ImageGenTool(BaseTool):
        name: str = "image_generation"
        description: str = "根据文字描述生成图片，返回图片URL"
        args_schema: Type[BaseModel] = ImageGenInput

        def _run(self, prompt: str, size: str = "1024*1024") -> str:
            llm = QwenImageLLM()
            result = llm.generate(prompt, size=size)
            if "image_url" in result:
                return "图片URL: " + result["image_url"]
            return "生成失败: " + result.get("error", "未知错误")

    return ImageGenTool()


def create_agent(config: AgentConfig) -> Agent:
    """统一构建 Agent 实例。"""
    extra_tools = list(config.tools)
    if config.llm_type == "image_gen":
        try:
            extra_tools.append(_build_image_gen_tool())
            llm = get_llm("text", config.temperature)
        except Exception:
            llm = get_llm("text", config.temperature)
    else:
        llm = get_llm(config.llm_type, config.temperature)
    if config.model:
        llm = get_llm(config.llm_type, config.temperature)
    return Agent(
        role=config.role,
        goal=config.goal,
        backstory=config.backstory,
        tools=extra_tools,
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
    return result.raw if hasattr(result, "raw") else str(result)


def build_backstory(identity, prompt_direction, work_method, deliverables, boundaries):
    return (
        "# 身份\n%s\n\n"
        "# Prompt 设计方向（核心职责）\n%s\n\n"
        "# 工作方法论\n%s\n\n"
        "# 核心交付物\n%s\n\n"
        "# 边界说明（NEVER 清单）\n%s\n\n"
        "**语言要求**：所有输出使用中文。"
    ) % (identity, prompt_direction, work_method, deliverables, boundaries)