"""
AccountManager - 账户配置管理

职责：
1. 管理账户配置（每个账户 = 完整配置单元）
2. 维护账户级策略组合
3. 提供账户信息查询

设计原则：
- 账户中心设计：每个账户有独立的策略选择、资金分配、风险偏好
- 支持多账户：保守账户、激进账户等
- 配置集中管理，易于理解和维护
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.services.orchestrator.service.strategy_registration import StrategyRegistration
from src.common.config.settings import settings


class RiskType(str, Enum):
    """风险类型"""
    BALANCED = "balanced"        # 平衡型
    AGGRESSIVE = "aggressive"    # 进取型
    CONSERVATIVE = "conservative"  # 保守型


class AccountStatus(str, Enum):
    """账户状态"""
    ACTIVE = "active"      # 激活
    PAUSED = "paused"      # 暂停
    CLOSED = "closed"      # 关闭


@dataclass
class AccountProfile:
    """
    账户风险配置

    定义账户的风险偏好和限制
    """
    risk_type: RiskType = RiskType.BALANCED  # 风险类型

    # 仓位限制
    max_total_exposure: float = 0.30     # 总仓位上限（30%）
    max_strategy_allocation: float = 0.10  # 单策略上限（10%）

    # 风险限制
    max_daily_loss: float = 0.05         # 单日最大亏损（5%）
    max_concurrent_trades: int = 10      # 最大并发交易数

    # 长短线配比（未来扩展）
    short_term_ratio: float = 0.50       # 短线占比（50%）
    long_term_ratio: float = 0.50        # 长线占比（50%）

    def __post_init__(self):
        """验证配置合法性"""
        assert self.max_total_exposure <= 1.0, "总仓位上限不能超过100%"
        assert self.max_strategy_allocation <= self.max_total_exposure, \
            "单策略上限不能超过总仓位上限"
        assert self.short_term_ratio + self.long_term_ratio == 1.0, \
            "长短线配比总和必须为100%"


@dataclass
class AllocationConfig:
    """
    资金分配配置

    定义如何选择策略和分配资金
    """
    mode: str = "balanced"  # balanced/aggressive/conservative
    max_strategies: int = 5  # 最多同时运行的策略数

    # 目标货币对
    target_symbols: List[str] = field(default_factory=lambda: ["EURUSD"])

    # 策略筛选条件（用于从激活策略中进一步筛选）
    strategy_filters: Dict = field(default_factory=dict)
    # 示例：
    # {
    #   "min_recommendation_score": 70,  # 最低推荐度70（比激活标准65更高）
    #   "min_sharpe_ratio": 0.60,
    #   "market_regime": "trend"  # 只选趋势策略
    # }

    # 再平衡
    rebalance_interval_hours: int = 24  # 每24小时重新平衡


@dataclass
class Account:
    """
    账户对象

    每个账户是一个完整的配置单元，包含：
    - 账户信息（ID、名称、余额）
    - 风险配置（AccountProfile）
    - 分配配置（AllocationConfig）
    - 当前状态
    """
    account_id: str  # 账户ID
    name: str        # 账户名称
    balance: float   # 账户余额

    profile: AccountProfile = field(default_factory=AccountProfile)
    allocation_config: AllocationConfig = field(default_factory=AllocationConfig)

    status: AccountStatus = AccountStatus.ACTIVE

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'account_id': self.account_id,
            'name': self.name,
            'balance': self.balance,
            'status': self.status.value,
            'profile': {
                'risk_type': self.profile.risk_type.value,
                'max_total_exposure': self.profile.max_total_exposure,
                'max_strategy_allocation': self.profile.max_strategy_allocation,
                'max_daily_loss': self.profile.max_daily_loss,
                'max_concurrent_trades': self.profile.max_concurrent_trades,
                'short_term_ratio': self.profile.short_term_ratio,
                'long_term_ratio': self.profile.long_term_ratio,
            },
            'allocation_config': {
                'mode': self.allocation_config.mode,
                'max_strategies': self.allocation_config.max_strategies,
                'target_symbols': self.allocation_config.target_symbols,
                'strategy_filters': self.allocation_config.strategy_filters,
                'rebalance_interval_hours': self.allocation_config.rebalance_interval_hours,
            },
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class AccountManager:
    """
    账户管理器

    负责账户配置的管理和查询
    V1：支持单账户
    V2+：支持多账户
    """

    def __init__(self):
        """初始化账户管理器"""
        self.registration = StrategyRegistration()

        # V1：单账户模式，从配置文件加载
        self._default_account = self._load_default_account()

        # V2+：多账户支持
        # self._accounts = {}  # {account_id: Account}

    def _load_default_account(self) -> Account:
        """
        从配置文件加载默认账户

        V1实现：读取config/development.yaml中的orchestrator配置
        """
        orchestrator_config = settings.get('orchestrator', {})

        # 读取资金配置
        portfolio_config = orchestrator_config.get('portfolio', {})
        balance = portfolio_config.get('initial_balance', 10000.0)
        max_total_exposure = portfolio_config.get('max_total_exposure', 0.30)
        max_strategy_allocation = portfolio_config.get('max_strategy_allocation', 0.10)

        # 读取分配配置
        allocation_config_dict = orchestrator_config.get('allocation', {})
        mode = allocation_config_dict.get('mode', 'balanced')
        max_strategies = allocation_config_dict.get('max_strategies', 5)
        rebalance_interval = allocation_config_dict.get('rebalance_interval_hours', 24)

        # 读取风险配置
        risk_config = orchestrator_config.get('risk', {})
        max_daily_loss = risk_config.get('max_daily_loss', 0.05)
        max_concurrent_trades = risk_config.get('max_concurrent_trades', 10)

        # 构建AccountProfile
        profile = AccountProfile(
            risk_type=RiskType(mode),
            max_total_exposure=max_total_exposure,
            max_strategy_allocation=max_strategy_allocation,
            max_daily_loss=max_daily_loss,
            max_concurrent_trades=max_concurrent_trades,
        )

        # 构建AllocationConfig
        allocation_config = AllocationConfig(
            mode=mode,
            max_strategies=max_strategies,
            target_symbols=["EURUSD"],  # V1默认
            rebalance_interval_hours=rebalance_interval,
        )

        # 创建默认账户
        return Account(
            account_id="default",
            name="Default Account",
            balance=balance,
            profile=profile,
            allocation_config=allocation_config,
        )

    def get_account(self, account_id: str = "default") -> Optional[Account]:
        """
        获取账户配置

        Args:
            account_id: 账户ID，V1默认为"default"

        Returns:
            账户对象，如果不存在返回None
        """
        if account_id == "default":
            return self._default_account

        # V2+: 从数据库或缓存获取
        # return self._accounts.get(account_id)
        return None

    def update_account_profile(
        self,
        account_id: str,
        profile: AccountProfile
    ) -> bool:
        """
        更新账户风险配置

        Args:
            account_id: 账户ID
            profile: 新的风险配置

        Returns:
            是否更新成功
        """
        account = self.get_account(account_id)
        if not account:
            return False

        account.profile = profile
        account.updated_at = datetime.now()

        # V2+: 持久化到数据库
        return True

    def update_allocation_config(
        self,
        account_id: str,
        allocation_config: AllocationConfig
    ) -> bool:
        """
        更新账户分配配置

        Args:
            account_id: 账户ID
            allocation_config: 新的分配配置

        Returns:
            是否更新成功
        """
        account = self.get_account(account_id)
        if not account:
            return False

        account.allocation_config = allocation_config
        account.updated_at = datetime.now()

        return True

    def get_account_strategies(self, account_id: str = "default") -> List:
        """
        获取账户的策略列表（已激活的）

        根据账户的allocation_config筛选策略

        Args:
            account_id: 账户ID

        Returns:
            符合账户配置的激活策略列表
        """
        account = self.get_account(account_id)
        if not account:
            return []

        # 获取所有激活的策略
        all_active = self.registration.get_active_strategies()

        # 根据账户配置筛选
        filtered = self._filter_strategies_by_account(all_active, account)

        # 限制数量
        max_strategies = account.allocation_config.max_strategies
        return filtered[:max_strategies]

    def _filter_strategies_by_account(self, strategies: List, account: Account) -> List:
        """
        根据账户配置筛选策略

        Args:
            strategies: 策略列表
            account: 账户对象

        Returns:
            筛选后的策略列表
        """
        result = []

        config = account.allocation_config
        target_symbols = set(config.target_symbols)
        filters = config.strategy_filters

        for strategy in strategies:
            # 检查货币对
            performance = strategy.performance or {}
            if 'profiles' in performance:
                # 多货币对
                strategy_symbols = set(performance['profiles'].keys())
                if not strategy_symbols.intersection(target_symbols):
                    continue
            else:
                # 单货币对
                backtested_symbol = performance.get('backtested_symbol', 'EURUSD')
                if backtested_symbol not in target_symbols:
                    continue

            # 应用自定义筛选条件
            if not self._apply_strategy_filters(strategy, filters):
                continue

            result.append(strategy)

        return result

    def _apply_strategy_filters(self, strategy, filters: Dict) -> bool:
        """
        应用策略筛选条件

        Args:
            strategy: 策略对象
            filters: 筛选条件字典

        Returns:
            是否通过筛选
        """
        if not filters:
            return True

        performance = strategy.performance or {}

        # 获取指标（处理单/多货币对）
        if 'profiles' in performance:
            # 多货币对：使用default_symbol的profile
            default_symbol = performance.get('default_symbol', 'EURUSD')
            profile = performance['profiles'].get(default_symbol, {})
        else:
            profile = performance

        rec_summary = performance.get('recommendation_summary', {})

        # 应用各项筛选
        for key, threshold in filters.items():
            if key == 'min_recommendation_score':
                score = rec_summary.get('recommendation_score', 0)
                if score < threshold:
                    return False

            elif key == 'min_sharpe_ratio':
                sharpe = profile.get('sharpe_ratio', 0)
                if sharpe < threshold:
                    return False

            elif key == 'max_drawdown':
                drawdown = abs(profile.get('max_drawdown', 1.0))
                if drawdown > threshold:
                    return False

            elif key == 'market_regime':
                # 根据策略名称或标签判断类型（简化实现）
                # 未来可以在strategy中添加explicit的regime字段
                regime = filters[key]
                strategy_name = strategy.name.lower()

                if regime == 'trend' and 'ma' not in strategy_name:
                    return False
                # 可扩展其他regime类型

        return True

    def get_available_balance(self, account_id: str = "default") -> float:
        """
        获取账户可用余额

        Args:
            account_id: 账户ID

        Returns:
            可用余额
        """
        account = self.get_account(account_id)
        if not account:
            return 0.0

        # V1：简化实现，返回总余额
        # V2+：减去已占用的资金
        return account.balance

    def get_account_summary(self, account_id: str = "default") -> Dict:
        """
        获取账户概览

        Args:
            account_id: 账户ID

        Returns:
            账户概览信息
        """
        account = self.get_account(account_id)
        if not account:
            return {}

        strategies = self.get_account_strategies(account_id)

        return {
            'account': account.to_dict(),
            'strategies': {
                'total': len(strategies),
                'strategies': [
                    {
                        'id': s.id,
                        'name': s.name,
                        'status': s.status.value,
                    }
                    for s in strategies
                ]
            },
            'balance': {
                'total': account.balance,
                'available': self.get_available_balance(account_id),
                'allocated': 0.0,  # V2+: 计算已分配资金
            }
        }
