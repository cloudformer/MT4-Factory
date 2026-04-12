"""风控管理器"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal

from src.common.config.settings import settings
from src.common.models.signal import Signal
from src.common.models.account import Account


class RiskCheckResult:
    """风控检查结果"""
    def __init__(self, passed: bool, reason: str = ""):
        self.passed = passed
        self.reason = reason


class RiskManager:
    """
    风控管理器

    功能：
    1. 检查订单大小限制
    2. 检查每日亏损限制
    3. 检查持仓数量限制
    4. 检查最大回撤
    5. 检查品种白名单
    """

    def __init__(self):
        self.config = settings.get('execution', {}).get('risk_limits', {})

        # 默认配置
        self.max_order_size = self.config.get('max_order_size', 1.0)
        self.max_daily_loss = self.config.get('max_daily_loss', 10000)
        self.max_position_count = self.config.get('max_position_count', 10)
        self.max_drawdown_percent = self.config.get('max_drawdown_percent', 20)
        self.allowed_symbols = self.config.get('allowed_symbols', [])

        # 内部状态
        self._daily_stats = {}  # 每日统计
        self._current_positions = []  # 当前持仓
        self._last_reset = datetime.now().date()

    def check_signal(self, signal: Signal, account: Optional[Account] = None) -> RiskCheckResult:
        """
        检查信号是否符合风控规则

        Args:
            signal: 交易信号
            account: 账户信息（可选）

        Returns:
            RiskCheckResult: 风控检查结果
        """
        # 1. 检查品种白名单
        if self.allowed_symbols and signal.symbol not in self.allowed_symbols:
            return RiskCheckResult(
                False,
                f"品种 {signal.symbol} 不在白名单中: {self.allowed_symbols}"
            )

        # 2. 检查订单大小
        volume = float(signal.volume)
        if volume > self.max_order_size:
            return RiskCheckResult(
                False,
                f"订单大小 {volume} 超过限制 {self.max_order_size}"
            )

        # 3. 检查持仓数量
        if len(self._current_positions) >= self.max_position_count:
            return RiskCheckResult(
                False,
                f"持仓数量已达上限 {self.max_position_count}"
            )

        # 4. 检查每日亏损（如果有账户信息）
        if account:
            daily_loss = self._calculate_daily_loss(account)
            if daily_loss >= self.max_daily_loss:
                return RiskCheckResult(
                    False,
                    f"今日亏损 ${daily_loss:.2f} 已达上限 ${self.max_daily_loss:.2f}"
                )

            # 5. 检查最大回撤
            drawdown_pct = self._calculate_drawdown(account)
            if drawdown_pct >= self.max_drawdown_percent:
                return RiskCheckResult(
                    False,
                    f"当前回撤 {drawdown_pct:.2f}% 超过限制 {self.max_drawdown_percent}%"
                )

        return RiskCheckResult(True, "风控检查通过")

    def update_position(self, ticket: int, symbol: str, action: str):
        """
        更新持仓状态

        Args:
            ticket: MT5订单号
            symbol: 交易品种
            action: 操作类型 ('open' 或 'close')
        """
        if action == 'open':
            self._current_positions.append({
                'ticket': ticket,
                'symbol': symbol,
                'open_time': datetime.now()
            })
        elif action == 'close':
            self._current_positions = [
                p for p in self._current_positions
                if p['ticket'] != ticket
            ]

    def _calculate_daily_loss(self, account: Account) -> float:
        """计算今日亏损"""
        # 检查是否需要重置每日统计
        today = datetime.now().date()
        if today != self._last_reset:
            self._daily_stats = {}
            self._last_reset = today

        # 计算今日亏损
        initial_balance = account.initial_balance or 0
        current_balance = account.current_balance or 0

        # 如果有记录今日开始余额，使用记录值
        if 'start_balance' not in self._daily_stats:
            self._daily_stats['start_balance'] = current_balance

        start_balance = self._daily_stats['start_balance']
        daily_loss = max(0, start_balance - current_balance)

        return daily_loss

    def _calculate_drawdown(self, account: Account) -> float:
        """计算当前回撤百分比"""
        initial_balance = account.initial_balance or 0
        current_equity = account.current_equity or 0

        if initial_balance == 0:
            return 0.0

        drawdown = max(0, initial_balance - current_equity)
        drawdown_pct = (drawdown / initial_balance) * 100

        return drawdown_pct

    def get_stats(self) -> Dict[str, Any]:
        """获取风控统计信息"""
        return {
            'max_order_size': self.max_order_size,
            'max_daily_loss': self.max_daily_loss,
            'max_position_count': self.max_position_count,
            'max_drawdown_percent': self.max_drawdown_percent,
            'allowed_symbols': self.allowed_symbols,
            'current_positions': len(self._current_positions),
            'daily_stats': self._daily_stats
        }
