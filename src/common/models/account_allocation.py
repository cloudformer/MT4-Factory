"""账户策略配比模型"""
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, UniqueConstraint
from datetime import datetime

from src.common.database.base import Base


class AccountAllocation(Base):
    """
    账户策略配比表

    管理每个账户使用哪些策略，以及各策略的资金配比
    """
    __tablename__ = "account_allocations"

    id = Column(String(32), primary_key=True)
    account_id = Column(String(32), ForeignKey('accounts.id'), nullable=False)
    strategy_id = Column(String(32), ForeignKey('strategies.id'), nullable=False)

    # 配比（百分比，0-1之间）
    allocation_percentage = Column(Float, nullable=False)  # 例如: 0.30 表示 30%

    # 状态
    is_active = Column(Boolean, default=True)  # 是否启用此配比

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 确保同一账户的同一策略只有一条配比记录
    __table_args__ = (
        UniqueConstraint('account_id', 'strategy_id', name='uix_account_strategy'),
    )

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'strategy_id': self.strategy_id,
            'allocation_percentage': float(self.allocation_percentage),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
