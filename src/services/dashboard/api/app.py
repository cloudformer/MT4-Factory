"""Dashboard Service FastAPI 应用"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .routes import data, registration, mt5_hosts
from .websocket import manager


# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：创建后台任务推送WebSocket数据
    push_task = asyncio.create_task(manager.start_push_loop())

    yield

    # 关闭时：取消后台任务
    push_task.cancel()


# 创建FastAPI应用
app = FastAPI(
    title="Dashboard Service",
    version="1.0.0",
    description="可视化 Dashboard",
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

# 注册API路由
app.include_router(data.router)
app.include_router(registration.router, prefix="/api")  # 策略注册管理
app.include_router(mt5_hosts.router)  # MT5主机管理

# 模板目录
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Dashboard 首页"""
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


@app.get("/health")
def health():
    """健康检查"""
    return {"service": "dashboard", "status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket连接端点

    客户端连接后会自动接收实时数据推送
    """
    await manager.connect(websocket)

    try:
        while True:
            # 接收客户端消息（保持连接活跃）
            data = await websocket.receive_text()

            # 可以处理客户端请求（如果需要）
            # 目前主要用于保持连接
            await manager.send_personal_message({
                "type": "pong",
                "message": "Connection alive"
            }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
