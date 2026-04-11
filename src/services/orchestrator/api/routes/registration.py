"""
策略注册服务API - Strategy Registration API

提供策略激活、停用、评估等接口
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from pydantic import BaseModel

from src.services.orchestrator.service.strategy_registration import StrategyRegistration


router = APIRouter(prefix="/registration", tags=["registration"])


# 请求/响应模型
class ActivateRequest(BaseModel):
    """激活策略请求"""
    force: bool = False  # 是否强制激活（忽略质量检查）


class DeactivateRequest(BaseModel):
    """停用策略请求"""
    reason: Optional[str] = None  # 停用原因


class ArchiveRequest(BaseModel):
    """归档策略请求"""
    reason: Optional[str] = None  # 归档原因


class StrategyBriefResponse(BaseModel):
    """策略简要信息"""
    id: str
    name: str
    status: str
    quality_score: Optional[float] = None
    backtested_symbol: Optional[str] = None


class EvaluationResponse(BaseModel):
    """质量评估响应"""
    qualified: bool
    quality_score: float
    stability_score: float
    core_passed: int
    core_required: int
    reasons: List[str]
    backtested_symbol: str


class OperationResponse(BaseModel):
    """操作结果响应"""
    success: bool
    message: str
    strategy_id: str
    evaluation: Optional[dict] = None


# 初始化服务
registration_service = StrategyRegistration()


@router.get("/active", response_model=List[StrategyBriefResponse])
def get_active_strategies(
    symbol: Optional[str] = Query(None, description="筛选指定货币对的策略")
):
    """
    获取所有激活的策略

    这些策略才能被Orchestrator编排使用

    Args:
        symbol: 可选，筛选指定货币对（如 EURUSD）

    Returns:
        激活状态的策略列表
    """
    strategies = registration_service.get_active_strategies(symbol=symbol)

    result = []
    for strategy in strategies:
        # 获取质量分数
        quality_score = registration_service.get_strategy_score(strategy.id)

        # 获取回测品种
        performance = strategy.performance or {}
        backtested_symbol = performance.get('backtested_symbol',
                                          performance.get('default_symbol', 'EURUSD'))

        result.append(StrategyBriefResponse(
            id=strategy.id,
            name=strategy.name,
            status=strategy.status.value,
            quality_score=quality_score,
            backtested_symbol=backtested_symbol
        ))

    return result


@router.get("/candidates", response_model=List[StrategyBriefResponse])
def get_candidate_strategies():
    """
    获取候选策略列表

    这些策略已生成但尚未激活，可通过评估决定是否激活
    """
    strategies = registration_service.get_candidate_strategies()

    result = []
    for strategy in strategies:
        quality_score = registration_service.get_strategy_score(strategy.id)
        performance = strategy.performance or {}
        backtested_symbol = performance.get('backtested_symbol',
                                          performance.get('default_symbol', 'EURUSD'))

        result.append(StrategyBriefResponse(
            id=strategy.id,
            name=strategy.name,
            status=strategy.status.value,
            quality_score=quality_score,
            backtested_symbol=backtested_symbol
        ))

    return result


@router.post("/activate/{strategy_id}", response_model=OperationResponse)
def activate_strategy(strategy_id: str, request: ActivateRequest = ActivateRequest()):
    """
    激活策略

    策略激活后才能被Orchestrator使用

    Args:
        strategy_id: 策略ID
        request: 激活选项（是否强制激活）

    Returns:
        操作结果，包含评估信息
    """
    result = registration_service.activate_strategy(
        strategy_id,
        force=request.force
    )

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])

    return OperationResponse(**result)


@router.post("/deactivate/{strategy_id}", response_model=OperationResponse)
def deactivate_strategy(strategy_id: str, request: DeactivateRequest = DeactivateRequest()):
    """
    停用策略

    策略停用后退出编排池，但不归档（可重新激活）

    Args:
        strategy_id: 策略ID
        request: 停用选项（原因）
    """
    result = registration_service.deactivate_strategy(
        strategy_id,
        reason=request.reason
    )

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])

    return OperationResponse(**result)


@router.post("/archive/{strategy_id}", response_model=OperationResponse)
def archive_strategy(strategy_id: str, request: ArchiveRequest = ArchiveRequest()):
    """
    归档策略

    只有候选状态可以归档，归档后可恢复到候选状态

    Args:
        strategy_id: 策略ID
        request: 归档选项（原因）
    """
    result = registration_service.archive_strategy(
        strategy_id,
        reason=request.reason
    )

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])

    return OperationResponse(**result)


@router.post("/restore/{strategy_id}", response_model=OperationResponse)
def restore_strategy(strategy_id: str):
    """
    恢复归档的策略到候选状态

    将归档状态的策略恢复为候选状态，然后可以重新激活

    Args:
        strategy_id: 策略ID
    """
    result = registration_service.restore_strategy(strategy_id)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])

    return OperationResponse(**result)


@router.delete("/delete/{strategy_id}", response_model=OperationResponse)
def delete_strategy(strategy_id: str):
    """
    永久删除策略

    从数据库中永久删除策略，此操作不可逆

    Args:
        strategy_id: 策略ID
    """
    result = registration_service.delete_strategy(strategy_id)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])

    return OperationResponse(**result)


@router.get("/evaluate/{strategy_id}", response_model=EvaluationResponse)
def evaluate_strategy(strategy_id: str):
    """
    评估策略质量

    根据激活标准评估策略，返回是否符合激活条件

    Args:
        strategy_id: 策略ID

    Returns:
        质量评估结果
    """
    from src.services.orchestrator.repository.strategy_repo import StrategyRepository

    repo = StrategyRepository()
    strategy = repo.get_by_id(strategy_id)

    if not strategy:
        raise HTTPException(status_code=404, detail=f"策略不存在: {strategy_id}")

    evaluation = registration_service.evaluate_strategy_quality(strategy)

    return EvaluationResponse(
        qualified=evaluation['qualified'],
        quality_score=evaluation['quality_score'],
        stability_score=evaluation['stability_score'],
        core_passed=evaluation['core_passed'],
        core_required=evaluation['core_required'],
        reasons=evaluation['reasons'],
        backtested_symbol=evaluation['backtested_symbol']
    )


@router.post("/batch-evaluate")
def batch_evaluate_candidates():
    """
    批量评估所有候选策略

    自动评估所有候选策略，符合条件的自动激活

    Returns:
        批量评估结果
    """
    result = registration_service.batch_evaluate_candidates()
    return result


@router.get("/summary")
def get_registration_summary():
    """
    获取注册服务概览

    显示总策略数、各状态数量、激活标准等

    Returns:
        注册服务概览信息
    """
    summary = registration_service.get_registration_summary()
    return summary


@router.get("/score/{strategy_id}")
def get_strategy_score(strategy_id: str):
    """
    获取策略质量分数

    Args:
        strategy_id: 策略ID

    Returns:
        质量分数（0-100）
    """
    score = registration_service.get_strategy_score(strategy_id)

    if score is None:
        raise HTTPException(status_code=404, detail=f"策略不存在: {strategy_id}")

    return {
        "strategy_id": strategy_id,
        "quality_score": score
    }
