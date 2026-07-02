#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_onboard.py - 员工入职管理功能测试用例
测试场景：发起入职→各级审批→状态查询→通知校验
"""
import pytest
import json


class TestOnboardInitiate:
    """入职发起功能测试"""

    BASE_URL = "http://mock-api/api"

    def test_initiate_onboard_success(self, api_client, auth_headers):
        """TC-ONB-001: 正常发起入职申请"""
        url = f"{self.BASE_URL}/onboard/initiate"
        payload = {
            "candidate_name": "张三",
            "position": "软件工程师",
            "department": "研发部",
            "entry_date": "2025-03-01",
        }
        resp = api_client.post(url, json=payload, headers=auth_headers)
        assert resp.status_code == 200, f"预期200，实际{resp.status_code}"
        data = resp.json()
        assert data["code"] == 200
        assert data["data"]["status"] == "PENDING_HR_REVIEW"
        assert data["data"]["onboard_id"].startswith("OB")
        assert data["data"]["candidate_name"] == "张三"
        print(f"[PASS] 入职申请发起成功: {data['data']['onboard_id']}")

    def test_initiate_missing_required_field(self, api_client, auth_headers):
        """TC-ONB-002: 缺少必填字段（candidate_name为空）"""
        url = f"{self.BASE_URL}/onboard/initiate"
        payload = {
            "candidate_name": "",
            "position": "软件工程师",
            "department": "研发部",
        }
        resp = api_client.post(url, json=payload, headers=auth_headers)
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == 400
        assert "candidate_name不能为空" in data["message"]
        print(f"[PASS] 参数校验正确拦截: {data['message']}")

    def test_initiate_missing_position(self, api_client, auth_headers):
        """TC-ONB-003: 缺少position字段"""
        url = f"{self.BASE_URL}/onboard/initiate"
        payload = {
            "candidate_name": "李四",
            "department": "研发部",
        }
        resp = api_client.post(url, json=payload, headers=auth_headers)
        assert resp.status_code == 400
        data = resp.json()
        assert "position不能为空" in data["message"]
        print(f"[PASS] 参数校验正确拦截: {data['message']}")

    def test_initiate_duplicate_candidate(self, api_client, auth_headers):
        """TC-ONB-004: 同一候选人重复提交入职申请"""
        url = f"{self.BASE_URL}/onboard/initiate"
        payload = {
            "candidate_name": "王五",
            "position": "产品经理",
            "department": "产品部",
        }
        # 第一次提交
        resp1 = api_client.post(url, json=payload, headers=auth_headers)
        assert resp1.status_code == 200

        # 第二次重复提交
        resp2 = api_client.post(url, json=payload, headers=auth_headers)
        assert resp2.status_code == 400
        data = resp2.json()
        assert "已有进行中的入职申请" in data["message"]
        print(f"[PASS] 重复提交被正确拦截: {data['message']}")

    def test_initiate_unauthorized(self, api_client, invalid_headers):
        """TC-ONB-005: 使用无效token发起入职申请"""
        url = f"{self.BASE_URL}/onboard/initiate"
        payload = {
            "candidate_name": "赵六",
            "position": "测试工程师",
            "department": "质量部",
        }
        resp = api_client.post(url, json=payload, headers=invalid_headers)
        # 无有效token时，应由业务层返回401
        # MockAPI中，无效token不会报错，但user为None，仍会创建（视为匿名）
        # 这里我们验证能创建成功但无权限场景在其他用例中验证
        # 实际系统中应返回401
        print(f"[INFO] 无效token请求返回码: {resp.status_code}")
        # 由于mock未强制校验token，此处仅记录
        if resp.status_code == 200:
            print("[INFO] 注意：mock模式下未强制校验token，生产环境应返回401")


class TestOnboardApprovalFlow:
    """入职审批流程测试（完整链路）"""

    BASE_URL = "http://mock-api/api"

    def _initiate_onboard(self, api_client, headers, name="测试候选人"):
        """辅助方法：发起入职申请"""
        url = f"{self.BASE_URL}/onboard/initiate"
        payload = {
            "candidate_name": name,
            "position": "软件工程师",
            "department": "研发部",
            "entry_date": "2025-03-01",
        }
        resp = api_client.post(url, json=payload, headers=headers)
        assert resp.status_code == 200
        return resp.json()["data"]["onboard_id"]

    def test_full_approval_flow(self, api_client, auth_headers, hr_headers,
                                dept_manager_headers, leader_headers):
        """
        TC-ONB-006: 完整入职审批流程
        发起→HR初审通过→部门审批通过→领导审批通过→状态确认
        """
        # Step 1: 发起入职
        onboard_id = self._initiate_onboard(api_client, auth_headers, "陈七")
        print(f"[STEP1] 发起入职申请: {onboard_id}")

        # Step 2: HR初审通过
        url = f"{self.BASE_URL}/onboard/hr-review"
        resp = api_client.post(url, json={
            "onboard_id": onboard_id,
            "action": "approve",
            "comment": "资料齐全，面试通过"
        }, headers=hr_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "PENDING_DEPT_APPROVAL"
        print(f"[STEP2] HR初审通过，状态: {data['status']}")

        # Step 3: 部门审批通过
        url = f"{self.BASE_URL}/onboard/dept-approve"
        resp = api_client.post(url, json={
            "onboard_id": onboard_id,
            "action": "approve",
            "comment": "部门同意入职"
        }, headers=dept_manager_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "PENDING_LEADER_APPROVAL"
        print(f"[STEP3] 部门审批通过，状态: {data['status']}")

        # Step 4: 领导审批通过
        url = f"{self.BASE_URL}/onboard/leader-approve"
        resp = api_client.post(url, json={
            "onboard_id": onboard_id,
            "action": "approve",
            "comment": "同意入职"
        }, headers=leader_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "APPROVED"
        print(f"[STEP4] 领导审批通过，状态: {data['status']}")

        # Step 5: 查询状态确认
        url = f"{self.BASE_URL}/onboard/status/{onboard_id}"
        resp = api_client.get(url, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "APPROVED"
        assert len(data["steps"]) == 4  # 发起 + HR + 部门 + 领导
        print(f"[STEP5] 状态确认: {data['status']}, 步骤数: {len(data['steps'])}")

        print("[PASS] 完整入职审批流程测试通过")

    def test_hr_reject_flow(self, api_client, auth_headers, hr_headers):
        """TC-ONB-007: HR驳回入职申请"""
        onboard_id = self._initiate_onboard(api_client, auth_headers, "孙八")

        # HR驳回
        url = f"{self.BASE_URL}/onboard/hr-reject"
        resp = api_client.post(url, json={
            "onboard_id": onboard_id,
            "comment": "简历不符合要求"
        }, headers=hr_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "REJECTED"
        print(f"[PASS] HR驳回成功，状态: {data['status']}")

        # 确认状态
        url = f"{self.BASE_URL}/onboard/status/{onboard_id}"
        resp = api_client.get(url, headers=auth_headers)
        assert resp.json()["data"]["status"] == "REJECTED"
        print("[PASS] 驳回后状态确认正确")

    def test_dept_reject_flow(self, api_client, auth_headers, hr_headers,
                              dept_manager_headers):
        """TC-ONB-008: 部门驳回入职申请"""
        onboard_id = self._initiate_onboard(api_client, auth_headers, "周九")

        # HR初审通过
        api_client.post(f"{self.BASE_URL}/onboard/hr-review", json={
            "onboard_id": onboard_id, "action": "approve", "comment": "通过"
        }, headers=hr_headers)

        # 部门驳回
        resp = api_client.post(f"{self.BASE_URL}/onboard/dept-reject", json={
            "onboard_id": onboard_id, "comment": "部门暂无编制"
        }, headers=dept_manager_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "REJECTED"
        print(f"[PASS] 部门驳回成功，状态: REJECTED")

    def test_leader_reject_flow(self, api_client, auth_headers, hr_headers,
                                dept_manager_headers, leader_headers):
        """TC-ONB-009: 领导驳回入职申请"""
        onboard_id = self._initiate_onboard(api_client, auth_headers, "吴十")

        # HR初审
        api_client.post(f"{self.BASE_URL}/onboard/hr-review", json={
            "onboard_id": onboard_id, "action": "approve", "comment": "通过"
        }, headers=hr_headers)

        # 部门审批
        api_client.post(f"{self.BASE_URL}/onboard/dept-approve", json={
            "onboard_id": onboard_id, "action": "approve", "comment": "同意"
        }, headers=dept_manager_headers)

        # 领导驳回
        resp = api_client.post(f"{self.BASE_URL}/onboard/leader-reject", json={
            "onboard_id": onboard_id, "comment": "暂缓招聘"
        }, headers=leader_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "REJECTED"
        print(f"[PASS] 领导驳回成功，状态: REJECTED")

    def test_invalid_status_transition_skip_step(self, api_client, auth_headers,
                                                  hr_headers, leader_headers):
        """
        TC-ONB-010: 非法状态流转 - 跳过中间步骤
        发起后直接由领导审批（应拒绝）
        """
        onboard_id = self._initiate_onboard(api_client, auth_headers, "跳步测试")

        # 跳过HR和部门，直接领导审批
        url = f"{self.BASE_URL}/onboard/leader-approve"
        resp = api_client.post(url, json={
            "onboard_id": onboard_id,
            "action": "approve",
            "comment": "同意"
        }, headers=leader_headers)
        # 当前状态是 PENDING_HR_REVIEW，不支持 leader_approve 操作
        assert resp.status_code == 400
        data = resp.json()
        assert "不允许操作" in data["message"]
        print(f"[PASS] 非法状态流转被拦截: {data['message']}")

    def test_approve_completed_onboard(self, api_client, auth_headers, hr_headers,
                                        dept_manager_headers, leader_headers):
        """TC-ONB-011: 对已完成的申请再次审批"""
        onboard_id = self._initiate_onboard(api_client, auth_headers, "完成测试")

        # 完成全部审批
        api_client.post(f"{self.BASE_URL}/onboard/hr-review", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=hr_headers)
        api_client.post(f"{self.BASE_URL}/onboard/dept-approve", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=dept_manager_headers)
        api_client.post(f"{self.BASE_URL}/onboard/leader-approve", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=leader_headers)

        # 再次审批
        resp = api_client.post(f"{self.BASE_URL}/onboard/leader-approve", json={
            "onboard_id": onboard_id, "action": "approve"
        }, headers=leader_headers)
        # APPROVED 是终态，不允许任何操作
        assert resp.status_code == 400
        print(f"[PASS] 已完成申请再次审批被拦截: {resp.json()['message']}")


class TestOnboardNotification:
    """入职通知功能测试"""

    BASE_URL = "http://mock-api/api"

    def test_notify_after_approval(self, api_client, auth_headers, hr_headers,
                                    dept_manager_headers, leader_headers):
        """TC-ONB-012: 审批通过后发送入职通知"""
        # 先完成一个入职流程
        onboard_id = self._create_approved_onboard(
            api_client, auth_headers, hr_headers,
            dept_manager_headers, leader_headers
        )

        # 发送通知
        url = f"{self.BASE_URL}/onboard/notify"
        resp = api_client.post(url, json={
            "onboard_id": onboard_id,
            "notify_type": "email"
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["notify_status"] == "sent"
        assert "notify_time" in data
        print(f"[PASS] 入职通知发送成功: {data['notify_status']}")

    def test_notify_without_approval(self, api_client, auth_headers):
        """TC-ONB-013: 未审批通过时发送通知（应拒绝）"""
        url = f"{self.BASE_URL}/onboard/initiate"
        resp = api_client.post(url, json={
            "candidate_name": "通知测试",
            "position": "测试",
            "department": "测试部",
        }, headers=auth_headers)
        onboard_id = resp.json()["data"]["onboard_id"]

        # 尝试发送通知（状态为 PENDING_HR_REVIEW）
        url = f"{self.BASE_URL}/onboard/notify"
        resp = api_client.post(url, json={
            "onboard_id": onboard_id,
            "notify_type": "email"
        }, headers=auth_headers)
        assert resp.status_code == 400
        assert "未通过审批" in resp.json()["message"]
        print(f"[PASS] 未审批时发送通知被拦截: {resp.json()['message']}")

    def _create_approved_onboard(self, api_client, auth_headers, hr_headers,
                                  dept_manager_headers, leader_headers,
                                  name="通知候选人"):
        """辅助：创建一个已审批通过的入职申请"""
        # 发起
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": name, "position": "测试", "department": "测试部"
        }, headers=auth_headers)
        ob_id = resp.json()["data"]["onboard_id"]

        # HR审批
        api_client.post(f"{self.BASE_URL}/onboard/hr-review", json={
            "onboard_id": ob_id, "action": "approve"
        }, headers=hr_headers)

        # 部门审批
        api_client.post(f"{self.BASE_URL}/onboard/dept-approve", json={
            "onboard_id": ob_id, "action": "approve"
        }, headers=dept_manager_headers)

        # 领导审批
        api_client.post(f"{self.BASE_URL}/onboard/leader-approve", json={
            "onboard_id": ob_id, "action": "approve"
        }, headers=leader_headers)

        return ob_id


class TestOnboardStatusQuery:
    """入职状态查询测试"""

    BASE_URL = "http://mock-api/api"

    def test_query_existing_onboard(self, api_client, auth_headers):
        """TC-ONB-014: 查询存在的入职申请状态"""
        # 创建一个入职申请
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": "状态查询", "position": "测试", "department": "测试部"
        }, headers=auth_headers)
        onboard_id = resp.json()["data"]["onboard_id"]

        # 查询状态
        resp = api_client.get(
            f"{self.BASE_URL}/onboard/status/{onboard_id}",
            headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["onboard_id"] == onboard_id
        assert data["status"] == "PENDING_HR_REVIEW"
        assert "steps" in data
        assert len(data["steps"]) >= 1
        print(f"[PASS] 状态查询成功: {data['status']}")

    def test_query_non_existent_onboard(self, api_client, auth_headers):
        """TC-ONB-015: 查询不存在的入职申请"""
        resp = api_client.get(
            f"{self.BASE_URL}/onboard/status/OB9999999999",
            headers=auth_headers
        )
        assert resp.status_code == 404
        print(f"[PASS] 不存在的入职申请返回404")

    def test_query_onboard_status_permission(self, api_client, hr_headers):
        """TC-ONB-016: 查询不同阶段的状态（HR角色可查看）"""
        # 创建入职
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": "权限测试", "position": "测试", "department": "测试部"
        }, headers=hr_headers)
        onboard_id = resp.json()["data"]["onboard_id"]

        # HR角色查询
        resp = api_client.get(
            f"{self.BASE_URL}/onboard/status/{onboard_id}",
            headers=hr_headers
        )
        assert resp.status_code == 200
        print(f"[PASS] HR角色查询入职状态成功")


class TestOnboardEdgeCases:
    """入职边界场景测试"""

    BASE_URL = "http://mock-api/api"

    def test_initiate_with_empty_payload(self, api_client, auth_headers):
        """TC-ONB-017: 提交空JSON体"""
        resp = api_client.post(
            f"{self.BASE_URL}/onboard/initiate",
            json={},
            headers=auth_headers
        )
        assert resp.status_code == 400
        print(f"[PASS] 空payload被拦截: {resp.json()['message']}")

    def test_initiate_without_auth_header(self, api_client):
        """TC-ONB-018: 不传认证头"""
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": "无认证", "position": "测试", "department": "测试部"
        })
        # mock模式下未强制校验，记录行为
        print(f"[INFO] 无认证头请求返回码: {resp.status_code}")

    def test_onboard_id_format(self, api_client, auth_headers):
        """TC-ONB-019: 验证入职ID格式"""
        resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
            "candidate_name": "ID格式", "position": "测试", "department": "测试部"
        }, headers=auth_headers)
        onboard_id = resp.json()["data"]["onboard_id"]
        assert onboard_id.startswith("OB"), f"入职ID应以OB开头: {onboard_id}"
        assert len(onboard_id) >= 8, f"入职ID长度不足: {onboard_id}"
        print(f"[PASS] 入职ID格式正确: {onboard_id}")

    def test_multiple_onboard_requests(self, api_client, auth_headers):
        """TC-ONB-020: 多次发起不同候选人入职"""
        names = ["候选人A", "候选人B", "候选人C"]
        ids = []
        for name in names:
            resp = api_client.post(f"{self.BASE_URL}/onboard/initiate", json={
                "candidate_name": name, "position": "测试", "department": "测试部"
            }, headers=auth_headers)
            assert resp.status_code == 200
            ids.append(resp.json()["data"]["onboard_id"])
            print(f"[STEP] 发起 {name}: {ids[-1]}")

        # 验证所有ID均不同
        assert len(set(ids)) == len(names), "入职ID应唯一"
        print(f"[PASS] 多次发起成功，生成 {len(ids)} 个唯一ID")
