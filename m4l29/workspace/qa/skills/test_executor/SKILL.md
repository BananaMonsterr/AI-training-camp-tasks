---
name: test_executor
type: task
description: >
  在沙盒中执行自动化测试脚本 /workspace/test_suite.py，
  收集测试结果（通过/失败/错误），输出结构化 JSON 报告。
  支持指定测试范围（模块、用例标签、回归模式）。
allowed-tools:
  - sandbox_execute_bash
  - sandbox_execute_code
  - sandbox_file_operations
---

# test_executor：自动化测试执行

## 概述

在 AIO-Sandbox 中执行 `/workspace/test_suite.py` 测试脚本，
收集并结构化输出测试结果。

## 执行步骤

### 第一步：确认测试脚本存在

```bash
test -f /workspace/test_suite.py && echo "EXISTS" || echo "NOT_FOUND"
```

如果不存在 → 返回 errcode=1, errmsg="测试脚本不存在，请先设计测试用例"

### 第二步：安装依赖（如有）

```bash
pip install pytest -q 2>/dev/null
```

### 第三步：执行测试

```bash
cd /workspace && python3 /workspace/test_suite.py 2>&1
```

如果测试脚本使用 pytest 风格：
```bash
cd /workspace && python3 -m pytest /workspace/test_suite.py -v --tb=short 2>&1
```

### 第四步：结构化输出结果

必须输出 JSON 格式：

```json
{
  "errcode": 0,
  "data": {
    "total": 25,
    "passed": 20,
    "failed": 4,
    "error": 1,
    "skipped": 0,
    "pass_rate": "80.0%",
    "duration_seconds": 12.3,
    "modules": {
      "M1_入职管理": {"total": 7, "passed": 6, "failed": 1},
      "M2_离职管理": {"total": 6, "passed": 5, "failed": 1},
      "M3_员工信息管理": {"total": 6, "passed": 5, "failed": 1},
      "M4_权限与审批流": {"total": 6, "passed": 4, "failed": 1, "error": 1}
    },
    "results": [
      {
        "id": "TC-001",
        "module": "M1_入职管理",
        "name": "HR 录入新员工 → 审批链完整流转",
        "status": "passed",
        "duration_seconds": 0.5
      },
      {
        "id": "TC-005",
        "module": "M1_入职管理",
        "name": "入职信息必填字段为空 → 阻止提交",
        "status": "failed",
        "error_message": "AssertionError: 期望返回 400，实际返回 200",
        "duration_seconds": 0.3
      }
    ]
  }
}
```

## 测试脚本规范

QA 编写的 `test_suite.py` 应遵循以下规范，确保 executor 能正确解析结果：

### 规范 1：使用 unittest 或 pytest 框架

```python
import unittest
import json
import sys

class TestOnboarding(unittest.TestCase):
    def test_tc001_hr_create_onboarding(self):
        """TC-001: M1_入职管理 — HR 录入新员工 → 审批链完整流转"""
        # 测试逻辑
        self.assertEqual(response.status_code, 201)

class TestOffboarding(unittest.TestCase):
    def test_tc008_employee_submit_resignation(self):
        """TC-008: M2_离职管理 — 员工提交离职申请 → 直属经理收到待办"""
        # 测试逻辑
        self.assertIn("pending", response.json()["status"])

if __name__ == "__main__":
    unittest.main()
```

### 规范 2：测试函数命名包含用例 ID

- 函数名格式：`test_tc{编号}_{模块}_{场景简述}`
- docstring 第一行：`TC-{编号}: {模块} — {用例名称}`

### 规范 3：输出机器可读的结果

在 `if __name__ == "__main__"` 中，使用 `unittest.TestProgram` 的 `--json` 或自定义 runner 输出 JSON。

## 错误处理

- 测试脚本语法错误 → errcode=1, errmsg 包含错误行号和提示
- 依赖缺失 → errcode=1, errmsg 提示缺失的包名
- 超时（> 5min）→ errcode=1, errmsg 提示超时
