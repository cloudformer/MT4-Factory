"""信号相关路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.common.database.connection import db
from src.common.models.strategy import Strategy, StrategyStatus
from ..schemas.request import GenerateSignalRequest
from ...service.orchestrator import SignalOrchestrator
from ...repository.signal_repo import SignalRepository

router = APIRouter(prefix="/signals", tags=["signals"])


def get_db_session():
    """获取数据库Session"""
    with db.session_scope() as session:
        yield session


def get_signal_orchestrator(session: Session = Depends(get_db_session)) -> SignalOrchestrator:
    """获取信号编排服务"""
    repo = SignalRepository(session)
    return SignalOrchestrator(repo)


@router.post("/generate")
def generate_signal(
    request: GenerateSignalRequest,
    orchestrator: SignalOrchestrator = Depends(get_signal_orchestrator),
    session: Session = Depends(get_db_session)
):
    """生成交易信号"""
    # 获取策略
    strategy = session.query(Strategy).filter(Strategy.id == request.strategy_id).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    if strategy.status != StrategyStatus.ACTIVE:
        raise HTTPException(status_code=400, detail=f"只有 Active 策略可以生成信号，当前状态: {strategy.status}")

    try:
        # 生成信号
        signal = orchestrator.generate_signal(strategy, request.symbol)

        return {
            "success": True,
            "signal_id": signal.id,
            "message": f"已生成信号: {signal.direction.value.upper()} {signal.volume} {signal.symbol}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成信号失败: {str(e)}")


@router.get("")
def list_signals(orchestrator: SignalOrchestrator = Depends(get_signal_orchestrator)):
    """获取所有信号"""
    signals = orchestrator.get_all_signals()

    return {
        "total": len(signals),
        "signals": [s.to_dict() for s in signals]
    }
