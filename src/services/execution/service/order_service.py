"""订单执行服务"""
from datetime import datetime

from src.common.models.signal import Signal
from src.common.models.trade import Trade
from src.common.utils.id_generator import generate_trade_id
from src.common.mt5 import mt5_manager, OrderRequest
from ..repository.trade_repo import TradeRepository


class OrderExecutionService:
    """订单执行业务逻辑"""

    def __init__(self, trade_repo: TradeRepository):
        self.trade_repo = trade_repo
        # 使用全局MT5连接管理器
        self.mt5_client = mt5_manager.get_client()

    def execute_signal(self, signal: Signal) -> Trade:
        """
        执行信号，创建交易

        Args:
            signal: 信号对象

        Returns:
            Trade对象
        """
        # 1. 检查MT5连接
        if not mt5_manager.is_connected():
            raise RuntimeError("MT5未连接，请检查连接状态")

        # 2. 构建订单请求
        order_request = OrderRequest(
            action=signal.direction.value,
            symbol=signal.symbol,
            volume=float(signal.volume),
            sl=float(signal.sl) if signal.sl else None,
            tp=float(signal.tp) if signal.tp else None,
            comment=f"Strategy: {signal.strategy_id}"
        )

        # 3. 发送订单到MT5
        result = self.mt5_client.order_send(order_request)

        if not result.success:
            raise RuntimeError(f"订单执行失败: {result.comment}")

        print(f"✅ 订单执行成功: Ticket={result.ticket}, Price={result.price}")

        # 4. 创建交易记录
        trade = Trade(
            id=generate_trade_id(),
            signal_id=signal.id,
            strategy_id=signal.strategy_id,
            ticket=result.ticket,
            symbol=signal.symbol,
            direction=signal.direction,
            volume=signal.volume,
            open_price=result.price,
            open_time=datetime.now()
        )

        # 5. 保存到数据库
        trade = self.trade_repo.create(trade)

        return trade

    def get_all_trades(self):
        """获取所有交易"""
        return self.trade_repo.get_all()
