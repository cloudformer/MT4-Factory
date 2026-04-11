"""API 请求模型"""
from pydantic import BaseModel, Field


class GenerateStrategyRequest(BaseModel):
    """生成策略请求"""
    count: int = Field(default=1, ge=1, le=10, description="生成策略数量")
    template: str = Field(default="ma_crossover", description="策略模板")
