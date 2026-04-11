"""
RiskManager - 风险管理器

职责：
1. 独立的风险检查和策略执行模块
2. 检查全局和单策略风险限制
3. 计算仓位占用和暴露度
4. 策略合规性检查

设计原则：
- 风险管理是关键功能，需要独立和透明
- 策略（Policy）和执行分离
- 支持复杂的风险计算逻辑
- 便于审计和回溯
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.services.orchestrator.service.account_manager import Account


@dataclass
class RiskCheckResult:
    """
    风险检查结果

    记录单次检查的结果和原因
    """
    passed: bool          # 是否通过检查
    check_type: str       # 检查类型
    message: str          # 检查消息
    current_value: float  # 当前值
    limit_value: float    # 限制值
    severity: str = "info"  # 严重程度：info/warning/error


class PolicyChecker:
    """
    策略检查器

    检查各种风险限制是否被违反
    """

    def __init__(self):
        """初始化策略检查器"""
        pass

    def check_total_exposure(
        self,
        current_exposure: float,
        new_exposure: float,
        max_exposure: float
    ) -> RiskCheckResult:
        """
        检查总仓位是否超限

        Args:
            current_exposure: 当前总仓位占用（0-1）
            new_exposure: 新增仓位（0-1）
            max_exposure: 最大仓位限制（0-1）

        Returns:
            检查结果
        """
        total = current_exposure + new_exposure
        passed = total <= max_exposure

        return RiskCheckResult(
            passed=passed,
            check_type="total_exposure",
            message=f"总仓位 {total:.2%} {'≤' if passed else '>'} 限制 {max_exposure:.2%}",
            current_value=total,
            limit_value=max_exposure,
            severity="error" if not passed else "info"
        )

    def check_strategy_limit(
        self,
        strategy_id: str,
        current_exposure: float,
        new_exposure: float,
        max_strategy_exposure: float
    ) -> RiskCheckResult:
        """
        检查单策略仓位是否超限

        Args:
            strategy_id: 策略ID
            current_exposure: 该策略当前仓位占用（0-1）
            new_exposure: 新增仓位（0-1）
            max_strategy_exposure: 单策略最大仓位（0-1）

        Returns:
            检查结果
        """
        total = current_exposure + new_exposure
        passed = total <= max_strategy_exposure

        return RiskCheckResult(
            passed=passed,
            check_type="strategy_limit",
            message=f"策略 {strategy_id[:8]} 仓位 {total:.2%} {'≤' if passed else '>'} 限制 {max_strategy_exposure:.2%}",
            current_value=total,
            limit_value=max_strategy_exposure,
            severity="error" if not passed else "info"
        )

    def check_daily_loss(
        self,
        account_id: str,
        current_daily_loss: float,
        max_daily_loss: float
    ) -> RiskCheckResult:
        """
        检查是否触及单日亏损限制

        Args:
            account_id: 账户ID
            current_daily_loss: 当前单日亏损（0-1，正数表示亏损）
            max_daily_loss: 单日最大亏损限制（0-1）

        Returns:
            检查结果
        """
        passed = current_daily_loss <= max_daily_loss

        return RiskCheckResult(
            passed=passed,
            check_type="daily_loss",
            message=f"账户 {account_id} 当日亏损 {current_daily_loss:.2%} {'≤' if passed else '>'} 限制 {max_daily_loss:.2%}",
            current_value=current_daily_loss,
            limit_value=max_daily_loss,
            severity="error" if not passed else "warning" if current_daily_loss > max_daily_loss * 0.8 else "info"
        )

    def check_concurrent_trades(
        self,
        current_trades: int,
        max_concurrent_trades: int
    ) -> RiskCheckResult:
        """
        检查并发交易数是否超限

        Args:
            current_trades: 当前并发交易数
            max_concurrent_trades: 最大并发交易数

        Returns:
            检查结果
        """
        passed = current_trades < max_concurrent_trades

        return RiskCheckResult(
            passed=passed,
            check_type="concurrent_trades",
            message=f"并发交易 {current_trades} {'<' if passed else '≥'} 限制 {max_concurrent_trades}",
            current_value=float(current_trades),
            limit_value=float(max_concurrent_trades),
            severity="error" if not passed else "info"
        )


class RiskCalculator:
    """
    风险计算器

    计算各种风险指标
    """

    def __init__(self):
        """初始化风险计算器"""
        pass

    def calculate_exposure(
        self,
        volume: float,
        account_balance: float,
        symbol: str = "EURUSD"
    ) -> float:
        """
        计算仓位占用比例

        Args:
            volume: 手数
            account_balance: 账户余额
            symbol: 货币对

        Returns:
            仓位占用比例（0-1）
        """
        # 简化计算：1手 = 100,000基础货币
        # EURUSD: 1手约等于100,000 USD
        # 仓位占用 = 手数 × 100,000 / 账户余额

        if account_balance <= 0:
            return 1.0  # 避免除零错误

        lot_value = 100000  # 标准手的基础货币价值
        position_value = volume * lot_value
        exposure = position_value / account_balance

        return min(exposure, 1.0)  # 上限1.0（100%）

    def calculate_total_exposure(
        self,
        positions: List[Dict],
        account_balance: float
    ) -> float:
        """
        计算总仓位占用

        Args:
            positions: 持仓列表，每个元素包含volume和symbol
            account_balance: 账户余额

        Returns:
            总仓位占用比例（0-1）
        """
        total_exposure = 0.0

        for position in positions:
            volume = position.get('volume', 0.0)
            symbol = position.get('symbol', 'EURUSD')
            exposure = self.calculate_exposure(volume, account_balance, symbol)
            total_exposure += exposure

        return min(total_exposure, 1.0)

    def calculate_strategy_risk(
        self,
        volume: float,
        stop_loss: Optional[float],
        entry_price: float,
        account_balance: float
    ) -> float:
        """
        计算单笔交易风险

        Args:
            volume: 手数
            stop_loss: 止损价格（可选）
            entry_price: 入场价格
            account_balance: 账户余额

        Returns:
            风险比例（0-1）
        """
        if not stop_loss or account_balance <= 0:
            # 如果没有止损，使用默认风险2%
            return 0.02

        # 计算止损点数
        stop_loss_pips = abs(entry_price - stop_loss)

        # 计算风险金额
        # 1手 = 100,000基础货币，1 pip通常价值约10 USD（EURUSD）
        pip_value = 10  # USD per pip for 1 standard lot
        risk_amount = volume * stop_loss_pips * pip_value * 10000  # 转换为pip

        # 计算风险比例
        risk_ratio = risk_amount / account_balance

        return min(risk_ratio, 1.0)

    def calculate_correlation(
        self,
        strategies: List,
        lookback_period: int = 30
    ) -> float:
        """
        计算策略间相关性（简化实现）

        Args:
            strategies: 策略列表
            lookback_period: 回溯周期（天）

        Returns:
            平均相关性（0-1）
        """
        # V1：简化实现，返回默认值
        # V2+：基于历史收益率计算真实相关性
        return 0.3  # 假设30%的相关性


class RiskManager:
    """
    风险管理器（协调器）

    集成PolicyChecker和RiskCalculator，提供统一的风险评估接口
    """

    def __init__(self):
        """初始化风险管理器"""
        self.policy_checker = PolicyChecker()
        self.risk_calculator = RiskCalculator()

        # 缓存当前状态（V1简化，V2+从数据库读取）
        self._current_positions = []  # 当前持仓
        self._daily_pnl = {}  # 每日盈亏 {date: pnl}

    def evaluate_signal_risk(
        self,
        signal: Dict,
        account: Account,
        strategy_id: str
    ) -> Dict:
        """
        综合风险评估

        Args:
            signal: 信号字典 {symbol, direction, volume, entry_price, stop_loss, ...}
            account: 账户对象
            strategy_id: 策略ID

        Returns:
            {
                "approved": True/False,
                "adjusted_volume": 0.05,  # 调整后的手数
                "risk_score": 2.5,        # 风险分数（0-10，越高越危险）
                "checks": [...],          # 各项检查结果
                "reason": "检查通过"
            }
        """
        checks = []

        # 1. 计算新增仓位占用
        new_volume = signal.get('volume', 0.01)
        symbol = signal.get('symbol', 'EURUSD')
        new_exposure = self.risk_calculator.calculate_exposure(
            new_volume,
            account.balance,
            symbol
        )

        # 2. 检查总仓位
        current_total_exposure = self.risk_calculator.calculate_total_exposure(
            self._current_positions,
            account.balance
        )
        total_exposure_check = self.policy_checker.check_total_exposure(
            current_total_exposure,
            new_exposure,
            account.profile.max_total_exposure
        )
        checks.append(total_exposure_check)

        # 3. 检查单策略仓位
        current_strategy_exposure = self._get_strategy_exposure(strategy_id)
        strategy_limit_check = self.policy_checker.check_strategy_limit(
            strategy_id,
            current_strategy_exposure,
            new_exposure,
            account.profile.max_strategy_allocation
        )
        checks.append(strategy_limit_check)

        # 4. 检查单日亏损
        current_daily_loss = self._get_daily_loss(account.account_id)
        daily_loss_check = self.policy_checker.check_daily_loss(
            account.account_id,
            current_daily_loss,
            account.profile.max_daily_loss
        )
        checks.append(daily_loss_check)

        # 5. 检查并发交易数
        current_trades = len(self._current_positions)
        concurrent_trades_check = self.policy_checker.check_concurrent_trades(
            current_trades,
            account.profile.max_concurrent_trades
        )
        checks.append(concurrent_trades_check)

        # 6. 计算交易风险
        entry_price = signal.get('entry_price', 1.0)
        stop_loss = signal.get('stop_loss')
        trade_risk = self.risk_calculator.calculate_strategy_risk(
            new_volume,
            stop_loss,
            entry_price,
            account.balance
        )

        # 综合判断
        all_passed = all(check.passed for check in checks)
        critical_passed = all(
            check.passed for check in checks
            if check.severity == "error"
        )

        # 如果关键检查未通过，拒绝
        if not critical_passed:
            return {
                'approved': False,
                'adjusted_volume': 0.0,
                'risk_score': 10.0,  # 最高风险
                'checks': checks,
                'reason': "风险检查未通过：" + "; ".join(
                    check.message for check in checks
                    if not check.passed and check.severity == "error"
                )
            }

        # 计算风险分数（0-10）
        risk_score = self._calculate_risk_score(
            checks,
            trade_risk,
            new_exposure
        )

        # 如果风险分数过高，调整手数
        adjusted_volume = new_volume
        if risk_score > 7.0:
            # 按比例降低手数
            scale_factor = 7.0 / risk_score
            adjusted_volume = new_volume * scale_factor

        return {
            'approved': True,
            'adjusted_volume': adjusted_volume,
            'original_volume': new_volume,
            'risk_score': risk_score,
            'trade_risk': trade_risk,
            'checks': checks,
            'reason': "风险检查通过" if all_passed else "风险检查通过（有警告）"
        }

    def _get_strategy_exposure(self, strategy_id: str) -> float:
        """
        获取指定策略的当前仓位占用

        Args:
            strategy_id: 策略ID

        Returns:
            仓位占用比例（0-1）
        """
        # V1：简化实现，从缓存读取
        # V2+：从数据库查询
        strategy_positions = [
            p for p in self._current_positions
            if p.get('strategy_id') == strategy_id
        ]

        if not strategy_positions:
            return 0.0

        # 简化：假设10000余额
        return self.risk_calculator.calculate_total_exposure(
            strategy_positions,
            10000.0
        )

    def _get_daily_loss(self, account_id: str) -> float:
        """
        获取当前单日亏损

        Args:
            account_id: 账户ID

        Returns:
            亏损比例（0-1，正数表示亏损）
        """
        # V1：简化实现，返回0
        # V2+：从数据库查询今日交易记录并计算盈亏
        today = datetime.now().date()
        daily_pnl = self._daily_pnl.get(today, 0.0)

        # 如果是盈利，返回0；如果是亏损，返回亏损比例
        if daily_pnl >= 0:
            return 0.0
        else:
            # 假设账户余额10000
            return abs(daily_pnl) / 10000.0

    def _calculate_risk_score(
        self,
        checks: List[RiskCheckResult],
        trade_risk: float,
        exposure: float
    ) -> float:
        """
        计算综合风险分数（0-10）

        Args:
            checks: 检查结果列表
            trade_risk: 单笔交易风险
            exposure: 仓位占用

        Returns:
            风险分数（0-10，越高越危险）
        """
        score = 0.0

        # 1. 未通过的检查增加分数
        for check in checks:
            if not check.passed:
                if check.severity == "error":
                    score += 3.0
                elif check.severity == "warning":
                    score += 1.5

        # 2. 交易风险贡献
        # trade_risk: 0.02 = 低风险, 0.05 = 中风险, 0.10+ = 高风险
        risk_contribution = (trade_risk / 0.05) * 2.0  # 最高2分
        score += risk_contribution

        # 3. 仓位占用贡献
        # exposure: 0.1 = 低, 0.2 = 中, 0.3+ = 高
        exposure_contribution = (exposure / 0.1) * 1.0  # 最高1分
        score += exposure_contribution

        # 4. 接近限制的检查增加分数
        for check in checks:
            if check.passed and check.limit_value > 0:
                utilization = check.current_value / check.limit_value
                if utilization > 0.8:  # 超过80%使用率
                    score += (utilization - 0.8) * 5  # 最高1分

        return min(score, 10.0)

    def update_positions(self, positions: List[Dict]):
        """
        更新当前持仓缓存

        Args:
            positions: 持仓列表
        """
        self._current_positions = positions

    def record_trade_result(self, pnl: float, date: datetime = None):
        """
        记录交易结果

        Args:
            pnl: 盈亏金额（正数为盈利，负数为亏损）
            date: 日期（默认今天）
        """
        if date is None:
            date = datetime.now().date()

        if date not in self._daily_pnl:
            self._daily_pnl[date] = 0.0

        self._daily_pnl[date] += pnl

    def get_risk_summary(self, account: Account) -> Dict:
        """
        获取风险概览

        Args:
            account: 账户对象

        Returns:
            风险概览信息
        """
        # 计算当前指标
        current_total_exposure = self.risk_calculator.calculate_total_exposure(
            self._current_positions,
            account.balance
        )
        current_trades = len(self._current_positions)
        current_daily_loss = self._get_daily_loss(account.account_id)

        # 计算利用率
        exposure_utilization = current_total_exposure / account.profile.max_total_exposure \
            if account.profile.max_total_exposure > 0 else 0.0
        trades_utilization = current_trades / account.profile.max_concurrent_trades \
            if account.profile.max_concurrent_trades > 0 else 0.0
        loss_utilization = current_daily_loss / account.profile.max_daily_loss \
            if account.profile.max_daily_loss > 0 else 0.0

        return {
            'account_id': account.account_id,
            'current': {
                'total_exposure': current_total_exposure,
                'concurrent_trades': current_trades,
                'daily_loss': current_daily_loss,
            },
            'limits': {
                'max_total_exposure': account.profile.max_total_exposure,
                'max_concurrent_trades': account.profile.max_concurrent_trades,
                'max_daily_loss': account.profile.max_daily_loss,
            },
            'utilization': {
                'exposure': exposure_utilization,
                'trades': trades_utilization,
                'daily_loss': loss_utilization,
            },
            'status': self._get_risk_status(
                exposure_utilization,
                trades_utilization,
                loss_utilization
            )
        }

    def _get_risk_status(
        self,
        exposure_util: float,
        trades_util: float,
        loss_util: float
    ) -> str:
        """
        获取风险状态

        Args:
            exposure_util: 仓位利用率
            trades_util: 交易数利用率
            loss_util: 亏损利用率

        Returns:
            风险状态：low/medium/high/critical
        """
        max_util = max(exposure_util, trades_util, loss_util)

        if max_util >= 1.0:
            return "critical"  # 超过限制
        elif max_util >= 0.8:
            return "high"  # 超过80%
        elif max_util >= 0.5:
            return "medium"  # 超过50%
        else:
            return "low"  # 低于50%
