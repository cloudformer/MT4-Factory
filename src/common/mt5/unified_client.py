"""统一MT5客户端：根据连接参数自动选择本地或远程"""
from typing import Optional, List, Dict, Any
import pandas as pd
import requests
import platform
from datetime import datetime

from .interface import (
    MT5Interface,
    AccountInfo,
    TickInfo,
    OrderRequest,
    OrderResult
)
from src.common.logger import get_logger

logger = get_logger(__name__)


class UnifiedMT5Client(MT5Interface):
    """
    统一MT5客户端 - 自动判断本地/远程

    判断逻辑：
    1. 如果在Windows系统 + localhost/127.0.0.1 → 本地直连MetaTrader5库
    2. 其他情况 → HTTP API远程调用

    配置参数：
        host: MT5地址
            - "localhost" / "127.0.0.1" → 本地（Windows）
            - "host.docker.internal" → 容器访问宿主机（Windows）
            - "52.xx.xx.xx" → 远程Windows VPS
        port: API端口（远程必需，默认9090）
        login: MT5账号
        password: MT5密码
        server: MT5服务器名称
        api_key: API认证密钥（远程可选）
        timeout: 超时时间（秒，默认10）
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9090,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 10
    ):
        """
        初始化统一客户端

        Args:
            host: MT5主机地址
            port: API端口（HTTP模式使用）
            login: MT5账号（可选）
            password: MT5密码（可选）
            server: MT5服务器（可选）
            api_key: API密钥（远程模式认证）
            timeout: 超时时间（秒）
        """
        self.host = host
        self.port = port
        self.login = login
        self.password = password
        self.server = server
        self.api_key = api_key
        self.timeout = timeout

        # 判断是否本地模式
        self._is_local = self._detect_local_mode()

        # 本地模式：导入MetaTrader5库
        if self._is_local:
            try:
                import MetaTrader5 as mt5
                self._mt5 = mt5
                logger.info("✅ 检测到本地模式：直连MetaTrader5")
            except ImportError:
                raise RuntimeError("本地模式需要MetaTrader5库（仅Windows支持）")

        # 远程模式：构建HTTP API地址
        else:
            self.base_url = f"http://{self.host}:{self.port}"
            self._headers = {}
            if self.api_key:
                self._headers["Authorization"] = f"Bearer {self.api_key}"
            logger.info(f"✅ 检测到远程模式：HTTP API → {self.base_url}")

    def _detect_local_mode(self) -> bool:
        """
        自动检测是否本地模式

        Returns:
            True: 本地直连
            False: 远程HTTP API
        """
        # 只有Windows系统才能本地直连
        if platform.system() != "Windows":
            return False

        # localhost或127.0.0.1视为本地
        if self.host in ["localhost", "127.0.0.1"]:
            return True

        return False

    # ==================== 初始化相关 ====================

    def initialize(self, login: Optional[int] = None, password: Optional[str] = None,
                   server: Optional[str] = None) -> bool:
        """
        初始化MT5连接

        如果构造函数已提供login/password/server，会优先使用构造参数
        """
        # 合并参数（构造函数参数优先）
        _login = login or self.login
        _password = password or self.password
        _server = server or self.server

        if self._is_local:
            return self._initialize_local(_login, _password, _server)
        else:
            return self._initialize_remote(_login, _password, _server)

    def _initialize_local(self, login: Optional[int], password: Optional[str],
                          server: Optional[str]) -> bool:
        """本地模式初始化"""
        init_kwargs = {}
        if login and password and server:
            init_kwargs['login'] = login
            init_kwargs['password'] = password
            init_kwargs['server'] = server

        result = self._mt5.initialize(**init_kwargs)
        if result:
            logger.info(f"✅ MT5本地初始化成功")
        else:
            logger.error(f"❌ MT5本地初始化失败: {self._mt5.last_error()}")
        return result

    def _initialize_remote(self, login: Optional[int], password: Optional[str],
                           server: Optional[str]) -> bool:
        """远程模式初始化"""
        try:
            # 健康检查
            resp = requests.get(
                f"{self.base_url}/health",
                headers=self._headers,
                timeout=self.timeout
            )
            resp.raise_for_status()

            # 如果提供了登录信息，执行登录
            if login and password and server:
                login_resp = requests.post(
                    f"{self.base_url}/login",
                    json={
                        "login": login,
                        "password": password,
                        "server": server
                    },
                    headers=self._headers,
                    timeout=self.timeout
                )
                login_resp.raise_for_status()
                data = login_resp.json()
                if not data.get("success"):
                    logger.error(f"❌ MT5远程登录失败: {data.get('error')}")
                    return False

            logger.info(f"✅ MT5远程连接成功 ({self.host}:{self.port})")
            return True

        except Exception as e:
            logger.error(f"❌ MT5远程初始化失败: {str(e)}")
            return False

    def shutdown(self) -> None:
        """关闭连接"""
        if self._is_local:
            self._mt5.shutdown()
            logger.info("MT5本地连接已关闭")
        else:
            logger.info("MT5远程连接无需关闭")

    def login(self, login: int, password: str, server: str) -> bool:
        """登录账户"""
        if self._is_local:
            return self._mt5.login(login, password=password, server=server)
        else:
            try:
                resp = requests.post(
                    f"{self.base_url}/login",
                    json={"login": login, "password": password, "server": server},
                    headers=self._headers,
                    timeout=self.timeout
                )
                resp.raise_for_status()
                return resp.json().get("success", False)
            except Exception as e:
                logger.error(f"远程登录失败: {str(e)}")
                return False

    # ==================== 数据查询 ====================

    def account_info(self) -> Optional[AccountInfo]:
        """获取账户信息"""
        if self._is_local:
            return self._account_info_local()
        else:
            return self._account_info_remote()

    def _account_info_local(self) -> Optional[AccountInfo]:
        """本地获取账户信息"""
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

    def _account_info_remote(self) -> Optional[AccountInfo]:
        """远程获取账户信息"""
        try:
            resp = requests.get(
                f"{self.base_url}/account",
                headers=self._headers,
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()

            return AccountInfo(**data)
        except Exception as e:
            logger.error(f"远程获取账户信息失败: {str(e)}")
            return None

    def symbol_info_tick(self, symbol: str) -> Optional[TickInfo]:
        """获取实时报价"""
        if self._is_local:
            return self._symbol_info_tick_local(symbol)
        else:
            return self._symbol_info_tick_remote(symbol)

    def _symbol_info_tick_local(self, symbol: str) -> Optional[TickInfo]:
        """本地获取报价"""
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

    def _symbol_info_tick_remote(self, symbol: str) -> Optional[TickInfo]:
        """远程获取报价"""
        try:
            resp = requests.get(
                f"{self.base_url}/tick/{symbol}",
                headers=self._headers,
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()

            return TickInfo(
                symbol=symbol,
                time=datetime.fromisoformat(data["time"]),
                bid=data["bid"],
                ask=data["ask"],
                last=data["last"],
                volume=data["volume"]
            )
        except Exception as e:
            logger.error(f"远程获取报价失败: {str(e)}")
            return None

    def get_bars(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """
        获取K线数据（核心方法）

        这是Validator和Execution最常用的接口
        """
        if self._is_local:
            return self._get_bars_local(symbol, timeframe, count)
        else:
            return self._get_bars_remote(symbol, timeframe, count)

    def _get_bars_local(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """本地获取K线"""
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

        rates = self._mt5.copy_rates_from_pos(symbol, tf_map[timeframe], 0, count)

        if rates is None or len(rates) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def _get_bars_remote(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """远程获取K线"""
        try:
            resp = requests.get(
                f"{self.base_url}/bars/{symbol}",
                params={"timeframe": timeframe, "count": count},
                headers=self._headers,
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()

            # 转换为DataFrame
            bars = data["bars"]
            if not bars:
                return pd.DataFrame()

            df = pd.DataFrame(bars)
            df['time'] = pd.to_datetime(df['time'])
            return df

        except Exception as e:
            logger.error(f"远程获取K线失败: {str(e)}")
            return pd.DataFrame()

    # ==================== 交易相关 ====================

    def order_send(self, request: OrderRequest) -> OrderResult:
        """发送订单"""
        if self._is_local:
            return self._order_send_local(request)
        else:
            return self._order_send_remote(request)

    def _order_send_local(self, request: OrderRequest) -> OrderResult:
        """本地下单"""
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

        price = tick.ask if request.action == 'buy' else tick.bid
        order_type = self._mt5.ORDER_TYPE_BUY if request.action == 'buy' else self._mt5.ORDER_TYPE_SELL

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

        result = self._mt5.order_send(mt5_request)

        return OrderResult(
            success=(result.retcode == self._mt5.TRADE_RETCODE_DONE),
            order_id=result.order if hasattr(result, 'order') else None,
            ticket=result.order if hasattr(result, 'order') else None,
            price=result.price if hasattr(result, 'price') else None,
            volume=result.volume if hasattr(result, 'volume') else None,
            comment=result.comment if hasattr(result, 'comment') else ""
        )

    def _order_send_remote(self, request: OrderRequest) -> OrderResult:
        """远程下单"""
        try:
            resp = requests.post(
                f"{self.base_url}/order",
                json={
                    "action": request.action,
                    "symbol": request.symbol,
                    "volume": request.volume,
                    "sl": request.sl,
                    "tp": request.tp,
                    "deviation": request.deviation,
                    "magic": request.magic,
                    "comment": request.comment
                },
                headers=self._headers,
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()

            return OrderResult(
                success=data.get("success", False),
                order_id=data.get("order_id"),
                ticket=data.get("ticket"),
                price=data.get("price"),
                volume=data.get("volume"),
                comment=data.get("comment", "")
            )
        except Exception as e:
            logger.error(f"远程下单失败: {str(e)}")
            return OrderResult(
                success=False,
                order_id=None,
                ticket=None,
                price=None,
                volume=None,
                comment=str(e)
            )

    def positions_get(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取持仓"""
        if self._is_local:
            return self._positions_get_local(symbol)
        else:
            return self._positions_get_remote(symbol)

    def _positions_get_local(self, symbol: Optional[str]) -> List[Dict[str, Any]]:
        """本地获取持仓"""
        if symbol:
            positions = self._mt5.positions_get(symbol=symbol)
        else:
            positions = self._mt5.positions_get()

        if positions is None:
            return []

        return [pos._asdict() for pos in positions]

    def _positions_get_remote(self, symbol: Optional[str]) -> List[Dict[str, Any]]:
        """远程获取持仓"""
        try:
            params = {"symbol": symbol} if symbol else {}
            resp = requests.get(
                f"{self.base_url}/positions",
                params=params,
                headers=self._headers,
                timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json().get("positions", [])
        except Exception as e:
            logger.error(f"远程获取持仓失败: {str(e)}")
            return []

    def last_error(self) -> tuple:
        """获取最后错误"""
        if self._is_local:
            return self._mt5.last_error()
        else:
            # 远程模式：错误已在logger中记录
            return (0, "Remote mode - check logs")
