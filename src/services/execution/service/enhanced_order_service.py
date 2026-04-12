"""增强订单执行服务 - 包含风控、重试、追踪"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

from src.common.models.signal import Signal, SignalStatus
from src.common.models.trade import Trade
from src.common.models.account import Account
from src.common.utils.id_generator import generate_trade_id
from src.common.mt5 import mt5_manager, OrderRequest
from src.common.logger import get_logger
from ..repository.trade_repo import TradeRepository
from .risk_manager import RiskManager, RiskCheckResult

logger = get_logger(__name__)


class OrderExecutionError(Exception):
    """订单执行异常"""
    pass


class EnhancedOrderService:
    """
    增强订单执行服务

    功能：
    1. ✅ 风控检查
    2. ✅ 错误重试（最多3次）
    3. ✅ 订单状态追踪
    4. ✅ 自动平仓（止损/止盈触发）
    5. ✅ 详细日志记录
    """

    def __init__(self, trade_repo: TradeRepository):
        self.trade_repo = trade_repo
        self.mt5_client = mt5_manager.get_client()
        self.risk_manager = RiskManager()

        # 配置
        self.max_retries = 3
        self.retry_delay = 2  # 秒

        # 订单追踪（内存缓存）
        self._active_orders: Dict[int, Trade] = {}  # ticket -> Trade

    async def execute_signal(
        self,
        signal: Signal,
        account: Optional[Account] = None
    ) -> Trade:
        """
        执行信号（异步）

        Args:
            signal: 交易信号
            account: 账户信息（用于风控检查）

        Returns:
            Trade对象

        Raises:
            OrderExecutionError: 执行失败
        """
        logger.info(f"📨 收到执行信号: {signal.id} | {signal.symbol} {signal.direction.value} {signal.volume}")

        # 1. 风控检查
        risk_result = self.risk_manager.check_signal(signal, account)
        if not risk_result.passed:
            logger.warning(f"❌ 风控拒绝: {risk_result.reason}")
            raise OrderExecutionError(f"风控拒绝: {risk_result.reason}")

        # 2. 检查MT5连接
        if not mt5_manager.is_connected():
            logger.error("❌ MT5未连接")
            raise OrderExecutionError("MT5未连接，请检查连接状态")

        # 3. 执行订单（带重试）
        trade = await self._execute_with_retry(signal, account)

        # 4. 更新风控状态
        self.risk_manager.update_position(trade.ticket, trade.symbol, 'open')

        # 5. 添加到追踪列表
        self._active_orders[trade.ticket] = trade

        logger.info(f"✅ 订单执行成功: Ticket={trade.ticket} | Price={trade.open_price}")

        return trade

    async def _execute_with_retry(
        self,
        signal: Signal,
        account: Optional[Account]
    ) -> Trade:
        """
        带重试的订单执行

        最多重试3次，每次间隔2秒
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"🔄 执行尝试 {attempt}/{self.max_retries}")

                # 构建订单请求
                order_request = OrderRequest(
                    action=signal.direction.value,
                    symbol=signal.symbol,
                    volume=float(signal.volume),
                    sl=float(signal.sl) if signal.sl else None,
                    tp=float(signal.tp) if signal.tp else None,
                    comment=f"Strategy: {signal.strategy_id}"
                )

                # 发送订单
                result = self.mt5_client.order_send(order_request)

                if not result.success:
                    raise OrderExecutionError(f"MT5返回失败: {result.comment}")

                # 创建交易记录
                trade = Trade(
                    id=generate_trade_id(),
                    signal_id=signal.id,
                    strategy_id=signal.strategy_id,
                    account_id=account.id if account else None,
                    ticket=result.ticket,
                    symbol=signal.symbol,
                    direction=signal.direction,
                    volume=signal.volume,
                    open_price=result.price,
                    open_time=datetime.utcnow()
                )

                # 保存到数据库
                trade = self.trade_repo.create(trade)

                return trade

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️  尝试 {attempt} 失败: {str(e)}")

                # 如果不是最后一次尝试，等待后重试
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"❌ 所有重试失败，放弃执行")

        # 所有重试都失败
        raise OrderExecutionError(f"订单执行失败（重试{self.max_retries}次）: {str(last_error)}")

    async def close_order(
        self,
        ticket: int,
        reason: str = "manual"
    ) -> Trade:
        """
        平仓订单

        Args:
            ticket: MT5订单号
            reason: 平仓原因 ('manual', 'stop_loss', 'take_profit', 'risk')

        Returns:
            更新后的Trade对象

        Raises:
            OrderExecutionError: 平仓失败
        """
        logger.info(f"📤 平仓请求: Ticket={ticket} | Reason={reason}")

        # 1. 检查订单是否在追踪列表
        if ticket not in self._active_orders:
            logger.warning(f"⚠️  订单 {ticket} 不在追踪列表中")
            # 尝试从数据库查询
            trade = self.trade_repo.get_by_ticket(ticket)
            if not trade:
                raise OrderExecutionError(f"订单 {ticket} 不存在")
        else:
            trade = self._active_orders[ticket]

        # 2. 调用MT5平仓
        try:
            result = self.mt5_client.order_close(ticket)

            if not result.success:
                raise OrderExecutionError(f"MT5平仓失败: {result.comment}")

            # 3. 更新交易记录
            trade.close_price = result.price
            trade.close_time = datetime.utcnow()
            trade.profit = result.profit

            # 保存到数据库
            trade = self.trade_repo.update(trade)

            # 4. 从追踪列表移除
            if ticket in self._active_orders:
                del self._active_orders[ticket]

            # 5. 更新风控状态
            self.risk_manager.update_position(ticket, trade.symbol, 'close')

            logger.info(f"✅ 平仓成功: Ticket={ticket} | Profit={trade.profit}")

            return trade

        except Exception as e:
            logger.error(f"❌ 平仓失败: {str(e)}")
            raise OrderExecutionError(f"平仓失败: {str(e)}")

    async def sync_positions(self):
        """
        同步持仓状态

        从MT5查询当前持仓，更新本地追踪列表
        """
        try:
            positions = self.mt5_client.positions_get()

            if positions is None:
                logger.warning("⚠️  无法获取持仓列表")
                return

            # 更新追踪列表
            active_tickets = {pos.ticket for pos in positions}

            # 检查是否有已平仓的订单（本地有记录但MT5没有）
            for ticket in list(self._active_orders.keys()):
                if ticket not in active_tickets:
                    logger.info(f"📊 检测到已平仓订单: Ticket={ticket}")
                    # 从MT5历史记录查询平仓信息
                    try:
                        await self._sync_closed_order(ticket)
                    except Exception as e:
                        logger.error(f"同步平仓订单失败: {str(e)}")

            logger.info(f"✅ 持仓同步完成: 活跃订单 {len(active_tickets)} 个")

        except Exception as e:
            logger.error(f"❌ 持仓同步失败: {str(e)}")

    async def _sync_closed_order(self, ticket: int):
        """同步已平仓订单信息"""
        # 从MT5历史记录查询
        deals = self.mt5_client.history_deals_get(ticket=ticket)

        if deals and len(deals) > 0:
            # 找到平仓成交
            close_deal = [d for d in deals if d.entry == 1]  # 1 = OUT
            if close_deal:
                deal = close_deal[0]

                # 更新交易记录
                trade = self._active_orders.get(ticket)
                if trade:
                    trade.close_price = deal.price
                    trade.close_time = datetime.fromtimestamp(deal.time)
                    trade.profit = deal.profit

                    self.trade_repo.update(trade)

                    # 从追踪列表移除
                    del self._active_orders[ticket]

                    # 更新风控状态
                    self.risk_manager.update_position(ticket, trade.symbol, 'close')

    def get_active_orders(self) -> list:
        """获取活跃订单列表"""
        return list(self._active_orders.values())

    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            'active_orders': len(self._active_orders),
            'risk_manager': self.risk_manager.get_stats(),
            'mt5_connected': mt5_manager.is_connected()
        }
