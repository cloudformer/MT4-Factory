"""Strategy Service FastAPI 应用 - 策略层"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import strategy

# 创建FastAPI应用
app = FastAPI(
    title="Strategy Service",
    version="1.0.0",
    description="策略层：策略生成、风控计算、信号生成"
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
app.include_router(strategy.router)


@app.get("/")
def health_check():
    """健康检查"""
    return {"service": "strategy", "status": "running", "version": "1.0.0"}


@app.get("/health")
def health():
    """健康检查（详细）"""
    return {
        "service": "strategy",
        "status": "healthy",
        "version": "1.0.0",
        "layer": "Strategy Layer"
    }
