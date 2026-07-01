"""
第29课：项目实战 — Agent 小队完成真实项目需求（QA 入口）

教学点：
  - QA 作为独立数字员工，基于 workspace 文件定义全部角色身份
  - 通过邮箱与 Manager 通信，接收测试任务 + 提交测试报告
  - 复用 DigitalWorkerCrew（与 m4l26/m4l27/m4l28 完全一致的框架）

运行方式：
  # QA 启动（检查邮箱，处理 Manager 分配的测试任务）
  python main.py

  # 或直接指定测试任务
  python main.py "请对员工入职离职管理系统的 M1 入职管理模块进行功能测试"
"""

from __future__ import annotations

import sys
from pathlib import Path

_M4L29_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _M4L29_DIR.parent
for _p in [str(_M4L29_DIR), str(_PROJECT_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from shared.digital_worker import DigitalWorkerCrew  # noqa: E402

WORKSPACE_DIR = _M4L29_DIR / "workspace" / "qa"
SANDBOX_PORT  = 8029
SESSION_ID    = "demo_m4l29_qa"


def _build_user_request() -> str:
    """根据命令行参数或默认场景构建 QA 测试任务。"""
    user_input = " ".join(sys.argv[1:]).strip()

    if user_input:
        return (
            f"你是 QA（测试工程师），负责员工入职离职管理系统的质量保障。\n\n"
            f"收到任务：{user_input}\n\n"
            f"请按照你的工作规范（agent.md）完成测试任务：\n"
            f"1. 加载 test_design Skill 获取测试设计规范\n"
            f"2. 设计测试用例并保存为 /workspace/test_suite.py\n"
            f"3. 加载 test_executor Skill 执行测试\n"
            f"4. 对失败的用例提交缺陷到 /workspace/defect_list.json\n"
            f"5. 生成测试报告到 /workspace/test_report.md\n"
            f"6. 同步产出的文件到 /mnt/shared/qa/"
        )

    # 默认：检查邮箱，处理 Manager 分配的测试任务
    return (
        "你是 QA（测试工程师），负责员工入职离职管理系统的质量保障。\n\n"
        "请检查邮箱，看 Manager 是否分配了测试任务。\n\n"
        "如果有 task_assign 消息：\n"
        "1. 阅读邮件中指定的产品文档和需求文档\n"
        "2. 根据 test_design Skill 设计测试用例\n"
        "3. 执行测试并生成报告\n"
        "4. 回邮通知 Manager\n\n"
        "如果邮箱为空，输出当前状态即可（无需虚构测试结果）。"
    )


def main() -> None:
    user_request = _build_user_request()

    worker = DigitalWorkerCrew(
        workspace_dir=WORKSPACE_DIR,
        sandbox_port=SANDBOX_PORT,
        session_id=SESSION_ID,
        model="qwen3.6-max-preview",
        has_shared=True,
    )

    print(f"\n{'='*60}")
    print("第29课：Agent 小队完成真实项目需求 — QA 启动")
    print(f"{'='*60}")
    print(f"Session ID : {SESSION_ID}")
    print(f"Workspace  : {WORKSPACE_DIR}")
    print(f"沙盒端口   : {SANDBOX_PORT}")
    print(f"{'─'*60}\n")

    result = worker.kickoff(user_request)

    print(f"\n{'─'*60}")
    print("QA 输出：")
    print(result)
    print(f"{'='*60}")


if __name__ == "__main__":
    main()