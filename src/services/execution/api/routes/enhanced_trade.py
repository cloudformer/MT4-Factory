"""增强交易路由 - 包含风控、重试、实时追踪"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from src.common.database.connection import db
from src.common.models.signal import Signal, SignalStatus
from src.common.models.account import Account
from ...service.enhanced_order_service import EnhancedOrderService, OrderExecutionError
from ...repository.trade_repo import TradeRepository

router = APIRouter(prefix="/api/execution", tags=["execution"])


# 请求模型
class ExecuteSignalRequest(BaseModel):
    signal_id: str
    account_id: Optional[str] = None


class CloseOrderRequest(BaseModel):
    ticket: int
    reason: str = "manual"  # manual, stop_loss, take_profit, risk


# 依赖注入
def get_db_session():
    """获取数据库Session"""
    with db.session_scope() as session:
        yield session


def get_order_service(session: Session = Depends(get_db_session)) -> EnhancedOrderService:
    """获取增强订单执行服务"""
    repo = TradeRepository(session)
    return EnhancedOrderService(repo)


@router.post("/execute")
async def execute_signal(
    request: ExecuteSignalRequest,
    session: Session = Depends(get_db_session),
    service: EnhancedOrderService = Depends(get_order_service)
):
    """
    执行信号（增强版）

    功能：
    - ✅ 风控检查
    - ✅ 自动重试（3次）
    - ✅ 详细错误信息
    """
    # 1. 获取信号
    signal = session.query(Signal).filter(Signal.id == request.signal_id).first()
    if not signal:
        raise HTTPException(status_code=404, detail="信号不存在")

    if signal.status != SignalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"信号状态为 {signal.status}，无法执行"
        )

    # 2. 获取账户信息（用于风控）
    account = None
    if request.account_id:
        account = session.query(Account).filter(Account.id == request.account_id).first()

    # 3. 执行订单
    try:
        trade = await service.execute_signal(signal, account)

        # 更新信号状态
        signal.status = SignalStatus.EXECUTED
        session.commit()

        return {
            "success": True,
            "trade_id": trade.id,
            "ticket": trade.ticket,
            "symbol": trade.symbol,
            "volume": float(trade.volume),
            "open_price": float(trade.open_price),
            "open_time": trade.open_time.isoformat(),
            "message": "订单执行成功"
        }

    except OrderExecutionError as e:
        # 订单执行失败
        signal.status = SignalStatus.FAILED
        session.commit()

        raise HTTPException(
            status_code=400,
            detail={
                "error": "OrderExecutionError",
                "message": str(e),
                "signal_id": signal.id
            }
        )

    except Exception as e:
        # 其他未知错误
        signal.status = SignalStatus.FAILED
        session.commit()

        raise HTTPException(
            status_code=500,
            detail={
                "error": "UnexpectedError",
                "message": str(e),
                "signal_id": signal.id
            }
        )


@router.post("/close")
async def close_order(
    request: CloseOrderRequest,
    service: EnhancedOrderService = Depends(get_order_service)
):
    """
    平仓订单

    原因：
    - manual: 手动平仓
    - stop_loss: 止损触发
    - take_profit: 止盈触发
    - risk: 风控平仓
    """
    try:
        trade = await service.close_order(request.ticket, request.reason)

        return {
            "success": True,
            "ticket": trade.ticket,
            "symbol": trade.symbol,
            "close_price": float(trade.close_price),
            "close_time": trade.close_time.isoformat(),
            "profit": float(trade.profit) if trade.profit else 0.0,
            "reason": request.reason,
            "message": "平仓成功"
        }

    except OrderExecutionError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "OrderExecutionError",
                "message": str(e),
                "ticket": request.ticket
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "UnexpectedError",
                "message": str(e),
                "ticket": request.ticket
            }
        )


@router.get("/positions")
async def get_positions(service: EnhancedOrderService = Depends(get_order_service)):
    """
    获取当前持仓

    返回正在追踪的活跃订单
    """
    active_orders = service.get_active_orders()

    return {
        "total": len(active_orders),
        "positions": [
            {
                "ticket": t.ticket,
                "symbol": t.symbol,
                "direction": t.direction.value,
                "volume": float(t.volume),
                "open_price": float(t.open_price),
                "open_time": t.open_time.isoformat(),
                "strategy_id": t.strategy_id,
                "account_id": t.account_id
            }
            for t in active_orders
        ]
    }


@router.post("/sync")
async def sync_positions(service: EnhancedOrderService = Depends(get_order_service)):
    """
    同步持仓状态

    从MT5查询当前持仓，更新本地追踪
    """
    try:
        await service.sync_positions()

        return {
            "success": True,
            "message": "持仓同步完成"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "SyncError",
                "message": str(e)
            }
        )


@router.get("/stats")
def get_stats(service: EnhancedOrderService = Depends(get_order_service)):
    """
    获取执行服务统计信息

    包括：
    - 活跃订单数
    - 风控配置
    - MT5连接状态
    """
    return service.get_stats()


@router.get("/risk")
def get_risk_config(service: EnhancedOrderService = Depends(get_order_service)):
    """
    获取风控配置

    返回当前风控规则和限制
    """
    return service.risk_manager.get_stats()
