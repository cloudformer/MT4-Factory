"""Dashboard WebSocket 实时推送"""
import asyncio
import json
from typing import Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from src.common.database.connection import db
from src.common.models.strategy import Strategy, StrategyStatus
from src.common.models.signal import Signal
from src.common.models.trade import Trade
from src.common.models.account import Account


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        # 活跃连接集合
        self.active_connections: Set[WebSocket] = set()
        # 推送间隔（秒）
        self.push_interval = 2

    async def connect(self, websocket: WebSocket):
        """接受新连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"✅ WebSocket连接: {websocket.client} | 总连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        self.active_connections.discard(websocket)
        print(f"❌ WebSocket断开: {websocket.client} | 总连接数: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"发送消息失败: {str(e)}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"广播失败: {str(e)}")
                disconnected.add(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)

    async def start_push_loop(self):
        """
        启动数据推送循环

        每隔N秒推送一次数据
        """
        print(f"🔄 启动WebSocket推送循环（间隔: {self.push_interval}秒）")

        while True:
            try:
                # 如果有活跃连接，推送数据
                if self.active_connections:
                    data = await self._fetch_latest_data()
                    await self.broadcast({
                        "type": "update",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": data
                    })

                # 等待下一次推送
                await asyncio.sleep(self.push_interval)

            except Exception as e:
                print(f"推送循环异常: {str(e)}", exc_info=True)
                await asyncio.sleep(self.push_interval)

    async def _fetch_latest_data(self) -> dict:
        """
        获取最新数据

        包括：
        - 策略统计
        - 最新信号
        - 最新交易
        - 账户状态
        """
        try:
            with db.session_scope() as session:
                # 1. 策略统计
                total_strategies = session.query(Strategy).count()
                active_strategies = session.query(Strategy).filter(
                    Strategy.status == StrategyStatus.ACTIVE
                ).count()
                candidate_strategies = session.query(Strategy).filter(
                    Strategy.status == StrategyStatus.CANDIDATE
                ).count()

                # 2. 信号统计
                total_signals = session.query(Signal).count()
                pending_signals = session.query(Signal).filter(
                    Signal.status == 'pending'
                ).count()

                # 3. 交易统计
                total_trades = session.query(Trade).count()
                open_trades = session.query(Trade).filter(
                    Trade.close_time.is_(None)
                ).count()

                # 4. 账户统计
                total_accounts = session.query(Account).count()
                active_accounts = session.query(Account).filter(
                    Account.is_active == True
                ).count()

                # 5. 最新策略（前5个）
                latest_strategies = session.query(Strategy).order_by(
                    Strategy.updated_at.desc()
                ).limit(5).all()

                # 6. 最新信号（前10个）
                latest_signals = session.query(Signal).order_by(
                    Signal.created_at.desc()
                ).limit(10).all()

                # 7. 最新交易（前10个）
                latest_trades = session.query(Trade).order_by(
                    Trade.created_at.desc()
                ).limit(10).all()

                return {
                    "stats": {
                        "total_strategies": total_strategies,
                        "active_strategies": active_strategies,
                        "candidate_strategies": candidate_strategies,
                        "total_signals": total_signals,
                        "pending_signals": pending_signals,
                        "total_trades": total_trades,
                        "open_trades": open_trades,
                        "total_accounts": total_accounts,
                        "active_accounts": active_accounts
                    },
                    "latest_strategies": [s.to_dict() for s in latest_strategies],
                    "latest_signals": [s.to_dict() for s in latest_signals],
                    "latest_trades": [t.to_dict() for t in latest_trades]
                }

        except Exception as e:
            print(f"获取数据失败: {str(e)}")
            return {
                "stats": {},
                "latest_strategies": [],
                "latest_signals": [],
                "latest_trades": [],
                "error": str(e)
            }


# 全局连接管理器
manager = ConnectionManager()
