"""Execution Service FastAPI 应用"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import trade

# 创建FastAPI应用
app = FastAPI(
    title="Execution Service",
    version="1.0.0",
    description="执行层服务"
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
    from src.common.mt5 import get_mt5_client

    mt5 = get_mt5_client()
    account = None

    if mt5.initialize():
        account = mt5.account_info()

    return {
        "service": "execution",
        "status": "running",
        "version": "1.0.0",
        "mt5_connected": account is not None,
        "account": {
            "login": account.login,
            "balance": account.balance,
            "currency": account.currency
        } if account else None
    }
