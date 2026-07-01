"""
第29课 conftest.py — pytest 配置
"""
from __future__ import annotations

import sys
from pathlib import Path

# 将 m4l29/ 和项目根加入 sys.path
_M4L29_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _M4L29_DIR.parent
for _p in [str(_M4L29_DIR), str(_PROJECT_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)