"""
AllocationEngine - 资金分配引擎

职责：
1. 纯算法层：只计算，不管理状态
2. 根据账户配置和策略Profile筛选策略
3. 计算资金分配比例
4. 提供多种分配算法

设计原则：
- 职责单一：只负责计算逻辑
- 无状态：不持有账户或策略数据
- 可测试：输入→输出，易于单元测试
- 可扩展：新增算法不影响其他模块
"""
from typing import List, Dict, Tuple
from dataclasses import dataclass

from src.services.orchestrator.service.account_manager import Account, RiskType


@dataclass
class AllocationResult:
    """
    资金分配结果

    包含每个策略的分配信息
    """
    strategy_id: str      # 策略ID
    strategy_name: str    # 策略名称
    allocation: float     # 分配比例（0-1）
    amount: float         # 分配金额
    reason: str          # 分配理由


class AllocationEngine:
    """
    资金分配引擎

    提供多种分配算法：
    - equal_weight: 等权重分配
    - performance_weight: 按表现加权（V2+）
    - risk_parity: 风险平价（V2+）
    """

    def __init__(self):
        """初始化分配引擎"""
        pass

    def allocate(
        self,
        strategies: List,
        account: Account,
        method: str = None
    ) -> List[AllocationResult]:
        """
        计算资金分配

        Args:
            strategies: 策略列表
            account: 账户对象
            method: 分配方法（如不指定，使用账户配置）

        Returns:
            分配结果列表
        """
        if not strategies:
            return []

        # 确定分配方法
        if method is None:
            method = self._get_default_method(account)

        # 调用对应的分配算法
        if method == "equal_weight":
            return self._allocate_equal_weight(strategies, account)
        elif method == "performance_weight":
            return self._allocate_performance_weight(strategies, account)
        elif method == "risk_parity":
            return self._allocate_risk_parity(strategies, account)
        else:
            # 默认：等权重
            return self._allocate_equal_weight(strategies, account)

    def _get_default_method(self, account: Account) -> str:
        """
        根据账户风险类型确定默认分配方法

        Args:
            account: 账户对象

        Returns:
            分配方法名称
        """
        risk_type = account.profile.risk_type

        if risk_type == RiskType.BALANCED:
            return "equal_weight"
        elif risk_type == RiskType.AGGRESSIVE:
            return "performance_weight"  # V2+实现
        elif risk_type == RiskType.CONSERVATIVE:
            return "risk_parity"  # V2+实现
        else:
            return "equal_weight"

    def _allocate_equal_weight(
        self,
        strategies: List,
        account: Account
    ) -> List[AllocationResult]:
        """
        等权重分配（V1实现）

        每个策略分配相同的资金比例

        Args:
            strategies: 策略列表
            account: 账户对象

        Returns:
            分配结果列表
        """
        n = len(strategies)
        if n == 0:
            return []

        # 计算每个策略的分配比例
        allocation_per_strategy = 1.0 / n

        # 检查是否超过单策略上限
        max_strategy_allocation = account.profile.max_strategy_allocation
        if allocation_per_strategy > max_strategy_allocation:
            allocation_per_strategy = max_strategy_allocation

        # 生成分配结果
        results = []
        for strategy in strategies:
            amount = account.balance * allocation_per_strategy

            results.append(AllocationResult(
                strategy_id=strategy.id,
                strategy_name=strategy.name,
                allocation=allocation_per_strategy,
                amount=amount,
                reason=f"等权重分配 (1/{n})"
            ))

        return results

    def _allocate_performance_weight(
        self,
        strategies: List,
        account: Account
    ) -> List[AllocationResult]:
        """
        按表现加权分配（V2+实现）

        根据策略的质量分数、收益率等指标加权分配

        Args:
            strategies: 策略列表
            account: 账户对象

        Returns:
            分配结果列表
        """
        # V1：暂时使用等权重
        # V2+：实现加权逻辑
        #   权重 = f(quality_score, sharpe_ratio, total_return)
        #   allocation = weight_i / sum(weights)
        return self._allocate_equal_weight(strategies, account)

    def _allocate_risk_parity(
        self,
        strategies: List,
        account: Account
    ) -> List[AllocationResult]:
        """
        风险平价分配（V2+实现）

        使每个策略贡献相同的风险

        Args:
            strategies: 策略列表
            account: 账户对象

        Returns:
            分配结果列表
        """
        # V1：暂时使用等权重
        # V2+：实现风险平价逻辑
        #   risk_contribution_i = allocation_i * volatility_i
        #   目标：所有risk_contribution相等
        return self._allocate_equal_weight(strategies, account)

    def calculate_total_exposure(
        self,
        allocations: List[AllocationResult]
    ) -> float:
        """
        计算总仓位占用

        Args:
            allocations: 分配结果列表

        Returns:
            总仓位占用比例（0-1）
        """
        return sum(alloc.allocation for alloc in allocations)

    def validate_allocation(
        self,
        allocations: List[AllocationResult],
        account: Account
    ) -> Tuple[bool, str]:
        """
        验证分配是否符合账户限制

        Args:
            allocations: 分配结果列表
            account: 账户对象

        Returns:
            (是否有效, 原因)
        """
        # 检查总仓位
        total_exposure = self.calculate_total_exposure(allocations)
        max_total = account.profile.max_total_exposure

        if total_exposure > max_total:
            return False, f"总仓位 {total_exposure:.2%} 超过限制 {max_total:.2%}"

        # 检查单策略仓位
        max_strategy = account.profile.max_strategy_allocation
        for alloc in allocations:
            if alloc.allocation > max_strategy:
                return False, f"策略 {alloc.strategy_name} 分配 {alloc.allocation:.2%} 超过限制 {max_strategy:.2%}"

        # 检查策略数量
        max_strategies = account.allocation_config.max_strategies
        if len(allocations) > max_strategies:
            return False, f"策略数量 {len(allocations)} 超过限制 {max_strategies}"

        return True, "分配有效"

    def adjust_allocation_for_risk(
        self,
        allocations: List[AllocationResult],
        account: Account
    ) -> List[AllocationResult]:
        """
        根据风险限制调整分配

        如果分配超过限制，按比例缩减

        Args:
            allocations: 分配结果列表
            account: 账户对象

        Returns:
            调整后的分配结果列表
        """
        # 检查总仓位
        total_exposure = self.calculate_total_exposure(allocations)
        max_total = account.profile.max_total_exposure

        if total_exposure <= max_total:
            return allocations  # 无需调整

        # 按比例缩减
        scale_factor = max_total / total_exposure

        adjusted = []
        for alloc in allocations:
            new_allocation = alloc.allocation * scale_factor
            new_amount = account.balance * new_allocation

            adjusted.append(AllocationResult(
                strategy_id=alloc.strategy_id,
                strategy_name=alloc.strategy_name,
                allocation=new_allocation,
                amount=new_amount,
                reason=f"{alloc.reason} (风险调整: {scale_factor:.2%})"
            ))

        return adjusted

    def get_allocation_summary(
        self,
        allocations: List[AllocationResult]
    ) -> Dict:
        """
        获取分配概览

        Args:
            allocations: 分配结果列表

        Returns:
            分配概览信息
        """
        if not allocations:
            return {
                'total_strategies': 0,
                'total_allocation': 0.0,
                'total_amount': 0.0,
                'allocations': []
            }

        total_allocation = sum(a.allocation for a in allocations)
        total_amount = sum(a.amount for a in allocations)

        return {
            'total_strategies': len(allocations),
            'total_allocation': total_allocation,
            'total_amount': total_amount,
            'allocations': [
                {
                    'strategy_id': a.strategy_id,
                    'strategy_name': a.strategy_name,
                    'allocation': a.allocation,
                    'allocation_pct': f"{a.allocation:.2%}",
                    'amount': a.amount,
                    'reason': a.reason
                }
                for a in allocations
            ]
        }


class PortfolioBuilder:
    """
    组合构建器

    组合AllocationEngine和其他模块，构建完整的投资组合
    """

    def __init__(self, allocation_engine: AllocationEngine = None):
        """初始化组合构建器"""
        self.allocation_engine = allocation_engine or AllocationEngine()

    def build_portfolio(
        self,
        strategies: List,
        account: Account,
        method: str = None
    ) -> Dict:
        """
        构建投资组合

        Args:
            strategies: 策略列表
            account: 账户对象
            method: 分配方法

        Returns:
            完整的组合信息
        """
        # 1. 计算分配
        allocations = self.allocation_engine.allocate(
            strategies,
            account,
            method=method
        )

        # 2. 根据风险限制调整
        allocations = self.allocation_engine.adjust_allocation_for_risk(
            allocations,
            account
        )

        # 3. 验证
        valid, reason = self.allocation_engine.validate_allocation(
            allocations,
            account
        )

        # 4. 生成概览
        summary = self.allocation_engine.get_allocation_summary(allocations)

        return {
            'account_id': account.account_id,
            'account_name': account.name,
            'valid': valid,
            'validation_message': reason,
            'summary': summary,
            'allocations': allocations,
        }
