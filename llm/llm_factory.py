"""
LLM Factory - 统一管理多模型LLM创建

提供两种LLM类型：
  1. text - DeepSeek API（纯文本任务）
  2. vision - 通义千问 Qwen API（生图/识图任务）
"""
from __future__ import annotations
import os
from crewai import LLM as CrewAILLM
from llm import aliyun_llm

def get_text_llm(temperature: float = 0.3):
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("[WARN] DEEPSEEK_API_KEY 未设置，回退到 Qwen 文本模型")
        return get_vision_llm(temperature)
    return CrewAILLM(
        provider="openai",
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        temperature=temperature,
    )

def get_vision_llm(temperature: float = 0.3):
    return aliyun_llm.AliyunLLM(
        model=os.getenv("QWEN_MODEL", "qwen3.6-max-preview"),
        api_key=os.getenv("QWEN_API_KEY", ""),
        region=os.getenv("QWEN_REGION", "cn"),
        temperature=temperature,
    )

def get_llm(llm_type: str = "text", temperature: float = 0.3):
    if llm_type == "vision":
        return get_vision_llm(temperature)
    return get_text_llm(temperature)