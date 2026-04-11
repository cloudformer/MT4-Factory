"""交易数据访问层"""
from typing import List
from sqlalchemy.orm import Session

from src.common.models.trade import Trade


class TradeRepository:
    """交易数据访问对象"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, trade: Trade) -> Trade:
        """创建交易记录"""
        self.session.add(trade)
        self.session.flush()
        return trade

    def get_all(self, limit: int = 50) -> List[Trade]:
        """获取所有交易"""
        return self.session.query(Trade).order_by(Trade.open_time.desc()).limit(limit).all()
