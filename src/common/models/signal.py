"""信号数据模型"""
from sqlalchemy import Column, String, Enum, DECIMAL, ForeignKey, DateTime
from datetime import datetime
import enum

from src.common.database.base import Base


class SignalStatus(str, enum.Enum):
    """信号状态枚举"""
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Direction(str, enum.Enum):
    """交易方向枚举"""
    BUY = "buy"
    SELL = "sell"


class Signal(Base):
    """信号表"""
    __tablename__ = "signals"

    id = Column(String(32), primary_key=True)
    strategy_id = Column(String(32), ForeignKey('strategies.id'), nullable=False)
    symbol = Column(String(10), nullable=False)
    direction = Column(Enum(Direction), nullable=False)
    volume = Column(DECIMAL(10, 2), nullable=False)
    sl = Column(DECIMAL(10, 5), nullable=True)
    tp = Column(DECIMAL(10, 5), nullable=True)
    status = Column(Enum(SignalStatus), default=SignalStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f"<Signal(id={self.id}, symbol={self.symbol}, direction={self.direction}, status={self.status})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "direction": self.direction.value if isinstance(self.direction, Direction) else self.direction,
            "volume": float(self.volume) if self.volume else None,
            "sl": float(self.sl) if self.sl else None,
            "tp": float(self.tp) if self.tp else None,
            "status": self.status.value if isinstance(self.status, SignalStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
