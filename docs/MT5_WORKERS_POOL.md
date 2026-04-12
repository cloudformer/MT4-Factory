# MT5 Workers Pool - 多Windows交易池

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│ Execution服务（分发中心）                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  WorkerPool管理器                                           │
│  ├─ 策略A → Worker 1 (EURUSD专用)                          │
│  ├─ 策略B → Worker 2 (GBPUSD专用)                          │
│  ├─ 策略C → Worker 3 (高频交易)                             │
│  ├─ 策略D → Worker 4 (长线持仓)                             │
│  └─ 负载均衡 → 自动选择最优Worker                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                        ↓ 分发交易
┌─────────────────────────────────────────────────────────────┐
│ MT5 Workers Pool（多个Windows机器）                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Worker 1              Worker 2              Worker 3       │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐   │
│  │ Windows1 │         │ Windows2 │         │ Windows3 │   │
│  │ IP: .101 │         │ IP: .102 │         │ IP: .103 │   │
│  │ Port:9090│         │ Port:9090│         │ Port:9090│   │
│  │ MT5 Demo │         │ MT5 Demo │         │ MT5 Real │   │
│  │ Account1 │         │ Account2 │         │ Account1 │   │
│  └──────────┘         └──────────┘         └──────────┘   │
│                                                             │
│  Worker 4              Worker 5              Worker 6       │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐   │
│  │ Windows4 │         │ Windows5 │         │ Windows6 │   │
│  │ IP: .104 │         │ IP: .105 │         │ IP: .106 │   │
│  │ Port:9090│         │ Port:9090│         │ Port:9090│   │
│  │ MT5 Real │         │ MT5 Real │         │ MT5 Real │   │
│  │ Account2 │         │ Account3 │         │ Account4 │   │
│  └──────────┘         └──────────┘         └──────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 配置示例

### config/cloud.yaml

```yaml
# ==================== MT5 Workers Pool ====================
mt5_hosts:
  # ========== Demo Workers ==========
  demo_worker_1:
    enabled: true
    name: "Demo Worker 1 - EURUSD专用"
    host: "192.168.1.101"
    port: 9090
    login: 5049130509
    password: "${MT5_DEMO1_PASSWORD}"
    server: "MetaQuotes-Demo"
    api_key: "${MT5_DEMO1_API_KEY}"
    
    # Worker标签（用于路由）
    tags:
      - "demo"
      - "eurusd"
      - "scalping"
    
    # 性能配置
    max_concurrent_orders: 10
    priority: 1

  demo_worker_2:
    enabled: true
    name: "Demo Worker 2 - GBPUSD专用"
    host: "192.168.1.102"
    port: 9090
    login: 5049130510
    password: "${MT5_DEMO2_PASSWORD}"
    server: "MetaQuotes-Demo"
    api_key: "${MT5_DEMO2_API_KEY}"
    
    tags:
      - "demo"
      - "gbpusd"
      - "swing"
    
    max_concurrent_orders: 10
    priority: 1

  # ========== Real Workers ==========
  real_worker_icm_1:
    enabled: true
    name: "ICMarkets Real 1 - 主账户"
    host: "52.10.20.101"
    port: 9091
    login: 8012345678
    password: "${MT5_REAL_ICM1_PASSWORD}"
    server: "ICMarkets-Live"
    api_key: "${MT5_REAL_ICM1_API_KEY}"
    
    tags:
      - "real"
      - "icmarkets"
      - "primary"
      - "major_pairs"
    
    max_concurrent_orders: 20
    priority: 10
    
    # 风控配置
    risk_limits:
      max_order_size: 1.0
      max_daily_loss: 5000
      max_positions: 10

  real_worker_icm_2:
    enabled: true
    name: "ICMarkets Real 2 - 备用账户"
    host: "52.10.20.102"
    port: 9091
    login: 8012345679
    password: "${MT5_REAL_ICM2_PASSWORD}"
    server: "ICMarkets-Live"
    api_key: "${MT5_REAL_ICM2_API_KEY}"
    
    tags:
      - "real"
      - "icmarkets"
      - "backup"
      - "major_pairs"
    
    max_concurrent_orders: 20
    priority: 5

  real_worker_pep_1:
    enabled: true
    name: "Pepperstone Real 1"
    host: "52.10.20.103"
    port: 9091
    login: 9012345678
    password: "${MT5_REAL_PEP1_PASSWORD}"
    server: "Pepperstone-Live"
    api_key: "${MT5_REAL_PEP1_API_KEY}"
    
    tags:
      - "real"
      - "pepperstone"
      - "exotic_pairs"
    
    max_concurrent_orders: 15
    priority: 8

  real_worker_hft:
    enabled: true
    name: "高频交易专用"
    host: "52.10.20.104"
    port: 9091
    login: 9012345679
    password: "${MT5_REAL_HFT_PASSWORD}"
    server: "ICMarkets-Live"
    api_key: "${MT5_REAL_HFT_API_KEY}"
    
    tags:
      - "real"
      - "hft"
      - "low_latency"
    
    max_concurrent_orders: 50
    priority: 15

# ==================== Worker Pool配置 ====================
worker_pool:
  # 启用Worker Pool管理
  enabled: true
  
  # 负载均衡策略
  load_balancing:
    strategy: "weighted_round_robin"  # round_robin / weighted / least_connections / tag_based
    
  # 健康检查
  health_check:
    interval: 30                      # 秒
    timeout: 5
    retry: 3
  
  # 故障转移
  failover:
    enabled: true
    retry_count: 3
    retry_delay: 2                    # 秒
  
  # 路由规则
  routing_rules:
    # 规则1: 按品种路由
    - name: "EURUSD专用Worker"
      condition:
        symbol: "EURUSD"
      target:
        tags: ["eurusd"]
    
    # 规则2: 按策略类型路由
    - name: "高频策略路由"
      condition:
        strategy_type: "scalping"
      target:
        tags: ["hft", "low_latency"]
    
    # 规则3: 按经纪商路由
    - name: "ICMarkets优先"
      condition:
        broker: "icmarkets"
      target:
        tags: ["icmarkets"]
        priority: "high"
    
    # 规则4: 按账户类型路由
    - name: "Demo测试路由"
      condition:
        account_type: "demo"
      target:
        tags: ["demo"]
    
    # 默认规则: 负载均衡
    - name: "默认负载均衡"
      condition: {}
      target:
        strategy: "least_connections"

# ==================== Execution配置 ====================
execution:
  enabled: true
  
  # 使用Worker Pool
  use_worker_pool: true
  
  # 默认Worker（如果Pool不可用）
  default_mt5_host: "real_worker_icm_1"
```

---

## 代码实现

### Worker Pool管理器

```python
# src/common/mt5_worker_pool.py

from typing import List, Dict, Optional, Any
from src.common.mt5_client import MT5Client
from src.common.config.settings import settings
import random
import logging

logger = logging.getLogger(__name__)


class MT5Worker:
    """单个MT5 Worker"""
    
    def __init__(self, worker_id: str, config: Dict):
        self.worker_id = worker_id
        self.config = config
        self.client: Optional[MT5Client] = None
        self.is_healthy = False
        self.active_orders = 0
        self.priority = config.get("priority", 1)
        self.tags = config.get("tags", [])
        self.max_concurrent_orders = config.get("max_concurrent_orders", 10)
    
    def connect(self):
        """连接Worker"""
        try:
            self.client = MT5Client.from_config(self.worker_id, auto_login=True)
            self.is_healthy = True
            logger.info(f"✓ Worker已连接: {self.worker_id}")
        except Exception as e:
            self.is_healthy = False
            logger.error(f"✗ Worker连接失败: {self.worker_id} - {e}")
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            self.client.health_check()
            self.is_healthy = True
            return True
        except:
            self.is_healthy = False
            return False
    
    def can_accept_order(self) -> bool:
        """是否可以接受新订单"""
        return (
            self.is_healthy and 
            self.active_orders < self.max_concurrent_orders
        )
    
    def place_order(self, **kwargs) -> Dict:
        """下单"""
        if not self.can_accept_order():
            raise Exception(f"Worker {self.worker_id} 无法接受新订单")
        
        try:
            self.active_orders += 1
            result = self.client.place_order(**kwargs)
            return result
        finally:
            self.active_orders -= 1


class MT5WorkerPool:
    """MT5 Worker Pool管理器"""
    
    def __init__(self):
        self.workers: Dict[str, MT5Worker] = {}
        self.load_balancing_strategy = "weighted_round_robin"
        self.current_worker_index = 0
        
        # 从配置加载Workers
        self._load_workers()
    
    def _load_workers(self):
        """从配置加载所有Workers"""
        mt5_hosts = settings.get("mt5_hosts", {})
        
        for worker_id, config in mt5_hosts.items():
            if not config.get("enabled", True):
                continue
            
            worker = MT5Worker(worker_id, config)
            worker.connect()
            self.workers[worker_id] = worker
            
            logger.info(f"✓ Worker已加载: {worker_id} - {config.get('name')}")
        
        logger.info(f"Worker Pool初始化完成: {len(self.workers)}个Workers")
    
    def get_worker_by_id(self, worker_id: str) -> Optional[MT5Worker]:
        """根据ID获取Worker"""
        return self.workers.get(worker_id)
    
    def get_workers_by_tags(self, tags: List[str]) -> List[MT5Worker]:
        """根据标签筛选Workers"""
        return [
            worker for worker in self.workers.values()
            if worker.is_healthy and any(tag in worker.tags for tag in tags)
        ]
    
    def select_worker(
        self, 
        symbol: Optional[str] = None,
        strategy_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> MT5Worker:
        """
        选择最优Worker
        
        Args:
            symbol: 交易品种
            strategy_type: 策略类型
            tags: 要求的标签
            **kwargs: 其他条件
        
        Returns:
            选中的Worker
        """
        # 1. 应用路由规则
        worker = self._apply_routing_rules(symbol, strategy_type, tags, **kwargs)
        if worker:
            return worker
        
        # 2. 根据标签筛选
        if tags:
            candidates = self.get_workers_by_tags(tags)
        else:
            candidates = [w for w in self.workers.values() if w.is_healthy]
        
        if not candidates:
            raise Exception("没有可用的Worker")
        
        # 3. 负载均衡选择
        return self._load_balance(candidates)
    
    def _apply_routing_rules(
        self, 
        symbol: Optional[str],
        strategy_type: Optional[str],
        tags: Optional[List[str]],
        **kwargs
    ) -> Optional[MT5Worker]:
        """应用路由规则"""
        routing_rules = settings.get("worker_pool", {}).get("routing_rules", [])
        
        for rule in routing_rules:
            condition = rule.get("condition", {})
            
            # 检查条件
            if symbol and condition.get("symbol") == symbol:
                target_tags = rule.get("target", {}).get("tags", [])
                workers = self.get_workers_by_tags(target_tags)
                if workers:
                    return self._load_balance(workers)
            
            if strategy_type and condition.get("strategy_type") == strategy_type:
                target_tags = rule.get("target", {}).get("tags", [])
                workers = self.get_workers_by_tags(target_tags)
                if workers:
                    return self._load_balance(workers)
        
        return None
    
    def _load_balance(self, candidates: List[MT5Worker]) -> MT5Worker:
        """负载均衡选择"""
        strategy = settings.get("worker_pool", {}).get("load_balancing", {}).get("strategy", "weighted_round_robin")
        
        if strategy == "round_robin":
            return self._round_robin(candidates)
        elif strategy == "weighted":
            return self._weighted_select(candidates)
        elif strategy == "least_connections":
            return self._least_connections(candidates)
        else:
            return self._weighted_round_robin(candidates)
    
    def _round_robin(self, candidates: List[MT5Worker]) -> MT5Worker:
        """轮询"""
        worker = candidates[self.current_worker_index % len(candidates)]
        self.current_worker_index += 1
        return worker
    
    def _weighted_select(self, candidates: List[MT5Worker]) -> MT5Worker:
        """加权随机"""
        weights = [w.priority for w in candidates]
        return random.choices(candidates, weights=weights)[0]
    
    def _weighted_round_robin(self, candidates: List[MT5Worker]) -> MT5Worker:
        """加权轮询"""
        # 按优先级排序后轮询
        sorted_workers = sorted(candidates, key=lambda w: w.priority, reverse=True)
        return self._round_robin(sorted_workers)
    
    def _least_connections(self, candidates: List[MT5Worker]) -> MT5Worker:
        """最少连接"""
        return min(candidates, key=lambda w: w.active_orders)
    
    def place_order(
        self,
        symbol: str,
        action: str,
        volume: float,
        strategy_type: Optional[str] = None,
        worker_id: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        下单（自动选择Worker）
        
        Args:
            symbol: 交易品种
            action: "buy" 或 "sell"
            volume: 手数
            strategy_type: 策略类型（可选，用于路由）
            worker_id: 指定Worker ID（可选）
            **kwargs: 其他下单参数
        """
        # 指定Worker
        if worker_id:
            worker = self.get_worker_by_id(worker_id)
            if not worker:
                raise Exception(f"Worker不存在: {worker_id}")
        else:
            # 自动选择Worker
            worker = self.select_worker(
                symbol=symbol,
                strategy_type=strategy_type
            )
        
        logger.info(f"选择Worker: {worker.worker_id} ({worker.config.get('name')})")
        
        # 下单（带故障转移）
        return self._place_order_with_retry(worker, symbol, action, volume, **kwargs)
    
    def _place_order_with_retry(
        self,
        worker: MT5Worker,
        symbol: str,
        action: str,
        volume: float,
        **kwargs
    ) -> Dict:
        """下单（带重试）"""
        retry_count = settings.get("worker_pool", {}).get("failover", {}).get("retry_count", 3)
        
        for attempt in range(retry_count):
            try:
                result = worker.place_order(
                    symbol=symbol,
                    action=action,
                    volume=volume,
                    **kwargs
                )
                return result
            except Exception as e:
                logger.error(f"下单失败（尝试{attempt+1}/{retry_count}）: {e}")
                
                if attempt < retry_count - 1:
                    # 切换到备用Worker
                    logger.info("切换到备用Worker...")
                    worker = self.select_worker(symbol=symbol)
                else:
                    raise
    
    def get_statistics(self) -> Dict:
        """获取Pool统计信息"""
        healthy_count = sum(1 for w in self.workers.values() if w.is_healthy)
        total_active_orders = sum(w.active_orders for w in self.workers.values())
        
        return {
            "total_workers": len(self.workers),
            "healthy_workers": healthy_count,
            "unhealthy_workers": len(self.workers) - healthy_count,
            "total_active_orders": total_active_orders,
            "workers": [
                {
                    "id": w.worker_id,
                    "name": w.config.get("name"),
                    "healthy": w.is_healthy,
                    "active_orders": w.active_orders,
                    "priority": w.priority,
                    "tags": w.tags
                }
                for w in self.workers.values()
            ]
        }


# ==================== 全局单例 ====================

_worker_pool: Optional[MT5WorkerPool] = None

def get_worker_pool() -> MT5WorkerPool:
    """获取全局Worker Pool实例"""
    global _worker_pool
    if _worker_pool is None:
        _worker_pool = MT5WorkerPool()
    return _worker_pool
```

### Execution服务使用Worker Pool

```python
# src/services/execution/execution_service.py

from src.common.mt5_worker_pool import get_worker_pool
from src.common.config.settings import settings

class ExecutionService:
    def __init__(self):
        """初始化Execution服务"""
        use_pool = settings.get("execution", {}).get("use_worker_pool", False)
        
        if use_pool:
            print("[Execution] 使用Worker Pool模式")
            self.worker_pool = get_worker_pool()
            
            # 打印Pool统计
            stats = self.worker_pool.get_statistics()
            print(f"[Execution] Worker Pool: {stats['healthy_workers']}/{stats['total_workers']}个健康")
        else:
            print("[Execution] 使用单Worker模式")
            # 传统单Worker模式
            mt5_host = settings.get("execution", {}).get("mt5_host", "demo_1")
            self.mt5_client = MT5Client.from_config(mt5_host, auto_login=True)
    
    def execute_trade(
        self,
        symbol: str,
        action: str,
        volume: float,
        strategy_type: Optional[str] = None,
        worker_id: Optional[str] = None
    ):
        """
        执行交易
        
        Args:
            symbol: 交易品种
            action: "buy" 或 "sell"
            volume: 手数
            strategy_type: 策略类型（用于路由）
            worker_id: 指定Worker（可选）
        """
        if hasattr(self, 'worker_pool'):
            # Worker Pool模式：自动选择最优Worker
            result = self.worker_pool.place_order(
                symbol=symbol,
                action=action,
                volume=volume,
                strategy_type=strategy_type,
                worker_id=worker_id
            )
        else:
            # 单Worker模式
            result = self.mt5_client.place_order(
                symbol=symbol,
                action=action,
                volume=volume
            )
        
        return result


# ==================== 使用示例 ====================

if __name__ == "__main__":
    service = ExecutionService()
    
    # 示例1: 自动选择Worker（根据配置规则）
    order1 = service.execute_trade(
        symbol="EURUSD",
        action="buy",
        volume=0.1,
        strategy_type="scalping"  # 会路由到带"hft"标签的Worker
    )
    
    # 示例2: 指定Worker
    order2 = service.execute_trade(
        symbol="GBPUSD",
        action="sell",
        volume=0.2,
        worker_id="real_worker_icm_1"  # 明确指定Worker
    )
    
    # 示例3: 获取Pool统计
    if hasattr(service, 'worker_pool'):
        stats = service.worker_pool.get_statistics()
        print(f"Pool状态: {stats}")
```

---

## 使用场景

### 场景1: 按品种分发

```yaml
routing_rules:
  - name: "EURUSD专用Worker"
    condition:
      symbol: "EURUSD"
    target:
      tags: ["eurusd"]
```

```python
# EURUSD订单会自动路由到带"eurusd"标签的Worker
service.execute_trade("EURUSD", "buy", 0.1)
```

### 场景2: 按策略类型分发

```yaml
routing_rules:
  - name: "高频策略"
    condition:
      strategy_type: "scalping"
    target:
      tags: ["hft", "low_latency"]
```

```python
# 高频策略会路由到低延迟Worker
service.execute_trade(
    "EURUSD", "buy", 0.1,
    strategy_type="scalping"
)
```

### 场景3: 按经纪商分发

```python
# 配置多个经纪商的Worker
mt5_hosts:
  icm_worker: {tags: ["icmarkets"]}
  pep_worker: {tags: ["pepperstone"]}

# 根据需要选择经纪商
pool.place_order(symbol="EURUSD", action="buy", volume=0.1, tags=["icmarkets"])
```

### 场景4: 负载均衡

```yaml
load_balancing:
  strategy: "least_connections"  # 选择当前订单最少的Worker
```

---

## 监控和管理

### API接口

```python
# src/services/execution/api/app.py

from fastapi import FastAPI
from src.common.mt5_worker_pool import get_worker_pool

app = FastAPI()

@app.get("/pool/stats")
def get_pool_statistics():
    """获取Pool统计信息"""
    pool = get_worker_pool()
    return pool.get_statistics()

@app.get("/pool/workers")
def list_workers():
    """列出所有Workers"""
    pool = get_worker_pool()
    return {
        "workers": [
            {
                "id": w.worker_id,
                "name": w.config.get("name"),
                "healthy": w.is_healthy,
                "active_orders": w.active_orders,
                "tags": w.tags
            }
            for w in pool.workers.values()
        ]
    }

@app.post("/pool/workers/{worker_id}/health_check")
def check_worker_health(worker_id: str):
    """检查Worker健康状态"""
    pool = get_worker_pool()
    worker = pool.get_worker_by_id(worker_id)
    if not worker:
        return {"error": "Worker not found"}
    
    is_healthy = worker.health_check()
    return {"worker_id": worker_id, "healthy": is_healthy}
```

### Dashboard监控

```
访问: http://localhost:8003/pool/stats

响应:
{
  "total_workers": 6,
  "healthy_workers": 5,
  "unhealthy_workers": 1,
  "total_active_orders": 12,
  "workers": [
    {
      "id": "real_worker_icm_1",
      "name": "ICMarkets Real 1",
      "healthy": true,
      "active_orders": 5,
      "priority": 10,
      "tags": ["real", "icmarkets", "primary"]
    },
    ...
  ]
}
```

---

## 总结

### ✅ 可以随意分发交易

1. **配置多个Worker**
   ```yaml
   mt5_hosts:
     worker_1: {...}
     worker_2: {...}
     worker_N: {...}
   ```

2. **定义路由规则**
   ```yaml
   routing_rules:
     - 按品种
     - 按策略类型
     - 按经纪商
     - 按标签
   ```

3. **自动分发**
   ```python
   # 代码中无需关心具体Worker
   service.execute_trade("EURUSD", "buy", 0.1)
   # Worker Pool自动选择最优Worker
   ```

### 优势

- ✅ **负载均衡**：自动分发到空闲Worker
- ✅ **故障转移**：Worker失败自动切换
- ✅ **灵活路由**：根据品种/策略/标签路由
- ✅ **横向扩展**：随时添加新Worker
- ✅ **高可用**：多Worker冗余

**你可以有N个Windows机器池，通过配置和标签灵活分发不同的交易！** ✅
