"""
统一响应格式 - 与API设计文档第2.3节对应
"""

import time
import uuid
from typing import Any, Optional
from pydantic import BaseModel


class ResponseWrapper(BaseModel):
    """通用响应包装"""
    code: int = 0
    message: str = "success"
    request_id: str = ""
    timestamp: int = 0
    data: Any = None

    @classmethod
    def success(cls, data: Any = None, message: str = "success") -> "ResponseWrapper":
        return cls(
            code=0,
            message=message,
            request_id=str(uuid.uuid4()),
            timestamp=int(time.time() * 1000),
            data=data,
        )

    @classmethod
    def error(cls, code: int, message: str, details: Optional[dict] = None) -> "ResponseWrapper":
        return cls(
            code=code,
            message=message,
            request_id=str(uuid.uuid4()),
            timestamp=int(time.time() * 1000),
            data=details,
        )


class PaginatedData(BaseModel):
    """分页数据包装"""
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: list, total: int, page: int, page_size: int) -> "PaginatedData":
        total_pages = max(1, (total + page_size - 1) // page_size) if page_size > 0 else 1
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
