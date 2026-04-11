"""交易仓储层"""
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from src.common.database.connection import db
from src.common.models.trade import Trade


class TradeRepository:
    """交易数据访问对象"""

    def __init__(self):
        self.db = db

    def get_by_id(self, trade_id: str) -> Optional[Trade]:
        """根据ID获取交易"""
        with self.db.session_scope() as session:
            return session.query(Trade).filter(Trade.id == trade_id).first()

    def get_by_account(self, account_id: str, limit: Optional[int] = None) -> List[Trade]:
        """获取账户的所有交易"""
        with self.db.session_scope() as session:
            query = session.query(Trade).filter(Trade.account_id == account_id)
            query = query.order_by(Trade.open_time.desc())
            if limit:
                query = query.limit(limit)
            return query.all()

    def get_by_strategy(self, strategy_id: str, limit: Optional[int] = None) -> List[Trade]:
        """获取策略的所有交易"""
        with self.db.session_scope() as session:
            query = session.query(Trade).filter(Trade.strategy_id == strategy_id)
            query = query.order_by(Trade.open_time.desc())
            if limit:
                query = query.limit(limit)
            return query.all()

    def get_all(self, limit: int = 50) -> List[Trade]:
        """获取所有交易"""
        with self.db.session_scope() as session:
            return session.query(Trade).order_by(Trade.open_time.desc()).limit(limit).all()
