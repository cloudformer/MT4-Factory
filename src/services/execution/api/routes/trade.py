"""交易相关路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.common.database.connection import db
from src.common.models.signal import Signal, SignalStatus
from ...service.order_service import OrderExecutionService
from ...repository.trade_repo import TradeRepository
from ....orchestrator.repository.signal_repo import SignalRepository

router = APIRouter(prefix="/trades", tags=["trades"])


def get_db_session():
    """获取数据库Session"""
    with db.session_scope() as session:
        yield session


def get_order_service(session: Session = Depends(get_db_session)) -> OrderExecutionService:
    """获取订单执行服务"""
    repo = TradeRepository(session)
    return OrderExecutionService(repo)


@router.post("/execute/{signal_id}")
def execute_signal(
    signal_id: str,
    session: Session = Depends(get_db_session),
    service: OrderExecutionService = Depends(get_order_service)
):
    """执行信号"""
    # 获取信号
    signal = session.query(Signal).filter(Signal.id == signal_id).first()

    if not signal:
        raise HTTPException(status_code=404, detail="信号不存在")

    if signal.status != SignalStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"信号状态为 {signal.status}，无法执行")

    try:
        # 执行订单
        trade = service.execute_signal(signal)

        # 更新信号状态
        signal.status = SignalStatus.EXECUTED
        session.commit()

        return {
            "success": True,
            "trade_id": trade.id,
            "ticket": trade.ticket,
            "message": "订单执行成功"
        }
    except Exception as e:
        signal.status = SignalStatus.FAILED
        session.commit()
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")


@router.get("")
def list_trades(service: OrderExecutionService = Depends(get_order_service)):
    """获取所有交易"""
    trades = service.get_all_trades()

    return {
        "total": len(trades),
        "trades": [t.to_dict() for t in trades]
    }
