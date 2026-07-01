"""LLM Factory - 统一管理多模型LLM创建

三种LLM类型:
  1. text        - DeepSeek v4 flash（纯文本生成/识别）
  2. vision      - Qwen3 VL plus（识图/图片理解）
  3. image_gen   - Qwen Image 2.0 pro（生图）

环境变量:
  DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL / DEEPSEEK_MODEL
  QWEN_API_KEY / QWEN_VL_MODEL / QWEN_IMAGE_MODEL / QWEN_REGION
"""
from __future__ import annotations
import os
from crewai import LLM as CrewAILLM
from llm import aliyun_llm
from llm.qwen_image_llm import QwenImageLLM


def get_text_llm(temperature: float = 0.3):
    """DeepSeek v4 flash - 文本生成/识别（所有纯文本Agent的默认LLM）"""
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("[WARN] DEEPSEEK_API_KEY 未设置，回退到 Qwen 文本模型")
        return get_vision_llm(temperature)
    return CrewAILLM(
        provider="openai",
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        temperature=temperature,
    )


def get_vision_llm(temperature: float = 0.3):
    """Qwen3 VL plus - 识图/图片理解"""
    return aliyun_llm.AliyunLLM(
        model=os.getenv("QWEN_VL_MODEL", "qwen3-vl-plus"),
        api_key=os.getenv("QWEN_API_KEY", ""),
        region=os.getenv("QWEN_REGION", "cn"),
        temperature=temperature,
    )


def get_image_gen_llm() -> QwenImageLLM:
    """Qwen Image 2.0 pro - 生图（返回可调用的 QwenImageLLM 实例）

    用法:
        img_llm = get_image_gen_llm()
        url = img_llm("一只猫")               # __call__
        # 或
        result = img_llm.generate("一只猫")    # 返回完整 dict
    """
    return QwenImageLLM(
        model=os.getenv("QWEN_IMAGE_MODEL", "qwen-image-2.0-pro"),
        api_key=os.getenv("QWEN_API_KEY", ""),
    )


def get_llm(llm_type: str = "text", temperature: float = 0.3):
    """根据类型获取对应的 LLM 实例。

    Args:
        llm_type: "text" | "vision" | "image_gen"
        temperature: 采样温度（仅 text/vision 生效）
    Returns:
        text/vision => CrewAI LLM 实例
        image_gen   => QwenImageLLM 实例（可调用的生图对象）
    """
    if llm_type == "vision":
        return get_vision_llm(temperature)
    elif llm_type == "image_gen":
        return get_image_gen_llm()
    return get_text_llm(temperature)