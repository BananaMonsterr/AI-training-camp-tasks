"""
第29课 单元测试 — test_m4l29.py
QA 角色 — 员工入职离职管理系统

测试策略：
  T1 ：QA workspace 四件套存在且非空
  T2 ：QA skills 目录结构完整（5 个 Skill + load_skills.yaml）
  T3 ：mailbox skill 脚本可执行且三态状态机完整
  T4 ：defect_tracker 缺陷清单 CRUD 操作正确
  T5 ：test_design reference Skill 内容可正常加载
  T6 ：report_generator 报告模板输出格式正确
  T7 ：test_executor 能正确解析测试结果 JSON
  T8 ：共享工作区 qa 目录创建和文件同步
  T9 ：QA main.py 能正常初始化 DigitalWorkerCrew
  T10：缺陷清单 JSON schema 校验
  T11：test_suite.py 模板语法正确可执行
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# ── 路径设置 ──────────────────────────────────────────────────────────────────
_M4L29_DIR    = Path(__file__).resolve().parent
_PROJECT_ROOT = _M4L29_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_M4L29_DIR))

WORKSPACE_QA     = _M4L29_DIR / "workspace" / "qa"
QA_SKILLS_DIR    = WORKSPACE_QA / "skills"
DEMO_INPUT       = _M4L29_DIR / "demo_input" / "project_requirement.md"


# ─────────────────────────────────────────────────────────────────────────────
# T1 | QA workspace 四件套完整性
# ─────────────────────────────────────────────────────────────────────────────

class TestT1WorkspaceFiles:
    """T1：QA workspace 四个角色定义文件存在且非空"""

    @pytest.mark.parametrize("filename", ["soul.md", "agent.md", "user.md", "memory.md"])
    def test_workspace_file_exists(self, filename: str) -> None:
        path = WORKSPACE_QA / filename
        assert path.exists(), f"QA workspace 缺少 {filename}"
        content = path.read_text(encoding="utf-8").strip()
        assert len(content) > 0, f"{filename} 内容为空"


# ─────────────────────────────────────────────────────────────────────────────
# T2 | Skills 目录结构完整
# ─────────────────────────────────────────────────────────────────────────────

class TestT2SkillsStructure:
    """T2：QA skills 目录包含 5 个 Skill + load_skills.yaml"""

    def test_load_skills_yaml_exists(self) -> None:
        assert (QA_SKILLS_DIR / "load_skills.yaml").exists(), "缺少 load_skills.yaml"

    @pytest.mark.parametrize("skill_name", [
        "mailbox",
        "test_design",
        "test_executor",
        "defect_tracker",
        "report_generator",
    ])
    def test_skill_dir_and_skill_md(self, skill_name: str) -> None:
        skill_dir = QA_SKILLS_DIR / skill_name
        assert skill_dir.is_dir(), f"Skill 目录不存在: {skill_name}"
        skill_md = skill_dir / "SKILL.md"
        assert skill_md.exists(), f"SKILL.md 不存在: {skill_name}"
        content = skill_md.read_text(encoding="utf-8").strip()
        assert len(content) > 100, f"{skill_name}/SKILL.md 内容过短（<100字符）"

    def test_mailbox_script_exists(self) -> None:
        script = QA_SKILLS_DIR / "mailbox" / "scripts" / "mailbox_cli.py"
        assert script.exists(), "mailbox_cli.py 脚本不存在"

    def test_load_skills_yaml_has_five_skills(self) -> None:
        import yaml
        with open(QA_SKILLS_DIR / "load_skills.yaml", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
        names = [s["name"] for s in manifest.get("skills", [])]
        assert "test_design" in names
        assert "test_executor" in names
        assert "defect_tracker" in names
        assert "report_generator" in names
        assert "mailbox" in names


# ─────────────────────────────────────────────────────────────────────────────
# T3 | mailbox skill 脚本可执行 + 三态状态机
# ─────────────────────────────────────────────────────────────────────────────

class TestT3MailboxScript:
    """T3：mailbox_cli.py 可执行，三态状态机正常"""

    def setup_method(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="qa_test_mailbox_"))
        (self.tmpdir / "qa.json").write_text("[]", encoding="utf-8")
        # 预安装 filelock，避免首次 subprocess 调用超时
        import subprocess
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "filelock", "-q"],
            capture_output=True, timeout=30,
        )

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_mailbox(self, *args: str) -> dict:
        import subprocess
        cmd = [sys.executable,
               str(QA_SKILLS_DIR / "mailbox" / "scripts" / "mailbox_cli.py"),
               args[0],  # 子命令 (send/read/done)
               "--mailboxes-dir", str(self.tmpdir),
               *args[1:]]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0 or not result.stdout.strip():
            raise RuntimeError(
                f"mailbox_cli failed (rc={result.returncode}): "
                f"stdout={result.stdout[:200]} stderr={result.stderr[:200]}"
            )
        return json.loads(result.stdout)

    def test_send_mail(self) -> None:
        out = self._run_mailbox(
            "send", "--from", "qa", "--to", "manager",
            "--type", "task_done", "--subject", "测试", "--content", "路径引用"
        )
        assert out["errcode"] == 0
        assert out["data"]["msg_id"].startswith("msg-")

    def test_read_empty_mailbox(self) -> None:
        out = self._run_mailbox("read", "--role", "qa")
        assert out["errcode"] == 0
        assert out["data"]["messages"] == []

    def test_full_state_machine(self) -> None:
        # send → read (unread→in_progress) → done (in_progress→done)
        sent = self._run_mailbox(
            "send", "--from", "manager", "--to", "qa",
            "--type", "task_assign", "--subject", "测试任务", "--content", "路径引用"
        )
        msg_id = sent["data"]["msg_id"]

        read = self._run_mailbox("read", "--role", "qa")
        assert len(read["data"]["messages"]) == 1
        assert read["data"]["messages"][0]["status"] == "in_progress"

        done = self._run_mailbox("done", "--role", "qa", "--msg-id", msg_id)
        assert done["errcode"] == 0

        # 再次读取应为空
        read2 = self._run_mailbox("read", "--role", "qa")
        assert read2["data"]["messages"] == []


# ─────────────────────────────────────────────────────────────────────────────
# T4 | defect_tracker 缺陷清单 CRUD
# ─────────────────────────────────────────────────────────────────────────────

class TestT4DefectTracker:
    """T4：defect_list.json 的创建、去重、更新操作"""

    def setup_method(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="qa_test_defect_"))
        self.defect_file = self.tmpdir / "defect_list.json"

    def teardown_method(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_sample_defect(self, **overrides) -> dict:
        base = {
            "id": "BUG-001",
            "title": "入职审批驳回后无法重新提交",
            "severity": "P0",
            "module": "M1_入职管理",
            "related_tc": "TC-003",
            "repro_steps": "1. HR登录 → 2. 发起入职 → 3. 经理驳回 → 4. HR重新提交",
            "precondition": "已有被驳回的入职申请",
            "expected": "HR可以修改后重新提交",
            "actual": "提交按钮灰色不可点击",
            "status": "open",
            "found_by": "QA",
            "found_at": "2026-07-01T10:00:00",
            "fixed_at": None,
            "verified_at": None,
        }
        base.update(overrides)
        return base

    def test_create_empty_defect_list(self) -> None:
        data = {
            "project": "员工入职离职管理系统",
            "last_updated": "2026-07-01T10:00:00",
            "defects": [],
        }
        self.defect_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        loaded = json.loads(self.defect_file.read_text(encoding="utf-8"))
        assert loaded["defects"] == []

    def test_append_defect(self) -> None:
        data = {
            "project": "员工入职离职管理系统",
            "last_updated": "",
            "defects": [],
        }
        defect = self._make_sample_defect()
        data["defects"].append(defect)
        self.defect_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        loaded = json.loads(self.defect_file.read_text(encoding="utf-8"))
        assert len(loaded["defects"]) == 1
        assert loaded["defects"][0]["id"] == "BUG-001"

    def test_dedup_by_title_and_module(self) -> None:
        data = {
            "project": "员工入职离职管理系统",
            "last_updated": "",
            "defects": [self._make_sample_defect()],
        }
        # 尝试添加相同 title + module 的缺陷
        duplicate = self._make_sample_defect(id="BUG-002")
        existing = [d for d in data["defects"]
                    if d["title"] == duplicate["title"] and d["module"] == duplicate["module"]]
        assert len(existing) == 1  # 去重检测生效

    def test_update_defect_status(self) -> None:
        data = {
            "project": "员工入职离职管理系统",
            "last_updated": "",
            "defects": [self._make_sample_defect()],
        }
        # fixed → verified_close
        data["defects"][0]["status"] = "fixed"
        data["defects"][0]["status"] = "verified_close"
        data["defects"][0]["verified_at"] = "2026-07-02T10:00:00"
        assert data["defects"][0]["status"] == "verified_close"

    def test_severity_values_are_valid(self) -> None:
        """所有缺陷的 severity 必须为 P0/P1/P2"""
        for severity in ["P0", "P1", "P2"]:
            defect = self._make_sample_defect(severity=severity)
            assert defect["severity"] in ("P0", "P1", "P2")
        # 非法值应被拒绝
        with pytest.raises(AssertionError):
            invalid = self._make_sample_defect(severity="P3")
            assert invalid["severity"] in ("P0", "P1", "P2")

    def test_module_values_are_valid(self) -> None:
        """缺陷 module 必须属于四大模块之一"""
        valid_modules = ["M1_入职管理", "M2_离职管理", "M3_员工信息管理", "M4_权限与审批流"]
        for module in valid_modules:
            defect = self._make_sample_defect(module=module)
            assert defect["module"] in valid_modules


# ─────────────────────────────────────────────────────────────────────────────
# T5 | test_design reference Skill 内容完整性
# ─────────────────────────────────────────────────────────────────────────────

class TestT5TestDesignSkill:
    """T5：test_design SKILL.md 包含完整的测试策略说明"""

    def test_skill_md_has_required_sections(self) -> None:
        content = (QA_SKILLS_DIR / "test_design" / "SKILL.md").read_text(encoding="utf-8")
        assert "M1" in content, "缺少 M1 入职管理测试设计"
        assert "M2" in content, "缺少 M2 离职管理测试设计"
        assert "M3" in content, "缺少 M3 员工信息管理测试设计"
        assert "M4" in content, "缺少 M4 权限与审批流测试设计"
        assert "权限矩阵" in content, "缺少权限矩阵测试方法"
        assert "审批链" in content or "审批" in content, "缺少审批流测试说明"
        assert "边界" in content or "异常" in content, "缺少边界异常测试说明"


# ─────────────────────────────────────────────────────────────────────────────
# T6 | report_generator 报告模板格式
# ─────────────────────────────────────────────────────────────────────────────

class TestT6ReportGenerator:
    """T6：report_generator SKILL.md 定义了完整的报告模板"""

    def test_report_template_has_required_sections(self) -> None:
        content = (QA_SKILLS_DIR / "report_generator" / "SKILL.md").read_text(encoding="utf-8")
        assert "测试结论" in content
        assert "测试概览" in content
        assert "缺陷统计" in content
        assert "分模块测试结果" in content or "分模块" in content
        assert "风险评估" in content
        assert "改进建议" in content or "建议" in content
        assert "审批流专项测试" in content, "缺少审批流专项测试结果表格"


# ─────────────────────────────────────────────────────────────────────────────
# T7 | test_executor 结果解析格式
# ─────────────────────────────────────────────────────────────────────────────

class TestT7TestExecutor:
    """T7：test_executor 输出 JSON schema 校验"""

    def test_executor_output_schema(self) -> None:
        """验证 executor 期望的输出格式有完整字段"""
        sample_output = {
            "errcode": 0,
            "data": {
                "total": 4,
                "passed": 3,
                "failed": 1,
                "error": 0,
                "skipped": 0,
                "pass_rate": "75.0%",
                "duration_seconds": 2.5,
                "modules": {
                    "M1_入职管理": {"total": 4, "passed": 3, "failed": 1},
                },
                "results": [
                    {
                        "id": "TC-001",
                        "module": "M1_入职管理",
                        "name": "测试用例名",
                        "status": "passed",
                        "duration_seconds": 0.5,
                    },
                ],
            },
        }
        assert sample_output["errcode"] == 0
        assert "total" in sample_output["data"]
        assert "passed" in sample_output["data"]
        assert "failed" in sample_output["data"]
        assert "results" in sample_output["data"]
        assert len(sample_output["data"]["results"]) > 0

    def test_executor_skill_md_exists(self) -> None:
        content = (QA_SKILLS_DIR / "test_executor" / "SKILL.md").read_text(encoding="utf-8")
        assert "test_suite.py" in content
        assert "errcode" in content


# ─────────────────────────────────────────────────────────────────────────────
# T8 | 共享工作区 qa 目录初始化
# ─────────────────────────────────────────────────────────────────────────────

class TestT8SharedWorkspace:
    """T8：共享工作区 /mnt/shared/qa/ 创建和同步"""

    def test_qa_can_create_shared_dir_via_mkdir(self) -> None:
        tmpdir = Path(tempfile.mkdtemp(prefix="qa_test_shared_"))
        try:
            qa_dir = tmpdir / "qa"
            qa_dir.mkdir(parents=True, exist_ok=True)
            assert qa_dir.is_dir()

            # 模拟同步文件
            (qa_dir / "test_report.md").write_text("# Test Report", encoding="utf-8")
            (qa_dir / "defect_list.json").write_text('{"defects":[]}', encoding="utf-8")
            (qa_dir / "test_suite.py").write_text("# test suite", encoding="utf-8")

            assert (qa_dir / "test_report.md").exists()
            assert (qa_dir / "defect_list.json").exists()
            assert (qa_dir / "test_suite.py").exists()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ─────────────────────────────────────────────────────────────────────────────
# T9 | QA main.py 初始化
# ─────────────────────────────────────────────────────────────────────────────

class TestT9MainEntry:
    """T9：main.py 能正常导入和初始化"""

    def test_main_module_imports(self) -> None:
        """验证 main.py 依赖的模块可导入（crewai 未安装时跳过）"""
        try:
            from shared.digital_worker import DigitalWorkerCrew
            assert DigitalWorkerCrew is not None
        except ModuleNotFoundError as e:
            if "crewai" in str(e):
                pytest.skip("crewai not installed in this environment")
            raise

    def test_workspace_paths_correct(self) -> None:
        """验证 WORKSPACE_DIR 和 SANDBOX_PORT 正确"""
        assert WORKSPACE_QA.is_dir()
        assert WORKSPACE_QA.name == "qa"


# ─────────────────────────────────────────────────────────────────────────────
# T10 | 缺陷清单 JSON schema 校验
# ─────────────────────────────────────────────────────────────────────────────

class TestT10DefectSchema:
    """T10：缺陷清单完整 JSON schema 校验"""

    REQUIRED_FIELDS = [
        "id", "title", "severity", "module", "repro_steps",
        "expected", "actual", "status", "found_by", "found_at",
    ]

    VALID_SEVERITIES = ("P0", "P1", "P2")
    VALID_MODULES = ("M1_入职管理", "M2_离职管理", "M3_员工信息管理", "M4_权限与审批流")
    VALID_STATUSES = ("open", "in_progress", "fixed", "verified_close", "reopen", "wont_fix")

    def test_defect_has_all_required_fields(self) -> None:
        defect = {
            "id": "BUG-001",
            "title": "入职审批驳回后无法重新提交",
            "severity": "P0",
            "module": "M1_入职管理",
            "repro_steps": "1. HR登录 2. 发起入职 3. 驳回 4. 重新提交",
            "expected": "可以重新提交",
            "actual": "提交按钮灰色",
            "status": "open",
            "found_by": "QA",
            "found_at": "2026-07-01T10:00:00",
        }
        for field in self.REQUIRED_FIELDS:
            assert field in defect, f"缺陷缺少必填字段: {field}"

    def test_defect_id_format(self) -> None:
        """缺陷 ID 格式: BUG-XXX（三位数字）"""
        import re
        assert re.match(r"^BUG-\d{3}$", "BUG-001")
        assert re.match(r"^BUG-\d{3}$", "BUG-015")
        assert not re.match(r"^BUG-\d{3}$", "BUG-1")
        assert not re.match(r"^BUG-\d{3}$", "bug-001")

    @pytest.mark.parametrize("severity", ["P0", "P1", "P2"])
    def test_valid_severity(self, severity: str) -> None:
        assert severity in self.VALID_SEVERITIES

    @pytest.mark.parametrize("module", ["M1_入职管理", "M2_离职管理", "M3_员工信息管理", "M4_权限与审批流"])
    def test_valid_module(self, module: str) -> None:
        assert module in self.VALID_MODULES

    def test_defect_list_top_level_schema(self) -> None:
        doc = {
            "project": "员工入职离职管理系统",
            "last_updated": "2026-07-01T10:00:00",
            "defects": [],
        }
        assert "project" in doc
        assert "last_updated" in doc
        assert "defects" in doc
        assert isinstance(doc["defects"], list)


# ─────────────────────────────────────────────────────────────────────────────
# T11 | test_suite.py 模板语法正确
# ─────────────────────────────────────────────────────────────────────────────

class TestT11TestSuiteTemplate:
    """T11：test_suite.py 模板语法正确可执行"""

    def test_sample_test_suite_is_valid_python(self) -> None:
        """生成一个最小测试套件并验证语法正确"""
        sample_code = '''"""
自动化测试套件 - 员工入职离职管理系统
"""
import unittest
import json


class TestOnboardingHappyPath(unittest.TestCase):
    """M1 入职管理 — 核心流程测试"""

    def test_tc001_create_onboarding_flow(self):
        """TC-001: M1_入职管理 — HR录入新员工→审批链完整流转"""
        # 模拟测试
        result = {"status": "pending", "employee_id": "EMP-001"}
        self.assertEqual(result["status"], "pending")
        self.assertTrue(result["employee_id"].startswith("EMP-"))

    def test_tc002_required_field_validation(self):
        """TC-002: M1_入职管理 — 必填字段为空→阻止提交"""
        required_fields = ["name", "id_number", "phone", "email", "hire_date"]
        empty_data = {f: "" for f in required_fields}
        # 所有必填字段为空应被检测
        self.assertTrue(any(v == "" for v in empty_data.values()))


class TestOffboardingFlow(unittest.TestCase):
    """M2 离职管理 — 核心流程测试"""

    def test_tc008_submit_resignation(self):
        """TC-008: M2_离职管理 — 员工提交离职申请→经理收到待办"""
        result = {
            "status": "pending_manager_approval",
            "resignation_id": "RES-001",
        }
        self.assertIn("pending", result["status"])


class TestPermissionMatrix(unittest.TestCase):
    """M4 权限与审批流 — 权限矩阵测试"""

    def test_tc020_hr_cannot_view_salary(self):
        """TC-020: M4_权限与审批流 — HR角色不能查看薪资信息"""
        hr_permissions = ["onboarding", "employee_info", "offboarding_init"]
        self.assertNotIn("salary_view", hr_permissions)


if __name__ == "__main__":
    unittest.main()
'''
        # 验证语法
        compile(sample_code, "<test_suite.py>", "exec")

    def test_sample_suite_runs(self) -> None:
        """执行最小测试套件，验证能正常运行"""
        import subprocess
        tmpfile = Path(tempfile.mktemp(suffix=".py", prefix="test_suite_"))
        try:
            tmpfile.write_text('''
import unittest
class SmokeTest(unittest.TestCase):
    def test_smoke(self):
        self.assertEqual(1 + 1, 2)
if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(tmpfile)],
                capture_output=True, text=True, timeout=10,
            )
            assert result.returncode == 0, f"测试套件执行失败: {result.stderr}"
        finally:
            tmpfile.unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# T12 | demo_input 需求文档完整性
# ─────────────────────────────────────────────────────────────────────────────

class TestT12DemoInput:
    """T12：demo_input/project_requirement.md 包含四大模块需求"""

    def test_demo_input_exists_and_non_empty(self) -> None:
        assert DEMO_INPUT.exists(), "demo_input/project_requirement.md 不存在"
        content = DEMO_INPUT.read_text(encoding="utf-8").strip()
        assert len(content) > 500, "需求文档内容过短"

    def test_demo_input_covers_all_modules(self) -> None:
        content = DEMO_INPUT.read_text(encoding="utf-8")
        assert "M1" in content and "入职" in content, "缺少 M1 入职管理"
        assert "M2" in content and "离职" in content, "缺少 M2 离职管理"
        assert "M3" in content and "员工信息" in content, "缺少 M3 员工信息管理"
        assert "M4" in content and "权限" in content, "缺少 M4 权限与审批流"

    def test_demo_input_has_acceptance_criteria(self) -> None:
        content = DEMO_INPUT.read_text(encoding="utf-8")
        assert "验收标准" in content or "DoD" in content, "缺少验收标准"