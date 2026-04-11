"""Brain API 请求模型"""
from pydantic import BaseModel, Field


class PromoteStrategyRequest(BaseModel):
    """晋升策略请求"""
    strategy_id: str = Field(..., description="策略ID")


class GenerateSignalRequest(BaseModel):
    """生成信号请求"""
    strategy_id: str = Field(..., description="策略ID")
    symbol: str = Field(default="EURUSD", description="交易品种")
