"""
HR系统对接服务（模拟实现）

使用模拟数据代替真实的HR系统接口调用，便于开发和测试。
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)


class HRServiceError(Exception):
    """HR服务异常"""
    pass


class HRMockClient:
    """
    HR系统模拟客户端
    模拟以下接口：
    1. 员工同步查询
    2. 部门信息查询
    3. 离职数据同步到HR系统
    """

    # 模拟数据
    _mock_employees = {
        'EMP000001': {
            'employee_no': 'EMP000001',
            'name': '张三',
            'email': 'zhangsan@company.com',
            'phone': '13800138001',
            'department_code': 'DEPT_TECH',
            'department_name': '技术部',
            'position': '高级工程师',
            'hire_date': '2022-03-15',
            'status': 'ACTIVE',
        },
        'EMP000002': {
            'employee_no': 'EMP000002',
            'name': '李四',
            'email': 'lisi@company.com',
            'phone': '13800138002',
            'department_code': 'DEPT_HR',
            'department_name': '人力资源部',
            'position': 'HR经理',
            'hire_date': '2021-06-01',
            'status': 'ACTIVE',
        },
        'EMP000003': {
            'employee_no': 'EMP000003',
            'name': '王五',
            'email': 'wangwu@company.com',
            'phone': '13800138003',
            'department_code': 'DEPT_FINANCE',
            'department_name': '财务部',
            'position': '财务主管',
            'hire_date': '2020-01-10',
            'status': 'ACTIVE',
        },
    }

    _mock_departments = {
        'DEPT_TECH': {'code': 'DEPT_TECH', 'name': '技术部', 'parent_code': None, 'manager': '张三'},
        'DEPT_HR': {'code': 'DEPT_HR', 'name': '人力资源部', 'parent_code': None, 'manager': '李四'},
        'DEPT_FINANCE': {'code': 'DEPT_FINANCE', 'name': '财务部', 'parent_code': None, 'manager': '王五'},
        'DEPT_SALES': {'code': 'DEPT_SALES', 'name': '销售部', 'parent_code': None, 'manager': '赵六'},
        'DEPT_TECH_BACKEND': {'code': 'DEPT_TECH_BACKEND', 'name': '后端组', 'parent_code': 'DEPT_TECH', 'manager': '张三'},
        'DEPT_TECH_FRONTEND': {'code': 'DEPT_TECH_FRONTEND', 'name': '前端组', 'parent_code': 'DEPT_TECH', 'manager': '钱七'},
    }

    def sync_employee(self, employee_no: str) -> Optional[Dict[str, Any]]:
        """
        从HR系统同步单个员工信息
        模拟: 通过员工编号查询
        """
        logger.info(f'[HR Mock] 同步员工: {employee_no}')
        return self._mock_employees.get(employee_no)

    def sync_employee_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """通过邮箱查询员工"""
        for emp in self._mock_employees.values():
            if emp['email'] == email:
                return emp
        return None

    def query_department(self, department_code: str) -> Optional[Dict[str, Any]]:
        """查询部门信息"""
        logger.info(f'[HR Mock] 查询部门: {department_code}')
        return self._mock_departments.get(department_code)

    def list_departments(self) -> List[Dict[str, Any]]:
        """列出所有部门"""
        logger.info('[HR Mock] 列出所有部门')
        return list(self._mock_departments.values())

    def sync_offboarding_data(self, employee_no: str, termination_date: date,
                              offboarding_type: str, reason: str = None) -> bool:
        """
        向HR系统同步离职数据
        模拟: 总是返回成功
        """
        logger.info(
            f'[HR Mock] 同步离职数据: 员工={employee_no}, '
            f'离职日期={termination_date}, 类型={offboarding_type}'
        )
        return True


class HRService:
    """HR系统对接服务"""

    def __init__(self):
        self.client = HRMockClient()

    def sync_employee(self, employee_no: str) -> Optional[dict]:
        """同步员工信息"""
        try:
            data = self.client.sync_employee(employee_no)
            if not data:
                raise HRServiceError(f'HR系统中未找到员工: {employee_no}')
            return data
        except Exception as e:
            if isinstance(e, HRServiceError):
                raise
            raise HRServiceError(f'同步员工失败: {str(e)}')

    def query_department(self, department_code: str) -> Optional[dict]:
        """查询部门"""
        try:
            data = self.client.query_department(department_code)
            if not data:
                raise HRServiceError(f'HR系统中未找到部门: {department_code}')
            return data
        except Exception as e:
            if isinstance(e, HRServiceError):
                raise
            raise HRServiceError(f'查询部门失败: {str(e)}')

    def sync_offboarding(self, employee_no: str, termination_date: date,
                         offboarding_type: str, reason: str = None) -> bool:
        """同步离职数据到HR系统"""
        try:
            result = self.client.sync_offboarding_data(
                employee_no, termination_date, offboarding_type, reason
            )
            if not result:
                raise HRServiceError('HR系统同步离职数据失败')
            return result
        except Exception as e:
            if isinstance(e, HRServiceError):
                raise
            raise HRServiceError(f'同步离职数据失败: {str(e)}')
