"""
Mock数据生成器 - Mac环境使用

用于在Mac环境下生成假数据，用于UI开发和测试
所有服务在Mac环境下都返回这些Mock数据
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import random


class MockDataGenerator:
    """Mock数据生成器"""

    @staticmethod
    def get_mt5_worker_status(worker_id: str, config: Dict) -> Dict[str, Any]:
        """获取MT5 Worker状态（Mock）"""
        worker_config = config.get("mt5_hosts", {}).get(worker_id, {})

        mock_status = worker_config.get("mock_status", "unknown")

        if mock_status == "connected":
            return {
                "worker_id": worker_id,
                "name": worker_config.get("name", worker_id),
                "status": "connected",
                "healthy": True,
                "host": worker_config.get("host", "unknown"),
                "port": worker_config.get("port", 9090),
                "account": {
                    "login": worker_config.get("login", 0),
                    "server": worker_config.get("server", "Unknown"),
                    "balance": worker_config.get("mock_balance", 0.0),
                    "equity": worker_config.get("mock_equity", 0.0),
                    "margin": worker_config.get("mock_balance", 0.0) * 0.3,
                    "margin_free": worker_config.get("mock_balance", 0.0) * 0.7,
                },
                "positions": MockDataGenerator._generate_mock_positions(
                    worker_config.get("mock_positions", 0)
                ),
                "tags": worker_config.get("tags", []),
                "weight": worker_config.get("weight", 1),
                "last_update": datetime.now().isoformat(),
            }
        elif mock_status == "disconnected":
            return {
                "worker_id": worker_id,
                "name": worker_config.get("name", worker_id),
                "status": "disconnected",
                "healthy": False,
                "host": worker_config.get("host", "unknown"),
                "port": worker_config.get("port", 9090),
                "error": worker_config.get("mock_error", "Connection failed"),
                "tags": worker_config.get("tags", []),
                "last_update": datetime.now().isoformat(),
            }
        else:  # disabled
            return {
                "worker_id": worker_id,
                "name": worker_config.get("name", worker_id),
                "status": "disabled",
                "healthy": False,
                "host": worker_config.get("host", "unknown"),
                "port": worker_config.get("port", 9090),
                "tags": worker_config.get("tags", []),
                "last_update": None,
            }

    @staticmethod
    def _generate_mock_positions(count: int) -> List[Dict[str, Any]]:
        """生成Mock持仓"""
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
        positions = []

        for i in range(count):
            symbol = random.choice(symbols)
            ticket = 10000000 + i
            direction = random.choice(["buy", "sell"])
            volume = round(random.uniform(0.01, 0.5), 2)
            price_open = round(random.uniform(1.0, 1.5), 5)
            profit = round(random.uniform(-50, 150), 2)

            positions.append({
                "ticket": ticket,
                "symbol": symbol,
                "type": direction,
                "volume": volume,
                "price_open": price_open,
                "price_current": round(price_open + profit * 0.0001, 5),
                "sl": round(price_open - 0.001, 5) if direction == "buy" else round(price_open + 0.001, 5),
                "tp": round(price_open + 0.002, 5) if direction == "buy" else round(price_open - 0.002, 5),
                "profit": profit,
                "swap": round(random.uniform(-2, 2), 2),
                "open_time": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat(),
            })

        return positions

    @staticmethod
    def get_validator_status(config: Dict) -> Dict[str, Any]:
        """获取Validator状态（Mock）"""
        validator_config = config.get("validator", {})
        data_sources = validator_config.get("data_sources", {})

        # Synthetic数据源
        synthetic = data_sources.get("synthetic", {})
        synthetic_status = {
            "enabled": synthetic.get("enabled", False),
            "status": synthetic.get("mock_status", "ready"),
            "weight": synthetic.get("weight", 0.2),
            "generated": synthetic.get("mock_generated", 0),
            "last_update": synthetic.get("mock_last_update", datetime.now().isoformat()),
        }

        # Historical数据源
        historical = data_sources.get("historical", {})
        historical_status = {
            "enabled": historical.get("enabled", False),
            "status": historical.get("mock_status", "ready"),
            "weight": historical.get("weight", 0.6),
            "progress": historical.get("mock_progress", 1.0),
            "symbols": historical.get("mock_symbols", 0),
            "timeframes": historical.get("mock_timeframes", []),
            "date_range": historical.get("mock_date_range", {}),
            "total_bars": historical.get("mock_total_bars", 0),
            "loaded_bars": historical.get("mock_loaded_bars", 0),
        }

        # Realtime数据源
        realtime = data_sources.get("realtime", {})
        mt5_host = realtime.get("mt5_host", "demo_worker_1")
        realtime_status = {
            "enabled": realtime.get("enabled", False),
            "status": realtime.get("mock_status", "connected"),
            "weight": realtime.get("weight", 0.2),
            "mt5_host": mt5_host,
            "last_tick": realtime.get("mock_last_tick", datetime.now().isoformat()),
            "symbols_available": realtime.get("mock_symbols_available", []),
        }

        return {
            "enabled": validator_config.get("enabled", False),
            "concurrency": validator_config.get("concurrency", 20),
            "data_sources": {
                "synthetic": synthetic_status,
                "historical": historical_status,
                "realtime": realtime_status,
            },
            "last_run": (datetime.now() - timedelta(minutes=15)).isoformat(),
            "next_run": (datetime.now() + timedelta(minutes=45)).isoformat(),
        }

    @staticmethod
    def get_execution_status(config: Dict) -> Dict[str, Any]:
        """获取Execution状态（Mock）"""
        execution_config = config.get("execution", {})
        mock_data = execution_config.get("mock_data", {})

        return {
            "enabled": execution_config.get("enabled", False),
            "total_positions": mock_data.get("total_positions", 0),
            "today_orders": mock_data.get("today_orders", 0),
            "today_pnl": mock_data.get("today_pnl", 0.0),
            "risk_limits": execution_config.get("risk_limits", {}),
            "last_update": datetime.now().isoformat(),
        }

    @staticmethod
    def get_orchestrator_status(config: Dict) -> Dict[str, Any]:
        """获取Orchestrator状态（Mock）"""
        orchestrator_config = config.get("orchestrator", {})
        mock_data = orchestrator_config.get("mock_data", {})

        return {
            "enabled": orchestrator_config.get("enabled", False),
            "active_strategies": mock_data.get("active_strategies", 0),
            "total_signals_today": mock_data.get("total_signals_today", 0),
            "pending_signals": mock_data.get("pending_signals", 0),
            "last_update": datetime.now().isoformat(),
        }

    @staticmethod
    def get_strategy_status(config: Dict) -> Dict[str, Any]:
        """获取Strategy状态（Mock）"""
        strategy_config = config.get("strategy_generation", {})
        mock_data = strategy_config.get("mock_data", {})

        return {
            "enabled": strategy_config.get("enabled", False),
            "total_generated": mock_data.get("total_generated", 0),
            "today_generated": mock_data.get("today_generated", 0),
            "success_rate": mock_data.get("success_rate", 0.0),
            "llm_provider": strategy_config.get("llm", {}).get("provider", "unknown"),
            "llm_model": strategy_config.get("llm", {}).get("model", "unknown"),
            "last_update": datetime.now().isoformat(),
        }

    @staticmethod
    def get_mock_strategies() -> List[Dict[str, Any]]:
        """获取Mock策略列表"""
        strategies = []
        statuses = ["ACTIVE", "ACTIVE", "ACTIVE", "CANDIDATE", "ARCHIVED"]

        for i in range(1, 16):
            status = random.choice(statuses)
            symbol = random.choice(["EURUSD", "GBPUSD", "USDJPY"])
            timeframe = random.choice(["M15", "H1", "H4"])
            rec_score = round(random.uniform(60, 95), 2)
            total_return = round(random.uniform(-0.05, 0.25), 4)
            sharpe = round(random.uniform(0.3, 1.5), 2)
            drawdown = round(random.uniform(0.05, 0.20), 4)
            win_rate = round(random.uniform(0.30, 0.65), 2)
            profit_factor = round(random.uniform(1.0, 2.5), 2)

            # 策略代码示例
            code = f"""import pandas as pd
import numpy as np

def generate_signal(data: pd.DataFrame) -> dict:
    # {symbol} {timeframe} Strategy {i}
    sma_fast = data['close'].rolling(window=10).mean()
    sma_slow = data['close'].rolling(window=30).mean()

    if sma_fast.iloc[-1] > sma_slow.iloc[-1]:
        return {{"signal": "buy", "confidence": {round(random.uniform(0.6, 0.9), 2)}}}
    elif sma_fast.iloc[-1] < sma_slow.iloc[-1]:
        return {{"signal": "sell", "confidence": {round(random.uniform(0.6, 0.9), 2)}}}

    return {{"signal": "hold", "confidence": 0.5}}
"""

            # 推荐度Emoji
            if rec_score >= 80:
                emoji = "🌟"
            elif rec_score >= 70:
                emoji = "✨"
            elif rec_score >= 60:
                emoji = "⭐"
            else:
                emoji = "💫"

            # 推荐度详细信息
            recommendation_summary = {
                "recommendation_score": rec_score,
                "recommendation_emoji": emoji,
                "one_line_summary": f"这是一个基于{timeframe}时间框架的{symbol}趋势跟踪策略，适合中等风险偏好的交易者。",
                "suitable_for": "中等风险偏好的趋势交易者" if rec_score > 70 else "保守型交易者",
                "account_requirement": f"建议账户余额 ${'10,000' if rec_score > 80 else '5,000'}+ (风险控制：每笔交易不超过2%)",
                "key_strengths": f"夏普比率{sharpe}表现良好，胜率{win_rate*100:.0f}%在可接受范围内" if sharpe > 1.0 else f"风险控制良好，最大回撤仅{drawdown*100:.1f}%",
                "key_weaknesses": f"最大回撤{drawdown*100:.1f}%偏高，需注意资金管理" if drawdown > 0.15 else "胜率略低，可能存在连续亏损期",
                "key_warnings": "策略表现受市场环境影响较大，建议定期监控和调整" if rec_score < 75 else "无特殊提示"
            }

            strategies.append({
                "id": f"STR_{i:03d}",
                "name": f"Strategy {i}",
                "status": status,
                "symbol": symbol,
                "timeframe": timeframe,
                "recommendation_score": rec_score,
                "total_return": total_return,
                "sharpe_ratio": sharpe,
                "max_drawdown": drawdown,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "code": code,
                "performance": {
                    "backtested_symbol": symbol,
                    "sharpe_ratio": sharpe,
                    "win_rate": win_rate,
                    "total_return": total_return,
                    "max_drawdown": drawdown,
                    "profit_factor": profit_factor,
                    "total_trades": random.randint(50, 200),
                    "avg_win": round(random.uniform(20, 50), 2),
                    "avg_loss": round(random.uniform(-15, -30), 2),
                    "recommendation_summary": recommendation_summary
                },
                "params": {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "fast_period": 10,
                    "slow_period": 30
                },
                "created_at": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
                "updated_at": datetime.now().isoformat(),
            })

        return strategies

    @staticmethod
    def get_mock_signals() -> List[Dict[str, Any]]:
        """获取Mock信号列表"""
        signals = []

        for i in range(1, 11):
            signal_type = random.choice(["buy", "sell"])

            signals.append({
                "id": f"SIG_{i:05d}",
                "strategy_id": f"STR_{random.randint(1, 15):03d}",
                "symbol": random.choice(["EURUSD", "GBPUSD", "USDJPY"]),
                "direction": signal_type,
                "volume": round(random.uniform(0.01, 0.5), 2),
                "entry_price": round(random.uniform(1.0, 1.5), 5),
                "sl": round(random.uniform(0.9, 1.0), 5),
                "tp": round(random.uniform(1.5, 1.6), 5),
                "status": random.choice(["pending", "executed", "cancelled"]),
                "created_at": (datetime.now() - timedelta(hours=random.randint(0, 24))).isoformat(),
            })

        return signals

    @staticmethod
    def get_mock_trades() -> List[Dict[str, Any]]:
        """获取Mock交易列表"""
        trades = []

        for i in range(1, 21):
            trade_type = random.choice(["buy", "sell"])
            pnl = round(random.uniform(-50, 200), 2)

            trades.append({
                "id": f"TRD_{i:06d}",
                "ticket": 10000000 + i,
                "strategy_id": f"STR_{random.randint(1, 15):03d}",
                "signal_id": f"SIG_{random.randint(1, 10):05d}",
                "symbol": random.choice(["EURUSD", "GBPUSD", "USDJPY"]),
                "direction": trade_type,
                "volume": round(random.uniform(0.01, 0.5), 2),
                "open_price": round(random.uniform(1.0, 1.5), 5),
                "close_price": round(random.uniform(1.0, 1.5), 5),
                "sl": round(random.uniform(0.9, 1.0), 5),
                "tp": round(random.uniform(1.5, 1.6), 5),
                "profit": pnl,
                "swap": round(random.uniform(-2, 2), 2),
                "commission": round(random.uniform(-1, -0.1), 2),
                "open_time": (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat(),
                "close_time": (datetime.now() - timedelta(hours=random.randint(0, 48))).isoformat(),
                "status": "closed",
            })

        return trades


# ==================== 便捷函数 ====================

def is_mock_mode(config: Dict = None) -> bool:
    """检查是否为Mock模式"""
    if config is None:
        from src.common.config.settings import settings
        config = settings

    return config.get("dev_tools", {}).get("mock_mt5", False)


def get_mock_data_generator() -> MockDataGenerator:
    """获取Mock数据生成器实例"""
    return MockDataGenerator()
