"""
基础模型定义
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 声明基类"""
    pass


def generate_uuid() -> str:
    """生成UUID字符串"""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """获取当前UTC时间"""
    return datetime.now(timezone.utc)


class TimestampMixin:
    """时间戳混入类"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        """将模型转换为字典"""
        result = {}
        for column in self.__table__.columns:  # type: ignore
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = int(value.timestamp() * 1000)
            result[column.name] = value
        return result

    def update(self, **kwargs) -> None:
        """更新模型字段"""
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
