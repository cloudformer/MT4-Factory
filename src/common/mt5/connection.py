"""MT5连接管理器"""
import platform
from typing import Optional
from .interface import MT5Interface
from .mock_client import MockMT5Client
from .real_client import RealMT5Client
from src.common.config.settings import settings


class MT5ConnectionManager:
    """MT5连接管理器 - 根据配置和平台自动选择实现"""

    _instance: Optional['MT5ConnectionManager'] = None
    _client: Optional[MT5Interface] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化连接管理器"""
        if self._client is None:
            self._client = self._create_client()

    def _create_client(self) -> MT5Interface:
        """
        创建MT5客户端

        根据平台和配置自动选择：
        - Windows: 使用真实MT5客户端
        - macOS/Linux: 使用Mock客户端（开发测试）
        """
        system = platform.system()

        # 获取MT5配置
        mt5_config = settings.get("mt5", {})

        if system == "Windows":
            print("🔌 使用真实MT5客户端 (Windows)")
            # 真实MT5客户端
            client = RealMT5Client(
                path=mt5_config.get("path"),
                timeout=mt5_config.get("timeout", 60000),
                portable=mt5_config.get("portable", False)
            )
        else:
            print(f"🔌 使用Mock MT5客户端 ({system} - 开发模式)")
            # Mock客户端用于开发
            client = MockMT5Client()

        return client

    def get_client(self) -> MT5Interface:
        """获取MT5客户端实例"""
        return self._client

    def connect(self, use_investor: bool = False) -> bool:
        """
        连接到MT5

        Args:
            use_investor: 是否使用投资者密码（只读模式）

        Returns:
            是否连接成功
        """
        mt5_config = settings.get("mt5", {})

        login = mt5_config.get("login")
        server = mt5_config.get("server")

        # 选择密码类型
        if use_investor:
            password = mt5_config.get("investor_password")
            mode = "投资者模式（只读）"
        else:
            password = mt5_config.get("password")
            mode = "交易模式"

        if not all([login, password, server]):
            raise ValueError("MT5配置不完整，请检查配置文件中的 login, password, server")

        print(f"📡 连接MT5 [{mode}]: {login}@{server}")

        # 初始化并登录
        success = self._client.initialize(
            login=login,
            password=password,
            server=server
        )

        if success:
            print(f"✅ MT5连接成功 [{mode}]")
            account_info = self._client.account_info()
            if account_info:
                print(f"   账户余额: {account_info.balance} {account_info.currency}")
                print(f"   杠杆: 1:{account_info.leverage}")
                print(f"   交易权限: {'是' if account_info.trade_allowed else '否'}")
        else:
            error = self._client.last_error()
            print(f"❌ MT5连接失败: {error}")

        return success

    def disconnect(self):
        """断开MT5连接"""
        if self._client:
            self._client.shutdown()
            print("📡 MT5连接已关闭")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        if not self._client:
            return False
        account = self._client.account_info()
        return account is not None


# 全局单例
mt5_manager = MT5ConnectionManager()
