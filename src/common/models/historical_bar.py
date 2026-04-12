"""Historical Bar Model - K线历史数据"""
from sqlalchemy import Column, String, DECIMAL, BigInteger, DateTime, Index
from datetime import datetime

from src.common.database.base import Base


class HistoricalBar(Base):
    """K线历史数据模型"""

    __tablename__ = 'historical_bars'

    # 基本字段
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    time = Column(DateTime, nullable=False, index=True)

    # OHLCV数据
    open = Column(DECIMAL(10, 5), nullable=False)
    high = Column(DECIMAL(10, 5), nullable=False)
    low = Column(DECIMAL(10, 5), nullable=False)
    close = Column(DECIMAL(10, 5), nullable=False)
    volume = Column(BigInteger, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 复合索引（最重要）
    __table_args__ = (
        Index('idx_symbol_timeframe_time', 'symbol', 'timeframe', 'time'),
        Index('idx_time_symbol', 'time', 'symbol'),
    )

    def __repr__(self):
        return f"<HistoricalBar {self.symbol} {self.timeframe} {self.time}>"

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'time': self.time.isoformat() if self.time else None,
            'open': float(self.open) if self.open else None,
            'high': float(self.high) if self.high else None,
            'low': float(self.low) if self.low else None,
            'close': float(self.close) if self.close else None,
            'volume': self.volume,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
