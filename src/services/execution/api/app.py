"""Execution Service FastAPI 应用"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .routes import trade
from src.common.mt5 import mt5_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时连接MT5
    print("🚀 Execution Service 启动中...")
    try:
        # 默认使用交易模式（如需只读模式，可传入 use_investor=True）
        mt5_manager.connect(use_investor=False)
    except Exception as e:
        print(f"⚠️  MT5连接失败（将使用Mock模式）: {e}")

    yield

    # 关闭时断开MT5
    print("🛑 Execution Service 关闭中...")
    mt5_manager.disconnect()


# 创建FastAPI应用
app = FastAPI(
    title="Execution Service",
    version="1.0.0",
    description="执行层服务",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(trade.router)


@app.get("/")
def health_check():
    """健康检查"""
    client = mt5_manager.get_client()
    account = client.account_info()

    return {
        "service": "execution",
        "status": "running",
        "version": "1.0.0",
        "mt5_connected": account is not None,
        "account": {
            "login": account.login,
            "balance": account.balance,
            "currency": account.currency,
            "leverage": account.leverage
        } if account else None
    }


@app.get("/health")
def health():
    """健康检查（详细）"""
    client = mt5_manager.get_client()
    is_connected = mt5_manager.is_connected()
    account = client.account_info()

    return {
        "service": "execution",
        "status": "healthy" if is_connected else "degraded",
        "version": "1.0.0",
        "layer": "Execution Layer",
        "mt5": {
            "connected": is_connected,
            "account": {
                "login": account.login,
                "server": account.server,
                "balance": account.balance,
                "equity": account.equity,
                "margin": account.margin,
                "margin_free": account.margin_free,
                "leverage": account.leverage,
                "currency": account.currency,
                "trade_allowed": account.trade_allowed
            } if account else None
        }
    }
