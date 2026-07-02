#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
conftest.py - 员工入离职管理系统 测试夹具与Mock后端
提供API客户端封装、Mock后端模拟、测试数据fixture
"""
import pytest
import json
import re
from urllib.parse import urlparse, parse_qs


class MockResponse:
    """模拟 requests.Response """

    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.headers = {"Content-Type": "application/json"}
        self.reason = "OK" if self.ok else "Error"
        self.url = ""
        self.encoding = "utf-8"

    def json(self):
        return self._json_data

    @property
    def text(self):
        return json.dumps(self._json_data, ensure_ascii=False)

    def __repr__(self):
        return f"<MockResponse [{self.status_code}]>"


class MockAPI:
    """
    模拟后端API，维护状态机来实现入职/离职业务流程
    每个测试用例执行前应调用 reset() 重置状态
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """重置所有数据"""
        # 入职申请数据存储：onboard_id -> {status, candidate_info, steps, notifications}
        self.onboards = {}
        # 离职申请数据存储：resign_id -> {status, employee_info, steps, assets}
        self.resigns = {}
        # 用户与令牌
        self.users = {
            "admin": {
                "password": "123456",
                "role": "admin",
                "token": "token_admin_001",
                "name": "系统管理员",
            },
            "hr_user": {
                "password": "123456",
                "role": "hr",
                "token": "token_hr_001",
                "name": "HR张经理",
            },
            "dept_manager": {
                "password": "123456",
                "role": "dept_manager",
                "token": "token_dept_001",
                "name": "部门李经理",
            },
            "leader": {
                "password": "123456",
                "role": "leader",
                "token": "token_leader_001",
                "name": "王总裁",
            },
            "employee": {
                "password": "123456",
                "role": "employee",
                "token": "token_emp_001",
                "name": "普通员工赵六",
            },
            "viewer": {
                "password": "123456",
                "role": "viewer",
                "token": "token_viewer_001",
                "name": "只读用户",
            },
        }
        # token -> user_key 映射
        self._token_map = {}
        for key, user in self.users.items():
            self._token_map[user["token"]] = key

        # 通知记录
        self.notifications = []
        # 自增计数器
        self.onboard_counter = 0
        self.resign_counter = 0

        # ------------------- 入职状态机定义 -------------------
        # 合法状态流转：当前状态 -> 可执行的操作 -> 下一状态
        self.onboard_status_machine = {
            "DRAFT": {"submit": "PENDING_HR_REVIEW"},
            "PENDING_HR_REVIEW": {"hr_approve": "PENDING_DEPT_APPROVAL", "hr_reject": "REJECTED"},
            "PENDING_DEPT_APPROVAL": {"dept_approve": "PENDING_LEADER_APPROVAL", "dept_reject": "REJECTED"},
            "PENDING_LEADER_APPROVAL": {"leader_approve": "APPROVED", "leader_reject": "REJECTED"},
            "APPROVED": {},  # 终态
            "REJECTED": {},  # 终态
        }

        # ------------------- 离职状态机定义 -------------------
        self.resign_status_machine = {
            "DRAFT": {"submit": "PENDING_HANDOVER"},
            "PENDING_HANDOVER": {"handover": "PENDING_APPROVAL"},
            "PENDING_APPROVAL": {"approve": "PENDING_RETURN_ASSETS", "reject": "REJECTED"},
            "PENDING_RETURN_ASSETS": {"return_assets": "COMPLETED"},
            "COMPLETED": {},
            "REJECTED": {},
        }

        # 操作所需的角色权限
        self.onboard_permissions = {
            "submit": ["admin", "hr"],
            "hr_approve": ["hr", "admin"],
            "hr_reject": ["hr", "admin"],
            "dept_approve": ["dept_manager", "admin"],
            "dept_reject": ["dept_manager", "admin"],
            "leader_approve": ["leader", "admin"],
            "leader_reject": ["leader", "admin"],
        }

        self.resign_permissions = {
            "submit": ["employee", "admin"],
            "handover": ["employee", "admin"],
            "approve": ["dept_manager", "leader", "admin"],
            "reject": ["dept_manager", "leader", "admin"],
            "return_assets": ["admin", "hr"],
        }

    # ---------- 工具方法 ----------

    def _get_user_by_token(self, headers):
        """从请求头中提取token并返回用户信息"""
        if not headers:
            return None
        auth = headers.get("Authorization", "")
        token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else auth
        user_key = self._token_map.get(token)
        if user_key:
            return self.users[user_key]
        # 也支持直接传token
        for key, user in self.users.items():
            if user["token"] == token:
                return user
        return None

    def _check_role(self, user, allowed_roles):
        """检查用户角色是否有权限"""
        if user is None:
            return False
        return user["role"] in allowed_roles

    def _make_onboard_id(self):
        self.onboard_counter += 1
        return f"OB{20250228:04d}{self.onboard_counter:04d}"

    def _make_resign_id(self):
        self.resign_counter += 1
        return f"RS{20250228:04d}{self.resign_counter:04d}"

    def _parse_path(self, url):
        """解析URL，返回路径部分和路径参数"""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        return path

    # ==================== 入职API处理方法 ====================

    def _handle_onboard_initiate(self, json_data, user):
        """发起入职申请"""
        # 参数校验
        required_fields = ["candidate_name", "position", "department"]
        for field in required_fields:
            if field not in json_data or not json_data[field]:
                return MockResponse(
                    {"code": 400, "message": f"参数校验失败：{field}不能为空"},
                    status_code=400,
                )

        candidate_name = json_data["candidate_name"]

        # 检查重复提交（同一候选人已有进行中的申请）
        for ob_id, ob in self.onboards.items():
            if ob["candidate_name"] == candidate_name and ob["status"] not in [
                "APPROVED",
                "REJECTED",
            ]:
                return MockResponse(
                    {"code": 400, "message": "该候选人已有进行中的入职申请"},
                    status_code=400,
                )

        # 创建入职申请
        ob_id = self._make_onboard_id()
        self.onboards[ob_id] = {
            "onboard_id": ob_id,
            "candidate_name": candidate_name,
            "position": json_data["position"],
            "department": json_data["department"],
            "entry_date": json_data.get("entry_date", ""),
            "status": "PENDING_HR_REVIEW",
            "current_step": "HR初审",
            "created_by": user["name"] if user else "unknown",
            "steps": [
                {"step": "发起申请", "operator": user["name"] if user else "unknown", "status": "done",
                 "time": "2025-02-28 09:00:00"}
            ],
        }

        return MockResponse({
            "code": 200,
            "data": {
                "onboard_id": ob_id,
                "candidate_name": candidate_name,
                "status": "PENDING_HR_REVIEW",
                "current_step": "HR初审",
            }
        })

    def _handle_onboard_review(self, path, json_data, user, action_type):
        """处理入职审批（hr_approve/hr_reject/dept_approve/dept_reject/leader_approve/leader_reject）"""
        onboard_id = json_data.get("onboard_id")
        if not onboard_id:
            return MockResponse(
                {"code": 400, "message": "参数校验失败：onboard_id不能为空"},
                status_code=400,
            )

        if onboard_id not in self.onboards:
            return MockResponse(
                {"code": 404, "message": f"入职申请 {onboard_id} 不存在"},
                status_code=404,
            )

        ob = self.onboards[onboard_id]
        current_status = ob["status"]
        action = json_data.get("action", "")
        comment = json_data.get("comment", "")

        # 检查权限
        # 根据action_type映射到操作名
        action_map = {
            "hr_approve": "hr_approve",
            "hr_reject": "hr_reject",
            "dept_approve": "dept_approve",
            "dept_reject": "dept_reject",
            "leader_approve": "leader_approve",
            "leader_reject": "leader_reject",
        }
        operation = action_map.get(action_type)
        if not operation:
            return MockResponse({"code": 400, "message": "非法操作"}, status_code=400)

        allowed_roles = self.onboard_permissions.get(operation, [])
        if not self._check_role(user, allowed_roles):
            return MockResponse(
                {"code": 403, "message": "无权限执行此操作"},
                status_code=403,
            )

        # 检查状态流转是否合法
        if current_status not in self.onboard_status_machine:
            return MockResponse(
                {"code": 400, "message": f"当前状态'{current_status}'不允许任何操作"},
                status_code=400,
            )

        valid_actions = self.onboard_status_machine[current_status]
        if operation not in valid_actions:
            return MockResponse(
                {"code": 400, "message": f"当前状态'{current_status}'不允许操作'{operation}'"},
                status_code=400,
            )

        # 执行状态流转
        next_status = valid_actions[operation]

        step_name_map = {
            "hr_approve": "HR初审通过",
            "hr_reject": "HR驳回",
            "dept_approve": "部门审批通过",
            "dept_reject": "部门驳回",
            "leader_approve": "领导审批通过",
            "leader_reject": "领导驳回",
        }

        ob["status"] = next_status
        ob["steps"].append({
            "step": step_name_map.get(operation, operation),
            "operator": user["name"] if user else "unknown",
            "comment": comment,
            "status": "done",
            "time": "2025-02-28 10:00:00",
        })

        # 更新当前步骤描述
        step_desc = {
            "PENDING_HR_REVIEW": "HR初审",
            "PENDING_DEPT_APPROVAL": "部门审批",
            "PENDING_LEADER_APPROVAL": "领导审批",
            "APPROVED": "已完成",
            "REJECTED": "已驳回",
        }
        ob["current_step"] = step_desc.get(next_status, "未知")

        return MockResponse({
            "code": 200,
            "data": {
                "onboard_id": onboard_id,
                "status": next_status,
                "current_step": ob["current_step"],
            }
        })

    def _handle_onboard_status(self, path, user):
        """查询入职申请状态"""
        # 从路径中提取 onboard_id: /api/onboard/status/{onboard_id}
        match = re.search(r"/api/onboard/status/(\S+)", path)
        if not match:
            return MockResponse({"code": 400, "message": "请求路径格式错误"}, status_code=400)

        onboard_id = match.group(1)
        if onboard_id not in self.onboards:
            return MockResponse(
                {"code": 404, "message": f"入职申请 {onboard_id} 不存在"},
                status_code=404,
            )

        ob = self.onboards[onboard_id]
        return MockResponse({
            "code": 200,
            "data": {
                "onboard_id": onboard_id,
                "candidate_name": ob["candidate_name"],
                "status": ob["status"],
                "current_step": ob["current_step"],
                "steps": ob["steps"],
            }
        })

    def _handle_onboard_notify(self, json_data, user):
        """发送入职通知"""
        onboard_id = json_data.get("onboard_id")
        notify_type = json_data.get("notify_type", "email")

        if not onboard_id:
            return MockResponse(
                {"code": 400, "message": "参数校验失败：onboard_id不能为空"},
                status_code=400,
            )

        if onboard_id not in self.onboards:
            return MockResponse(
                {"code": 404, "message": f"入职申请 {onboard_id} 不存在"},
                status_code=404,
            )

        ob = self.onboards[onboard_id]
        if ob["status"] != "APPROVED":
            return MockResponse(
                {"code": 400, "message": "入职申请未通过审批，无法发送通知"},
                status_code=400,
            )

        # 记录通知
        notify_record = {
            "onboard_id": onboard_id,
            "candidate_name": ob["candidate_name"],
            "notify_type": notify_type,
            "status": "sent",
            "notify_time": "2025-02-28 11:00:00",
        }
        self.notifications.append(notify_record)
        ob.setdefault("notifications", []).append(notify_record)

        return MockResponse({
            "code": 200,
            "data": {
                "onboard_id": onboard_id,
                "notify_status": "sent",
                "notify_time": "2025-02-28 11:00:00",
                "notify_type": notify_type,
            }
        })

    # ==================== 离职API处理方法 ====================

    def _handle_resign_apply(self, json_data, user):
        """提交离职申请"""
        required_fields = ["employee_id", "reason"]
        for field in required_fields:
            if field not in json_data or not json_data[field]:
                return MockResponse(
                    {"code": 400, "message": f"参数校验失败：{field}不能为空"},
                    status_code=400,
                )

        employee_id = json_data["employee_id"]

        # 检查是否有进行中的离职申请
        for rs_id, rs in self.resigns.items():
            if rs["employee_id"] == employee_id and rs["status"] not in ["COMPLETED", "REJECTED"]:
                return MockResponse(
                    {"code": 400, "message": "该员工已有进行中的离职申请"},
                    status_code=400,
                )

        rs_id = self._make_resign_id()
        self.resigns[rs_id] = {
            "resign_id": rs_id,
            "employee_id": employee_id,
            "employee_name": json_data.get("employee_name", ""),
            "reason": json_data["reason"],
            "last_working_day": json_data.get("last_working_day", ""),
            "status": "PENDING_HANDOVER",
            "current_step": "工作交接",
            "created_by": user["name"] if user else "unknown",
            "steps": [
                {"step": "提交离职申请", "operator": user["name"] if user else "unknown", "status": "done",
                 "time": "2025-02-28 09:00:00"}
            ],
            "assets_returned": [],
        }

        return MockResponse({
            "code": 200,
            "data": {
                "resign_id": rs_id,
                "status": "PENDING_HANDOVER",
                "current_step": "工作交接",
            }
        })

    def _handle_resign_handover(self, json_data, user):
        """工作交接"""
        resign_id = json_data.get("resign_id")
        if not resign_id:
            return MockResponse(
                {"code": 400, "message": "参数校验失败：resign_id不能为空"},
                status_code=400,
            )

        if resign_id not in self.resigns:
            return MockResponse(
                {"code": 404, "message": f"离职申请 {resign_id} 不存在"},
                status_code=404,
            )

        rs = self.resigns[resign_id]
        if rs["status"] != "PENDING_HANDOVER":
            return MockResponse(
                {"code": 400, "message": f"当前状态'{rs['status']}'不允许工作交接操作"},
                status_code=400,
            )

        handover_items = json_data.get("handover_items", [])
        rs["handover_items"] = handover_items
        rs["status"] = "PENDING_APPROVAL"
        rs["current_step"] = "审批中"
        rs["steps"].append({
            "step": "工作交接完成",
            "operator": user["name"] if user else "unknown",
            "items_count": len(handover_items),
            "status": "done",
            "time": "2025-02-28 10:00:00",
        })

        return MockResponse({
            "code": 200,
            "data": {
                "resign_id": resign_id,
                "status": "PENDING_APPROVAL",
                "current_step": "审批中",
                "handover_items": handover_items,
            }
        })

    def _handle_resign_approve_or_reject(self, json_data, user, is_approve):
        """审批离职（通过或驳回）"""
        resign_id = json_data.get("resign_id")
        if not resign_id:
            return MockResponse(
                {"code": 400, "message": "参数校验失败：resign_id不能为空"},
                status_code=400,
            )

        if resign_id not in self.resigns:
            return MockResponse(
                {"code": 404, "message": f"离职申请 {resign_id} 不存在"},
                status_code=404,
            )

        rs = self.resigns[resign_id]
        if rs["status"] != "PENDING_APPROVAL":
            return MockResponse(
                {"code": 400, "message": f"当前状态'{rs['status']}'不允许审批操作"},
                status_code=400,
            )

        # 权限检查
        allowed_roles = self.resign_permissions.get("approve", [])
        if not self._check_role(user, allowed_roles):
            return MockResponse(
                {"code": 403, "message": "无权限执行此操作"},
                status_code=403,
            )

        comment = json_data.get("comment", "")

        if is_approve:
            rs["status"] = "PENDING_RETURN_ASSETS"
            rs["current_step"] = "资产归还"
            step_name = "审批通过"
        else:
            rs["status"] = "REJECTED"
            rs["current_step"] = "已驳回"
            step_name = "审批驳回"

        rs["steps"].append({
            "step": step_name,
            "operator": user["name"] if user else "unknown",
            "comment": comment,
            "status": "done",
            "time": "2025-02-28 11:00:00",
        })

        return MockResponse({
            "code": 200,
            "data": {
                "resign_id": resign_id,
                "status": rs["status"],
                "current_step": rs["current_step"],
            }
        })

    def _handle_resign_return_assets(self, json_data, user):
        """归还资产"""
        resign_id = json_data.get("resign_id")
        if not resign_id:
            return MockResponse(
                {"code": 400, "message": "参数校验失败：resign_id不能为空"},
                status_code=400,
            )

        if resign_id not in self.resigns:
            return MockResponse(
                {"code": 404, "message": f"离职申请 {resign_id} 不存在"},
                status_code=404,
            )

        rs = self.resigns[resign_id]
        if rs["status"] != "PENDING_RETURN_ASSETS":
            return MockResponse(
                {"code": 400, "message": f"当前状态'{rs['status']}'不允许资产归还操作"},
                status_code=400,
            )

        assets = json_data.get("assets", [])
        if not assets:
            return MockResponse(
                {"code": 400, "message": "参数校验失败：assets不能为空"},
                status_code=400,
            )

        # 记录归还的资产
        rs["assets_returned"].extend(assets)

        # 检查是否所有资产都已归还（模拟：只要传了资产就视为全部归还）
        rs["status"] = "COMPLETED"
        rs["current_step"] = "已完成"
        rs["steps"].append({
            "step": "资产归还完成",
            "operator": user["name"] if user else "unknown",
            "assets_count": len(assets),
            "status": "done",
            "time": "2025-02-28 14:00:00",
        })

        return MockResponse({
            "code": 200,
            "data": {
                "resign_id": resign_id,
                "status": "COMPLETED",
                "current_step": "已完成",
                "returned_assets": assets,
            }
        })

    def _handle_resign_status(self, path, user):
        """查询离职状态"""
        match = re.search(r"/api/resign/status/(\S+)", path)
        if not match:
            return MockResponse({"code": 400, "message": "请求路径格式错误"}, status_code=400)

        resign_id = match.group(1)
        if resign_id not in self.resigns:
            return MockResponse(
                {"code": 404, "message": f"离职申请 {resign_id} 不存在"},
                status_code=404,
            )

        rs = self.resigns[resign_id]
        return MockResponse({
            "code": 200,
            "data": {
                "resign_id": resign_id,
                "employee_id": rs["employee_id"],
                "status": rs["status"],
                "current_step": rs["current_step"],
                "steps": rs["steps"],
                "assets_returned": rs.get("assets_returned", []),
            }
        })

    # ==================== 认证处理方法 ====================

    def _handle_login(self, json_data):
        """用户登录"""
        username = json_data.get("username", "")
        password = json_data.get("password", "")

        if not username or not password:
            return MockResponse(
                {"code": 400, "message": "用户名和密码不能为空"},
                status_code=400,
            )

        user = self.users.get(username)
        if not user or user["password"] != password:
            return MockResponse(
                {"code": 401, "message": "用户名或密码错误"},
                status_code=401,
            )

        return MockResponse({
            "code": 200,
            "data": {
                "token": user["token"],
                "role": user["role"],
                "username": username,
                "name": user["name"],
            }
        })

    # ==================== 主路由 ====================

    def post(self, url, data=None, json=None, headers=None, **kwargs):
        """处理 POST 请求"""
        path = self._parse_path(url)
        json_data = json if json is not None else (data if data else {})
        if isinstance(json_data, str):
            try:
                json_data = json.loads(json_data)
            except json.JSONDecodeError:
                json_data = {}

        user = self._get_user_by_token(headers)

        # 路由分发
        if path.endswith("/api/auth/login"):
            return self._handle_login(json_data)

        # ---- 入职相关 ----
        if path.endswith("/api/onboard/initiate"):
            return self._handle_onboard_initiate(json_data, user)

        if path.endswith("/api/onboard/hr-review"):
            return self._handle_onboard_review(path, json_data, user, "hr_approve")

        if path.endswith("/api/onboard/hr-reject"):
            return self._handle_onboard_review(path, json_data, user, "hr_reject")

        if path.endswith("/api/onboard/dept-approve"):
            return self._handle_onboard_review(path, json_data, user, "dept_approve")

        if path.endswith("/api/onboard/dept-reject"):
            return self._handle_onboard_review(path, json_data, user, "dept_reject")

        if path.endswith("/api/onboard/leader-approve"):
            return self._handle_onboard_review(path, json_data, user, "leader_approve")

        if path.endswith("/api/onboard/leader-reject"):
            return self._handle_onboard_review(path, json_data, user, "leader_reject")

        if path.endswith("/api/onboard/notify"):
            return self._handle_onboard_notify(json_data, user)

        # ---- 离职相关 ----
        if path.endswith("/api/resign/apply"):
            return self._handle_resign_apply(json_data, user)

        if path.endswith("/api/resign/handover"):
            return self._handle_resign_handover(json_data, user)

        if path.endswith("/api/resign/approve"):
            return self._handle_resign_approve_or_reject(json_data, user, is_approve=True)

        if path.endswith("/api/resign/reject"):
            return self._handle_resign_approve_or_reject(json_data, user, is_approve=False)

        if path.endswith("/api/resign/return-assets"):
            return self._handle_resign_return_assets(json_data, user)

        # 未匹配到路由
        return MockResponse({"code": 404, "message": f"接口不存在: {method} {path}"}, status_code=404)

    def get(self, url, headers=None, **kwargs):
        """处理 GET 请求"""
        path = self._parse_path(url)
        user = self._get_user_by_token(headers)

        # 入职状态查询
        if "/api/onboard/status/" in path:
            return self._handle_onboard_status(path, user)

        # 离职状态查询
        if "/api/resign/status/" in path:
            return self._handle_resign_status(path, user)

        return MockResponse({"code": 404, "message": f"接口不存在: GET {path}"}, status_code=404)


# ==================== pytest fixtures ====================

@pytest.fixture(scope="session")
def mock_api():
    """全局MockAPI实例（session级别，但每个测试前需要reset）"""
    return MockAPI()


@pytest.fixture
def api_client(monkeypatch, mock_api):
    """
    API客户端fixture
    - mock了requests.post和requests.get
    - 每个测试前自动重置mock数据
    - 返回mock后的requests模块
    """
    mock_api.reset()

    def mock_post(url, data=None, json=None, headers=None, **kwargs):
        return mock_api.post(url, data=data, json=json, headers=headers, **kwargs)

    def mock_get(url, headers=None, **kwargs):
        return mock_api.get(url, headers=headers, **kwargs)

    monkeypatch.setattr("requests.post", mock_post)
    monkeypatch.setattr("requests.get", mock_get)

    # 返回requests模块（已被mock）
    import requests
    return requests


@pytest.fixture
def auth_headers():
    """提供管理员认证头"""
    return {"Authorization": "Bearer token_admin_001"}


@pytest.fixture
def hr_headers():
    """提供HR认证头"""
    return {"Authorization": "Bearer token_hr_001"}


@pytest.fixture
def dept_manager_headers():
    """提供部门经理认证头"""
    return {"Authorization": "Bearer token_dept_001"}


@pytest.fixture
def leader_headers():
    """提供领导认证头"""
    return {"Authorization": "Bearer token_leader_001"}


@pytest.fixture
def employee_headers():
    """提供员工认证头"""
    return {"Authorization": "Bearer token_emp_001"}


@pytest.fixture
def viewer_headers():
    """提供只读用户认证头"""
    return {"Authorization": "Bearer token_viewer_001"}


@pytest.fixture
def invalid_headers():
    """提供无效认证头"""
    return {"Authorization": "Bearer token_invalid_999"}


# ==================== 命令行选项 ====================

def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        action="store",
        default="http://localhost:8080/api",
        help="后端API基础地址",
    )
    parser.addoption(
        "--real-api",
        action="store_true",
        default=False,
        help="连接真实API而非使用mock",
    )


@pytest.fixture
def base_url(request):
    """获取API基础地址"""
    return request.config.getoption("--base-url")


@pytest.fixture
def use_real_api(request):
    """是否使用真实API"""
    return request.config.getoption("--real-api")
