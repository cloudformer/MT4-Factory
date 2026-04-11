"""Orchestrator Service FastAPI 应用 - 编排层"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import signal

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
app.include_router(signal.router)


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
