---
name: defect_tracker
type: task
description: >
  缺陷清单管理工具。支持创建新缺陷、查询已有缺陷、更新缺陷状态、去重检查。
  缺陷清单存储在 /workspace/defect_list.json。
allowed-tools:
  - sandbox_file_operations
  - sandbox_execute_bash
  - sandbox_execute_code
---

# defect_tracker：缺陷追踪工具

## 概述

管理 `/workspace/defect_list.json` 中的缺陷记录。支持创建、查询、更新、去重。

## 数据结构

```json
{
  "project": "员工入职离职管理系统",
  "last_updated": "2026-07-01T10:30:00",
  "defects": [
    {
      "id": "BUG-001",
      "title": "入职审批驳回后无法重新提交",
      "severity": "P0",
      "module": "M1_入职管理",
      "related_tc": "TC-003",
      "repro_steps": "1. 以HR角色登录\n2. 为新员工zhangsan发起入职审批\n3. 以直属经理角色登录\n4. 审批驳回\n5. 切回HR角色\n6. 尝试重新提交入职申请",
      "precondition": "员工zhangsan已有被驳回的入职申请",
      "expected": "HR可以修改入职信息后重新提交审批",
      "actual": "提交按钮灰色不可点击，提示'该员工已有进行中的入职申请'",
      "status": "open",
      "found_by": "QA",
      "found_at": "2026-07-01T10:00:00",
      "fixed_at": null,
      "verified_at": null
    }
  ]
}
```

## 严重级别定义（人事系统专用）

| 级别 | 定义 | 人事系统示例 |
|------|------|------------|
| P0 | 核心流程阻断，无法发布 | 入职审批链断裂、离职审批无法完成、权限越权可看到他人薪资 |
| P1 | 功能可用但不满足验收标准 | 审批超时未自动升级、驳回后状态未正确还原、工作交接确认后未流转 |
| P2 | 非核心边界/体验问题 | 日期格式不统一、错误提示不够清晰、页面加载超过3秒 |

## 状态流转

```
open → in_progress(Dev认领) → fixed(Dev修复) → verified_close(QA验证通过)
  ↓                              ↓
wont_fix(设计如此/不修)        reopen(QA验证不通过, 修复无效)
```

QA 可操作的状态变更：
- 创建缺陷：status = "open"
- 回归验证通过：open/fixed → verified_close
- 回归验证不通过：fixed → reopen（附新的 actual 结果）

## 操作方式

### 创建缺陷

在沙盒中通过 Python 脚本操作 `defect_list.json`：

```python
import json
from pathlib import Path
from datetime import datetime, timezone

defect_list_path = Path("/workspace/defect_list.json")

# 加载已有清单
if defect_list_path.exists():
    data = json.loads(defect_list_path.read_text(encoding="utf-8"))
else:
    data = {"project": "员工入职离职管理系统", "last_updated": "", "defects": []}

# 去重检查：相同 title + module 的缺陷不重复创建
existing = [d for d in data["defects"] if d["title"] == new_defect["title"] and d["module"] == new_defect["module"]]
if existing:
    print(json.dumps({"errcode": 2, "errmsg": f"缺陷已存在: {existing[0]['id']}"}))
    return

# 生成 ID
max_id = 0
for d in data["defects"]:
    num = int(d["id"].replace("BUG-", ""))
    max_id = max(max_id, num)
new_defect["id"] = f"BUG-{max_id + 1:03d}"

# 追加并保存
data["defects"].append(new_defect)
data["last_updated"] = datetime.now(timezone.utc).isoformat()
defect_list_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"errcode": 0, "data": {"defect_id": new_defect["id"]}}, ensure_ascii=False))
```

### 查询缺陷

```python
# 按状态查询
open_defects = [d for d in data["defects"] if d["status"] == "open"]
# 按模块查询
m1_defects = [d for d in data["defects"] if d["module"] == "M1_入职管理"]
# 按严重级别查询
p0_defects = [d for d in data["defects"] if d["severity"] == "P0"]
```

### 更新缺陷状态

```python
for d in data["defects"]:
    if d["id"] == target_id:
        d["status"] = new_status  # verified_close / reopen
        if new_status == "verified_close":
            d["verified_at"] = datetime.now(timezone.utc).isoformat()
        break
```

## 注意事项

1. **去重**：创建缺陷前必须检查是否已存在相同 title + module 的记录
2. **增量更新**：不要覆盖已有的 defects 数组，始终 append
3. **状态安全**：不能直接把 `open` 改成 `verified_close`（必须经过 `fixed`）
4. **read-back 验证**：每次写入后必须 read-back 确认 JSON 文件未损坏