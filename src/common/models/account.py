"""账户数据模型"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, JSON
from datetime import datetime

from src.common.database.base import Base


class Account(Base):
    """
    MT5账户表

    管理多个MT5账户及其配置
    """
    __tablename__ = "accounts"

    id = Column(String(32), primary_key=True)  # 账户唯一ID
    login = Column(Integer, nullable=False, unique=True)  # MT5账号
    server = Column(String(255), nullable=False)  # 服务器名称
    company = Column(String(255))  # 经纪商名称

    # 账户信息
    name = Column(String(255))  # 账户别名（便于识别）
    currency = Column(String(10), default="USD")  # 账户货币
    leverage = Column(Integer, default=100)  # 杠杆

    # 初始状态（用于计算收益率）
    initial_balance = Column(Float, nullable=False)  # 初始资金
    start_time = Column(DateTime, default=datetime.now)  # 上线时间

    # 当前状态（定期从MT5同步）
    current_balance = Column(Float)  # 当前余额
    current_equity = Column(Float)  # 当前净值
    last_sync_time = Column(DateTime)  # 最后同步时间

    # 账户状态
    is_active = Column(Boolean, default=True)  # 是否激活
    trade_allowed = Column(Boolean, default=True)  # 是否允许交易

    # 风控配置（JSON）
    risk_config = Column(JSON, default=dict)
    # 例如: {
    #   "max_daily_loss": 0.05,
    #   "max_total_exposure": 0.30,
    #   "max_trades_per_day": 20
    # }

    # 备注
    notes = Column(String(500))

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'login': self.login,
            'server': self.server,
            'company': self.company,
            'name': self.name,
            'currency': self.currency,
            'leverage': self.leverage,
            'initial_balance': float(self.initial_balance) if self.initial_balance else 0.0,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'current_balance': float(self.current_balance) if self.current_balance else None,
            'current_equity': float(self.current_equity) if self.current_equity else None,
            'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'is_active': self.is_active,
            'trade_allowed': self.trade_allowed,
            'risk_config': self.risk_config or {},
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
