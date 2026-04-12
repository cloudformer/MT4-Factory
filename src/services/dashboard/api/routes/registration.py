"""策略注册管理路由 - 直接操作数据库"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import httpx

from src.common.config.settings import settings
from src.common.database.connection import db
from src.common.models.strategy import Strategy, StrategyStatus
from src.common.models.mt5_host import MT5Host

router = APIRouter(prefix="/registration", tags=["registration"])

# 从配置读取Orchestrator服务URL
ORCHESTRATOR_URL = settings.get("service_urls", {}).get("orchestrator", "http://127.0.0.1:8002")


def get_db_session():
    """获取数据库Session"""
    with db.session_scope() as session:
        yield session


@router.get("/summary")
async def get_registration_summary():
    """获取注册服务概览"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{ORCHESTRATOR_URL}/registration/summary")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"无法连接Orchestrator: {str(e)}")


@router.get("/candidates")
async def get_candidate_strategies():
    """获取候选策略列表"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{ORCHESTRATOR_URL}/registration/candidates")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"无法连接Orchestrator: {str(e)}")


@router.get("/active")
async def get_active_strategies():
    """获取激活的策略列表"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{ORCHESTRATOR_URL}/registration/active")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"无法连接Orchestrator: {str(e)}")


@router.post("/activate/{strategy_id}")
def activate_strategy(strategy_id: str, session: Session = Depends(get_db_session)):
    """激活策略"""
    strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        return {"success": False, "message": "策略不存在", "strategy_id": strategy_id}

    strategy.status = StrategyStatus.ACTIVE
    session.commit()

    return {"success": True, "message": f"策略 {strategy.name} 已激活", "strategy_id": strategy_id}


@router.post("/deactivate/{strategy_id}")
def deactivate_strategy(strategy_id: str, session: Session = Depends(get_db_session)):
    """停用策略"""
    strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        return {"success": False, "message": "策略不存在", "strategy_id": strategy_id}

    strategy.status = StrategyStatus.CANDIDATE
    session.commit()

    return {"success": True, "message": f"策略 {strategy.name} 已停用", "strategy_id": strategy_id}


@router.post("/archive/{strategy_id}")
def archive_strategy(strategy_id: str, session: Session = Depends(get_db_session)):
    """归档策略（永久停用）"""
    strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        return {"success": False, "message": "策略不存在", "strategy_id": strategy_id}

    strategy.status = StrategyStatus.ARCHIVED
    session.commit()

    return {"success": True, "message": f"策略 {strategy.name} 已归档", "strategy_id": strategy_id}


@router.get("/evaluate/{strategy_id}")
async def evaluate_strategy(strategy_id: str):
    """评估策略质量"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{ORCHESTRATOR_URL}/registration/evaluate/{strategy_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"评估失败: {str(e)}")


@router.post("/batch-evaluate")
async def batch_evaluate_candidates():
    """批量评估候选策略（自动激活符合条件的）"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(f"{ORCHESTRATOR_URL}/registration/batch-evaluate")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"批量评估失败: {str(e)}")


@router.post("/restore/{strategy_id}")
def restore_strategy(strategy_id: str, session: Session = Depends(get_db_session)):
    """恢复归档的策略到候选状态"""
    strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        return {"success": False, "message": "策略不存在", "strategy_id": strategy_id}

    strategy.status = StrategyStatus.CANDIDATE
    session.commit()

    return {"success": True, "message": f"策略 {strategy.name} 已恢复到候选状态", "strategy_id": strategy_id}


@router.delete("/delete/{strategy_id}")
def delete_strategy(strategy_id: str, session: Session = Depends(get_db_session)):
    """永久删除策略"""
    strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        return {"success": False, "message": "策略不存在", "strategy_id": strategy_id}

    strategy_name = strategy.name
    session.delete(strategy)
    session.commit()

    return {"success": True, "message": f"策略 {strategy_name} 已删除", "strategy_id": strategy_id}


class BindMT5HostRequest(BaseModel):
    """绑定MT5主机请求"""
    mt5_host_id: Optional[str] = None


@router.post("/bind-mt5/{strategy_id}")
def bind_mt5_host(strategy_id: str, request: BindMT5HostRequest, session: Session = Depends(get_db_session)):
    """
    绑定策略到MT5主机

    如果mt5_host_id为null，则解绑
    """
    strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()

    if not strategy:
        return {"success": False, "message": "策略不存在", "strategy_id": strategy_id}

    # 如果指定了MT5 host，验证其存在
    if request.mt5_host_id:
        mt5_host = session.query(MT5Host).filter(MT5Host.id == request.mt5_host_id).first()
        if not mt5_host:
            return {"success": False, "message": f"MT5主机不存在: {request.mt5_host_id}"}

        strategy.mt5_host_id = request.mt5_host_id
        message = f"策略 {strategy.name} 已绑定到 {mt5_host.name}"
    else:
        # 解绑
        strategy.mt5_host_id = None
        message = f"策略 {strategy.name} 已解绑MT5主机"

    session.commit()

    return {
        "success": True,
        "message": message,
        "strategy_id": strategy_id,
        "mt5_host_id": strategy.mt5_host_id
    }
