"""配置管理"""
import yaml
import os
from pathlib import Path
from typing import Dict, Any


class Settings:
    """全局配置管理"""

    def __init__(self, env: str = None):
        # 优先从环境变量DEVICE读取，如果没有则使用传入参数，最后默认windows
        self.env = env or os.getenv('DEVICE', 'windows')
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = Path(__file__).parent.parent.parent.parent / "config" / f"{self.env}.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @property
    def database(self) -> Dict[str, Any]:
        """数据库配置"""
        return self._config.get('database', {})

    @property
    def services(self) -> Dict[str, Any]:
        """服务配置"""
        return self._config.get('services', {})

    @property
    def mt5(self) -> Dict[str, Any]:
        """MT5配置"""
        return self._config.get('mt5', {})

    @property
    def logging(self) -> Dict[str, Any]:
        """日志配置"""
        return self._config.get('logging', {})

    def get(self, key: str, default=None):
        """获取配置项"""
        return self._config.get(key, default)


# 全局配置实例
settings = Settings()
