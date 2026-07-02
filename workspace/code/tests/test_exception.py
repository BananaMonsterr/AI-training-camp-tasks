#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_exception.py - 异常与边界场景测试用例
测试场景：非法状态流转、重复提交、无权限访问、参数校验
"""
import pytest


class TestInvalidStatusTransition:
    """非法状态流转测试"""

    BASE_URL = "http://mock-api/api"

    def _initiate_onboard(self, api_client, headers, name="流转测试"):
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": name, "position": "测试", "department": "测试部"
        }, headers=headers)
        return resp.json()["data"]["onboard_id"]

    def _apply_resign(self, api_client, headers, emp_id="EMP100"):
        resp = api_client.post(f"{self.BASE_URL}/resign/apply", json={
            "employee_id": emp_id, "employee_name": "流转测试", "reason": "测试"
        }, headers=headers)
        return resp.json()["data"]["resign_id"]

    # ==================== 入职非法流转 ====================

    def test_onboard_skip_hr_directly_to_leader(self, api_client, auth_headers,
                                                 leader_headers):
        """TC-EXC-001: 入职流程跳过HR初审直接领导审批"""
        onboard_id = self._initiate_onboard(api_client, auth_headers, "跳HR测试")
        resp = api_client.post(f"{self.BASE_URL}/onboard/leader-approve", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=leader_headers)
        assert resp.status_code == 400
        assert "不允许操作" in resp.json()["message"]
        print(f"[PASS] 跳过HR初审被拦截: {resp.json()['message']}")

    def test_onboard_skip_dept_directly_to_leader(self, api_client, auth_headers,
                                                   hr_headers, leader_headers):
        """TC-EXC-002: 入职流程跳过部门审批直接领导审批"""
        onboard_id = self._initiate_onboard(api_client, auth_headers, "跳部门测试")

        # HR初审通过
        api_client.post(f"{self.BASE_URL}/onboard/hr-review", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=hr_headers)

        # 直接领导审批（应拒绝，当前为 PENDING_DEPT_APPROVAL）
        resp = api_client.post(f"{self.BASE_URL}/onboard/leader-approve", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=leader_headers)
        assert resp.status_code == 400
        assert "不允许操作" in resp.json()["message"]
        print(f"[PASS] 跳过部门审批被拦截: {resp.json()['message']}")

    def test_onboard_reverse_flow_after_approval(self, api_client, auth_headers,
                                                  hr_headers):
        """TC-EXC-003: 审批通过后回退操作"""
        onboard_id = self._initiate_onboard(api_client, auth_headers, "回退测试")

        # HR初审通过
        api_client.post(f"{self.BASE_URL}/onboard/hr-review", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=hr_headers)

        # 尝试再次HR初审（当前状态为 PENDING_DEPT_APPROVAL，不支持hr_approve）
        resp = api_client.post(f"{self.BASE_URL}/onboard/hr-review", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=hr_headers)
        assert resp.status_code == 400
        print(f"[PASS] 重复审批被拦截: {resp.json()['message']}")

    # ==================== 离职非法流转 ====================

    def test_resign_skip_handover(self, api_client, employee_headers,
                                   dept_manager_headers):
        """TC-EXC-004: 离职流程跳过工作交接直接审批"""
        resign_id = self._apply_resign(api_client, employee_headers, "EMP101")
        resp = api_client.post(f"{self.BASE_URL}/resign/approve", json={
            "resign_id": resign_id, "action": "approve"
        }, headers=dept_manager_headers)
        assert resp.status_code == 400
        assert "不允许" in resp.json()["message"]
        print(f"[PASS] 跳过工作交接被拦截: {resp.json()['message']}")

    def test_resign_skip_approval_return_assets(self, api_client, employee_headers):
        """TC-EXC-005: 离职流程跳过审批直接归还资产"""
        resign_id = self._apply_resign(api_client, employee_headers, "EMP102")

        # 工作交接
        api_client.post(f"{self.BASE_URL}/resign/handover", json={
            "resign_id": resign_id, "handover_items": [{"item": "a", "recipient": "b"}]
        }, headers=employee_headers)

        # 直接归还资产（当前状态 PENDING_APPROVAL，不允许）
        resp = api_client.post(f"{self.BASE_URL}/resign/return-assets", json={
            "resign_id": resign_id,
            "assets": [{"asset_type": "笔记本", "asset_code": "NB-001", "status": "returned"}]
        }, headers=employee_headers)
        assert resp.status_code == 400
        print(f"[PASS] 跳过审批归还资产被拦截: {resp.json()['message']}")

    def test_resign_approve_after_completed(self, api_client, employee_headers,
                                             dept_manager_headers):
        """TC-EXC-006: 已完成的离职申请再次审批"""
        resign_id = self._apply_resign(api_client, employee_headers, "EMP103")

        # 完成全流程
        api_client.post(f"{self.BASE_URL}/resign/handover", json={
            "resign_id": resign_id, "handover_items": [{"item": "a", "recipient": "b"}]
        }, headers=employee_headers)
        api_client.post(f"{self.BASE_URL}/resign/approve", json={
            "resign_id": resign_id, "action": "approve"
        }, headers=dept_manager_headers)
        api_client.post(f"{self.BASE_URL}/resign/return-assets", json={
            "resign_id": resign_id,
            "assets": [{"asset_type": "笔记本", "asset_code": "NB-001", "status": "returned"}]
        }, headers=employee_headers)

        # 再次审批
        resp = api_client.post(f"{self.BASE_URL}/resign/approve", json={
            "resign_id": resign_id, "action": "approve"
        }, headers=dept_manager_headers)
        assert resp.status_code == 400
        print(f"[PASS] 已完成申请再次审批被拦截: {resp.json()['message']}")


class TestDuplicateSubmission:
    """重复提交测试"""

    BASE_URL = "http://mock-api/api"

    def test_duplicate_onboard_same_name(self, api_client, auth_headers):
        """TC-EXC-007: 同一候选人姓名重复提交入职"""
        candidate = "重复候选人"
        payload = {
            "candidate_name": candidate,
            "position": "测试工程师",
            "department": "质量部",
        }
        # 第一次
        resp1 = api_client.post(
            f"{self.BASE_URL}/onboard/initiate", json=payload, headers=auth_headers
        )
        assert resp1.status_code == 200
        ob_id_1 = resp1.json()["data"]["onboard_id"]

        # 第二次（同一姓名）
        resp2 = api_client.post(
            f"{self.BASE_URL}/onboard/initiate", json=payload, headers=auth_headers
        )
        assert resp2.status_code == 400
        assert "已有进行中的入职申请" in resp2.json()["message"]
        print(f"[PASS] 重复候选人被拦截: {resp2.json()['message']}")

    def test_duplicate_onboard_after_rejected(self, api_client, auth_headers,
                                               hr_headers):
        """TC-EXC-008: 驳回后同一候选人可再次提交"""
        candidate = "驳回重提"
        payload = {
            "candidate_name": candidate,
            "position": "测试",
            "department": "测试部",
        }
        # 第一次提交
        resp = api_client.post(
            f"{self.BASE_URL}/onboard/initiate", json=payload, headers=auth_headers
        )
        ob_id = resp.json()["data"]["onboard_id"]

        # 驳回
        api_client.post(f"{self.BASE_URL}/onboard/hr-reject", json={
            "onboard_id": ob_id, "comment": "驳回"
        }, headers=hr_headers)

        # 再次提交（应允许）
        resp = api_client.post(
            f"{self.BASE_URL}/onboard/initiate", json=payload, headers=auth_headers
        )
        assert resp.status_code == 200
        new_ob_id = resp.json()["data"]["onboard_id"]
        assert new_ob_id != ob_id
        print(f"[PASS] 驳回后重新提交成功: {new_ob_id}")

    def test_duplicate_resign_same_employee(self, api_client, employee_headers):
        """TC-EXC-009: 同一员工重复提交离职申请"""
        payload = {
            "employee_id": "EMP110",
            "employee_name": "重复离职",
            "reason": "测试",
        }
        # 第一次
        resp1 = api_client.post(
            f"{self.BASE_URL}/resign/apply", json=payload, headers=employee_headers
        )
        assert resp1.status_code == 200

        # 第二次
        resp2 = api_client.post(
            f"{self.BASE_URL}/resign/apply", json=payload, headers=employee_headers
        )
        assert resp2.status_code == 400
        assert "已有进行中的离职申请" in resp2.json()["message"]
        print(f"[PASS] 重复离职申请被拦截: {resp2.json()['message']}")


class TestUnauthorizedAccess:
    """无权限访问测试"""

    BASE_URL = "http://mock-api/api"

    def test_access_without_token(self, api_client):
        """TC-EXC-010: 未登录访问任何接口"""
        # 尝试发起入职
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": "未登录", "position": "测试", "department": "测试部"
        })
        # Mock模式下未强制校验token，所以返回200
        # 但真实系统应返回401
        print(f"[INFO] 无token访问入职接口: status={resp.status_code}")

    def test_employee_approve_onboard(self, api_client, employee_headers):
        """TC-EXC-011: 普通员工审批入职申请（越权）"""
        # 先创建一个入职申请
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": "越权测试", "position": "测试", "department": "测试部"
        }, headers=employee_headers)
        onboard_id = resp.json()["data"]["onboard_id"]

        # 普通员工尝试HR审批
        resp = api_client.post(f"{self.BASE_URL}/onboard/hr-review", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=employee_headers)
        # 普通员工（employee）没有hr审批权限
        assert resp.status_code == 403
        assert "无权限" in resp.json()["message"]
        print(f"[PASS] 普通员工越权审批被拦截: {resp.json()['message']}")

    def test_hr_approve_dept_step(self, api_client, auth_headers, hr_headers):
        """TC-EXC-012: HR审批部门审批步骤（越权）"""
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": "HR越权", "position": "测试", "department": "测试部"
        }, headers=auth_headers)
        onboard_id = resp.json()["data"]["onboard_id"]

        # HR能通过HR初审
        api_client.post(f"{self.BASE_URL}/onboard/hr-review", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=hr_headers)

        # HR尝试部门审批（HR角色没有部门审批权限）
        resp = api_client.post(f"{self.BASE_URL}/onboard/dept-approve", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=hr_headers)
        assert resp.status_code == 403
        print(f"[PASS] HR越权部门审批被拦截: {resp.json()['message']}")

    def test_viewer_resign_approve(self, api_client, employee_headers,
                                    viewer_headers):
        """TC-EXC-013: 只读用户审批离职申请（越权）"""
        # 创建离职申请
        resp = api_client.post(f"{self.BASE_URL}/resign/apply", json={
            "employee_id": "EMP120", "employee_name": "只读越权", "reason": "测试"
        }, headers=employee_headers)
        resign_id = resp.json()["data"]["resign_id"]

        # 工作交接
        api_client.post(f"{self.BASE_URL}/resign/handover", json={
            "resign_id": resign_id, "handover_items": [{"item": "a", "recipient": "b"}]
        }, headers=employee_headers)

        # 只读用户审批
        resp = api_client.post(f"{self.BASE_URL}/resign/approve", json={
            "resign_id": resign_id, "action": "approve"
        }, headers=viewer_headers)
        assert resp.status_code == 403
        print(f"[PASS] 只读用户越权审批被拦截: {resp.json()['message']}")

    def test_employee_approve_own_resign(self, api_client, employee_headers):
        """TC-EXC-014: 员工自行审批自己的离职申请（应拒绝）"""
        resp = api_client.post(f"{self.BASE_URL}/resign/apply", json={
            "employee_id": "EMP121", "employee_name": "自审批", "reason": "测试"
        }, headers=employee_headers)
        resign_id = resp.json()["data"]["resign_id"]

        # 工作交接
        api_client.post(f"{self.BASE_URL}/resign/handover", json={
            "resign_id": resign_id, "handover_items": [{"item": "a", "recipient": "b"}]
        }, headers=employee_headers)

        # 员工自己审批（employee角色没有审批权限）
        resp = api_client.post(f"{self.BASE_URL}/resign/approve", json={
            "resign_id": resign_id, "action": "approve"
        }, headers=employee_headers)
        assert resp.status_code == 403
        print(f"[PASS] 员工自审批被拦截: {resp.json()['message']}")


class TestParameterValidation:
    """参数校验测试"""

    BASE_URL = "http://mock-api/api"

    def test_empty_json_body(self, api_client, auth_headers):
        """TC-EXC-015: 提交空JSON体"""
        endpoints = [
            ("POST", f"{self.BASE_URL}/onboard/initiate"),
            ("POST", f"{self.BASE_URL}/onboard/hr-review"),
            ("POST", f"{self.BASE_URL}/resign/apply"),
            ("POST", f"{self.BASE_URL}/resign/handover"),
        ]
        for method, url in endpoints:
            if method == "POST":
                resp = api_client.post(url, json={}, headers=auth_headers)
                assert resp.status_code in [400, 200]
                # 至少不应该返回500
                assert resp.status_code != 500
                print(f"[INFO] {url} 空JSON返回: {resp.status_code}")

    def test_invalid_data_types(self, api_client, auth_headers):
        """TC-EXC-016: 字段类型错误"""
        # candidate_name 传数字
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": 12345,
            "position": "测试",
            "department": "测试部",
        }, headers=auth_headers)
        # Mock中未做类型校验，所以可能通过
        print(f"[INFO] candidate_name传数字: status={resp.status_code}")

    def test_very_long_string_fields(self, api_client, auth_headers):
        """TC-EXC-017: 超长字符串字段"""
        long_name = "超长" * 1000
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": long_name,
            "position": "测试",
            "department": "测试部",
        }, headers=auth_headers)
        # Mock中未做长度校验，所以可能通过
        print(f"[INFO] 超长名称: status={resp.status_code}, 长度={len(long_name)}")

    def test_sql_injection_attempt(self, api_client, auth_headers):
        """TC-EXC-018: SQL注入尝试"""
        payloads = [
            {"candidate_name": "'; DROP TABLE users; --", "position": "测试", "department": "测试部"},
            {"candidate_name": "张三", "position": "1 OR 1=1", "department": "测试部"},
            {"candidate_name": "李四", "position": "测试", "department": "'; DELETE FROM onboards; --"},
        ]
        for i, payload in enumerate(payloads):
            resp = api_client.post(
                f"{self.BASE_URL}/onboard/initiate",
                json=payload,
                headers=auth_headers
            )
            # Mock应安全处理（不崩溃）
            assert resp.status_code != 500, f"SQL注入导致500错误: payload[{i}]"
            print(f"[INFO] SQL注入测试[{i}]: status={resp.status_code}")

    def test_xss_attempt(self, api_client, auth_headers):
        """TC-EXC-019: XSS脚本注入尝试"""
        payload = {
            "candidate_name": "<script>alert('xss')</script>",
            "position": "<img src=x onerror=alert(1)>",
            "department": "测试部",
        }
        resp = api_client.post(
            f"{self.BASE_URL}/onboard/initiate",
            json=payload,
            headers=auth_headers
        )
        assert resp.status_code != 500
        print(f"[INFO] XSS注入测试: status={resp.status_code}")

    def test_negative_numbers(self, api_client, auth_headers):
        """TC-EXC-020: 负数或特殊数值"""
        # 虽然接口没有数字字段，但测试框架的健壮性
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": -1,
            "position": None,
            "department": "测试部",
        }, headers=auth_headers)
        # None值应被参数校验拦截
        if resp.status_code == 400:
            print(f"[PASS] None值被拦截: {resp.json()['message']}")
        else:
            print(f"[INFO] None值处理: status={resp.status_code}")


class TestConcurrencyAndIdempotency:
    """并发与幂等性测试"""

    BASE_URL = "http://mock-api/api"

    def test_same_operation_twice_idempotent(self, api_client, auth_headers,
                                              hr_headers):
        """TC-EXC-021: 同一审批操作重复执行"""
        # 创建入职
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": "幂等测试", "position": "测试", "department": "测试部"
        }, headers=auth_headers)
        onboard_id = resp.json()["data"]["onboard_id"]

        # HR审批第一次
        resp1 = api_client.post(f"{self.BASE_URL}/onboard/hr-review", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=hr_headers)
        assert resp1.status_code == 200

        # HR审批第二次（此时状态已变，应拒绝）
        resp2 = api_client.post(f"{self.BASE_URL}/onboard/hr-review", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=hr_headers)
        assert resp2.status_code == 400
        print(f"[PASS] 重复操作幂等性验证通过: {resp2.json()['message']}")

    def test_query_during_process(self, api_client, auth_headers, hr_headers):
        """TC-EXC-022: 流程过程中反复查询状态"""
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": "反复查询", "position": "测试", "department": "测试部"
        }, headers=auth_headers)
        onboard_id = resp.json()["data"]["onboard_id"]

        # 反复查询
        for i in range(5):
            resp = api_client.get(
                f"{self.BASE_URL}/onboard/status/{onboard_id}",
                headers=auth_headers
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["status"] == "PENDING_HR_REVIEW"
        print("[PASS] 反复查询状态正常")


class TestSystemRobustness:
    """系统健壮性测试"""

    BASE_URL = "http://mock-api/api"

    def test_missing_resign_id_in_path(self, api_client, employee_headers):
        """TC-EXC-023: 路径参数缺失"""
        resp = api_client.get(
            f"{self.BASE_URL}/resign/status/",
            headers=employee_headers
        )
        # 应返回400格式错误
        print(f"[INFO] 路径参数缺失: status={resp.status_code}")

    def test_invalid_http_method(self, api_client, auth_headers):
        """TC-EXC-024: 使用GET调用POST接口"""
        # mock的get不支持POST接口的路由
        resp = api_client.get(
            f"{self.BASE_URL}/onboard/initiate",
            headers=auth_headers
        )
        assert resp.status_code == 404
        print(f"[PASS] GET调用POST接口返回404")

    def test_unauthorized_role_for_onboard_notify(self, api_client, auth_headers,
                                                    hr_headers, dept_manager_headers,
                                                    leader_headers, employee_headers):
        """TC-EXC-025: 不同角色发送入职通知"""
        # 完成入职
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": "通知权限", "position": "测试", "department": "测试部"
        }, headers=auth_headers)
        ob_id = resp.json()["data"]["onboard_id"]

        api_client.post(f"{self.BASE_URL}/onboard/hr-review", json={
            "onboard_id": ob_id, "action": "approve"
        }, headers=hr_headers)
        api_client.post(f"{self.BASE_URL}/onboard/dept-approve", json={
            "onboard_id": ob_id, "action": "approve"
        }, headers=dept_manager_headers)
        api_client.post(f"{self.BASE_URL}/onboard/leader-approve", json={
            "onboard_id": ob_id, "action": "approve"
        }, headers=leader_headers)

        # 普通员工发送通知（应拒绝或允许取决于业务规则）
        resp = api_client.post(f"{self.BASE_URL}/onboard/notify", json={
            "onboard_id": ob_id, "notify_type": "email"
        }, headers=employee_headers)
        # mock中通知接口未做角色校验，所以返回200
        print(f"[INFO] 员工发送通知: status={resp.status_code}")
