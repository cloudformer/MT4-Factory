"""
风险管理API - Risk Management API

提供风险检查和监控接口
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict
from pydantic import BaseModel

from src.services.orchestrator.service.account_manager import AccountManager
from src.services.orchestrator.service.risk_manager import RiskManager


router = APIRouter(prefix="/risk", tags=["risk"])


# 请求/响应模型
class EvaluateSignalRiskRequest(BaseModel):
    """评估信号风险请求"""
    signal: Dict  # 信号字典
    strategy_id: str
    account_id: str = "default"


# 初始化服务
account_manager = AccountManager()
risk_manager = RiskManager()


@router.get("/summary")
def get_risk_summary(account_id: str = Query("default", description="账户ID")):
    """
    获取风险概览

    显示当前的风险状态和各项限制的使用情况

    Args:
        account_id: 账户ID

    Returns:
        风险概览信息
    """
    # 获取账户
    account = account_manager.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"账户不存在: {account_id}")

    # 获取风险概览
    summary = risk_manager.get_risk_summary(account)

    return summary


@router.post("/evaluate-signal")
def evaluate_signal_risk(request: EvaluateSignalRiskRequest):
    """
    评估信号风险

    检查信号是否符合风险限制

    Args:
        request: 评估请求

    Returns:
        风险评估结果
    """
    # 获取账户
    account = account_manager.get_account(request.account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"账户不存在: {request.account_id}")

    # 评估风险
    result = risk_manager.evaluate_signal_risk(
        request.signal,
        account,
        request.strategy_id
    )

    return result


@router.get("/limits")
def get_risk_limits(account_id: str = Query("default", description="账户ID")):
    """
    获取风险限制配置

    显示账户的所有风险限制

    Args:
        account_id: 账户ID

    Returns:
        风险限制配置
    """
    # 获取账户
    account = account_manager.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"账户不存在: {account_id}")

    return {
        'account_id': account_id,
        'limits': {
            'max_total_exposure': account.profile.max_total_exposure,
            'max_total_exposure_pct': f"{account.profile.max_total_exposure:.2%}",
            'max_strategy_allocation': account.profile.max_strategy_allocation,
            'max_strategy_allocation_pct': f"{account.profile.max_strategy_allocation:.2%}",
            'max_daily_loss': account.profile.max_daily_loss,
            'max_daily_loss_pct': f"{account.profile.max_daily_loss:.2%}",
            'max_concurrent_trades': account.profile.max_concurrent_trades
        }
    }


@router.get("/status")
def get_risk_status(account_id: str = Query("default", description="账户ID")):
    """
    获取风险状态

    显示当前风险级别：low/medium/high/critical

    Args:
        account_id: 账户ID

    Returns:
        风险状态信息
    """
    # 获取账户
    account = account_manager.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"账户不存在: {account_id}")

    # 获取风险概览
    summary = risk_manager.get_risk_summary(account)

    status = summary.get('status', 'unknown')
    utilization = summary.get('utilization', {})

    # 风险级别说明
    status_description = {
        'low': '风险级别低 - 所有指标使用率 < 50%',
        'medium': '风险级别中等 - 部分指标使用率 50-80%',
        'high': '风险级别高 - 部分指标使用率 80-100%',
        'critical': '风险级别危急 - 部分指标超过限制'
    }

    # 风险建议
    recommendations = []
    if utilization.get('exposure', 0) > 0.8:
        recommendations.append("总仓位接近限制，建议减少新开仓")
    if utilization.get('trades', 0) > 0.8:
        recommendations.append("并发交易数接近限制，建议控制开仓频率")
    if utilization.get('daily_loss', 0) > 0.5:
        recommendations.append("当日亏损较大，建议暂停交易")

    return {
        'account_id': account_id,
        'status': status,
        'description': status_description.get(status, '未知状态'),
        'utilization': {
            'exposure': utilization.get('exposure', 0),
            'exposure_pct': f"{utilization.get('exposure', 0):.2%}",
            'trades': utilization.get('trades', 0),
            'trades_pct': f"{utilization.get('trades', 0):.2%}",
            'daily_loss': utilization.get('daily_loss', 0),
            'daily_loss_pct': f"{utilization.get('daily_loss', 0):.2%}",
        },
        'recommendations': recommendations
    }


@router.post("/update-positions")
def update_positions(positions: list):
    """
    更新持仓缓存

    用于RiskManager计算当前仓位占用

    Args:
        positions: 持仓列表

    Returns:
        更新结果
    """
    try:
        risk_manager.update_positions(positions)
        return {
            'success': True,
            'message': f'已更新 {len(positions)} 个持仓'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.post("/record-trade")
def record_trade_result(
    pnl: float = Query(..., description="盈亏金额"),
    account_id: str = Query("default", description="账户ID")
):
    """
    记录交易结果

    用于计算单日盈亏

    Args:
        pnl: 盈亏金额（正数为盈利，负数为亏损）
        account_id: 账户ID

    Returns:
        记录结果
    """
    try:
        risk_manager.record_trade_result(pnl)
        return {
            'success': True,
            'message': f'已记录交易结果: {pnl:+.2f} USD'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录失败: {str(e)}")
