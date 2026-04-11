"""
StrategyRegistration Service - Orchestrator核心服务

职责：
1. 管理策略激活状态（只有激活的策略才能被编排）
2. 策略质量评估和分数计算
3. 作为所有编排调度决策的基础
4. 策略生命周期管理（candidate → active → archived）

V1实现：基于评估指标（recommendation_score, total_return等）
未来扩展：实时分数系统，持续评估策略质量
"""
from typing import List, Dict, Optional
from datetime import datetime

from src.common.models.strategy import Strategy, StrategyStatus
from src.services.orchestrator.repository.strategy_repo import StrategyRepository
from src.common.config.settings import settings


class ActivationCriteria:
    """策略激活标准"""

    def __init__(self, config: Dict):
        """
        初始化激活标准

        Args:
            config: 配置字典，包含各项阈值
        """
        self.min_recommendation_score = config.get('min_recommendation_score', 65)
        self.min_total_return = config.get('min_total_return', 0.03)  # 3%
        self.min_sharpe_ratio = config.get('min_sharpe_ratio', 0.50)
        self.max_drawdown = config.get('max_drawdown', 0.12)  # 12%
        self.min_win_rate = config.get('min_win_rate', 0.35)  # 35%
        self.min_profit_factor = config.get('min_profit_factor', 1.5)
        self.min_stability_score = config.get('min_stability_score', 0.45)

    def evaluate(self, strategy: Strategy) -> Dict:
        """
        评估策略是否满足激活条件

        Args:
            strategy: 策略对象

        Returns:
            {
                "qualified": True/False,
                "score": 75.5,  # 综合质量分数
                "reasons": ["推荐度达标", "收益率不足"],
                "checks": {
                    "recommendation_score": {"passed": True, "value": 75.5, "threshold": 65},
                    "total_return": {"passed": False, "value": 0.02, "threshold": 0.03},
                    ...
                }
            }
        """
        performance = strategy.performance or {}

        # 提取关键指标
        rec_summary = performance.get('recommendation_summary', {})
        rec_score = rec_summary.get('recommendation_score', 0)

        # 处理单货币对和多货币对两种数据结构
        if 'profiles' in performance:
            # 多货币对：使用default_symbol的profile
            default_symbol = performance.get('default_symbol', 'EURUSD')
            profile = performance['profiles'].get(default_symbol, {})
        else:
            # 单货币对：直接使用performance
            profile = performance

        total_return = profile.get('total_return', 0)
        sharpe_ratio = profile.get('sharpe_ratio', 0)
        max_drawdown = abs(profile.get('max_drawdown', 1.0))  # 取绝对值
        win_rate = profile.get('win_rate', 0)
        profit_factor = profile.get('profit_factor', 0)

        # 稳定性分数（综合多个指标）
        stability_factors = profile.get('stability_factors', {})
        stability_score = stability_factors.get('stability_score', 0)

        # 逐项检查
        checks = {
            'recommendation_score': {
                'passed': rec_score >= self.min_recommendation_score,
                'value': rec_score,
                'threshold': self.min_recommendation_score,
                'weight': 0.30  # 权重30%
            },
            'total_return': {
                'passed': total_return >= self.min_total_return,
                'value': total_return,
                'threshold': self.min_total_return,
                'weight': 0.20
            },
            'sharpe_ratio': {
                'passed': sharpe_ratio >= self.min_sharpe_ratio,
                'value': sharpe_ratio,
                'threshold': self.min_sharpe_ratio,
                'weight': 0.15
            },
            'max_drawdown': {
                'passed': max_drawdown <= self.max_drawdown,
                'value': max_drawdown,
                'threshold': self.max_drawdown,
                'weight': 0.15
            },
            'win_rate': {
                'passed': win_rate >= self.min_win_rate,
                'value': win_rate,
                'threshold': self.min_win_rate,
                'weight': 0.10
            },
            'profit_factor': {
                'passed': profit_factor >= self.min_profit_factor,
                'value': profit_factor,
                'threshold': self.min_profit_factor,
                'weight': 0.10
            }
        }

        # 计算通过的核心指标数量
        core_checks = ['recommendation_score', 'total_return', 'sharpe_ratio', 'max_drawdown']
        core_passed = sum(1 for key in core_checks if checks[key]['passed'])

        # 激活条件：核心指标至少通过3个
        qualified = core_passed >= 3

        # 计算综合质量分数（加权平均）
        quality_score = sum(
            (checks[key]['value'] / checks[key]['threshold'] * 100 * checks[key]['weight'])
            if checks[key]['threshold'] > 0 else 0
            for key in checks
        )
        quality_score = min(quality_score, 100)  # 上限100

        # 生成原因说明
        reasons = []
        for key, check in checks.items():
            label = {
                'recommendation_score': '推荐度',
                'total_return': '收益率',
                'sharpe_ratio': 'Sharpe比率',
                'max_drawdown': '最大回撤',
                'win_rate': '胜率',
                'profit_factor': '盈亏比'
            }.get(key, key)

            if check['passed']:
                reasons.append(f"✅ {label}达标 ({check['value']:.2%})" if key in ['total_return', 'max_drawdown', 'win_rate'] else f"✅ {label}达标 ({check['value']:.2f})")
            else:
                reasons.append(f"❌ {label}不足 ({check['value']:.2%} < {check['threshold']:.2%})" if key in ['total_return', 'max_drawdown', 'win_rate'] else f"❌ {label}不足 ({check['value']:.2f} < {check['threshold']:.2f})")

        return {
            'qualified': qualified,
            'quality_score': quality_score,
            'stability_score': stability_score,
            'core_passed': core_passed,
            'core_required': 3,
            'reasons': reasons,
            'checks': checks,
            'backtested_symbol': performance.get('backtested_symbol',
                                                performance.get('default_symbol', 'EURUSD'))
        }


class StrategyRegistration:
    """策略注册服务 - Orchestrator编排的基础"""

    def __init__(self):
        """初始化策略注册服务"""
        self.repo = StrategyRepository()

        # 加载配置
        orchestrator_config = settings.get('orchestrator', {})
        activation_config = orchestrator_config.get('activation', {})

        self.criteria = ActivationCriteria(activation_config)

        # 缓存（可选：减少数据库查询）
        self._cache = {}
        self._cache_ttl = 300  # 5分钟过期
        self._last_refresh = None

    def get_active_strategies(self, symbol: Optional[str] = None) -> List[Strategy]:
        """
        获取所有激活的策略（只有这些策略才能被编排）

        Args:
            symbol: 可选，筛选指定货币对的策略

        Returns:
            激活状态的策略列表
        """
        strategies = self.repo.get_by_status(StrategyStatus.ACTIVE)

        # 如果指定了货币对，进一步筛选
        if symbol:
            strategies = [
                s for s in strategies
                if self._strategy_supports_symbol(s, symbol)
            ]

        return strategies

    def get_candidate_strategies(self) -> List[Strategy]:
        """获取候选策略（待评估激活）"""
        return self.repo.get_by_status(StrategyStatus.CANDIDATE)

    def evaluate_strategy_quality(self, strategy: Strategy) -> Dict:
        """
        评估策略质量，判断是否符合激活条件

        Args:
            strategy: 策略对象

        Returns:
            评估结果字典（包含qualified, quality_score, reasons等）
        """
        return self.criteria.evaluate(strategy)

    def activate_strategy(self, strategy_id: str, force: bool = False) -> Dict:
        """
        激活策略

        Args:
            strategy_id: 策略ID
            force: 是否强制激活（忽略质量检查）

        Returns:
            {
                "success": True/False,
                "message": "激活成功",
                "strategy_id": "STR_xxx",
                "evaluation": {...}  # 质量评估结果
            }
        """
        strategy = self.repo.get_by_id(strategy_id)
        if not strategy:
            return {
                'success': False,
                'message': f'策略不存在: {strategy_id}'
            }

        # 检查当前状态
        if strategy.status == StrategyStatus.ACTIVE:
            return {
                'success': False,
                'message': '策略已经是激活状态',
                'strategy_id': strategy_id
            }

        # ❌ 归档的策略不能直接激活，必须先恢复到候选状态
        if strategy.status == StrategyStatus.ARCHIVED:
            return {
                'success': False,
                'message': '归档的策略不能直接激活，请先恢复到候选状态',
                'strategy_id': strategy_id
            }

        # 只有候选状态可以激活
        if strategy.status != StrategyStatus.CANDIDATE:
            return {
                'success': False,
                'message': f'只有候选状态的策略可以激活，当前状态: {strategy.status.value}',
                'strategy_id': strategy_id
            }

        # 评估质量
        evaluation = self.evaluate_strategy_quality(strategy)

        if not force and not evaluation['qualified']:
            return {
                'success': False,
                'message': '策略未达到激活标准',
                'strategy_id': strategy_id,
                'evaluation': evaluation
            }

        # 激活策略
        strategy.status = StrategyStatus.ACTIVE
        self.repo.update(strategy)

        # 清除缓存
        self._invalidate_cache()

        return {
            'success': True,
            'message': '策略激活成功' + (' (强制激活)' if force else ''),
            'strategy_id': strategy_id,
            'evaluation': evaluation
        }

    def deactivate_strategy(self, strategy_id: str, reason: str = None) -> Dict:
        """
        停用策略（但不归档）

        Args:
            strategy_id: 策略ID
            reason: 停用原因

        Returns:
            操作结果
        """
        strategy = self.repo.get_by_id(strategy_id)
        if not strategy:
            return {
                'success': False,
                'message': f'策略不存在: {strategy_id}'
            }

        if strategy.status != StrategyStatus.ACTIVE:
            return {
                'success': False,
                'message': '策略当前不是激活状态',
                'strategy_id': strategy_id
            }

        # 停用策略（回到candidate状态）
        strategy.status = StrategyStatus.CANDIDATE
        self.repo.update(strategy)

        self._invalidate_cache()

        return {
            'success': True,
            'message': f'策略已停用{": " + reason if reason else ""}',
            'strategy_id': strategy_id
        }

    def archive_strategy(self, strategy_id: str, reason: str = None) -> Dict:
        """
        归档策略

        只有候选状态的策略可以归档。
        归档后需要先恢复到候选状态才能激活。

        Args:
            strategy_id: 策略ID
            reason: 归档原因

        Returns:
            操作结果
        """
        strategy = self.repo.get_by_id(strategy_id)
        if not strategy:
            return {
                'success': False,
                'message': f'策略不存在: {strategy_id}'
            }

        # 只有候选状态可以归档
        if strategy.status != StrategyStatus.CANDIDATE:
            return {
                'success': False,
                'message': f'只有候选状态的策略可以归档，当前状态: {strategy.status.value}',
                'strategy_id': strategy_id
            }

        strategy.status = StrategyStatus.ARCHIVED
        self.repo.update(strategy)

        self._invalidate_cache()

        return {
            'success': True,
            'message': f'策略已归档{": " + reason if reason else ""}',
            'strategy_id': strategy_id
        }

    def restore_strategy(self, strategy_id: str, reason: str = None) -> Dict:
        """
        恢复归档的策略到候选状态

        Args:
            strategy_id: 策略ID
            reason: 恢复原因

        Returns:
            操作结果
        """
        strategy = self.repo.get_by_id(strategy_id)
        if not strategy:
            return {
                'success': False,
                'message': f'策略不存在: {strategy_id}'
            }

        # 只有归档状态可以恢复
        if strategy.status != StrategyStatus.ARCHIVED:
            return {
                'success': False,
                'message': f'只有归档状态的策略可以恢复，当前状态: {strategy.status.value}',
                'strategy_id': strategy_id
            }

        strategy.status = StrategyStatus.CANDIDATE
        self.repo.update(strategy)

        self._invalidate_cache()

        return {
            'success': True,
            'message': f'策略已恢复到候选状态{": " + reason if reason else ""}',
            'strategy_id': strategy_id
        }

    def delete_strategy(self, strategy_id: str) -> Dict:
        """
        删除策略（永久删除）

        从数据库中永久删除策略，不可恢复。

        Args:
            strategy_id: 策略ID

        Returns:
            操作结果
        """
        strategy = self.repo.get_by_id(strategy_id)
        if not strategy:
            return {
                'success': False,
                'message': f'策略不存在: {strategy_id}'
            }

        # 删除策略
        success = self.repo.delete(strategy_id)

        if success:
            self._invalidate_cache()
            return {
                'success': True,
                'message': f'策略已永久删除: {strategy_id}',
                'strategy_id': strategy_id
            }
        else:
            return {
                'success': False,
                'message': '删除失败',
                'strategy_id': strategy_id
            }

    def get_strategy_score(self, strategy_id: str) -> Optional[float]:
        """
        获取策略当前质量分数

        Args:
            strategy_id: 策略ID

        Returns:
            质量分数 0-100，如果策略不存在返回None
        """
        strategy = self.repo.get_by_id(strategy_id)
        if not strategy:
            return None

        evaluation = self.evaluate_strategy_quality(strategy)
        return evaluation['quality_score']

    def batch_evaluate_candidates(self) -> Dict:
        """
        批量评估所有候选策略，自动激活符合条件的策略

        Returns:
            {
                "evaluated": 10,
                "activated": 3,
                "results": [...]
            }
        """
        candidates = self.get_candidate_strategies()

        results = []
        activated_count = 0

        for strategy in candidates:
            evaluation = self.evaluate_strategy_quality(strategy)

            result = {
                'strategy_id': strategy.id,
                'strategy_name': strategy.name,
                'evaluation': evaluation
            }

            # 如果符合条件，自动激活
            if evaluation['qualified']:
                activate_result = self.activate_strategy(strategy.id)
                result['activated'] = activate_result['success']
                if activate_result['success']:
                    activated_count += 1
            else:
                result['activated'] = False

            results.append(result)

        return {
            'evaluated': len(candidates),
            'activated': activated_count,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }

    def get_registration_summary(self) -> Dict:
        """
        获取注册服务概览

        Returns:
            {
                "total": 50,
                "active": 12,
                "candidate": 35,
                "archived": 3,
                "activation_criteria": {...}
            }
        """
        all_strategies = self.repo.get_all()

        status_counts = {
            'active': 0,
            'candidate': 0,
            'archived': 0
        }

        for strategy in all_strategies:
            status_counts[strategy.status.value] += 1

        return {
            'total': len(all_strategies),
            'active': status_counts['active'],
            'candidate': status_counts['candidate'],
            'archived': status_counts['archived'],
            'activation_criteria': {
                'min_recommendation_score': self.criteria.min_recommendation_score,
                'min_total_return': self.criteria.min_total_return,
                'min_sharpe_ratio': self.criteria.min_sharpe_ratio,
                'max_drawdown': self.criteria.max_drawdown,
                'min_win_rate': self.criteria.min_win_rate,
                'min_profit_factor': self.criteria.min_profit_factor,
            },
            'timestamp': datetime.now().isoformat()
        }

    def _strategy_supports_symbol(self, strategy: Strategy, symbol: str) -> bool:
        """
        检查策略是否支持指定货币对

        Args:
            strategy: 策略对象
            symbol: 货币对代码

        Returns:
            是否支持
        """
        performance = strategy.performance or {}

        # 多货币对模式：检查profiles
        if 'profiles' in performance:
            return symbol in performance['profiles']

        # 单货币对模式：检查backtested_symbol
        backtested_symbol = performance.get('backtested_symbol', 'EURUSD')
        return symbol == backtested_symbol

    def _invalidate_cache(self):
        """清除缓存"""
        self._cache = {}
        self._last_refresh = None
