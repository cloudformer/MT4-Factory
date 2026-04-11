"""实时数据评估器 - 在实时行情中测试策略（纸面交易）"""
from typing import Dict, Optional, Callable
from datetime import datetime
import pandas as pd
import time

from .base_evaluator import BaseEvaluator


class RealtimeDataEvaluator(BaseEvaluator):
    """实时数据评估器 - 使用实时行情进行纸面交易测试"""

    def __init__(self, initial_balance: float = 10000.0):
        super().__init__(initial_balance)
        self.is_running = False
        self.tick_buffer = []
        self.max_buffer_size = 1000

    def evaluate(self, strategy_code: str, symbol: str = "EURUSD",
                 duration_minutes: int = 60,
                 tick_callback: Optional[Callable] = None) -> Dict:
        """
        实时评估策略（纸面交易）

        Args:
            strategy_code: 策略代码
            symbol: 交易品种
            duration_minutes: 测试持续时间（分钟）
            tick_callback: tick数据回调函数

        Returns:
            性能指标字典
        """
        print(f"   🔴 启动实时评估：{symbol} x {duration_minutes}分钟...")
        print(f"   ⚠️  这是纸面交易，不会实际下单")

        # 加载策略
        strategy = self._load_strategy(strategy_code)

        # 初始化
        self.balance = self.initial_balance
        self.trades = []
        self.equity_curve = [self.initial_balance]
        self.is_running = True
        current_position = None

        start_time = datetime.now()
        end_time = start_time.timestamp() + duration_minutes * 60

        try:
            while self.is_running and time.time() < end_time:
                # 1. 获取实时tick
                tick = self._fetch_realtime_tick(symbol)

                if tick is None:
                    time.sleep(1)  # 等待下一个tick
                    continue

                # 2. 添加到缓冲区
                self.tick_buffer.append(tick)
                if len(self.tick_buffer) > self.max_buffer_size:
                    self.tick_buffer.pop(0)

                # 3. 转换为K线数据
                if len(self.tick_buffer) < 50:
                    continue  # 需要足够的数据计算均线

                window_data = self._ticks_to_bars(self.tick_buffer)

                # 4. 执行策略
                try:
                    signal = strategy.on_tick(window_data)
                except Exception as e:
                    print(f"   ❌ 策略执行出错: {e}")
                    signal = None

                # 5. 处理信号（纸面交易）
                if signal and current_position is None:
                    # 开仓
                    current_position = self._open_position(
                        signal, tick, len(self.tick_buffer)
                    )
                    print(f"   📈 开仓: {signal} @ {tick['bid']}")

                elif current_position and signal:
                    direction, entry_price, volume, entry_idx = current_position
                    if (direction == 'buy' and signal == 'sell') or \
                       (direction == 'sell' and signal == 'buy'):
                        # 平仓
                        self._close_position(current_position, tick, len(self.tick_buffer))
                        print(f"   📉 平仓: 盈亏 ${self.trades[-1]['pnl']:.2f}")
                        current_position = None

                        # 开新仓
                        current_position = self._open_position(
                            signal, tick, len(self.tick_buffer)
                        )
                        print(f"   📈 开仓: {signal} @ {tick['bid']}")

                # 6. 更新权益曲线
                if current_position:
                    direction, entry_price, volume, entry_idx = current_position
                    current_price = tick['bid']
                    if direction == 'buy':
                        unrealized_pnl = (current_price - entry_price) * volume * 100000
                    else:
                        unrealized_pnl = (entry_price - current_price) * volume * 100000
                    self.equity_curve.append(self.balance + unrealized_pnl)
                else:
                    self.equity_curve.append(self.balance)

                # 7. 回调
                if tick_callback:
                    tick_callback(tick, signal, current_position)

                # 控制频率
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n   ⚠️  用户中断测试")

        finally:
            self.is_running = False

            # 平掉最后的持仓
            if current_position and len(self.tick_buffer) > 0:
                self._close_position(
                    current_position,
                    self.tick_buffer[-1],
                    len(self.tick_buffer)
                )

        # 计算指标
        metrics = self.calculate_metrics()
        metrics['data_source'] = 'realtime'
        metrics['data_symbol'] = symbol
        metrics['test_duration_minutes'] = duration_minutes
        metrics['backtest_date'] = datetime.now().isoformat()

        return metrics

    def _fetch_realtime_tick(self, symbol: str) -> Optional[Dict]:
        """
        获取实时tick数据

        TODO: 实现真实tick获取
        - 从MT5获取实时报价
        - 从WebSocket连接获取
        - 从第三方API获取

        Args:
            symbol: 交易品种

        Returns:
            tick字典: {'time': datetime, 'bid': float, 'ask': float}
        """
        raise NotImplementedError(
            "实时tick获取功能待实现。\n"
            "可选方案：\n"
            "1. 从MT5获取：使用MetaTrader5.symbol_info_tick()\n"
            "2. 从WebSocket：连接经纪商WebSocket API\n"
            "3. 从REST API：轮询第三方行情服务"
        )

    def _ticks_to_bars(self, ticks: list) -> pd.DataFrame:
        """
        将tick数据转换为K线数据

        简化版本：使用滑动窗口聚合tick为1分钟K线

        Args:
            ticks: tick列表

        Returns:
            K线DataFrame
        """
        if not ticks:
            return pd.DataFrame()

        # 转换为DataFrame
        df = pd.DataFrame(ticks)
        df['time'] = pd.to_datetime(df['time'])
        df['price'] = (df['bid'] + df['ask']) / 2

        # 按1分钟聚合
        df.set_index('time', inplace=True)
        bars = df['price'].resample('1min').agg(
            open='first',
            high='max',
            low='min',
            close='last'
        ).dropna()

        bars['volume'] = 100  # 模拟成交量
        bars = bars.reset_index()

        return bars

    def stop(self):
        """停止实时评估"""
        self.is_running = False

    def _open_position(self, direction: str, tick: Dict, idx: int) -> tuple:
        """开仓（纸面交易）"""
        entry_price = tick['ask'] if direction == 'buy' else tick['bid']
        volume = 0.1  # 固定0.1手

        return (direction, entry_price, volume, idx)

    def _close_position(self, position: tuple, tick: Dict, idx: int):
        """平仓（纸面交易）"""
        direction, entry_price, volume, entry_idx = position
        exit_price = tick['bid'] if direction == 'buy' else tick['ask']

        # 计算盈亏
        if direction == 'buy':
            pnl = (exit_price - entry_price) * volume * 100000
        else:
            pnl = (entry_price - exit_price) * volume * 100000

        self.balance += pnl

        # 记录交易
        self.trades.append({
            'entry_time': entry_idx,
            'exit_time': idx,
            'direction': direction,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'volume': volume,
            'pnl': pnl,
            'balance': self.balance
        })
