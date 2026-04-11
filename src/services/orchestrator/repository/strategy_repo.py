"""策略数据访问层 - Orchestrator专用"""
from typing import List, Optional
from sqlalchemy.orm import Session

from src.common.models.strategy import Strategy, StrategyStatus
from src.common.database.connection import db


class StrategyRepository:
    """策略数据访问对象 - 用于Orchestrator服务"""

    def __init__(self, session: Optional[Session] = None):
        """
        初始化Repository

        Args:
            session: 可选的数据库会话，如果不提供则自动创建
        """
        self._external_session = session is not None
        self.session = session or db.get_session()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._external_session:
            self.session.close()

    def create(self, strategy: Strategy) -> Strategy:
        """创建策略"""
        self.session.add(strategy)
        self.session.commit()
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
        self.session.commit()
        return strategy

    def delete(self, strategy_id: str) -> bool:
        """删除策略"""
        strategy = self.get_by_id(strategy_id)
        if strategy:
            self.session.delete(strategy)
            self.session.commit()
            return True
        return False

    def get_by_symbols(self, symbols: List[str]) -> List[Strategy]:
        """
        根据货币对获取策略

        Args:
            symbols: 货币对列表，如 ["EURUSD", "GBPUSD"]

        Returns:
            支持这些货币对的策略列表
        """
        strategies = self.get_all()
        result = []

        for strategy in strategies:
            performance = strategy.performance or {}

            # 检查是否支持任一货币对
            if 'profiles' in performance:
                # 多货币对模式
                strategy_symbols = set(performance['profiles'].keys())
                if strategy_symbols.intersection(symbols):
                    result.append(strategy)
            else:
                # 单货币对模式
                backtested_symbol = performance.get('backtested_symbol', 'EURUSD')
                if backtested_symbol in symbols:
                    result.append(strategy)

        return result

    def count_by_status(self) -> dict:
        """
        统计各状态的策略数量

        Returns:
            {"candidate": 10, "active": 5, "archived": 2}
        """
        from sqlalchemy import func

        results = self.session.query(
            Strategy.status,
            func.count(Strategy.id)
        ).group_by(Strategy.status).all()

        counts = {
            'candidate': 0,
            'active': 0,
            'archived': 0
        }

        for status, count in results:
            counts[status.value] = count

        return counts
