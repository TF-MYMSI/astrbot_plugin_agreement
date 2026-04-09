"""数据模型定义"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass


class AgreementState(str, Enum):
    """协议状态枚举"""
    NONE = None
    WAITING = "waiting"
    AGREED = "yes"
    REFUSED = "no"


@dataclass
class UserData:
    """用户数据"""
    user_id: str
    state: Optional[AgreementState]
    timestamp: float = 0
    last_trigger: float = 0
    undo_count: int = 0
    last_undo: float = 0


@dataclass
class Statistics:
    """统计数据"""
    total: int = 0
    agreed: int = 0
    refused: int = 0
    waiting: int = 0

    @property
    def rate(self) -> float:
        return (self.agreed / self.total * 100) if self.total > 0 else 0
