"""策略相关路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.common.database.connection import db
from ..schemas.request import GenerateStrategyRequest
from ..schemas.response import GenerateStrategyResponse, ListStrategiesResponse, StrategyResponse
from ...service.generator import StrategyGeneratorService
from ...repository.strategy_repo import StrategyRepository

router = APIRouter(prefix="/strategies", tags=["strategies"])


def get_db_session():
    """获取数据库Session"""
    with db.session_scope() as session:
        yield session


def get_strategy_service(session: Session = Depends(get_db_session)) -> StrategyGeneratorService:
    """获取策略生成服务"""
    repo = StrategyRepository(session)
    return StrategyGeneratorService(repo)


@router.post("/generate", response_model=GenerateStrategyResponse)
def generate_strategies(
    request: GenerateStrategyRequest,
    service: StrategyGeneratorService = Depends(get_strategy_service)
):
    """生成策略"""
    try:
        strategies = service.generate_strategies(
            count=request.count,
            template=request.template
        )

        return GenerateStrategyResponse(
            success=True,
            strategy_ids=[s.id for s in strategies],
            message=f"成功生成 {len(strategies)} 个策略"
        )
    except Exception as e:
        return GenerateStrategyResponse(
            success=False,
            strategy_ids=[],
            message=f"生成失败: {str(e)}"
        )


@router.get("", response_model=ListStrategiesResponse)
def list_strategies(service: StrategyGeneratorService = Depends(get_strategy_service)):
    """获取所有策略"""
    strategies = service.get_all_strategies()

    return ListStrategiesResponse(
        total=len(strategies),
        strategies=[
            StrategyResponse(
                id=s.id,
                name=s.name,
                status=s.status.value if hasattr(s.status, 'value') else s.status,
                performance=s.performance,
                created_at=s.created_at
            )
            for s in strategies
        ]
    )


@router.get("/{strategy_id}", response_model=StrategyResponse)
def get_strategy(
    strategy_id: str,
    service: StrategyGeneratorService = Depends(get_strategy_service)
):
    """获取单个策略"""
    strategy = service.get_strategy(strategy_id)

    if not strategy:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="策略不存在")

    return StrategyResponse(
        id=strategy.id,
        name=strategy.name,
        status=strategy.status.value if hasattr(strategy.status, 'value') else strategy.status,
        performance=strategy.performance,
        created_at=strategy.created_at
    )
