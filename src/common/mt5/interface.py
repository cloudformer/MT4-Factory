"""MT5接口抽象层"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import pandas as pd


@dataclass
class AccountInfo:
    """账户信息"""
    login: int
    server: str
    balance: float
    equity: float
    margin: float
    margin_free: float
    leverage: int
    currency: str
    trade_allowed: bool


@dataclass
class TickInfo:
    """报价信息"""
    symbol: str
    time: datetime
    bid: float
    ask: float
    last: float
    volume: int


@dataclass
class OrderRequest:
    """订单请求"""
    action: str  # 'buy' or 'sell'
    symbol: str
    volume: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    deviation: int = 20
    magic: int = 234000
    comment: str = ""


@dataclass
class OrderResult:
    """订单结果"""
    success: bool
    order_id: Optional[int]
    ticket: Optional[int]
    price: Optional[float]
    volume: Optional[float]
    comment: str = ""


class MT5Interface(ABC):
    """MT5接口抽象类"""

    @abstractmethod
    def initialize(self) -> bool:
        """初始化连接"""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """关闭连接"""
        pass

    @abstractmethod
    def login(self, login: int, password: str, server: str) -> bool:
        """登录账户"""
        pass

    @abstractmethod
    def account_info(self) -> Optional[AccountInfo]:
        """获取账户信息"""
        pass

    @abstractmethod
    def symbol_info_tick(self, symbol: str) -> Optional[TickInfo]:
        """获取实时报价"""
        pass

    @abstractmethod
    def get_bars(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """获取K线数据"""
        pass

    @abstractmethod
    def order_send(self, request: OrderRequest) -> OrderResult:
        """发送订单"""
        pass

    @abstractmethod
    def positions_get(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取持仓"""
        pass

    @abstractmethod
    def last_error(self) -> tuple:
        """获取最后错误"""
        pass
