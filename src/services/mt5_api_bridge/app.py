"""
MT5 API Bridge - FastAPI HTTP包装器

用途：
1. 运行在Windows系统上（MT5必须是Windows原生）
2. 提供HTTP接口包装MetaTrader5库功能
3. 允许远程服务（Linux容器）通过HTTP访问MT5

部署：
- Windows本地：localhost:9090（容器通过host.docker.internal访问）
- Windows VPS：0.0.0.0:9090（云端容器通过公网IP访问）
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import MetaTrader5 as mt5

app = FastAPI(
    title="MT5 API Bridge",
    description="MetaTrader5 HTTP API包装器",
    version="1.0.0"
)

# 安全认证（可选，生产环境强烈推荐）
security = HTTPBearer(auto_error=False)

# API密钥配置（从环境变量读取）
import os
API_KEYS = os.getenv("MT5_API_KEYS", "").split(",") if os.getenv("MT5_API_KEYS") else []
REQUIRE_AUTH = len(API_KEYS) > 0  # 如果配置了密钥，则启用认证


def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """验证API密钥"""
    if not REQUIRE_AUTH:
        return None  # 不需要认证

    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing API key")

    if credentials.credentials not in API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return credentials.credentials


# ==================== Pydantic模型 ====================

class LoginRequest(BaseModel):
    login: int
    password: str
    server: str


class OrderRequest(BaseModel):
    action: str  # "buy" or "sell"
    symbol: str
    volume: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    deviation: int = 20
    magic: int = 234000
    comment: str = ""


# ==================== 启动/关闭事件 ====================

@app.on_event("startup")
async def startup_event():
    """启动时初始化MT5"""
    if not mt5.initialize():
        print(f"❌ MT5初始化失败: {mt5.last_error()}")
        raise RuntimeError("MT5初始化失败")
    print("✅ MT5 API Bridge已启动")
    print(f"🔐 认证模式: {'启用' if REQUIRE_AUTH else '禁用（仅限开发）'}")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时释放MT5"""
    mt5.shutdown()
    print("MT5 API Bridge已关闭")


# ==================== API端点 ====================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "mt5_connected": mt5.terminal_info() is not None,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/login")
async def login(request: LoginRequest, _: str = Depends(verify_api_key)):
    """登录MT5账户"""
    success = mt5.login(
        login=request.login,
        password=request.password,
        server=request.server
    )

    if not success:
        error = mt5.last_error()
        return {
            "success": False,
            "error": f"登录失败: {error}"
        }

    return {
        "success": True,
        "login": request.login,
        "server": request.server
    }


@app.get("/account")
async def get_account_info(_: str = Depends(verify_api_key)):
    """获取账户信息"""
    info = mt5.account_info()
    if info is None:
        raise HTTPException(status_code=500, detail="无法获取账户信息")

    return {
        "login": info.login,
        "server": info.server,
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "margin_free": info.margin_free,
        "leverage": info.leverage,
        "currency": info.currency,
        "trade_allowed": info.trade_allowed
    }


@app.get("/tick/{symbol}")
async def get_tick(symbol: str, _: str = Depends(verify_api_key)):
    """获取实时报价"""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"Symbol not found: {symbol}")

    return {
        "symbol": symbol,
        "time": datetime.fromtimestamp(tick.time).isoformat(),
        "bid": tick.bid,
        "ask": tick.ask,
        "last": tick.last,
        "volume": tick.volume
    }


@app.get("/bars/{symbol}")
async def get_bars(
    symbol: str,
    timeframe: str = Query("H1", description="时间框架: M1, M5, M15, M30, H1, H4, D1"),
    count: int = Query(100, ge=1, le=10000, description="K线数量"),
    _: str = Depends(verify_api_key)
):
    """
    获取K线数据（核心接口）

    这是Validator和Execution最常用的接口
    """
    # 时间框架映射
    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }

    if timeframe not in tf_map:
        raise HTTPException(status_code=400, detail=f"不支持的时间框架: {timeframe}")

    rates = mt5.copy_rates_from_pos(symbol, tf_map[timeframe], 0, count)

    if rates is None or len(rates) == 0:
        raise HTTPException(status_code=404, detail=f"无法获取数据: {symbol}")

    # 转换为JSON格式
    bars = [
        {
            "time": datetime.fromtimestamp(int(rate[0])).isoformat(),
            "open": float(rate[1]),
            "high": float(rate[2]),
            "low": float(rate[3]),
            "close": float(rate[4]),
            "tick_volume": int(rate[5]),
            "spread": int(rate[6]),
            "real_volume": int(rate[7])
        }
        for rate in rates
    ]

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(bars),
        "bars": bars
    }


@app.post("/order")
async def place_order(request: OrderRequest, _: str = Depends(verify_api_key)):
    """
    下单接口（危险操作）

    注意：仅用于真实交易，Validator不应调用此接口
    """
    # 获取报价
    tick = mt5.symbol_info_tick(request.symbol)
    if tick is None:
        raise HTTPException(status_code=404, detail=f"Symbol not found: {request.symbol}")

    # 订单类型
    price = tick.ask if request.action == 'buy' else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if request.action == 'buy' else mt5.ORDER_TYPE_SELL

    # 构建订单请求
    mt5_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": request.symbol,
        "volume": request.volume,
        "type": order_type,
        "price": price,
        "deviation": request.deviation,
        "magic": request.magic,
        "comment": request.comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    if request.sl is not None:
        mt5_request["sl"] = request.sl
    if request.tp is not None:
        mt5_request["tp"] = request.tp

    # 发送订单
    result = mt5.order_send(mt5_request)

    return {
        "success": result.retcode == mt5.TRADE_RETCODE_DONE,
        "order_id": result.order if hasattr(result, 'order') else None,
        "ticket": result.order if hasattr(result, 'order') else None,
        "price": result.price if hasattr(result, 'price') else None,
        "volume": result.volume if hasattr(result, 'volume') else None,
        "comment": result.comment if hasattr(result, 'comment') else "",
        "retcode": result.retcode
    }


@app.get("/positions")
async def get_positions(
    symbol: Optional[str] = Query(None, description="过滤品种"),
    _: str = Depends(verify_api_key)
):
    """获取持仓"""
    if symbol:
        positions = mt5.positions_get(symbol=symbol)
    else:
        positions = mt5.positions_get()

    if positions is None:
        return {"positions": []}

    return {
        "positions": [
            {
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "type": "buy" if pos.type == mt5.ORDER_TYPE_BUY else "sell",
                "volume": pos.volume,
                "price_open": pos.price_open,
                "price_current": pos.price_current,
                "sl": pos.sl,
                "tp": pos.tp,
                "profit": pos.profit,
                "time": datetime.fromtimestamp(pos.time).isoformat()
            }
            for pos in positions
        ]
    }


@app.get("/terminal_info")
async def get_terminal_info(_: str = Depends(verify_api_key)):
    """获取MT5终端信息"""
    info = mt5.terminal_info()
    if info is None:
        raise HTTPException(status_code=500, detail="无法获取终端信息")

    return {
        "build": info.build,
        "connected": info.connected,
        "trade_allowed": info.trade_allowed,
        "company": info.company,
        "name": info.name,
        "language": info.language,
        "path": info.path
    }


# ==================== 启动命令 ====================

if __name__ == "__main__":
    import uvicorn

    # 从环境变量读取配置
    host = os.getenv("MT5_API_HOST", "0.0.0.0")  # 0.0.0.0允许外部访问
    port = int(os.getenv("MT5_API_PORT", "9090"))

    print("=" * 60)
    print("🚀 MT5 API Bridge 启动中...")
    print(f"📍 监听地址: http://{host}:{port}")
    print(f"🔐 认证: {'启用' if REQUIRE_AUTH else '禁用'}")
    print("=" * 60)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
