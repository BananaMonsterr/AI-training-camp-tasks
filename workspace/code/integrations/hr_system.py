"""
HR系统对接模块 - 模拟外部HR系统的接口
对应API文档第10章
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class SyncDirection(str, Enum):
    """同步方向"""
    INBOUND = "inbound"    # HR -> 本系统
    OUTBOUND = "outbound"  # 本系统 -> HR


class SyncStatus(str, Enum):
    """同步状态"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


@dataclass
class SyncLog:
    """同步日志"""
    id: str
    direction: SyncDirection
    event_type: str
    employee_no: str
    status: SyncStatus
    message: str
    created_at: int
    details: dict = field(default_factory=dict)


class HRSystemClient:
    """
    HR系统对接客户端（模拟实现）
    
    提供：
    1. 同步员工信息（HR→本系统）
    2. 入离职状态回写（本系统→HR）
    3. 查询同步日志
    
    生产环境中应替换为真实的HTTP客户端
    """

    def __init__(self, api_key: str = "mock-hr-api-key", base_url: str = "https://hr-api.company.com"):
        self.api_key = api_key
        self.base_url = base_url
        self._sync_logs: list[SyncLog] = []
        # 模拟HR系统的员工数据
        self._hr_employees: dict[str, dict] = {
            "EMP20240001": {
                "employee_no": "EMP20240001",
                "name": "李四",
                "department_code": "DEPT001",
                "department_name": "技术部",
                "position": "技术经理",
                "email": "lisi@company.com",
            },
            "EMP20240002": {
                "employee_no": "EMP20240002",
                "name": "王五",
                "department_code": "DEPT002",
                "department_name": "人力资源部",
                "position": "HR总监",
                "email": "wangwu@company.com",
            },
        }

    def sync_employee(self, employee_data: dict) -> dict:
        """
        同步员工信息（HR系统→本系统）
        对应API文档10.2.1
        
        模拟实现：返回同步结果，并记录日志
        """
        employee_no = employee_data.get("employee_no", "")
        
        # 模拟HR系统的校验
        if not employee_no:
            return self._log_and_return(
                direction=SyncDirection.INBOUND,
                event_type="sync_employee",
                employee_no=employee_no,
                status=SyncStatus.FAILED,
                message="员工工号不能为空",
            )

        # 模拟处理成功
        self._hr_employees[employee_no] = employee_data
        
        return self._log_and_return(
            direction=SyncDirection.INBOUND,
            event_type="sync_employee",
            employee_no=employee_no,
            status=SyncStatus.SUCCESS,
            message="员工信息同步成功",
            details={"synced_fields": list(employee_data.keys())},
        )

    def writeback_status(self, employee_no: str, event_type: str,
                         status: str, effective_date: str) -> dict:
        """
        入离职状态回写（本系统→HR系统）
        对应API文档10.2.2
        
        模拟实现：向HR系统发送状态变更
        """
        valid_events = ["onboarding_completed", "offboarding_completed", "status_change"]
        if event_type not in valid_events:
            return self._log_and_return(
                direction=SyncDirection.OUTBOUND,
                event_type=event_type,
                employee_no=employee_no,
                status=SyncStatus.FAILED,
                message=f"无效的事件类型: {event_type}，有效值: {valid_events}",
            )

        # 模拟成功回写
        return self._log_and_return(
            direction=SyncDirection.OUTBOUND,
            event_type=event_type,
            employee_no=employee_no,
            status=SyncStatus.SUCCESS,
            message=f"状态回写成功: {employee_no} -> {status}",
            details={
                "event_type": event_type,
                "status": status,
                "effective_date": effective_date,
            },
        )

    def query_employee_from_hr(self, employee_no: str) -> Optional[dict]:
        """
        从HR系统查询员工信息（模拟）
        """
        return self._hr_employees.get(employee_no)

    def query_department_employees(self, department_code: str) -> list[dict]:
        """
        查询部门下所有员工（模拟）
        """
        return [
            emp for emp in self._hr_employees.values()
            if emp.get("department_code") == department_code
        ]

    def get_sync_logs(self, page: int = 1, page_size: int = 20,
                      direction: Optional[str] = None,
                      status: Optional[str] = None) -> dict:
        """
        查询同步日志
        对应API文档10.2.3
        """
        filtered = self._sync_logs[:]

        if direction:
            filtered = [log for log in filtered if log.direction.value == direction]
        if status:
            filtered = [log for log in filtered if log.status.value == status]

        # 按时间倒序
        filtered.sort(key=lambda x: x.created_at, reverse=True)

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        items = filtered[start:end]

        return {
            "items": [self._log_to_dict(log) for log in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size) if page_size > 0 else 1,
        }

    def verify_api_key(self, api_key: str) -> bool:
        """验证HR系统API Key"""
        return api_key == self.api_key

    def _log_and_return(self, direction: SyncDirection, event_type: str,
                        employee_no: str, status: SyncStatus,
                        message: str, details: dict = None) -> dict:
        """记录日志并返回结果"""
        log = SyncLog(
            id=str(uuid.uuid4()),
            direction=direction,
            event_type=event_type,
            employee_no=employee_no,
            status=status,
            message=message,
            created_at=int(time.time() * 1000),
            details=details or {},
        )
        self._sync_logs.append(log)

        return {
            "success": status == SyncStatus.SUCCESS,
            "log_id": log.id,
            "message": message,
            "timestamp": log.created_at,
        }

    def _log_to_dict(self, log: SyncLog) -> dict:
        """转换日志为字典"""
        return {
            "id": log.id,
            "direction": log.direction.value,
            "event_type": log.event_type,
            "employee_no": log.employee_no,
            "status": log.status.value,
            "message": log.message,
            "created_at": log.created_at,
            "details": log.details,
        }
