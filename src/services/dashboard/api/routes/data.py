"""Dashboard 数据接口"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx

from src.common.database.connection import db
from src.common.models.strategy import Strategy, StrategyStatus
from src.common.models.signal import Signal
from src.common.models.trade import Trade
from src.common.models.account import Account
from src.common.config.settings import settings
from src.common.mock_data import MockDataGenerator, is_mock_mode

router = APIRouter(prefix="/api", tags=["data"])

# Mock数据生成器
mock_gen = MockDataGenerator()

# 请求模型
class GenerateStrategiesRequest(BaseModel):
    count: int = 2


class GenerateSignalRequest(BaseModel):
    strategy_id: str
    symbol: str = "EURUSD"


class ExecuteSignalRequest(BaseModel):
    signal_id: str

# 其他服务地址
STRATEGY_URL = "http://localhost:8000"
ORCHESTRATOR_URL = "http://localhost:8002"
EXECUTION_URL = "http://localhost:8003"


def get_db_session():
    """获取数据库Session"""
    with db.session_scope() as session:
        yield session


@router.get("/stats")
def get_stats(session: Session = Depends(get_db_session)):
    """获取统计数据"""
    # 从数据库读取真实数据
    total_strategies = session.query(Strategy).count()
    active_strategies = session.query(Strategy).filter(Strategy.status == StrategyStatus.ACTIVE).count()
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
    # 从数据库读取真实数据
    strategies = session.query(Strategy).order_by(Strategy.created_at.desc()).all()
    return {
        "strategies": [s.to_dict() for s in strategies]
    }


@router.get("/strategies/{strategy_id}")
def get_strategy_detail(strategy_id: str, session: Session = Depends(get_db_session)):
    """获取策略详情"""
    # 从数据库读取真实数据
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
    # 从数据库读取真实数据
    signals = session.query(Signal).order_by(Signal.created_at.desc()).limit(50).all()
    return {
        "signals": [s.to_dict() for s in signals]
    }


@router.get("/trades")
def get_trades(session: Session = Depends(get_db_session)):
    """获取所有交易（最多返回50条）"""
    # 从数据库读取真实数据
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

    return {
        "trades": trades_list
    }


@router.get("/accounts")
def get_accounts(session: Session = Depends(get_db_session)):
    """获取账户列表"""
    # 从数据库读取真实数据
    accounts = session.query(Account).all()
    return {
        "accounts": [a.to_dict() for a in accounts]
    }


# ========== 服务状态接口 ==========

@router.get("/services/execution/status")
async def get_execution_status():
    """获取Execution服务状态"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{EXECUTION_URL}/status")
            return response.json()
    except httpx.TimeoutException:
        return {"error": "连接超时", "service": "execution"}
    except httpx.ConnectError:
        return {"error": "连接失败", "service": "execution"}
    except Exception as e:
        return {"error": str(e), "service": "execution"}


@router.get("/services/validator/status")
async def get_validator_status():
    """获取Validator服务状态"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8004/status")
            return response.json()
    except httpx.TimeoutException:
        return {"error": "连接超时", "service": "validator"}
    except httpx.ConnectError:
        return {"error": "连接失败", "service": "validator"}
    except Exception as e:
        return {"error": str(e), "service": "validator"}


@router.get("/services/orchestrator/status")
async def get_orchestrator_status():
    """获取Orchestrator服务状态"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ORCHESTRATOR_URL}/status")
            return response.json()
    except httpx.TimeoutException:
        return {"error": "连接超时", "service": "orchestrator"}
    except httpx.ConnectError:
        return {"error": "连接失败", "service": "orchestrator"}
    except Exception as e:
        return {"error": str(e), "service": "orchestrator"}


@router.get("/services/strategy/status")
async def get_strategy_status():
    """获取Strategy服务状态"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{STRATEGY_URL}/health")
            return response.json()
    except httpx.TimeoutException:
        return {"error": "连接超时", "service": "strategy"}
    except httpx.ConnectError:
        return {"error": "连接失败", "service": "strategy"}
    except Exception as e:
        return {"error": str(e), "service": "strategy"}


@router.get("/mt5/workers")
async def get_mt5_workers():
    """获取所有MT5 Workers状态"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{EXECUTION_URL}/mt5/workers")
            return response.json()
    except httpx.TimeoutException:
        return {"error": "连接超时", "workers": []}
    except httpx.ConnectError:
        return {"error": "Execution服务未启动", "workers": []}
    except Exception as e:
        return {"error": str(e), "workers": []}


@router.get("/mt5/workers/{worker_id}")
async def get_mt5_worker(worker_id: str):
    """获取指定MT5 Worker状态"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{EXECUTION_URL}/mt5/workers/{worker_id}")
            return response.json()
    except httpx.TimeoutException:
        return {"error": "连接超时", "worker_id": worker_id}
    except httpx.ConnectError:
        return {"error": "Execution服务未启动", "worker_id": worker_id}
    except Exception as e:
        return {"error": str(e), "worker_id": worker_id}


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


# ========== 策略操作接口 ==========

@router.put("/strategies/{strategy_id}/activate")
def activate_strategy(strategy_id: str, session: Session = Depends(get_db_session)):
    """激活策略"""
    strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        return {"success": False, "error": "策略不存在"}

    strategy.status = StrategyStatus.ACTIVE
    session.commit()

    return {"success": True, "message": f"策略 {strategy.name} 已激活"}


@router.put("/strategies/{strategy_id}/deactivate")
def deactivate_strategy(strategy_id: str, session: Session = Depends(get_db_session)):
    """停用策略"""
    strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        return {"success": False, "error": "策略不存在"}

    strategy.status = StrategyStatus.CANDIDATE
    session.commit()

    return {"success": True, "message": f"策略 {strategy.name} 已停用"}


@router.put("/strategies/{strategy_id}/archive")
def archive_strategy(strategy_id: str, session: Session = Depends(get_db_session)):
    """归档策略"""
    strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        return {"success": False, "error": "策略不存在"}

    strategy.status = StrategyStatus.ARCHIVED
    session.commit()

    return {"success": True, "message": f"策略 {strategy.name} 已归档"}


@router.put("/strategies/{strategy_id}/restore")
def restore_strategy(strategy_id: str, session: Session = Depends(get_db_session)):
    """恢复策略到候选状态"""
    strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        return {"success": False, "error": "策略不存在"}

    strategy.status = StrategyStatus.CANDIDATE
    session.commit()

    return {"success": True, "message": f"策略 {strategy.name} 已恢复到候选状态"}


@router.delete("/strategies/{strategy_id}")
def delete_strategy(strategy_id: str, session: Session = Depends(get_db_session)):
    """删除策略"""
    strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        return {"success": False, "error": "策略不存在"}

    strategy_name = strategy.name
    session.delete(strategy)
    session.commit()

    return {"success": True, "message": f"策略 {strategy_name} 已删除"}


@router.post("/strategies/{strategy_id}/evaluate")
async def evaluate_strategy(strategy_id: str, session: Session = Depends(get_db_session)):
    """实时评估策略激活条件（调用Validator服务）"""
    strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        return {"success": False, "error": "策略不存在"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8004/validate/strategy",
                json={"strategy_id": strategy_id}
            )
            return response.json()
    except httpx.TimeoutException:
        return {"success": False, "error": "Validator服务连接超时"}
    except httpx.ConnectError:
        return {"success": False, "error": "Validator服务未启动"}
    except Exception as e:
        return {"success": False, "error": str(e)}
