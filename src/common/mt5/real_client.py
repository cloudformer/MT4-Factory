"""真实 MT5 客户端（用于 Windows 生产环境）"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import pandas as pd

from .interface import (
    MT5Interface,
    AccountInfo,
    TickInfo,
    OrderRequest,
    OrderResult
)


class RealMT5Client(MT5Interface):
    """真实 MT5 实现 - 用于 Windows 生产环境"""

    def __init__(self):
        try:
            import MetaTrader5 as mt5
            self._mt5 = mt5
        except ImportError:
            raise RuntimeError("MetaTrader5 库只能在 Windows 上使用")

    def initialize(self) -> bool:
        return self._mt5.initialize()

    def shutdown(self) -> None:
        self._mt5.shutdown()

    def login(self, login: int, password: str, server: str) -> bool:
        return self._mt5.login(login, password=password, server=server)

    def account_info(self) -> Optional[AccountInfo]:
        info = self._mt5.account_info()
        if info is None:
            return None

        return AccountInfo(
            login=info.login,
            server=info.server,
            balance=info.balance,
            equity=info.equity,
            margin=info.margin,
            margin_free=info.margin_free,
            leverage=info.leverage,
            currency=info.currency,
            trade_allowed=info.trade_allowed
        )

    def symbol_info_tick(self, symbol: str) -> Optional[TickInfo]:
        tick = self._mt5.symbol_info_tick(symbol)
        if tick is None:
            return None

        return TickInfo(
            symbol=symbol,
            time=datetime.fromtimestamp(tick.time),
            bid=tick.bid,
            ask=tick.ask,
            last=tick.last,
            volume=tick.volume
        )

    def get_bars(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """获取真实K线数据"""
        # 时间框架映射
        tf_map = {
            "M1": self._mt5.TIMEFRAME_M1,
            "M5": self._mt5.TIMEFRAME_M5,
            "M15": self._mt5.TIMEFRAME_M15,
            "M30": self._mt5.TIMEFRAME_M30,
            "H1": self._mt5.TIMEFRAME_H1,
            "H4": self._mt5.TIMEFRAME_H4,
            "D1": self._mt5.TIMEFRAME_D1,
        }

        if timeframe not in tf_map:
            raise ValueError(f"不支持的时间框架: {timeframe}")

        rates = self._mt5.copy_rates_from_pos(
            symbol,
            tf_map[timeframe],
            0,
            count
        )

        if rates is None or len(rates) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')

        return df

    def order_send(self, request: OrderRequest) -> OrderResult:
        # 获取报价
        tick = self._mt5.symbol_info_tick(request.symbol)
        if tick is None:
            return OrderResult(
                success=False,
                order_id=None,
                ticket=None,
                price=None,
                volume=None,
                comment="Symbol not found"
            )

        # 订单类型
        price = tick.ask if request.action == 'buy' else tick.bid
        order_type = self._mt5.ORDER_TYPE_BUY if request.action == 'buy' else self._mt5.ORDER_TYPE_SELL

        # 构建订单请求
        mt5_request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": request.symbol,
            "volume": request.volume,
            "type": order_type,
            "price": price,
            "deviation": request.deviation,
            "magic": request.magic,
            "comment": request.comment,
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_IOC,
        }

        if request.sl is not None:
            mt5_request["sl"] = request.sl
        if request.tp is not None:
            mt5_request["tp"] = request.tp

        # 发送订单
        result = self._mt5.order_send(mt5_request)

        return OrderResult(
            success=(result.retcode == self._mt5.TRADE_RETCODE_DONE),
            order_id=result.order if hasattr(result, 'order') else None,
            ticket=result.order if hasattr(result, 'order') else None,
            price=result.price if hasattr(result, 'price') else None,
            volume=result.volume if hasattr(result, 'volume') else None,
            comment=result.comment if hasattr(result, 'comment') else ""
        )

    def positions_get(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if symbol:
            positions = self._mt5.positions_get(symbol=symbol)
        else:
            positions = self._mt5.positions_get()

        if positions is None:
            return []

        return [pos._asdict() for pos in positions]

    def last_error(self) -> tuple:
        return self._mt5.last_error()
