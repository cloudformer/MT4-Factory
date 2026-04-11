"""策略数据模型"""
from sqlalchemy import Column, String, Text, Enum, DateTime, JSON
from datetime import datetime
import enum

from src.common.database.base import Base


class StrategyStatus(str, enum.Enum):
    """策略状态枚举"""
    CANDIDATE = "candidate"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Strategy(Base):
    """
    策略表

    performance字段结构（JSON）：
    - 当前：单货币对
      {
        "backtested_symbol": "EURUSD",
        "sharpe_ratio": 0.52,
        "win_rate": 0.405,
        ...
      }

    - 🔮 未来扩展：多货币对
      {
        "profiles": {
          "EURUSD": {"sharpe_ratio": 0.52, ...},
          "GBPUSD": {"sharpe_ratio": 0.35, ...},
          "USDJPY": {"sharpe_ratio": 0.61, ...}
        },
        "default_symbol": "EURUSD"
      }
    """
    __tablename__ = "strategies"

    id = Column(String(32), primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(Text, nullable=False)
    status = Column(
        Enum(StrategyStatus),
        default=StrategyStatus.CANDIDATE,
        nullable=False
    )
    performance = Column(JSON)  # 灵活的JSON字段，支持单/多货币对扩展
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False
    )

    def __repr__(self):
        return f"<Strategy(id={self.id}, name={self.name}, status={self.status})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "status": self.status.value if isinstance(self.status, StrategyStatus) else self.status,
            "performance": self.performance,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
