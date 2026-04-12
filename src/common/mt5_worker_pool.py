"""
MT5 Worker Pool - 多Windows机器管理

用于Cloud生产环境，管理多个Windows MT5工作节点
支持负载均衡、标签路由、健康检查、故障转移

用法:
    from src.common.mt5_worker_pool import MT5WorkerPool

    # 创建Worker池（自动从config读取）
    pool = MT5WorkerPool.from_config()

    # 选择最优Worker下单
    result = pool.place_order(
        symbol="EURUSD",
        action="buy",
        volume=0.1,
        tags=["real", "eurusd"]  # 按标签路由
    )

    # 查询所有Worker的持仓
    all_positions = pool.get_all_positions()
"""

import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .mt5_client import MT5Client, MT5ClientError

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(str, Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"


@dataclass
class MT5Worker:
    """MT5工作节点"""
    worker_id: str
    client: MT5Client
    tags: List[str]
    weight: int = 1
    enabled: bool = True
    max_positions: int = 100

    # 运行时状态
    current_positions: int = 0
    last_health_check: Optional[datetime] = None
    is_healthy: bool = True
    error_count: int = 0


class RoutingRule:
    """路由规则"""

    def __init__(self, name: str, condition: Dict[str, Any], target: Dict[str, Any]):
        """
        Args:
            name: 规则名称
            condition: 匹配条件 {"symbol": "EURUSD", "strategy_type": "scalping"}
            target: 目标选择 {"tags": ["eurusd", "scalping"], "worker_ids": ["worker_1"]}
        """
        self.name = name
        self.condition = condition
        self.target = target

    def matches(self, request: Dict[str, Any]) -> bool:
        """检查请求是否匹配此规则"""
        for key, value in self.condition.items():
            if request.get(key) != value:
                return False
        return True


class MT5WorkerPool:
    """MT5 Worker池管理器"""

    def __init__(
        self,
        workers: List[MT5Worker],
        routing_rules: Optional[List[RoutingRule]] = None,
        load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
        health_check_interval: int = 60
    ):
        """
        初始化Worker池

        Args:
            workers: Worker列表
            routing_rules: 路由规则
            load_balancing_strategy: 负载均衡策略
            health_check_interval: 健康检查间隔（秒）
        """
        self.workers: Dict[str, MT5Worker] = {w.worker_id: w for w in workers}
        self.routing_rules = routing_rules or []
        self.load_balancing_strategy = load_balancing_strategy
        self.health_check_interval = health_check_interval

        self._round_robin_index = 0

        logger.info(f"Worker Pool初始化: {len(self.workers)}个Worker")
        for worker_id, worker in self.workers.items():
            logger.info(f"  - {worker_id}: tags={worker.tags}, weight={worker.weight}")

    @classmethod
    def from_config(cls, config: Optional[Dict] = None):
        """
        从配置创建Worker池

        Args:
            config: 配置字典（如果None，从settings读取）

        Returns:
            MT5WorkerPool实例

        Example:
            pool = MT5WorkerPool.from_config()
        """
        if config is None:
            from src.common.config.settings import settings
            config = settings

        # 读取worker_pool配置
        pool_config = config.get("worker_pool", {})
        if not pool_config.get("enabled", False):
            raise ValueError("Worker Pool未启用，请检查config中的worker_pool.enabled")

        # 读取所有mt5_hosts，筛选enabled的作为workers
        mt5_hosts = config.get("mt5_hosts", {})
        workers = []

        for worker_id, host_config in mt5_hosts.items():
            if not host_config.get("enabled", False):
                continue

            # 创建MT5客户端
            client = MT5Client(
                host=host_config["host"],
                port=host_config["port"],
                login=host_config.get("login"),
                password=host_config.get("password"),
                server=host_config.get("server"),
                api_key=host_config.get("api_key"),
                timeout=host_config.get("timeout", 10),
                auto_login=host_config.get("auto_login", True)
            )

            # 创建Worker
            worker = MT5Worker(
                worker_id=worker_id,
                client=client,
                tags=host_config.get("tags", []),
                weight=host_config.get("weight", 1),
                enabled=True,
                max_positions=host_config.get("max_positions", 100)
            )
            workers.append(worker)

        if not workers:
            raise ValueError("没有可用的Worker，请检查config中的mt5_hosts")

        # 读取路由规则
        routing_rules = []
        for rule_config in pool_config.get("routing_rules", []):
            rule = RoutingRule(
                name=rule_config["name"],
                condition=rule_config["condition"],
                target=rule_config["target"]
            )
            routing_rules.append(rule)

        # 读取负载均衡策略
        lb_strategy_str = pool_config.get("load_balancing", {}).get("strategy", "weighted_round_robin")
        lb_strategy = LoadBalancingStrategy(lb_strategy_str)

        return cls(
            workers=workers,
            routing_rules=routing_rules,
            load_balancing_strategy=lb_strategy,
            health_check_interval=pool_config.get("health_check_interval", 60)
        )

    def select_worker(
        self,
        symbol: Optional[str] = None,
        strategy_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        worker_id: Optional[str] = None,
        **kwargs
    ) -> MT5Worker:
        """
        选择最优Worker

        选择流程：
        1. 如果指定worker_id，直接返回
        2. 应用路由规则过滤
        3. 按tags过滤
        4. 使用负载均衡策略选择

        Args:
            symbol: 交易品种
            strategy_type: 策略类型
            tags: 要求的标签
            worker_id: 指定Worker ID
            **kwargs: 其他路由参数

        Returns:
            选中的Worker

        Raises:
            ValueError: 没有可用Worker
        """
        # 1. 指定worker_id
        if worker_id:
            if worker_id not in self.workers:
                raise ValueError(f"Worker不存在: {worker_id}")
            worker = self.workers[worker_id]
            if not worker.enabled or not worker.is_healthy:
                raise ValueError(f"Worker不可用: {worker_id}")
            return worker

        # 2. 构建请求上下文
        request_context = {
            "symbol": symbol,
            "strategy_type": strategy_type,
            **kwargs
        }

        # 3. 应用路由规则
        candidates = list(self.workers.values())

        for rule in self.routing_rules:
            if rule.matches(request_context):
                logger.debug(f"匹配路由规则: {rule.name}")

                # 按规则目标过滤
                if "worker_ids" in rule.target:
                    worker_ids = rule.target["worker_ids"]
                    candidates = [w for w in candidates if w.worker_id in worker_ids]

                if "tags" in rule.target:
                    required_tags = rule.target["tags"]
                    candidates = [
                        w for w in candidates
                        if any(tag in w.tags for tag in required_tags)
                    ]

                break  # 只应用第一个匹配的规则

        # 4. 按tags过滤
        if tags:
            candidates = [
                w for w in candidates
                if any(tag in w.tags for tag in tags)
            ]

        # 5. 过滤enabled和healthy的Worker
        candidates = [
            w for w in candidates
            if w.enabled and w.is_healthy
        ]

        if not candidates:
            raise ValueError(f"没有可用Worker: symbol={symbol}, tags={tags}")

        # 6. 负载均衡选择
        worker = self._select_by_load_balancing(candidates)

        logger.info(f"选择Worker: {worker.worker_id} (strategy={self.load_balancing_strategy.value})")
        return worker

    def _select_by_load_balancing(self, candidates: List[MT5Worker]) -> MT5Worker:
        """使用负载均衡策略选择Worker"""
        if self.load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            # 轮询
            worker = candidates[self._round_robin_index % len(candidates)]
            self._round_robin_index += 1
            return worker

        elif self.load_balancing_strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            # 加权轮询
            total_weight = sum(w.weight for w in candidates)
            target = self._round_robin_index % total_weight
            current = 0
            for worker in candidates:
                current += worker.weight
                if current > target:
                    self._round_robin_index += 1
                    return worker
            return candidates[0]

        elif self.load_balancing_strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            # 最少连接（这里用持仓数代替）
            return min(candidates, key=lambda w: w.current_positions)

        else:  # RANDOM
            import random
            return random.choice(candidates)

    def place_order(
        self,
        symbol: str,
        action: str,
        volume: float,
        worker_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        下单（自动选择Worker）

        Args:
            symbol: 交易品种
            action: "buy" 或 "sell"
            volume: 手数
            worker_id: 指定Worker（可选）
            **kwargs: 其他下单参数（sl, tp等）+ 路由参数（tags, strategy_type等）

        Returns:
            {
                "success": true,
                "worker_id": "real_worker_icm_1",
                "order": 12345678,
                "price": 1.08456,
                ...
            }
        """
        # 提取路由参数
        routing_kwargs = {
            k: v for k, v in kwargs.items()
            if k in ["tags", "strategy_type"]
        }

        # 提取下单参数
        order_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in ["tags", "strategy_type"]
        }

        # 选择Worker
        worker = self.select_worker(
            symbol=symbol,
            worker_id=worker_id,
            **routing_kwargs
        )

        # 下单
        try:
            result = worker.client.place_order(
                symbol=symbol,
                action=action,
                volume=volume,
                **order_kwargs
            )

            # 更新状态
            worker.current_positions += 1
            worker.error_count = 0

            # 添加worker_id到结果
            result["worker_id"] = worker.worker_id

            logger.info(f"✓ 下单成功: worker={worker.worker_id}, order={result.get('order')}")
            return result

        except Exception as e:
            worker.error_count += 1
            logger.error(f"✗ 下单失败: worker={worker.worker_id}, error={e}")

            # 错误次数过多，标记为不健康
            if worker.error_count >= 3:
                worker.is_healthy = False
                logger.warning(f"Worker标记为不健康: {worker.worker_id}")

            raise

    def get_positions(self, worker_id: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取持仓

        Args:
            worker_id: 指定Worker（None=获取所有Worker）

        Returns:
            {
                "worker_1": [{...}, {...}],
                "worker_2": [{...}, {...}],
                ...
            }
        """
        if worker_id:
            worker = self.workers[worker_id]
            positions = worker.client.get_positions()
            return {worker_id: positions}

        # 获取所有Worker的持仓
        all_positions = {}
        for wid, worker in self.workers.items():
            if not worker.enabled:
                continue

            try:
                positions = worker.client.get_positions()
                all_positions[wid] = positions
                worker.current_positions = len(positions)
            except Exception as e:
                logger.error(f"获取持仓失败: worker={wid}, error={e}")
                all_positions[wid] = []

        return all_positions

    def get_all_positions(self) -> List[Dict[str, Any]]:
        """
        获取所有Worker的持仓（扁平化列表）

        Returns:
            [
                {"worker_id": "worker_1", "ticket": 123, "symbol": "EURUSD", ...},
                {"worker_id": "worker_2", "ticket": 456, "symbol": "GBPUSD", ...},
                ...
            ]
        """
        positions_by_worker = self.get_positions()

        all_positions = []
        for worker_id, positions in positions_by_worker.items():
            for pos in positions:
                pos["worker_id"] = worker_id
                all_positions.append(pos)

        return all_positions

    def close_position(self, ticket: int, worker_id: Optional[str] = None) -> Dict[str, Any]:
        """
        平仓

        Args:
            ticket: 持仓票据号
            worker_id: Worker ID（如果None，自动搜索）

        Returns:
            {"success": true, "worker_id": "worker_1", ...}
        """
        if worker_id:
            worker = self.workers[worker_id]
            result = worker.client.close_position(ticket)
            result["worker_id"] = worker_id
            worker.current_positions = max(0, worker.current_positions - 1)
            return result

        # 自动搜索ticket所在的Worker
        for wid, worker in self.workers.items():
            if not worker.enabled:
                continue

            try:
                result = worker.client.close_position(ticket)
                result["worker_id"] = wid
                worker.current_positions = max(0, worker.current_positions - 1)
                logger.info(f"✓ 平仓成功: worker={wid}, ticket={ticket}")
                return result
            except MT5ClientError:
                continue

        raise ValueError(f"未找到持仓: ticket={ticket}")

    def health_check(self) -> Dict[str, Dict[str, Any]]:
        """
        健康检查所有Worker

        Returns:
            {
                "worker_1": {"healthy": true, "positions": 10, "error": null},
                "worker_2": {"healthy": false, "positions": 0, "error": "Connection timeout"},
                ...
            }
        """
        results = {}

        for worker_id, worker in self.workers.items():
            try:
                health = worker.client.health_check()
                worker.is_healthy = health.get("status") == "healthy"
                worker.last_health_check = datetime.now()
                worker.error_count = 0

                results[worker_id] = {
                    "healthy": worker.is_healthy,
                    "positions": worker.current_positions,
                    "error": None
                }
            except Exception as e:
                worker.is_healthy = False
                worker.error_count += 1

                results[worker_id] = {
                    "healthy": False,
                    "positions": worker.current_positions,
                    "error": str(e)
                }

                logger.error(f"Worker健康检查失败: {worker_id} - {e}")

        return results

    def get_worker_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有Worker统计信息

        Returns:
            {
                "worker_1": {
                    "enabled": true,
                    "healthy": true,
                    "positions": 10,
                    "max_positions": 100,
                    "tags": ["real", "icmarkets"],
                    "weight": 2
                },
                ...
            }
        """
        stats = {}

        for worker_id, worker in self.workers.items():
            stats[worker_id] = {
                "enabled": worker.enabled,
                "healthy": worker.is_healthy,
                "positions": worker.current_positions,
                "max_positions": worker.max_positions,
                "tags": worker.tags,
                "weight": worker.weight,
                "error_count": worker.error_count,
                "last_health_check": worker.last_health_check.isoformat() if worker.last_health_check else None
            }

        return stats


# ==================== 便捷函数 ====================

def create_worker_pool() -> MT5WorkerPool:
    """
    创建Worker池（从配置）

    Returns:
        MT5WorkerPool实例

    Example:
        pool = create_worker_pool()
        result = pool.place_order("EURUSD", "buy", 0.1)
    """
    return MT5WorkerPool.from_config()
