"""
组合管理API - Portfolio Management API

提供资金分配查询和组合管理接口
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

from src.services.orchestrator.service.account_manager import AccountManager
from src.services.orchestrator.service.allocation_engine import AllocationEngine, PortfolioBuilder


router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# 请求/响应模型
class RebalanceRequest(BaseModel):
    """重新平衡请求"""
    method: Optional[str] = None  # equal_weight/performance_weight/risk_parity


# 初始化服务
account_manager = AccountManager()
allocation_engine = AllocationEngine()
portfolio_builder = PortfolioBuilder(allocation_engine)


@router.get("/status")
def get_portfolio_status(account_id: str = Query("default", description="账户ID")):
    """
    获取组合状态

    显示当前的资金分配、仓位占用等信息

    Args:
        account_id: 账户ID

    Returns:
        组合状态信息
    """
    # 获取账户
    account = account_manager.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"账户不存在: {account_id}")

    # 获取账户策略
    strategies = account_manager.get_account_strategies(account_id)

    # 计算分配
    allocations = allocation_engine.allocate(strategies, account)

    # 调整分配
    allocations = allocation_engine.adjust_allocation_for_risk(allocations, account)

    # 验证
    valid, message = allocation_engine.validate_allocation(allocations, account)

    # 计算总仓位
    total_exposure = allocation_engine.calculate_total_exposure(allocations)

    # 获取概览
    summary = allocation_engine.get_allocation_summary(allocations)

    return {
        'account_id': account_id,
        'account_name': account.name,
        'balance': account.balance,
        'status': {
            'total_strategies': len(strategies),
            'allocated_strategies': len(allocations),
            'total_exposure': total_exposure,
            'total_exposure_pct': f"{total_exposure:.2%}",
            'max_exposure': account.profile.max_total_exposure,
            'valid': valid,
            'message': message
        },
        'summary': summary
    }


@router.get("/allocation")
def get_allocation(
    account_id: str = Query("default", description="账户ID"),
    method: Optional[str] = Query(None, description="分配方法")
):
    """
    查看资金分配

    显示每个策略的详细分配信息

    Args:
        account_id: 账户ID
        method: 分配方法（可选）

    Returns:
        详细的资金分配信息
    """
    # 获取账户
    account = account_manager.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"账户不存在: {account_id}")

    # 获取策略
    strategies = account_manager.get_account_strategies(account_id)

    # 构建组合
    portfolio = portfolio_builder.build_portfolio(strategies, account, method=method)

    return portfolio


@router.post("/rebalance")
def rebalance_portfolio(
    request: RebalanceRequest,
    account_id: str = Query("default", description="账户ID")
):
    """
    重新平衡组合

    根据当前策略表现重新计算资金分配

    Args:
        account_id: 账户ID
        request: 重新平衡请求

    Returns:
        新的分配方案
    """
    # 获取账户
    account = account_manager.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"账户不存在: {account_id}")

    # 获取策略
    strategies = account_manager.get_account_strategies(account_id)

    if not strategies:
        raise HTTPException(status_code=400, detail="没有可用策略")

    # 重新计算分配
    method = request.method or account.allocation_config.mode
    portfolio = portfolio_builder.build_portfolio(strategies, account, method=method)

    return {
        'success': True,
        'message': f'组合已重新平衡 (方法: {method})',
        'portfolio': portfolio
    }


@router.get("/history")
def get_allocation_history(
    account_id: str = Query("default", description="账户ID"),
    days: int = Query(7, description="查询天数")
):
    """
    查看分配历史

    显示过去N天的资金分配变化（V2+功能）

    Args:
        account_id: 账户ID
        days: 查询天数

    Returns:
        分配历史记录
    """
    # V1: 暂未实现持久化
    # V2+: 从数据库查询历史分配记录

    return {
        'account_id': account_id,
        'days': days,
        'history': [],
        'message': 'V1暂未实现历史记录功能'
    }


@router.get("/comparison")
def compare_allocation_methods(
    account_id: str = Query("default", description="账户ID")
):
    """
    对比不同分配方法

    展示不同分配算法的结果对比

    Args:
        account_id: 账户ID

    Returns:
        各方法的分配结果
    """
    # 获取账户
    account = account_manager.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail=f"账户不存在: {account_id}")

    # 获取策略
    strategies = account_manager.get_account_strategies(account_id)

    if not strategies:
        raise HTTPException(status_code=400, detail="没有可用策略")

    # 使用不同方法计算
    methods = ['equal_weight', 'performance_weight', 'risk_parity']
    results = {}

    for method in methods:
        try:
            portfolio = portfolio_builder.build_portfolio(
                strategies,
                account,
                method=method
            )
            results[method] = portfolio
        except Exception as e:
            results[method] = {
                'error': str(e),
                'message': f'{method} 方法暂未实现'
            }

    return {
        'account_id': account_id,
        'methods': methods,
        'results': results
    }
