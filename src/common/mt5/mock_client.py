"""Mock MT5 客户端（用于开发测试）"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np

from .interface import (
    MT5Interface,
    AccountInfo,
    TickInfo,
    OrderRequest,
    OrderResult
)


class MockMT5Client(MT5Interface):
    """Mock MT5 实现 - 用于 macOS 开发测试"""

    def __init__(self, path: Optional[str] = None, timeout: int = 60000, portable: bool = False):
        """
        初始化Mock客户端

        Args:
            path: MT5终端路径（Mock中不使用）
            timeout: 连接超时时间（Mock中不使用）
            portable: 是否使用便携模式（Mock中不使用）
        """
        self._initialized = False
        self._logged_in = False
        self._account = None
        self._positions = []
        self._last_error = (0, "No error")
        self._order_counter = 1000

    def initialize(self, login: Optional[int] = None, password: Optional[str] = None,
                   server: Optional[str] = None) -> bool:
        """
        初始化连接（Mock）

        Args:
            login: 账号（可选，如果提供则自动登录）
            password: 密码（可选）
            server: 服务器（可选）
        """
        print("[MockMT5] 初始化连接（模拟）")
        self._initialized = True

        # 如果提供了登录信息，自动登录
        if login and password and server:
            print(f"[MockMT5] 自动登录: {login}@{server}")
            return self.login(login, password, server)

        return True

    def shutdown(self) -> None:
        print("[MockMT5] 关闭连接（模拟）")
        self._initialized = False
        self._logged_in = False

    def login(self, login: int, password: str, server: str) -> bool:
        print(f"[MockMT5] 登录账户（模拟）: {login}@{server}")
        if not self._initialized:
            self._last_error = (1, "Not initialized")
            return False

        self._logged_in = True
        self._account = AccountInfo(
            login=login,
            server=server,
            balance=10000.0,
            equity=10000.0,
            margin=0.0,
            margin_free=10000.0,
            leverage=100,
            currency="USD",
            trade_allowed=True
        )
        return True

    def account_info(self) -> Optional[AccountInfo]:
        if not self._logged_in:
            return None
        return self._account

    def symbol_info_tick(self, symbol: str) -> Optional[TickInfo]:
        if not self._logged_in:
            return None

        # 模拟报价数据
        mock_prices = {
            "EURUSD": (1.0850, 1.0852),
            "GBPUSD": (1.2650, 1.2652),
            "USDJPY": (149.50, 149.52),
            "USDCHF": (0.8850, 0.8852),
            "AUDUSD": (0.6550, 0.6552),
        }

        if symbol not in mock_prices:
            return None

        bid, ask = mock_prices[symbol]
        return TickInfo(
            symbol=symbol,
            time=datetime.now(),
            bid=bid,
            ask=ask,
            last=ask,
            volume=100
        )

    def get_bars(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """获取模拟K线数据"""
        if not self._logged_in:
            return pd.DataFrame()

        # 生成模拟K线 (使用小写h避免pandas警告)
        dates = pd.date_range(end=datetime.now(), periods=count, freq='h')

        # 基础价格
        base_price = 1.0850 if symbol == "EURUSD" else 1.2650

        # 生成价格序列（随机游走）
        returns = np.random.randn(count) * 0.001
        close_prices = base_price * (1 + returns).cumprod()

        df = pd.DataFrame({
            'time': dates,
            'open': close_prices,
            'high': close_prices * 1.0005,
            'low': close_prices * 0.9995,
            'close': close_prices,
            'volume': np.random.randint(100, 1000, count)
        })

        return df

    def order_send(self, request: OrderRequest) -> OrderResult:
        if not self._logged_in:
            return OrderResult(
                success=False,
                order_id=None,
                ticket=None,
                price=None,
                volume=None,
                comment="Not logged in"
            )

        # 模拟下单成功
        ticket = self._order_counter
        self._order_counter += 1

        tick = self.symbol_info_tick(request.symbol)
        if tick is None:
            return OrderResult(
                success=False,
                order_id=None,
                ticket=None,
                price=None,
                volume=None,
                comment="Invalid symbol"
            )

        price = tick.ask if request.action == 'buy' else tick.bid

        print(f"[MockMT5] 模拟下单: {request.action.upper()} {request.volume} {request.symbol} @ {price}")

        return OrderResult(
            success=True,
            order_id=ticket,
            ticket=ticket,
            price=price,
            volume=request.volume,
            comment="Mock order executed"
        )

    def positions_get(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self._logged_in:
            return []
        return self._positions

    def last_error(self) -> tuple:
        return self._last_error
