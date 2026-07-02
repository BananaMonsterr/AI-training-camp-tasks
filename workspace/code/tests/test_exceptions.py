"""
异常体系单元测试
"""

import pytest
from utils.exceptions import (
    AppException, BadRequestException, ValidationException,
    UnauthorizedException, ForbiddenException, NotFoundException,
    EmployeeNotFoundException, FlowNotFoundException,
    StatusConflictException, InternalException,
)


class TestAppException:
    """基础异常测试"""

    def test_base_exception(self):
        exc = AppException(40000, "test error", 400, {"field": "name"})
        assert exc.code == 40000
        assert exc.message == "test error"
        assert exc.status_code == 400
        assert exc.details == {"field": "name"}

    def test_default_details(self):
        exc = AppException(50000, "error")
        assert exc.details == {}


class TestSpecificExceptions:
    """特定异常测试"""

    def test_bad_request(self):
        exc = BadRequestException()
        assert exc.code == 40000
        assert exc.status_code == 400

    def test_bad_request_custom_message(self):
        exc = BadRequestException("自定义错误")
        assert exc.message == "自定义错误"

    def test_validation_exception(self):
        exc = ValidationException("校验失败", {"field": "email"})
        assert exc.code == 40001
        assert exc.details == {"field": "email"}

    def test_unauthorized(self):
        exc = UnauthorizedException()
        assert exc.code == 40100
        assert exc.status_code == 401

    def test_forbidden(self):
        exc = ForbiddenException()
        assert exc.code == 40300
        assert exc.status_code == 403

    def test_not_found(self):
        exc = NotFoundException("资源不存在")
        assert exc.code == 40400
        assert exc.status_code == 404

    def test_employee_not_found(self):
        exc = EmployeeNotFoundException()
        assert exc.code == 40401
        assert "员工" in exc.message

    def test_flow_not_found(self):
        exc = FlowNotFoundException()
        assert exc.code == 40402
        assert "审批流" in exc.message

    def test_status_conflict(self):
        exc = StatusConflictException("当前状态不允许")
        assert exc.code == 40901
        assert exc.status_code == 409

    def test_internal_error(self):
        exc = InternalException("数据库连接失败")
        assert exc.code == 50000
        assert exc.status_code == 500


class TestExceptionInheritance:
    """异常继承测试"""

    def test_is_instance_of_base(self):
        assert isinstance(ValidationException(), AppException)
        assert isinstance(ForbiddenException(), AppException)
        assert isinstance(InternalException(), AppException)

    def test_exception_raise_and_catch(self):
        """测试异常可以被捕获"""
        with pytest.raises(AppException) as exc_info:
            raise ValidationException("参数错误")
        assert exc_info.value.code == 40001

    def test_exception_str(self):
        exc = NotFoundException("用户不存在")
        assert str(exc) == "用户不存在"
