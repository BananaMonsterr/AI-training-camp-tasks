"""
测试 Agent - 员工入离职管理系统 + 统一入口点

运行方式：
  python main.py                            # 显示帮助信息
  python main.py --pipeline                 # 全流水线模式
  python main.py --stage 需求分析            # 单阶段模式
  python main.py --agent architect          # 单Agent模式
  python main.py "测试任务"                  # QA测试模式(保留原有功能)
"""

from __future__ import annotations
import sys
from pathlib import Path

_PROJECT_DIR = Path(__file__).resolve().parent
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))


def print_banner():
    print("=" * 60)
    print("  员工入离职管理系统 - 多Agent协作框架")
    print("=" * 60)
    print("")
    print("  运行模式:")
    print("    python main.py --pipeline        # 全流水线模式")
    print("    python main.py --stage 需求分析    # 单阶段模式")
    print("    python main.py --agent architect # 单Agent模式")
    print("    python main.py \"测试任务\"         # QA测试模式(原有)")
    print("")
    print("  Agent角色列表:")
    print("    产品: requirement_analyst(徐意), business_designer(张梦晴), solution_designer(刘紫璇)")
    print("    开发: architect(李兆贵), backend_dev(龚茂林), frontend_dev(张铃)")
    print("    测试: test_analyst(张桦彬), test_executor(韩均楠), acceptance_tester(测试工程师C)")
    print("")
    print("  流水线阶段:")
    print("    需求分析 -> 方案设计 -> 系统分析 -> 代码开发 -> 测试分析 -> 测试验收")
    print("")


def run_qa_mode(user_request: str):
    """运行韩均楠QA测试模式（原有功能）。"""
    from shared.digital_worker import DigitalWorkerCrew
    WORKSPACE_DIR = _PROJECT_DIR / "workspace" / "qa"
    SANDBOX_PORT = 8029
    SESSION_ID = "qa_agent_onboarding"

    worker = DigitalWorkerCrew(
        workspace_dir=WORKSPACE_DIR,
        sandbox_port=SANDBOX_PORT,
        session_id=SESSION_ID,
        model="qwen3.6-max-preview",
        has_shared=True,
    )

    if not user_request:
        user_request = (
            "你是测试工程师B（韩均楠），负责功能测试执行。\n"
            "请检查邮箱是否有任务分配，并按工作规范完成测试任务。"
        )

    print("\n{0}".format("="*60))
    print("测试Agent - 员工入离职管理系统 (韩均楠)")
    print("{0}".format("="*60))
    print("Session ID : {0}".format(SESSION_ID))
    print("Workspace  : {0}".format(WORKSPACE_DIR))

    result = worker.kickoff(user_request)

    print("\n{0}".format("-"*60))
    print("QA输出:")
    print(result)
    print("{0}".format("="*60))


def main():
    args = sys.argv[1:]

    if not args:
        print_banner()
        return

    if args[0] == "--pipeline":
        from agents.orchestrator import Orchestrator
        orch = Orchestrator()
        stages = args[1:] if len(args) > 1 else None
        summary = orch.run_pipeline(stages)
        print("\n流水线完成！执行角色: {0}".format(summary["completed_agents"]))

    elif args[0] == "--stage":
        from agents.orchestrator import Orchestrator
        orch = Orchestrator()
        orch.run_stage(args[1])

    elif args[0] == "--agent":
        from agents.orchestrator import Orchestrator
        orch = Orchestrator()
        result = orch.run_agent(args[1])
        print("\n结果: {0}".format(result[:500] if len(result) > 500 else result))

    else:
        run_qa_mode(" ".join(args))


if __name__ == "__main__":
    main()
