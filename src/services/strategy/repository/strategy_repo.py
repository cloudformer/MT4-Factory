"""策略数据访问层"""
from typing import List, Optional
from sqlalchemy.orm import Session

from src.common.models.strategy import Strategy, StrategyStatus


class StrategyRepository:
    """策略数据访问对象"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, strategy: Strategy) -> Strategy:
        """创建策略"""
        self.session.add(strategy)
        self.session.flush()
        return strategy

    def get_by_id(self, strategy_id: str) -> Optional[Strategy]:
        """根据ID获取策略"""
        return self.session.query(Strategy).filter(Strategy.id == strategy_id).first()

    def get_all(self) -> List[Strategy]:
        """获取所有策略"""
        return self.session.query(Strategy).all()

    def get_by_status(self, status: StrategyStatus) -> List[Strategy]:
        """根据状态获取策略"""
        return self.session.query(Strategy).filter(Strategy.status == status).all()

    def update(self, strategy: Strategy) -> Strategy:
        """更新策略"""
        self.session.flush()
        return strategy

    def delete(self, strategy_id: str) -> bool:
        """删除策略"""
        strategy = self.get_by_id(strategy_id)
        if strategy:
            self.session.delete(strategy)
            self.session.flush()
            return True
        return False
