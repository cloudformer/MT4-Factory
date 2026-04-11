"""API 响应模型"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class StrategyResponse(BaseModel):
    """策略响应"""
    id: str
    name: str
    status: str
    performance: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class GenerateStrategyResponse(BaseModel):
    """生成策略响应"""
    success: bool
    strategy_ids: List[str]
    message: str


class ListStrategiesResponse(BaseModel):
    """策略列表响应"""
    total: int
    strategies: List[StrategyResponse]
