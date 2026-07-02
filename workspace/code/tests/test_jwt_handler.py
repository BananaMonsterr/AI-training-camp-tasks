"""
JWT处理器单元测试
"""

import pytest
import time

from auth.jwt_handler import JWTHandler
from utils.exceptions import TokenExpiredException, UnauthorizedException


class TestJWTHandler:
    """JWT处理器测试"""

    def test_create_token(self, jwt_handler):
        token = jwt_handler.create_token(
            user_id="user-001",
            employee_id="emp-001",
            role="admin",
            department_id="dept-001",
            username="admin",
            display_name="系统管理员",
        )
        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT格式校验

    def test_decode_token(self, jwt_handler):
        token = jwt_handler.create_token(
            user_id="user-001",
            employee_id="emp-001",
            role="hr_manager",
            department_id="dept-001",
            username="hr_wang",
            display_name="王HR",
        )
        payload = jwt_handler.decode_token(token)
        assert payload.sub == "user-001"
        assert payload.role == "hr_manager"
        assert payload.username == "hr_wang"
        assert payload.display_name == "王HR"

    def test_decode_expired_token(self, jwt_handler):
        """测试过期Token"""
        # 使用极短的过期时间
        handler = JWTHandler(secret_key="test", expire_minutes=-1)
        token = handler.create_token(
            user_id="u1", employee_id="e1", role="admin",
            department_id="d1", username="u", display_name="U",
        )
        # 等待一下确保过期
        with pytest.raises(TokenExpiredException):
            handler.decode_token(token)

    def test_decode_invalid_token(self, jwt_handler):
        with pytest.raises(UnauthorizedException):
            jwt_handler.decode_token("invalid.token.here")

    def test_decode_tampered_token(self, jwt_handler):
        token = jwt_handler.create_token(
            user_id="u1", employee_id="e1", role="admin",
            department_id="d1", username="u", display_name="U",
        )
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + ".tampered"

        with pytest.raises(UnauthorizedException):
            jwt_handler.decode_token(tampered)

    def test_refresh_token(self, jwt_handler):
        token = jwt_handler.create_token(
            user_id="user-001", employee_id="emp-001", role="employee",
            department_id="dept-001", username="zhangsan",
            display_name="张三",
        )
        new_token = jwt_handler.refresh_token(token)
        assert new_token != token

        # 新token应该能解码
        payload = jwt_handler.decode_token(new_token)
        assert payload.sub == "user-001"

    def test_get_current_user(self, jwt_handler):
        token = jwt_handler.create_token(
            user_id="user-001", employee_id="emp-001", role="admin",
            department_id="dept-001", username="admin",
            display_name="管理员",
        )
        user = jwt_handler.get_current_user(token)
        assert user.role == "admin"
        assert user.tenant_id == "default"

    def test_create_token_with_tenant(self, jwt_handler):
        token = jwt_handler.create_token(
            user_id="u1", employee_id="e1", role="admin",
            department_id="d1", username="u", display_name="U",
            tenant_id="tenant-002",
        )
        payload = jwt_handler.decode_token(token)
        assert payload.tenant_id == "tenant-002"

    def test_token_structure(self, jwt_handler):
        """验证token包含所有必要字段"""
        token = jwt_handler.create_token(
            user_id="user-001", employee_id="emp-001", role="dept_manager",
            department_id="dept-002", username="manager",
            display_name="部门经理",
        )
        payload = jwt_handler.decode_token(token)
        assert payload.sub == "user-001"
        assert payload.employee_id == "emp-001"
        assert payload.role == "dept_manager"
        assert payload.department_id == "dept-002"
        assert payload.username == "manager"
        assert payload.display_name == "部门经理"
        assert payload.exp > time.time()
