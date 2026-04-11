"""Orchestrator Service FastAPI 应用 - 编排层"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import signal, registration, account, portfolio, risk, evaluation, accounts_db, platform

# 创建FastAPI应用
app = FastAPI(
    title="Orchestrator Service",
    version="1.0.0",
    description="编排层：策略注册、调度决策、仓位管理、资金分配"
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
app.include_router(signal.router)            # 信号管理
app.include_router(registration.router)      # 策略注册服务
app.include_router(account.router)           # 账户管理（配置）
app.include_router(accounts_db.router)       # 账户管理（数据库）
app.include_router(platform.router)          # 平台检测
app.include_router(portfolio.router)         # 组合管理
app.include_router(risk.router)              # 风险管理
app.include_router(evaluation.router)        # 信号评估


@app.get("/")
def health_check():
    """健康检查"""
    return {"service": "orchestrator", "status": "running", "version": "1.0.0"}


@app.get("/health")
def health():
    """健康检查（详细）"""
    return {
        "service": "orchestrator",
        "status": "healthy",
        "version": "1.0.0",
        "layer": "Orchestrator Layer"
    }
