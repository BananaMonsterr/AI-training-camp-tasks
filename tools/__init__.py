"""
Tools 模块

提供自定义工具实现，包括 Skill 加载、文件记忆等工具。

主要工具：
- SkillLoaderTool：Skill 加载与执行工具（任务型 + 参考型）—— 需要 crewai
- build_bootstrap_prompt：Workspace 导航骨架构建
- session 管理函数：load_session_ctx / save_session_ctx / append_session_raw
- 上下文优化：prune_tool_results / maybe_compress
"""

# ── 纯 Python 工具：不依赖 crewai，任何时候都可以安全导入 ────────────────────
from tools.m3l20_file_memory import (
    build_bootstrap_prompt,
    load_session_ctx,
    save_session_ctx,
    append_session_raw,
    prune_tool_results,
    maybe_compress,
)

__all__ = [
    "build_bootstrap_prompt",
    "load_session_ctx",
    "save_session_ctx",
    "append_session_raw",
    "prune_tool_results",
    "maybe_compress",
]

# ── SkillLoaderTool：依赖 crewai，仅在 crewai 可用时暴露 ──────────────────
_SKILL_LOADER_AVAILABLE = False
try:
    from tools.skill_loader_tool import SkillLoaderTool  # noqa: F401 (re-export)

    _SKILL_LOADER_AVAILABLE = True
except ModuleNotFoundError:
    pass

if _SKILL_LOADER_AVAILABLE:
    __all__.append("SkillLoaderTool")

