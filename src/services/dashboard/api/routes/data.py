"""Dashboard 数据接口"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx

from src.common.database.connection import db
from src.common.models.strategy import Strategy
from src.common.models.signal import Signal
from src.common.models.trade import Trade
from src.common.models.account import Account

router = APIRouter(prefix="/api", tags=["data"])


# 请求模型
class GenerateStrategiesRequest(BaseModel):
    count: int = 2


class GenerateSignalRequest(BaseModel):
    strategy_id: str
    symbol: str = "EURUSD"


class ExecuteSignalRequest(BaseModel):
    signal_id: str

# 其他服务地址
STRATEGY_URL = "http://localhost:8001"
ORCHESTRATOR_URL = "http://localhost:8002"
EXECUTION_URL = "http://localhost:8003"


def get_db_session():
    """获取数据库Session"""
    with db.session_scope() as session:
        yield session


@router.get("/stats")
def get_stats(session: Session = Depends(get_db_session)):
    """获取统计数据"""
    total_strategies = session.query(Strategy).count()
    active_strategies = session.query(Strategy).filter(Strategy.status == "active").count()
    total_signals = session.query(Signal).count()
    total_trades = session.query(Trade).count()

    # 计算总盈亏
    trades = session.query(Trade).all()
    total_profit = sum([float(t.profit) for t in trades if t.profit])

    return {
        "total_strategies": total_strategies,
        "active_strategies": active_strategies,
        "total_signals": total_signals,
        "total_trades": total_trades,
        "total_profit": round(total_profit, 2)
    }


@router.get("/strategies")
def get_strategies(session: Session = Depends(get_db_session)):
    """获取所有策略"""
    strategies = session.query(Strategy).order_by(Strategy.created_at.desc()).all()
    return {
        "strategies": [s.to_dict() for s in strategies]
    }


@router.get("/strategies/{strategy_id}")
def get_strategy_detail(strategy_id: str, session: Session = Depends(get_db_session)):
    """获取策略详情"""
    strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        return {"error": "策略不存在"}

    # 获取该策略的信号和交易
    signals = session.query(Signal).filter(Signal.strategy_id == strategy_id).all()
    trades = session.query(Trade).filter(Trade.strategy_id == strategy_id).all()

    return {
        "strategy": strategy.to_dict(),
        "signals": [s.to_dict() for s in signals],
        "trades": [t.to_dict() for t in trades]
    }


@router.get("/signals")
def get_signals(session: Session = Depends(get_db_session)):
    """获取所有信号"""
    signals = session.query(Signal).order_by(Signal.created_at.desc()).limit(50).all()
    return {
        "signals": [s.to_dict() for s in signals]
    }


@router.get("/trades")
def get_trades(session: Session = Depends(get_db_session)):
    """获取所有交易（最多返回50条）"""
    # Join with Account to get login info
    trades_with_accounts = (
        session.query(Trade, Account)
        .outerjoin(Account, Trade.account_id == Account.id)
        .order_by(Trade.open_time.desc())
        .limit(50)  # ⚠️ 只返回最新50条
        .all()
    )

    trades_list = []
    for trade, account in trades_with_accounts:
        trade_dict = trade.to_dict()
        trade_dict['account_login'] = account.login if account else None
        trades_list.append(trade_dict)

    return {"trades": trades_list}


# ========== 操作接口 ==========

@router.post("/actions/generate-strategies")
async def generate_strategies(request: GenerateStrategiesRequest):
    """生成策略（代理到 Strategy 服务）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{STRATEGY_URL}/strategies/generate",
                json={"count": request.count}
            )
            return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/actions/generate-signal")
async def generate_signal(request: GenerateSignalRequest):
    """生成信号（代理到 Orchestrator 服务）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/signals/generate",
                json={"strategy_id": request.strategy_id, "symbol": request.symbol}
            )
            return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/actions/execute-signal")
async def execute_signal(request: ExecuteSignalRequest):
    """执行信号（代理到 Execution 服务）"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{EXECUTION_URL}/trades/execute/{request.signal_id}"
            )
            return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}
