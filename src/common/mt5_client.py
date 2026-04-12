"""
MT5 Client - HTTP客户端库
用于Execution/Orchestrator/Validator等服务连接Windows MT5 API Bridge

用法:
    from src.common.mt5_client import MT5Client

    # 从配置创建客户端
    client = MT5Client.from_config("demo_1")  # 读取config中的mt5_hosts.demo_1

    # 自动登录MT5
    client.login()

    # 获取数据
    account = client.get_account()
    bars = client.get_bars("EURUSD", "H1", 100)
"""

import requests
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MT5ClientError(Exception):
    """MT5客户端异常"""
    pass


class MT5Client:
    """MT5 HTTP客户端"""

    def __init__(
        self,
        host: str,
        port: int,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 10,
        auto_login: bool = True
    ):
        """
        初始化MT5客户端

        Args:
            host: API Bridge地址 (localhost / 52.10.20.30)
            port: API Bridge端口 (9090)
            login: MT5账号（用于自动登录）
            password: MT5密码
            server: MT5服务器
            api_key: API Bridge认证密钥
            timeout: 请求超时（秒）
            auto_login: 是否在初始化时自动登录
        """
        self.base_url = f"http://{host}:{port}"
        self.login_info = {
            "login": login,
            "password": password,
            "server": server
        }
        self.api_key = api_key
        self.timeout = timeout
        self._logged_in = False

        logger.info(f"MT5Client初始化: {self.base_url}")

        # 自动登录
        if auto_login and login and password and server:
            try:
                self.login()
            except Exception as e:
                logger.warning(f"自动登录失败: {e}")

    @classmethod
    def from_config(cls, mt5_host_key: str, config: Optional[Dict] = None, auto_login: bool = True):
        """
        从配置文件创建客户端

        Args:
            mt5_host_key: mt5_hosts中的key (如 "demo_1")
            config: 配置字典（如果None，从settings读取）
            auto_login: 是否自动登录

        Returns:
            MT5Client实例

        Example:
            # 读取config/windows.yaml中的mt5_hosts.demo_1
            client = MT5Client.from_config("demo_1")
        """
        if config is None:
            from src.common.config.settings import settings
            config = settings

        # 读取mt5_hosts配置
        mt5_hosts = config.get("mt5_hosts", {})
        if mt5_host_key not in mt5_hosts:
            raise MT5ClientError(f"配置中未找到mt5_host: {mt5_host_key}")

        host_config = mt5_hosts[mt5_host_key]

        # 检查是否启用
        if not host_config.get("enabled", True):
            raise MT5ClientError(f"MT5主机 {mt5_host_key} 未启用")

        return cls(
            host=host_config["host"],
            port=host_config["port"],
            login=host_config.get("login"),
            password=host_config.get("password"),
            server=host_config.get("server"),
            api_key=host_config.get("api_key"),
            timeout=host_config.get("timeout", 10),
            auto_login=auto_login
        )

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        发送HTTP请求

        Args:
            method: HTTP方法 (GET/POST)
            endpoint: API端点 (/health, /account等)
            **kwargs: requests参数

        Returns:
            响应JSON数据

        Raises:
            MT5ClientError: 请求失败
        """
        url = f"{self.base_url}{endpoint}"

        # 添加API密钥
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # 设置超时
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"MT5 API请求失败: {method} {url} - {e}")
            raise MT5ClientError(f"MT5 API请求失败: {e}")

    def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            {"status": "healthy", "mt5_connected": true, ...}
        """
        return self._request("GET", "/health")

    def login(self) -> bool:
        """
        登录MT5账户

        使用初始化时提供的login/password/server信息

        Returns:
            True: 登录成功
            False: 登录失败

        Raises:
            MT5ClientError: 缺少登录信息或请求失败
        """
        if not all([self.login_info["login"], self.login_info["password"], self.login_info["server"]]):
            raise MT5ClientError("缺少登录信息: login, password, server")

        logger.info(f"登录MT5: {self.login_info['login']}@{self.login_info['server']}")

        result = self._request("POST", "/login", json=self.login_info)

        if result.get("success"):
            self._logged_in = True
            logger.info(f"✓ MT5登录成功: {self.login_info['login']}")
            return True
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"✗ MT5登录失败: {error}")
            raise MT5ClientError(f"MT5登录失败: {error}")

    def get_account(self) -> Dict[str, Any]:
        """
        获取账户信息

        Returns:
            {
                "login": 5049130509,
                "server": "MetaQuotes-Demo",
                "balance": 100000.0,
                "equity": 100000.0,
                ...
            }
        """
        return self._request("GET", "/account")

    def get_tick(self, symbol: str) -> Dict[str, Any]:
        """
        获取实时报价

        Args:
            symbol: 交易品种 (EURUSD, GBPUSD等)

        Returns:
            {"bid": 1.08456, "ask": 1.08458, "time": "2024-04-11 10:00:00", ...}
        """
        return self._request("GET", f"/tick/{symbol}")

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        count: int = 100,
        start_pos: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取K线数据

        Args:
            symbol: 交易品种
            timeframe: 时间周期 (M1, M5, M15, M30, H1, H4, D1, W1, MN1)
            count: 获取数量
            start_pos: 起始位置（0=最新）

        Returns:
            [
                {
                    "time": "2024-04-11 10:00:00",
                    "open": 1.08456,
                    "high": 1.08523,
                    "low": 1.08412,
                    "close": 1.08489,
                    "volume": 1234
                },
                ...
            ]
        """
        params = {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": count,
            "start_pos": start_pos
        }
        return self._request("GET", "/bars", params=params)

    def place_order(
        self,
        symbol: str,
        action: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        deviation: int = 20,
        magic: int = 234000,
        comment: str = ""
    ) -> Dict[str, Any]:
        """
        下单

        Args:
            symbol: 交易品种
            action: "buy" 或 "sell"
            volume: 手数
            sl: 止损价
            tp: 止盈价
            deviation: 滑点
            magic: 魔术数字
            comment: 订单备注

        Returns:
            {
                "success": true,
                "order": 12345678,
                "volume": 0.1,
                "price": 1.08456,
                ...
            }
        """
        order_data = {
            "symbol": symbol,
            "action": action,
            "volume": volume,
            "sl": sl,
            "tp": tp,
            "deviation": deviation,
            "magic": magic,
            "comment": comment
        }
        return self._request("POST", "/order", json=order_data)

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取持仓

        Args:
            symbol: 交易品种（None=获取所有）

        Returns:
            [
                {
                    "ticket": 12345678,
                    "symbol": "EURUSD",
                    "type": "buy",
                    "volume": 0.1,
                    "price_open": 1.08456,
                    "sl": 1.08356,
                    "tp": 1.08656,
                    "profit": 12.34,
                    ...
                },
                ...
            ]
        """
        params = {"symbol": symbol} if symbol else {}
        return self._request("GET", "/positions", params=params)

    def close_position(self, ticket: int) -> Dict[str, Any]:
        """
        平仓

        Args:
            ticket: 持仓票据号

        Returns:
            {"success": true, "ticket": 12345678, ...}
        """
        return self._request("POST", f"/position/{ticket}/close")

    def __repr__(self):
        return f"<MT5Client {self.base_url} login={self.login_info['login']} logged_in={self._logged_in}>"


# ==================== 便捷函数 ====================

def create_mt5_client(mt5_host_key: str = "demo_1", auto_login: bool = True) -> MT5Client:
    """
    创建MT5客户端（从配置）

    Args:
        mt5_host_key: mt5_hosts中的key
        auto_login: 是否自动登录

    Returns:
        MT5Client实例

    Example:
        client = create_mt5_client("demo_1")
        account = client.get_account()
    """
    return MT5Client.from_config(mt5_host_key, auto_login=auto_login)
