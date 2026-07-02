"""
HR系统对接单元测试
"""

import pytest

from integrations.hr_system import HRSystemClient, SyncDirection, SyncStatus


class TestSyncEmployee:
    """同步员工信息测试"""

    def test_sync_success(self, hr_client):
        data = {
            "employee_no": "EMP20250001",
            "name": "张三",
            "id_card": "110101199001011234",
            "email": "zhangsan@company.com",
            "phone": "13800138000",
            "department_code": "DEPT001",
            "department_name": "技术部",
            "position": "高级工程师",
            "hire_date": "2025-01-16",
            "employment_type": "full_time",
        }
        result = hr_client.sync_employee(data)
        assert result["success"] is True
        assert "同步成功" in result["message"]

    def test_sync_empty_employee_no(self, hr_client):
        result = hr_client.sync_employee({"employee_no": ""})
        assert result["success"] is False
        assert "不能为空" in result["message"]

    def test_sync_duplicate(self, hr_client):
        """重复同步相同的员工（应该覆盖更新）"""
        data = {
            "employee_no": "EMP20250002",
            "name": "李四",
            "department_code": "DEPT002",
        }
        r1 = hr_client.sync_employee(data)
        assert r1["success"] is True

        r2 = hr_client.sync_employee({**data, "name": "李四更新"})
        assert r2["success"] is True


class TestWritebackStatus:
    """状态回写测试"""

    def test_writeback_success(self, hr_client):
        result = hr_client.writeback_status(
            employee_no="EMP20250001",
            event_type="onboarding_completed",
            status="active",
            effective_date="2025-02-01",
        )
        assert result["success"] is True

    def test_writeback_invalid_event(self, hr_client):
        result = hr_client.writeback_status(
            employee_no="EMP20250001",
            event_type="invalid_event",
            status="active",
            effective_date="2025-02-01",
        )
        assert result["success"] is False
        assert "无效的事件类型" in result["message"]

    def test_writeback_offboarding(self, hr_client):
        result = hr_client.writeback_status(
            employee_no="EMP20250001",
            event_type="offboarding_completed",
            status="terminated",
            effective_date="2025-03-01",
        )
        assert result["success"] is True


class TestQueryFromHR:
    """HR系统查询测试"""

    def test_query_existing_employee(self, hr_client):
        # 先同步一个员工
        hr_client.sync_employee({
            "employee_no": "EMP20250001",
            "name": "张三",
            "department_code": "DEPT001",
        })
        emp = hr_client.query_employee_from_hr("EMP20250001")
        assert emp is not None
        assert emp["name"] == "张三"

    def test_query_nonexistent(self, hr_client):
        emp = hr_client.query_employee_from_hr("EMP99999999")
        assert emp is None

    def test_query_department_employees(self, hr_client):
        hr_client.sync_employee({
            "employee_no": "EMP001", "name": "A", "department_code": "DEPT-X"
        })
        hr_client.sync_employee({
            "employee_no": "EMP002", "name": "B", "department_code": "DEPT-X"
        })
        hr_client.sync_employee({
            "employee_no": "EMP003", "name": "C", "department_code": "DEPT-Y"
        })

        employees = hr_client.query_department_employees("DEPT-X")
        assert len(employees) == 2

        employees = hr_client.query_department_employees("DEPT-Z")
        assert len(employees) == 0


class TestSyncLogs:
    """同步日志测试"""

    def test_get_logs(self, hr_client):
        hr_client.sync_employee({"employee_no": "EMP001", "name": "test"})
        hr_client.writeback_status("EMP001", "onboarding_completed", "active", "2025-02-01")

        result = hr_client.get_sync_logs()
        assert result["total"] >= 2

    def test_filter_logs_by_direction(self, hr_client):
        hr_client.sync_employee({"employee_no": "EMP001", "name": "test"})
        hr_client.writeback_status("EMP001", "onboarding_completed", "active", "2025-02-01")

        inbound = hr_client.get_sync_logs(direction="inbound")
        assert inbound["total"] >= 1

        outbound = hr_client.get_sync_logs(direction="outbound")
        assert outbound["total"] >= 1

    def test_filter_logs_by_status(self, hr_client):
        hr_client.sync_employee({"employee_no": "EMP001", "name": "test"})
        # 制造一条失败日志
        hr_client.writeback_status("EMP001", "invalid", "active", "2025-02-01")

        success_logs = hr_client.get_sync_logs(status="success")
        assert success_logs["total"] >= 1

        failed_logs = hr_client.get_sync_logs(status="failed")
        assert failed_logs["total"] >= 1

    def test_pagination(self, hr_client):
        for i in range(5):
            hr_client.sync_employee({"employee_no": f"EMP{i:03d}", "name": f"User{i}"})

        page1 = hr_client.get_sync_logs(page=1, page_size=2)
        assert len(page1["items"]) == 2
        assert page1["total"] >= 5
        assert page1["total_pages"] >= 3


class TestApiKey:
    """API Key验证测试"""

    def test_valid_api_key(self, hr_client):
        assert hr_client.verify_api_key("test-api-key") is True

    def test_invalid_api_key(self, hr_client):
        assert hr_client.verify_api_key("wrong-key") is False
