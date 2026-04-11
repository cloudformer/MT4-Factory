"""
SignalEvaluator - 信号评估器

职责：
1. 协调所有模块进行信号决策
2. 整合各模块的评估结果
3. 记录决策链和理由

设计原则：
- 集成点：调用StrategyRegistration、AccountManager、AllocationEngine、RiskManager
- 不实现具体逻辑，只负责编排调用
- 提供统一的决策接口
- 记录完整决策链，便于审计
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.services.orchestrator.service.strategy_registration import StrategyRegistration
from src.services.orchestrator.service.account_manager import AccountManager
from src.services.orchestrator.service.allocation_engine import AllocationEngine
from src.services.orchestrator.service.risk_manager import RiskManager


class DecisionType(str, Enum):
    """决策类型"""
    APPROVED = "approved"      # 批准执行
    REJECTED = "rejected"      # 拒绝执行
    ADJUSTED = "adjusted"      # 调整后执行


@dataclass
class DecisionStep:
    """
    决策步骤

    记录决策链中的单个步骤
    """
    step: int                # 步骤序号
    module: str              # 模块名称
    action: str              # 执行动作
    result: str              # 结果
    passed: bool             # 是否通过
    details: Dict = field(default_factory=dict)  # 详细信息


@dataclass
class SignalDecision:
    """
    信号决策结果

    包含最终决策和完整的决策链
    """
    signal_id: str                          # 信号ID
    decision: DecisionType                  # 决策类型
    approved: bool                          # 是否批准

    # 调整后的参数
    original_volume: float                  # 原始手数
    adjusted_volume: float                  # 调整后手数

    # 决策链
    steps: List[DecisionStep] = field(default_factory=list)  # 决策步骤

    # 综合评估
    reason: str = ""                        # 决策理由
    risk_score: float = 0.0                 # 风险分数（0-10）
    confidence: float = 0.0                 # 决策置信度（0-1）

    # 元数据
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'signal_id': self.signal_id,
            'decision': self.decision.value,
            'approved': self.approved,
            'original_volume': self.original_volume,
            'adjusted_volume': self.adjusted_volume,
            'steps': [
                {
                    'step': s.step,
                    'module': s.module,
                    'action': s.action,
                    'result': s.result,
                    'passed': s.passed,
                    'details': s.details
                }
                for s in self.steps
            ],
            'reason': self.reason,
            'risk_score': self.risk_score,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat()
        }


class SignalEvaluator:
    """
    信号评估器（协调器）

    集成所有Orchestrator模块，进行信号决策
    """

    def __init__(self):
        """初始化信号评估器"""
        self.registration = StrategyRegistration()
        self.account_manager = AccountManager()
        self.allocation_engine = AllocationEngine()
        self.risk_manager = RiskManager()

    def evaluate_signal(
        self,
        signal: Dict,
        account_id: str = "default"
    ) -> SignalDecision:
        """
        评估信号

        完整的决策链：
        1. StrategyRegistration检查 - 策略是否激活
        2. AccountManager查询 - 账户配置和策略列表
        3. AllocationEngine计算 - 资金分配和手数调整
        4. RiskManager检查 - 风险限制和综合评估
        5. 生成最终决策

        Args:
            signal: 信号字典
            account_id: 账户ID

        Returns:
            SignalDecision对象
        """
        signal_id = signal.get('id', 'unknown')
        strategy_id = signal.get('strategy_id')
        original_volume = signal.get('volume', 0.01)

        # 初始化决策对象
        decision = SignalDecision(
            signal_id=signal_id,
            decision=DecisionType.REJECTED,  # 默认拒绝
            approved=False,
            original_volume=original_volume,
            adjusted_volume=0.0
        )

        # === Step 1: 策略注册检查 ===
        step1_result = self._check_strategy_registration(strategy_id)
        decision.steps.append(step1_result)

        if not step1_result.passed:
            decision.reason = f"策略未激活: {step1_result.result}"
            decision.confidence = 0.0
            return decision

        # === Step 2: 账户配置查询 ===
        step2_result = self._check_account_config(strategy_id, account_id)
        decision.steps.append(step2_result)

        if not step2_result.passed:
            decision.reason = f"账户检查失败: {step2_result.result}"
            decision.confidence = 0.0
            return decision

        account = step2_result.details.get('account')

        # === Step 3: 资金分配计算 ===
        step3_result = self._calculate_allocation(strategy_id, account, original_volume)
        decision.steps.append(step3_result)

        if not step3_result.passed:
            decision.reason = f"资金分配失败: {step3_result.result}"
            decision.confidence = 0.0
            return decision

        suggested_volume = step3_result.details.get('suggested_volume', original_volume)

        # === Step 4: 风险检查 ===
        # 更新信号的手数为分配建议的手数
        signal_with_allocation = signal.copy()
        signal_with_allocation['volume'] = suggested_volume

        step4_result = self._check_risk(signal_with_allocation, account, strategy_id)
        decision.steps.append(step4_result)

        if not step4_result.passed:
            decision.reason = f"风险检查未通过: {step4_result.result}"
            decision.risk_score = step4_result.details.get('risk_score', 10.0)
            decision.confidence = 0.0
            return decision

        # === Step 5: 生成最终决策 ===
        adjusted_volume = step4_result.details.get('adjusted_volume', suggested_volume)
        risk_score = step4_result.details.get('risk_score', 0.0)

        # 判断决策类型
        if adjusted_volume == original_volume:
            decision_type = DecisionType.APPROVED
        elif adjusted_volume > 0:
            decision_type = DecisionType.ADJUSTED
        else:
            decision_type = DecisionType.REJECTED

        # 计算置信度（基于各步骤的结果）
        confidence = self._calculate_confidence(decision.steps, risk_score)

        # 更新决策
        decision.decision = decision_type
        decision.approved = (decision_type != DecisionType.REJECTED)
        decision.adjusted_volume = adjusted_volume
        decision.risk_score = risk_score
        decision.confidence = confidence
        decision.reason = self._generate_reason(decision_type, decision.steps, risk_score)

        # 记录最终决策步骤
        decision.steps.append(DecisionStep(
            step=5,
            module="SignalEvaluator",
            action="生成最终决策",
            result=decision_type.value,
            passed=True,
            details={
                'adjusted_volume': adjusted_volume,
                'risk_score': risk_score,
                'confidence': confidence
            }
        ))

        return decision

    def _check_strategy_registration(self, strategy_id: str) -> DecisionStep:
        """
        Step 1: 检查策略是否激活

        Args:
            strategy_id: 策略ID

        Returns:
            决策步骤
        """
        try:
            # 获取所有激活的策略
            active_strategies = self.registration.get_active_strategies()
            active_ids = [s.id for s in active_strategies]

            if strategy_id in active_ids:
                # 获取质量分数
                quality_score = self.registration.get_strategy_score(strategy_id)

                return DecisionStep(
                    step=1,
                    module="StrategyRegistration",
                    action="检查策略激活状态",
                    result=f"策略已激活 (质量分数: {quality_score:.1f})",
                    passed=True,
                    details={
                        'strategy_id': strategy_id,
                        'is_active': True,
                        'quality_score': quality_score
                    }
                )
            else:
                return DecisionStep(
                    step=1,
                    module="StrategyRegistration",
                    action="检查策略激活状态",
                    result="策略未激活或不存在",
                    passed=False,
                    details={
                        'strategy_id': strategy_id,
                        'is_active': False
                    }
                )

        except Exception as e:
            return DecisionStep(
                step=1,
                module="StrategyRegistration",
                action="检查策略激活状态",
                result=f"检查失败: {str(e)}",
                passed=False,
                details={'error': str(e)}
            )

    def _check_account_config(self, strategy_id: str, account_id: str) -> DecisionStep:
        """
        Step 2: 检查账户配置

        Args:
            strategy_id: 策略ID
            account_id: 账户ID

        Returns:
            决策步骤
        """
        try:
            # 获取账户
            account = self.account_manager.get_account(account_id)

            if not account:
                return DecisionStep(
                    step=2,
                    module="AccountManager",
                    action="查询账户配置",
                    result=f"账户不存在: {account_id}",
                    passed=False,
                    details={'account_id': account_id}
                )

            # 检查账户状态
            if account.status.value != 'active':
                return DecisionStep(
                    step=2,
                    module="AccountManager",
                    action="查询账户配置",
                    result=f"账户状态异常: {account.status.value}",
                    passed=False,
                    details={
                        'account_id': account_id,
                        'status': account.status.value
                    }
                )

            # 检查策略是否在账户的策略列表中
            account_strategies = self.account_manager.get_account_strategies(account_id)
            strategy_ids = [s.id for s in account_strategies]

            in_account = strategy_id in strategy_ids

            return DecisionStep(
                step=2,
                module="AccountManager",
                action="查询账户配置",
                result=f"账户配置有效 (策略{'在' if in_account else '不在'}账户列表)",
                passed=True,  # V1: 即使不在列表也通过，只是记录
                details={
                    'account_id': account_id,
                    'account_name': account.name,
                    'balance': account.balance,
                    'risk_type': account.profile.risk_type.value,
                    'strategy_in_account': in_account,
                    'account': account
                }
            )

        except Exception as e:
            return DecisionStep(
                step=2,
                module="AccountManager",
                action="查询账户配置",
                result=f"查询失败: {str(e)}",
                passed=False,
                details={'error': str(e)}
            )

    def _calculate_allocation(
        self,
        strategy_id: str,
        account,
        original_volume: float
    ) -> DecisionStep:
        """
        Step 3: 计算资金分配

        Args:
            strategy_id: 策略ID
            account: 账户对象
            original_volume: 原始手数

        Returns:
            决策步骤
        """
        try:
            # 获取账户的所有策略
            strategies = self.account_manager.get_account_strategies(account.account_id)

            # 计算分配
            allocations = self.allocation_engine.allocate(
                strategies,
                account
            )

            # 找到该策略的分配
            strategy_allocation = None
            for alloc in allocations:
                if alloc.strategy_id == strategy_id:
                    strategy_allocation = alloc
                    break

            if not strategy_allocation:
                # 策略不在分配列表中
                return DecisionStep(
                    step=3,
                    module="AllocationEngine",
                    action="计算资金分配",
                    result="策略未获得资金分配",
                    passed=False,
                    details={
                        'strategy_id': strategy_id,
                        'allocated': False
                    }
                )

            # 根据分配比例调整手数
            # allocation.allocation 是资金占比（0-1）
            # 我们可以根据这个比例来限制最大手数
            max_allowed_volume = strategy_allocation.allocation * 10  # 简化：每10%分配对应1手上限

            suggested_volume = min(original_volume, max_allowed_volume)

            return DecisionStep(
                step=3,
                module="AllocationEngine",
                action="计算资金分配",
                result=f"分配 {strategy_allocation.allocation:.2%} ({strategy_allocation.amount:.2f} USD)",
                passed=True,
                details={
                    'strategy_id': strategy_id,
                    'allocation': strategy_allocation.allocation,
                    'amount': strategy_allocation.amount,
                    'original_volume': original_volume,
                    'suggested_volume': suggested_volume,
                    'reason': strategy_allocation.reason
                }
            )

        except Exception as e:
            return DecisionStep(
                step=3,
                module="AllocationEngine",
                action="计算资金分配",
                result=f"计算失败: {str(e)}",
                passed=False,
                details={'error': str(e)}
            )

    def _check_risk(
        self,
        signal: Dict,
        account,
        strategy_id: str
    ) -> DecisionStep:
        """
        Step 4: 风险检查

        Args:
            signal: 信号字典（已调整手数）
            account: 账户对象
            strategy_id: 策略ID

        Returns:
            决策步骤
        """
        try:
            # 调用RiskManager进行风险评估
            risk_result = self.risk_manager.evaluate_signal_risk(
                signal,
                account,
                strategy_id
            )

            approved = risk_result.get('approved', False)
            adjusted_volume = risk_result.get('adjusted_volume', 0.0)
            risk_score = risk_result.get('risk_score', 10.0)
            reason = risk_result.get('reason', '')

            # 提取检查结果摘要
            checks = risk_result.get('checks', [])
            failed_checks = [c for c in checks if not c.passed]
            critical_failures = [c for c in failed_checks if c.severity == 'error']

            if approved:
                result_text = f"风险检查通过 (风险分数: {risk_score:.1f})"
            else:
                result_text = f"风险检查未通过: {len(critical_failures)} 项关键限制"

            return DecisionStep(
                step=4,
                module="RiskManager",
                action="风险检查",
                result=result_text,
                passed=approved,
                details={
                    'approved': approved,
                    'adjusted_volume': adjusted_volume,
                    'original_volume': signal.get('volume'),
                    'risk_score': risk_score,
                    'trade_risk': risk_result.get('trade_risk', 0.0),
                    'checks_passed': len(checks) - len(failed_checks),
                    'checks_failed': len(failed_checks),
                    'critical_failures': len(critical_failures),
                    'reason': reason,
                    'full_result': risk_result
                }
            )

        except Exception as e:
            return DecisionStep(
                step=4,
                module="RiskManager",
                action="风险检查",
                result=f"检查失败: {str(e)}",
                passed=False,
                details={'error': str(e)}
            )

    def _calculate_confidence(
        self,
        steps: List[DecisionStep],
        risk_score: float
    ) -> float:
        """
        计算决策置信度

        Args:
            steps: 决策步骤列表
            risk_score: 风险分数（0-10）

        Returns:
            置信度（0-1）
        """
        # 基础置信度：所有步骤都通过 = 1.0
        base_confidence = 1.0 if all(s.passed for s in steps) else 0.0

        # 风险调整：风险分数越高，置信度越低
        # risk_score: 0 = 置信度1.0, 5 = 置信度0.5, 10 = 置信度0.0
        risk_adjustment = max(0.0, 1.0 - (risk_score / 10.0))

        # 质量分数调整（从Step 1获取）
        quality_adjustment = 1.0
        for step in steps:
            if step.module == "StrategyRegistration":
                quality_score = step.details.get('quality_score', 70.0)
                # quality_score: 60 = 0.6, 80 = 0.8, 100 = 1.0
                quality_adjustment = min(quality_score / 100.0, 1.0)
                break

        # 综合置信度
        confidence = base_confidence * risk_adjustment * quality_adjustment

        return round(confidence, 2)

    def _generate_reason(
        self,
        decision_type: DecisionType,
        steps: List[DecisionStep],
        risk_score: float
    ) -> str:
        """
        生成决策理由

        Args:
            decision_type: 决策类型
            steps: 决策步骤列表
            risk_score: 风险分数

        Returns:
            决策理由文本
        """
        if decision_type == DecisionType.REJECTED:
            # 找到第一个失败的步骤
            failed_step = next((s for s in steps if not s.passed), None)
            if failed_step:
                return f"{failed_step.module}检查未通过: {failed_step.result}"
            else:
                return "未知原因导致拒绝"

        elif decision_type == DecisionType.ADJUSTED:
            # 找到调整原因
            reasons = []
            for step in steps:
                if step.module == "AllocationEngine":
                    if step.details.get('suggested_volume') != step.details.get('original_volume'):
                        reasons.append("根据资金分配调整手数")
                elif step.module == "RiskManager":
                    if step.details.get('adjusted_volume') != step.details.get('original_volume'):
                        reasons.append(f"风险控制调整手数 (风险分数: {risk_score:.1f})")

            return "信号调整: " + "; ".join(reasons) if reasons else "手数已调整"

        else:  # APPROVED
            return f"所有检查通过，批准执行 (风险分数: {risk_score:.1f})"

    def evaluate_batch(
        self,
        signals: List[Dict],
        account_id: str = "default"
    ) -> List[SignalDecision]:
        """
        批量评估信号

        Args:
            signals: 信号列表
            account_id: 账户ID

        Returns:
            决策结果列表
        """
        decisions = []
        for signal in signals:
            decision = self.evaluate_signal(signal, account_id)
            decisions.append(decision)
        return decisions

    def get_evaluation_summary(
        self,
        decisions: List[SignalDecision]
    ) -> Dict:
        """
        获取评估概览

        Args:
            decisions: 决策结果列表

        Returns:
            概览信息
        """
        total = len(decisions)
        approved = sum(1 for d in decisions if d.decision == DecisionType.APPROVED)
        adjusted = sum(1 for d in decisions if d.decision == DecisionType.ADJUSTED)
        rejected = sum(1 for d in decisions if d.decision == DecisionType.REJECTED)

        avg_risk_score = sum(d.risk_score for d in decisions) / total if total > 0 else 0.0
        avg_confidence = sum(d.confidence for d in decisions) / total if total > 0 else 0.0

        return {
            'total': total,
            'approved': approved,
            'adjusted': adjusted,
            'rejected': rejected,
            'approval_rate': approved / total if total > 0 else 0.0,
            'average_risk_score': avg_risk_score,
            'average_confidence': avg_confidence
        }
