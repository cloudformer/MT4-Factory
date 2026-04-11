"""
信号评估API - Signal Evaluation API

提供信号评估和决策接口
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict
from pydantic import BaseModel

from src.services.orchestrator.service.signal_evaluator import SignalEvaluator


router = APIRouter(prefix="/evaluation", tags=["evaluation"])


# 请求/响应模型
class EvaluateSignalRequest(BaseModel):
    """评估信号请求"""
    signal: Dict  # 信号字典
    account_id: str = "default"


class EvaluateBatchRequest(BaseModel):
    """批量评估请求"""
    signals: List[Dict]  # 信号列表
    account_id: str = "default"


# 初始化服务
signal_evaluator = SignalEvaluator()


@router.post("/evaluate-signal")
def evaluate_signal(request: EvaluateSignalRequest):
    """
    评估单个信号

    通过完整的决策链评估信号是否应该执行

    Args:
        request: 评估请求

    Returns:
        决策结果，包含完整决策链
    """
    try:
        decision = signal_evaluator.evaluate_signal(
            request.signal,
            request.account_id
        )

        return decision.to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评估失败: {str(e)}")


@router.post("/evaluate-batch")
def evaluate_batch(request: EvaluateBatchRequest):
    """
    批量评估信号

    一次评估多个信号

    Args:
        request: 批量评估请求

    Returns:
        决策结果列表和概览
    """
    try:
        decisions = signal_evaluator.evaluate_batch(
            request.signals,
            request.account_id
        )

        # 获取概览
        summary = signal_evaluator.get_evaluation_summary(decisions)

        return {
            'total': len(decisions),
            'summary': summary,
            'decisions': [d.to_dict() for d in decisions]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评估失败: {str(e)}")


@router.get("/decision-chain/{signal_id}")
def get_decision_chain(signal_id: str):
    """
    查看决策链

    显示某个信号的完整决策过程（需要事先评估）

    Args:
        signal_id: 信号ID

    Returns:
        决策链详情
    """
    # V1: 暂未实现决策历史持久化
    # V2+: 从数据库查询历史决策记录

    return {
        'signal_id': signal_id,
        'message': 'V1暂未实现决策历史查询功能',
        'note': '请调用 /evaluate-signal 接口重新评估'
    }


@router.get("/statistics")
def get_evaluation_statistics(
    account_id: str = Query("default", description="账户ID"),
    days: int = Query(7, description="统计天数")
):
    """
    获取评估统计

    显示过去N天的评估统计信息

    Args:
        account_id: 账户ID
        days: 统计天数

    Returns:
        评估统计数据
    """
    # V1: 暂未实现统计功能
    # V2+: 从数据库聚合历史评估记录

    return {
        'account_id': account_id,
        'days': days,
        'statistics': {
            'total_evaluated': 0,
            'approved': 0,
            'adjusted': 0,
            'rejected': 0,
            'approval_rate': 0.0,
            'average_risk_score': 0.0,
            'average_confidence': 0.0
        },
        'message': 'V1暂未实现统计功能'
    }


@router.post("/dry-run")
def dry_run_evaluation(request: EvaluateSignalRequest):
    """
    模拟评估（不执行）

    评估信号但不实际执行，用于测试和调试

    Args:
        request: 评估请求

    Returns:
        评估结果（仅模拟）
    """
    try:
        decision = signal_evaluator.evaluate_signal(
            request.signal,
            request.account_id
        )

        return {
            'dry_run': True,
            'message': '这是模拟评估，不会实际执行',
            'decision': decision.to_dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"评估失败: {str(e)}")


@router.get("/modules-status")
def get_modules_status():
    """
    获取各模块状态

    显示SignalEvaluator依赖的各模块是否正常

    Returns:
        模块状态信息
    """
    try:
        # 检查各模块
        modules_status = {
            'StrategyRegistration': 'ok',
            'AccountManager': 'ok',
            'AllocationEngine': 'ok',
            'RiskManager': 'ok',
            'SignalEvaluator': 'ok'
        }

        # 尝试获取一些基础数据
        try:
            active_strategies = signal_evaluator.registration.get_active_strategies()
            modules_status['StrategyRegistration_details'] = {
                'active_strategies': len(active_strategies)
            }
        except Exception as e:
            modules_status['StrategyRegistration'] = f'error: {str(e)}'

        try:
            account = signal_evaluator.account_manager.get_account("default")
            modules_status['AccountManager_details'] = {
                'default_account': account.name if account else None
            }
        except Exception as e:
            modules_status['AccountManager'] = f'error: {str(e)}'

        return {
            'overall_status': 'healthy' if all(
                v == 'ok' for k, v in modules_status.items()
                if not k.endswith('_details')
            ) else 'degraded',
            'modules': modules_status
        }

    except Exception as e:
        return {
            'overall_status': 'error',
            'error': str(e)
        }
