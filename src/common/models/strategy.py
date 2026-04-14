"""策略数据模型"""
from sqlalchemy import Column, String, Text, Enum, DateTime, JSON, Float, Integer
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
        Enum(StrategyStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=StrategyStatus.CANDIDATE,
        nullable=False
    )
    performance = Column(JSON)  # 灵活的JSON字段，支持单/多货币对扩展
    params = Column(JSON)  # 策略参数：symbol, timeframe等
    mt5_host_id = Column(String(32), nullable=True)  # 关联的MT5主机ID

    # Validator验证结果字段
    last_validation_time = Column(DateTime, nullable=True)
    validation_win_rate = Column(Float, nullable=True)
    validation_total_return = Column(Float, nullable=True)
    validation_total_trades = Column(Integer, nullable=True)
    validation_sharpe_ratio = Column(Float, nullable=True)
    validation_max_drawdown = Column(Float, nullable=True)
    validation_profit_factor = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
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
            "params": self.params,
            "mt5_host_id": self.mt5_host_id,
            "last_validation_time": self.last_validation_time.isoformat() if self.last_validation_time else None,
            "validation_win_rate": self.validation_win_rate,
            "validation_total_return": self.validation_total_return,
            "validation_total_trades": self.validation_total_trades,
            "validation_sharpe_ratio": self.validation_sharpe_ratio,
            "validation_max_drawdown": self.validation_max_drawdown,
            "validation_profit_factor": self.validation_profit_factor,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
