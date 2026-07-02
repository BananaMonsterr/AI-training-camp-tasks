#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_resign.py - 员工离职管理功能测试用例
测试场景：离职申请→工作交接→审批→资产归还→状态校验
"""
import pytest


class TestResignApply:
    """离职申请功能测试"""

    BASE_URL = "http://mock-api/api"

    def test_apply_resign_success(self, api_client, employee_headers):
        """TC-RSG-001: 正常提交离职申请"""
        url = f"{self.BASE_URL}/resign/apply"
        payload = {
            "employee_id": "EMP001",
            "employee_name": "赵六",
            "reason": "个人发展",
            "last_working_day": "2025-03-31",
        }
        resp = api_client.post(url, json=payload, headers=employee_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "PENDING_HANDOVER"
        assert data["resign_id"].startswith("RS")
        assert data["current_step"] == "工作交接"
        print(f"[PASS] 离职申请提交成功: {data['resign_id']}")

    def test_apply_resign_missing_reason(self, api_client, employee_headers):
        """TC-RSG-002: 缺少离职原因"""
        url = f"{self.BASE_URL}/resign/apply"
        payload = {
            "employee_id": "EMP002",
            "employee_name": "钱七",
            "reason": "",
        }
        resp = api_client.post(url, json=payload, headers=employee_headers)
        assert resp.status_code == 400
        assert "reason不能为空" in resp.json()["message"]
        print(f"[PASS] 缺少原因被拦截: {resp.json()['message']}")

    def test_apply_resign_duplicate(self, api_client, employee_headers):
        """TC-RSG-003: 重复提交离职申请"""
        url = f"{self.BASE_URL}/resign/apply"
        payload = {
            "employee_id": "EMP003",
            "employee_name": "孙八",
            "reason": "家庭原因",
        }
        # 第一次提交
        resp1 = api_client.post(url, json=payload, headers=employee_headers)
        assert resp1.status_code == 200

        # 重复提交
        resp2 = api_client.post(url, json=payload, headers=employee_headers)
        assert resp2.status_code == 400
        assert "已有进行中的离职申请" in resp2.json()["message"]
        print(f"[PASS] 重复提交被拦截: {resp2.json()['message']}")

    def test_apply_resign_empty_payload(self, api_client, employee_headers):
        """TC-RSG-004: 提交空数据"""
        resp = api_client.post(
            f"{self.BASE_URL}/resign/apply",
            json={},
            headers=employee_headers
        )
        assert resp.status_code == 400
        print(f"[PASS] 空payload被拦截")


class TestResignFullFlow:
    """离职完整流程测试"""

    BASE_URL = "http://mock-api/api"

    def _apply_resign(self, api_client, headers, emp_id="EMP010", name="离职测试"):
        """辅助：提交离职申请"""
        resp = api_client.post(f"{self.BASE_URL}/resign/apply", json={
            "employee_id": emp_id,
            "employee_name": name,
            "reason": "个人发展",
            "last_working_day": "2025-03-31",
        }, headers=headers)
        assert resp.status_code == 200
        return resp.json()["data"]["resign_id"]

    def test_full_resign_flow(self, api_client, employee_headers,
                               dept_manager_headers):
        """
        TC-RSG-005: 完整离职流程
        申请→工作交接→审批→资产归还→状态确认
        """
        # Step 1: 提交离职申请
        resign_id = self._apply_resign(api_client, employee_headers, "EMP011", "周九")
        print(f"[STEP1] 离职申请提交: {resign_id}")

        # Step 2: 工作交接
        url = f"{self.BASE_URL}/resign/handover"
        resp = api_client.post(url, json={
            "resign_id": resign_id,
            "handover_items": [
                {"item": "项目文档", "recipient": "李四"},
                {"item": "代码仓库权限", "recipient": "王五"},
                {"item": "测试账号", "recipient": "管理员"},
            ]
        }, headers=employee_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "PENDING_APPROVAL"
        assert data["current_step"] == "审批中"
        print(f"[STEP2] 工作交接完成，状态: {data['status']}")

        # Step 3: 审批通过
        url = f"{self.BASE_URL}/resign/approve"
        resp = api_client.post(url, json={
            "resign_id": resign_id,
            "action": "approve",
            "comment": "同意离职"
        }, headers=dept_manager_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "PENDING_RETURN_ASSETS"
        assert data["current_step"] == "资产归还"
        print(f"[STEP3] 审批通过，状态: {data['status']}")

        # Step 4: 归还资产
        url = f"{self.BASE_URL}/resign/return-assets"
        resp = api_client.post(url, json={
            "resign_id": resign_id,
            "assets": [
                {"asset_type": "笔记本电脑", "asset_code": "NB-001", "status": "returned"},
                {"asset_type": "工卡", "asset_code": "CARD-001", "status": "returned"},
                {"asset_type": "门禁卡", "asset_code": "KEY-001", "status": "returned"},
            ]
        }, headers=employee_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "COMPLETED"
        assert data["current_step"] == "已完成"
        print(f"[STEP4] 资产归还完成，状态: {data['status']}")

        # Step 5: 查询状态确认
        url = f"{self.BASE_URL}/resign/status/{resign_id}"
        resp = api_client.get(url, headers=employee_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "COMPLETED"
        assert len(data["steps"]) == 4  # 申请+交接+审批+归还
        print(f"[STEP5] 最终状态确认: {data['status']}, 步骤数: {len(data['steps'])}")

        print("[PASS] 完整离职流程测试通过")

    def test_resign_rejected_flow(self, api_client, employee_headers,
                                   dept_manager_headers):
        """TC-RSG-006: 离职申请被驳回"""
        resign_id = self._apply_resign(api_client, employee_headers, "EMP012", "吴十")

        # 工作交接
        api_client.post(f"{self.BASE_URL}/resign/handover", json={
            "resign_id": resign_id,
            "handover_items": [{"item": "文档", "recipient": "张三"}]
        }, headers=employee_headers)

        # 审批驳回
        resp = api_client.post(f"{self.BASE_URL}/resign/reject", json={
            "resign_id": resign_id,
            "action": "reject",
            "comment": "项目未完成，暂不同意离职"
        }, headers=dept_manager_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "REJECTED"
        print(f"[PASS] 离职申请被驳回，状态: {data['status']}")

        # 确认状态
        resp = api_client.get(
            f"{self.BASE_URL}/resign/status/{resign_id}",
            headers=employee_headers
        )
        assert resp.json()["data"]["status"] == "REJECTED"
        print("[PASS] 驳回后状态确认正确")

    def test_resign_approve_without_handover(self, api_client, employee_headers,
                                              dept_manager_headers):
        """TC-RSG-007: 未完成工作交接直接审批（应拒绝）"""
        resign_id = self._apply_resign(api_client, employee_headers, "EMP013", "郑十一")

        # 直接审批（跳过交接）
        resp = api_client.post(f"{self.BASE_URL}/resign/approve", json={
            "resign_id": resign_id,
            "action": "approve"
        }, headers=dept_manager_headers)
        # 当前状态是 PENDING_HANDOVER，不允许审批
        assert resp.status_code == 400
        assert "不允许" in resp.json()["message"]
        print(f"[PASS] 跳过交接直接审批被拦截: {resp.json()['message']}")

    def test_return_assets_without_approval(self, api_client, employee_headers):
        """TC-RSG-008: 未审批直接归还资产（应拒绝）"""
        resign_id = self._apply_resign(api_client, employee_headers, "EMP014", "冯十二")

        # 工作交接
        api_client.post(f"{self.BASE_URL}/resign/handover", json={
            "resign_id": resign_id,
            "handover_items": [{"item": "文档", "recipient": "张三"}]
        }, headers=employee_headers)

        # 直接归还资产（此时状态为 PENDING_APPROVAL，不允许）
        resp = api_client.post(f"{self.BASE_URL}/resign/return-assets", json={
            "resign_id": resign_id,
            "assets": [{"asset_type": "笔记本", "asset_code": "NB-001", "status": "returned"}]
        }, headers=employee_headers)
        assert resp.status_code == 400
        assert "不允许" in resp.json()["message"]
        print(f"[PASS] 未审批直接归还资产被拦截: {resp.json()['message']}")


class TestResignHandover:
    """工作交接功能测试"""

    BASE_URL = "http://mock-api/api"

    def test_handover_empty_items(self, api_client, employee_headers):
        """TC-RSG-009: 工作交接无交接项"""
        # 先申请
        resp = api_client.post(f"{self.BASE_URL}/resign/apply", json={
            "employee_id": "EMP020", "employee_name": "交接测试", "reason": "测试"
        }, headers=employee_headers)
        resign_id = resp.json()["data"]["resign_id"]

        # 空交接项
        resp = api_client.post(f"{self.BASE_URL}/resign/handover", json={
            "resign_id": resign_id,
            "handover_items": []
        }, headers=employee_headers)
        # Mock中允许空列表，状态仍然流转
        assert resp.status_code == 200
        print(f"[INFO] 空交接项请求返回: {resp.status_code}")

    def test_handover_wrong_resign_id(self, api_client, employee_headers):
        """TC-RSG-010: 使用不存在的离职ID进行交接"""
        resp = api_client.post(f"{self.BASE_URL}/resign/handover", json={
            "resign_id": "RS9999999999",
            "handover_items": [{"item": "文档", "recipient": "张三"}]
        }, headers=employee_headers)
        assert resp.status_code == 404
        print(f"[PASS] 不存在的离职ID返回404")


class TestResignReturnAssets:
    """资产归还功能测试"""

    BASE_URL = "http://mock-api/api"

    def _prepare_for_return_assets(self, api_client, employee_headers,
                                    dept_manager_headers, emp_id="EMP030"):
        """辅助：准备到待归还资产状态"""
        resp = api_client.post(f"{self.BASE_URL}/resign/apply", json={
            "employee_id": emp_id, "employee_name": "资产测试", "reason": "测试"
        }, headers=employee_headers)
        resign_id = resp.json()["data"]["resign_id"]

        api_client.post(f"{self.BASE_URL}/resign/handover", json={
            "resign_id": resign_id,
            "handover_items": [{"item": "文档", "recipient": "张三"}]
        }, headers=employee_headers)

        api_client.post(f"{self.BASE_URL}/resign/approve", json={
            "resign_id": resign_id, "action": "approve"
        }, headers=dept_manager_headers)

        return resign_id

    def test_return_assets_success(self, api_client, employee_headers,
                                    dept_manager_headers):
        """TC-RSG-011: 正常归还资产"""
        resign_id = self._prepare_for_return_assets(
            api_client, employee_headers, dept_manager_headers, "EMP031"
        )

        resp = api_client.post(f"{self.BASE_URL}/resign/return-assets", json={
            "resign_id": resign_id,
            "assets": [
                {"asset_type": "笔记本电脑", "asset_code": "NB-002", "status": "returned"},
                {"asset_type": "显示器", "asset_code": "MON-001", "status": "returned"},
            ]
        }, headers=employee_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "COMPLETED"
        assert len(data["returned_assets"]) == 2
        print(f"[PASS] 资产归还成功，状态: {data['status']}")

    def test_return_assets_empty_list(self, api_client, employee_headers,
                                       dept_manager_headers):
        """TC-RSG-012: 归还资产列表为空"""
        resign_id = self._prepare_for_return_assets(
            api_client, employee_headers, dept_manager_headers, "EMP032"
        )

        resp = api_client.post(f"{self.BASE_URL}/resign/return-assets", json={
            "resign_id": resign_id,
            "assets": []
        }, headers=employee_headers)
        assert resp.status_code == 400
        print(f"[PASS] 空资产列表被拦截: {resp.json()['message']}")

    def test_return_assets_no_resign_id(self, api_client, employee_headers):
        """TC-RSG-013: 未提供离职ID"""
        resp = api_client.post(f"{self.BASE_URL}/resign/return-assets", json={
            "assets": [{"asset_type": "笔记本", "asset_code": "NB-003", "status": "returned"}]
        }, headers=employee_headers)
        assert resp.status_code == 400
        assert "resign_id不能为空" in resp.json()["message"]
        print(f"[PASS] 缺少离职ID被拦截")


class TestResignStatusQuery:
    """离职状态查询测试"""

    BASE_URL = "http://mock-api/api"

    def test_query_resign_status(self, api_client, employee_headers):
        """TC-RSG-014: 查询离职申请状态"""
        resp = api_client.post(f"{self.BASE_URL}/resign/apply", json={
            "employee_id": "EMP040", "employee_name": "状态查询", "reason": "测试"
        }, headers=employee_headers)
        resign_id = resp.json()["data"]["resign_id"]

        resp = api_client.get(
            f"{self.BASE_URL}/resign/status/{resign_id}",
            headers=employee_headers
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "PENDING_HANDOVER"
        assert "steps" in data
        print(f"[PASS] 离职状态查询成功: {data['status']}")

    def test_query_non_existent_resign(self, api_client, employee_headers):
        """TC-RSG-015: 查询不存在的离职申请"""
        resp = api_client.get(
            f"{self.BASE_URL}/resign/status/RS9999999999",
            headers=employee_headers
        )
        assert resp.status_code == 404
        print(f"[PASS] 不存在的离职申请返回404")

    def test_query_completed_resign(self, api_client, employee_headers,
                                     dept_manager_headers):
        """TC-RSG-016: 查询已完成的离职申请"""
        # 完成一个离职流程
        resp = api_client.post(f"{self.BASE_URL}/resign/apply", json={
            "employee_id": "EMP041", "employee_name": "完成查询", "reason": "测试"
        }, headers=employee_headers)
        resign_id = resp.json()["data"]["resign_id"]

        api_client.post(f"{self.BASE_URL}/resign/handover", json={
            "resign_id": resign_id, "handover_items": [{"item": "文档", "recipient": "张三"}]
        }, headers=employee_headers)

        api_client.post(f"{self.BASE_URL}/resign/approve", json={
            "resign_id": resign_id, "action": "approve"
        }, headers=dept_manager_headers)

        api_client.post(f"{self.BASE_URL}/resign/return-assets", json={
            "resign_id": resign_id,
            "assets": [{"asset_type": "笔记本", "asset_code": "NB-010", "status": "returned"}]
        }, headers=employee_headers)

        # 查询
        resp = api_client.get(
            f"{self.BASE_URL}/resign/status/{resign_id}",
            headers=employee_headers
        )
        assert resp.json()["data"]["status"] == "COMPLETED"
        print(f"[PASS] 已完成离职申请查询成功")


class TestResignEdgeCases:
    """离职边界场景测试"""

    BASE_URL = "http://mock-api/api"

    def test_resign_without_auth(self, api_client):
        """TC-RSG-017: 无认证提交离职申请"""
        resp = api_client.post(f"{self.BASE_URL}/resign/apply", json={
            "employee_id": "EMP050", "employee_name": "无认证", "reason": "测试"
        })
        print(f"[INFO] 无认证请求返回码: {resp.status_code}")

    def test_multiple_resign_after_completed(self, api_client, employee_headers,
                                              dept_manager_headers):
        """
        TC-RSG-018: 上次离职完成后再次提交
        同一员工，完成离职后可以再次提交
        """
        emp_id = "EMP060"

        # 第一次：完成离职
        resp = api_client.post(f"{self.BASE_URL}/resign/apply", json={
            "employee_id": emp_id, "employee_name": "多次离职", "reason": "第一次"
        }, headers=employee_headers)
        resign_id1 = resp.json()["data"]["resign_id"]

        api_client.post(f"{self.BASE_URL}/resign/handover", json={
            "resign_id": resign_id1, "handover_items": [{"item": "a", "recipient": "b"}]
        }, headers=employee_headers)
        api_client.post(f"{self.BASE_URL}/resign/approve", json={
            "resign_id": resign_id1, "action": "approve"
        }, headers=dept_manager_headers)
        api_client.post(f"{self.BASE_URL}/resign/return-assets", json={
            "resign_id": resign_id1,
            "assets": [{"asset_type": "笔记本", "asset_code": "NB-060", "status": "returned"}]
        }, headers=employee_headers)

        # 第二次：再次提交（应为成功）
        resp = api_client.post(f"{self.BASE_URL}/resign/apply", json={
            "employee_id": emp_id, "employee_name": "多次离职", "reason": "第二次"
        }, headers=employee_headers)
        assert resp.status_code == 200
        resign_id2 = resp.json()["data"]["resign_id"]
        assert resign_id2 != resign_id1
        print(f"[PASS] 同一员工完成离职后可再次提交: {resign_id2}")
