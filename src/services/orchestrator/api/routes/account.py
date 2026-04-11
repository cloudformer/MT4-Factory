"""
账户管理API - Account Management API

提供账户配置查询和管理接口
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

from src.services.orchestrator.service.account_manager import (
    AccountManager,
    AccountProfile,
    AllocationConfig,
    RiskType
)


router = APIRouter(prefix="/account", tags=["account"])


# 请求/响应模型
class UpdateProfileRequest(BaseModel):
    """更新账户配置请求"""
    risk_type: Optional[str] = None
    max_total_exposure: Optional[float] = None
    max_strategy_allocation: Optional[float] = None
    max_daily_loss: Optional[float] = None
    max_concurrent_trades: Optional[int] = None


class UpdateAllocationRequest(BaseModel):
    """更新分配配置请求"""
    mode: Optional[str] = None
    max_strategies: Optional[int] = None
    target_symbols: Optional[list] = None


# 初始化服务
account_manager = AccountManager()


@router.get("/{account_id}")
def get_account(account_id: str = "default"):
    """
    获取账户配置

    返回账户的完整配置信息

    Args:
        account_id: 账户ID（默认"default"）

    Returns:
        账户配置详情
    """
    account = account_manager.get_account(account_id)

    if not account:
        raise HTTPException(status_code=404, detail=f"账户不存在: {account_id}")

    return account.to_dict()


@router.get("/{account_id}/summary")
def get_account_summary(account_id: str = "default"):
    """
    获取账户概览

    包含账户配置、策略列表、余额信息等

    Args:
        account_id: 账户ID

    Returns:
        账户概览信息
    """
    summary = account_manager.get_account_summary(account_id)

    if not summary:
        raise HTTPException(status_code=404, detail=f"账户不存在: {account_id}")

    return summary


@router.get("/{account_id}/strategies")
def get_account_strategies(account_id: str = "default"):
    """
    获取账户的策略列表

    返回符合账户配置的激活策略

    Args:
        account_id: 账户ID

    Returns:
        策略列表
    """
    strategies = account_manager.get_account_strategies(account_id)

    return {
        'account_id': account_id,
        'total': len(strategies),
        'strategies': [
            {
                'id': s.id,
                'name': s.name,
                'status': s.status.value,
                'created_at': s.created_at.isoformat() if s.created_at else None
            }
            for s in strategies
        ]
    }


@router.put("/{account_id}/profile")
def update_account_profile(
    account_id: str,
    request: UpdateProfileRequest
):
    """
    更新账户风险配置

    Args:
        account_id: 账户ID
        request: 更新请求

    Returns:
        更新结果
    """
    account = account_manager.get_account(account_id)

    if not account:
        raise HTTPException(status_code=404, detail=f"账户不存在: {account_id}")

    # 创建新的Profile（只更新提供的字段）
    new_profile = AccountProfile(
        risk_type=RiskType(request.risk_type) if request.risk_type else account.profile.risk_type,
        max_total_exposure=request.max_total_exposure if request.max_total_exposure is not None else account.profile.max_total_exposure,
        max_strategy_allocation=request.max_strategy_allocation if request.max_strategy_allocation is not None else account.profile.max_strategy_allocation,
        max_daily_loss=request.max_daily_loss if request.max_daily_loss is not None else account.profile.max_daily_loss,
        max_concurrent_trades=request.max_concurrent_trades if request.max_concurrent_trades is not None else account.profile.max_concurrent_trades,
        short_term_ratio=account.profile.short_term_ratio,
        long_term_ratio=account.profile.long_term_ratio
    )

    # 更新
    success = account_manager.update_account_profile(account_id, new_profile)

    if not success:
        raise HTTPException(status_code=500, detail="更新失败")

    return {
        'success': True,
        'message': '账户配置已更新',
        'account_id': account_id
    }


@router.put("/{account_id}/allocation")
def update_allocation_config(
    account_id: str,
    request: UpdateAllocationRequest
):
    """
    更新账户分配配置

    Args:
        account_id: 账户ID
        request: 更新请求

    Returns:
        更新结果
    """
    account = account_manager.get_account(account_id)

    if not account:
        raise HTTPException(status_code=404, detail=f"账户不存在: {account_id}")

    # 创建新的AllocationConfig
    new_config = AllocationConfig(
        mode=request.mode if request.mode else account.allocation_config.mode,
        max_strategies=request.max_strategies if request.max_strategies is not None else account.allocation_config.max_strategies,
        target_symbols=request.target_symbols if request.target_symbols else account.allocation_config.target_symbols,
        strategy_filters=account.allocation_config.strategy_filters,
        rebalance_interval_hours=account.allocation_config.rebalance_interval_hours
    )

    # 更新
    success = account_manager.update_allocation_config(account_id, new_config)

    if not success:
        raise HTTPException(status_code=500, detail="更新失败")

    return {
        'success': True,
        'message': '分配配置已更新',
        'account_id': account_id
    }


@router.get("/{account_id}/balance")
def get_available_balance(account_id: str = "default"):
    """
    获取账户可用余额

    Args:
        account_id: 账户ID

    Returns:
        余额信息
    """
    account = account_manager.get_account(account_id)

    if not account:
        raise HTTPException(status_code=404, detail=f"账户不存在: {account_id}")

    available = account_manager.get_available_balance(account_id)

    return {
        'account_id': account_id,
        'total_balance': account.balance,
        'available_balance': available,
        'allocated': account.balance - available
    }
