"""Dashboard Service FastAPI 应用"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .routes import data, registration

# 创建FastAPI应用
app = FastAPI(
    title="Dashboard Service",
    version="1.0.0",
    description="可视化 Dashboard"
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
