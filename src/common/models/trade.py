"""交易数据模型"""
from sqlalchemy import Column, String, BigInteger, DECIMAL, ForeignKey, DateTime, Enum
from datetime import datetime

from src.common.database.base import Base
from src.common.models.signal import Direction


class Trade(Base):
    """交易表"""
    __tablename__ = "trades"

    id = Column(String(32), primary_key=True)
    account_id = Column(String(32), ForeignKey('accounts.id'), nullable=True)
    signal_id = Column(String(32), ForeignKey('signals.id'), nullable=True)
    strategy_id = Column(String(32), ForeignKey('strategies.id'), nullable=True)  # 允许为空（手动交易）
    ticket = Column(BigInteger, nullable=True)
    symbol = Column(String(10), nullable=False)
    direction = Column(Enum(Direction), nullable=False)
    volume = Column(DECIMAL(10, 2), nullable=False)
    open_price = Column(DECIMAL(10, 5), nullable=True)
    close_price = Column(DECIMAL(10, 5), nullable=True)
    profit = Column(DECIMAL(10, 2), nullable=True)
    open_time = Column(DateTime, nullable=True)
    close_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Trade(id={self.id}, symbol={self.symbol}, ticket={self.ticket})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "signal_id": self.signal_id,
            "strategy_id": self.strategy_id,
            "ticket": self.ticket,
            "symbol": self.symbol,
            "direction": self.direction.value if isinstance(self.direction, Direction) else self.direction,
            "volume": float(self.volume) if self.volume else None,
            "open_price": float(self.open_price) if self.open_price else None,
            "close_price": float(self.close_price) if self.close_price else None,
            "profit": float(self.profit) if self.profit else None,
            "open_time": self.open_time.isoformat() if self.open_time else None,
            "close_time": self.close_time.isoformat() if self.close_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
