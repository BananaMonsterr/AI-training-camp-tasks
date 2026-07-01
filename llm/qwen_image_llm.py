"""Qwen Image LLM - 通义万相生图 API 封装

调用 DashScope 异步任务式 API 生成图片。
API 文档: https://help.aliyun.com/zh/model-studio/developer-reference/text-to-image

使用方式:
    llm = QwenImageLLM()
    result = llm.generate("一只猫坐在沙发上")
    # result => {"image_url": "https://...", "task_id": "..."}

    # 也可传入参数:
    result = llm.generate(
        prompt="赛博朋克风格的城市夜景",
        size="1024*1024",
        n=1,
    )
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests


class QwenImageLLM:
    """通义万相图片生成 LLM，封装 DashScope 异步任务 API。"""

    TASK_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
    QUERY_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        max_retries: int = 30,
        retry_interval: float = 2.0,
    ):
        self.model = model or os.getenv("QWEN_IMAGE_MODEL", "qwen-image-2.0-pro")
        self.api_key = api_key or os.getenv("QWEN_API_KEY", "")
        self.max_retries = max_retries
        self.retry_interval = retry_interval

        if not self.api_key:
            print("[WARN] QWEN_API_KEY 未设置，图片生成功能不可用")

    def generate(
        self,
        prompt: str,
        size: str = "1024*1024",
        n: int = 1,
        negative_prompt: str | None = None,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """生成图片。

        Args:
            prompt: 图片描述提示词
            size: 图片尺寸，如 "1024*1024", "720*1280"
            n: 生成数量（通常为1）
            negative_prompt: 负面提示词
            seed: 随机种子

        Returns:
            {"image_url": str, "task_id": str} 或 {"error": str}
        """
        if not self.api_key:
            return {"error": "QWEN_API_KEY 未设置"}

        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Content-Type": "application/json",
        }

        body = {
            "model": self.model,
            "input": {"prompt": prompt},
            "parameters": {"size": size, "n": n},
        }
        if negative_prompt:
            body["parameters"]["negative_prompt"] = negative_prompt
        if seed is not None:
            body["parameters"]["seed"] = seed

        try:
            # Step 1: 提交任务
            resp = requests.post(
                self.TASK_ENDPOINT,
                headers=headers,
                json=body,
                timeout=30,
            )
            if resp.status_code != 200:
                return {"error": "提交任务失败: HTTP %d - %s" % (resp.status_code, resp.text)}

            task_data = resp.json()
            task_id = task_data.get("output", {}).get("task_id", "")
            if not task_id:
                return {"error": "未获取到 task_id: " + json.dumps(task_data, ensure_ascii=False)}

            # Step 2: 轮询任务结果
            for attempt in range(self.max_retries):
                time.sleep(self.retry_interval)
                result = self._query_task(task_id)
                status = result.get("output", {}).get("task_status", "")

                if status == "SUCCEEDED":
                    results = result.get("output", {}).get("results", [])
                    if results:
                        image_url = results[0].get("url", "")
                        return {
                            "image_url": image_url,
                            "task_id": task_id,
                            "model": self.model,
                        }
                    return {"error": "任务成功但无图片URL", "task_id": task_id}

                elif status == "FAILED":
                    msg = result.get("output", {}).get("message", "未知错误")
                    return {"error": "任务失败: " + msg, "task_id": task_id}

                # 继续轮询 (RUNNING / PENDING)

            return {"error": "轮询超时", "task_id": task_id}

        except requests.exceptions.RequestException as e:
            return {"error": "API请求异常: " + str(e)}
        except Exception as e:
            return {"error": "未知异常: " + str(e)}

    def _query_task(self, task_id: str) -> dict:
        """查询异步任务状态。"""
        url = self.QUERY_ENDPOINT.format(task_id=task_id)
        headers = {
            "Authorization": "Bearer " + self.api_key,
        }
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return {}

    def call(self, prompt: str, **kwargs) -> str:
        """简化的调用接口，直接返回图片URL或错误信息。"""
        result = self.generate(prompt, **kwargs)
        if "image_url" in result:
            return result["image_url"]
        return result.get("error", "生成失败")

    def __call__(self, prompt: str, **kwargs) -> str:
        """支持直接像函数一样调用。"""
        return self.call(prompt, **kwargs)


# 使用示例
if __name__ == "__main__":
    llm = QwenImageLLM()
    url = llm("一只橘猫在键盘上睡觉，插画风格")
    print("生图结果:", url)