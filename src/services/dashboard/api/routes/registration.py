"""策略注册管理路由 - 代理Orchestrator的Registration API"""
from fastapi import APIRouter, HTTPException
import httpx

from src.common.config.settings import settings

router = APIRouter(prefix="/registration", tags=["registration"])

# 从配置读取Orchestrator服务URL
ORCHESTRATOR_URL = settings.get("service_urls", {}).get("orchestrator", "http://127.0.0.1:8002")


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
async def activate_strategy(strategy_id: str, force: bool = False):
    """激活策略"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/registration/activate/{strategy_id}",
                json={"force": force}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.post("/deactivate/{strategy_id}")
async def deactivate_strategy(strategy_id: str, reason: str = None):
    """停用策略"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/registration/deactivate/{strategy_id}",
                json={"reason": reason}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


@router.post("/archive/{strategy_id}")
async def archive_strategy(strategy_id: str, reason: str = None):
    """归档策略（永久停用）"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/registration/archive/{strategy_id}",
                json={"reason": reason}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")


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
async def restore_strategy(strategy_id: str):
    """恢复归档的策略到候选状态"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{ORCHESTRATOR_URL}/registration/restore/{strategy_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"恢复失败: {str(e)}")


@router.delete("/delete/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """永久删除策略"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{ORCHESTRATOR_URL}/registration/delete/{strategy_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
