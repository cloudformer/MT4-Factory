# 多Worker交易查询方案

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│ 查询层（统一入口）                                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  TradeQueryService                                      │
│  ├─ 查询所有持仓 → 聚合所有Workers                      │
│  ├─ 查询历史订单 → 从数据库                             │
│  ├─ 查询特定订单 → 直接定位到Worker                     │
│  └─ 实时统计 → 汇总所有Workers数据                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 数据存储层（中心化）                                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  PostgreSQL数据库                                       │
│  ┌───────────────────────────────────────────────────┐ │
│  │ trades表                                          │ │
│  │ ├─ order_id (唯一)                                │ │
│  │ ├─ worker_id (哪个Worker执行的)                  │ │
│  │ ├─ symbol, action, volume                        │ │
│  │ ├─ open_price, close_price                       │ │
│  │ ├─ profit, status                                │ │
│  │ └─ created_at, closed_at                         │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
                        ↑
┌─────────────────────────────────────────────────────────┐
│ Worker层（分布式执行）                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Worker 1          Worker 2          Worker N          │
│  ├─ 下单           ├─ 下单           ├─ 下单           │
│  └─ 记录到DB       └─ 记录到DB       └─ 记录到DB       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 数据库设计

### trades表

```sql
CREATE TABLE trades (
    id BIGSERIAL PRIMARY KEY,
    
    -- 订单信息
    order_id BIGINT UNIQUE NOT NULL,        -- MT5订单号
    ticket BIGINT,                           -- MT5票据号
    
    -- Worker信息
    worker_id VARCHAR(50) NOT NULL,          -- 哪个Worker执行的
    worker_name VARCHAR(100),                -- Worker名称
    mt5_account BIGINT,                      -- MT5账号
    
    -- 交易信息
    symbol VARCHAR(20) NOT NULL,             -- 交易品种
    action VARCHAR(10) NOT NULL,             -- buy/sell
    volume DECIMAL(10, 2) NOT NULL,          -- 手数
    
    -- 价格信息
    open_price DECIMAL(10, 5),               -- 开仓价
    close_price DECIMAL(10, 5),              -- 平仓价
    sl DECIMAL(10, 5),                       -- 止损
    tp DECIMAL(10, 5),                       -- 止盈
    
    -- 损益
    profit DECIMAL(10, 2),                   -- 盈亏
    commission DECIMAL(10, 2),               -- 手续费
    swap DECIMAL(10, 2),                     -- 隔夜利息
    
    -- 状态
    status VARCHAR(20) NOT NULL,             -- pending/open/closed/failed
    
    -- 策略信息
    strategy_id VARCHAR(50),                 -- 策略ID
    strategy_name VARCHAR(100),              -- 策略名称
    magic INT,                               -- 魔术数字
    comment TEXT,                            -- 备注
    
    -- 时间
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    opened_at TIMESTAMP,
    closed_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_trades_worker_id ON trades(worker_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_created_at ON trades(created_at);
CREATE INDEX idx_trades_strategy_id ON trades(strategy_id);
CREATE INDEX idx_trades_mt5_account ON trades(mt5_account);
```

---

## 代码实现

### 交易查询服务

```python
# src/services/execution/trade_query_service.py

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from src.common.mt5_worker_pool import get_worker_pool
from src.common.database import get_db_session
from sqlalchemy import and_, or_

class TradeQueryService:
    """交易查询服务（支持多Worker）"""
    
    def __init__(self):
        self.worker_pool = get_worker_pool()
        self.db = get_db_session()
    
    # ==================== 实时查询（从Workers）====================
    
    def get_all_positions(self) -> List[Dict]:
        """
        获取所有持仓（聚合所有Workers）
        
        Returns:
            [
                {
                    "worker_id": "real_worker_1",
                    "worker_name": "ICMarkets Real 1",
                    "ticket": 12345678,
                    "symbol": "EURUSD",
                    "type": "buy",
                    "volume": 0.1,
                    "price_open": 1.08456,
                    "profit": 12.34,
                    ...
                },
                ...
            ]
        """
        all_positions = []
        
        # 遍历所有健康的Workers
        for worker_id, worker in self.worker_pool.workers.items():
            if not worker.is_healthy:
                continue
            
            try:
                # 获取该Worker的持仓
                positions = worker.client.get_positions()
                
                # 添加Worker信息
                for pos in positions:
                    pos['worker_id'] = worker_id
                    pos['worker_name'] = worker.config.get('name')
                    pos['mt5_account'] = worker.config.get('login')
                    all_positions.append(pos)
            
            except Exception as e:
                print(f"[Warning] 获取Worker {worker_id} 持仓失败: {e}")
        
        return all_positions
    
    def get_position_by_ticket(self, ticket: int) -> Optional[Dict]:
        """
        根据票据号查询持仓（自动查找所有Workers）
        
        Args:
            ticket: MT5票据号
        
        Returns:
            持仓详情（如果存在）
        """
        for worker_id, worker in self.worker_pool.workers.items():
            if not worker.is_healthy:
                continue
            
            try:
                positions = worker.client.get_positions()
                for pos in positions:
                    if pos['ticket'] == ticket:
                        pos['worker_id'] = worker_id
                        pos['worker_name'] = worker.config.get('name')
                        return pos
            except:
                continue
        
        return None
    
    def get_positions_by_symbol(self, symbol: str) -> List[Dict]:
        """
        按品种查询持仓（聚合所有Workers）
        
        Args:
            symbol: 交易品种（如 "EURUSD"）
        """
        all_positions = self.get_all_positions()
        return [pos for pos in all_positions if pos['symbol'] == symbol]
    
    def get_positions_by_worker(self, worker_id: str) -> List[Dict]:
        """
        查询特定Worker的持仓
        
        Args:
            worker_id: Worker ID
        """
        worker = self.worker_pool.get_worker_by_id(worker_id)
        if not worker or not worker.is_healthy:
            return []
        
        return worker.client.get_positions()
    
    # ==================== 历史查询（从数据库）====================
    
    def get_trade_history(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None,
        worker_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        查询历史交易记录
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbol: 交易品种
            worker_id: Worker ID
            strategy_id: 策略ID
            status: 状态（open/closed/failed）
            limit: 返回数量限制
        """
        query = self.db.query(Trade)
        
        # 时间范围
        if start_date:
            query = query.filter(Trade.created_at >= start_date)
        if end_date:
            query = query.filter(Trade.created_at <= end_date)
        
        # 其他过滤条件
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        if worker_id:
            query = query.filter(Trade.worker_id == worker_id)
        if strategy_id:
            query = query.filter(Trade.strategy_id == strategy_id)
        if status:
            query = query.filter(Trade.status == status)
        
        # 排序和限制
        query = query.order_by(Trade.created_at.desc()).limit(limit)
        
        trades = query.all()
        return [self._trade_to_dict(t) for t in trades]
    
    def get_trade_by_order_id(self, order_id: int) -> Optional[Dict]:
        """
        根据订单号查询交易
        
        Args:
            order_id: MT5订单号
        """
        trade = self.db.query(Trade).filter(Trade.order_id == order_id).first()
        return self._trade_to_dict(trade) if trade else None
    
    # ==================== 统计查询 ====================
    
    def get_daily_statistics(self, date: Optional[datetime] = None) -> Dict:
        """
        获取每日统计
        
        Args:
            date: 日期（默认今天）
        """
        if date is None:
            date = datetime.now().date()
        
        start_time = datetime.combine(date, datetime.min.time())
        end_time = datetime.combine(date, datetime.max.time())
        
        trades = self.db.query(Trade).filter(
            and_(
                Trade.created_at >= start_time,
                Trade.created_at <= end_time
            )
        ).all()
        
        total_trades = len(trades)
        closed_trades = [t for t in trades if t.status == 'closed']
        total_profit = sum(t.profit or 0 for t in closed_trades)
        win_trades = [t for t in closed_trades if (t.profit or 0) > 0]
        loss_trades = [t for t in closed_trades if (t.profit or 0) < 0]
        
        return {
            "date": date.isoformat(),
            "total_trades": total_trades,
            "closed_trades": len(closed_trades),
            "open_trades": total_trades - len(closed_trades),
            "total_profit": round(total_profit, 2),
            "win_trades": len(win_trades),
            "loss_trades": len(loss_trades),
            "win_rate": round(len(win_trades) / len(closed_trades) * 100, 2) if closed_trades else 0,
            "avg_profit": round(total_profit / len(closed_trades), 2) if closed_trades else 0
        }
    
    def get_worker_statistics(self) -> List[Dict]:
        """
        获取各Worker统计
        
        Returns:
            [
                {
                    "worker_id": "real_worker_1",
                    "worker_name": "ICMarkets Real 1",
                    "total_trades": 150,
                    "total_profit": 1234.56,
                    "open_positions": 5,
                    ...
                },
                ...
            ]
        """
        stats = []
        
        for worker_id, worker in self.worker_pool.workers.items():
            # 从数据库统计历史
            trades = self.db.query(Trade).filter(Trade.worker_id == worker_id).all()
            closed_trades = [t for t in trades if t.status == 'closed']
            total_profit = sum(t.profit or 0 for t in closed_trades)
            
            # 从Worker获取实时持仓
            open_positions = 0
            if worker.is_healthy:
                try:
                    positions = worker.client.get_positions()
                    open_positions = len(positions)
                except:
                    pass
            
            stats.append({
                "worker_id": worker_id,
                "worker_name": worker.config.get('name'),
                "mt5_account": worker.config.get('login'),
                "total_trades": len(trades),
                "closed_trades": len(closed_trades),
                "total_profit": round(total_profit, 2),
                "open_positions": open_positions,
                "is_healthy": worker.is_healthy
            })
        
        return stats
    
    def get_symbol_statistics(self, days: int = 30) -> List[Dict]:
        """
        获取各品种统计
        
        Args:
            days: 统计天数
        """
        start_date = datetime.now() - timedelta(days=days)
        
        trades = self.db.query(Trade).filter(
            Trade.created_at >= start_date
        ).all()
        
        # 按品种分组统计
        symbol_stats = {}
        for trade in trades:
            symbol = trade.symbol
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {
                    "symbol": symbol,
                    "total_trades": 0,
                    "total_profit": 0,
                    "win_trades": 0,
                    "loss_trades": 0
                }
            
            symbol_stats[symbol]["total_trades"] += 1
            if trade.status == 'closed' and trade.profit:
                symbol_stats[symbol]["total_profit"] += trade.profit
                if trade.profit > 0:
                    symbol_stats[symbol]["win_trades"] += 1
                else:
                    symbol_stats[symbol]["loss_trades"] += 1
        
        # 计算胜率
        for stats in symbol_stats.values():
            closed = stats["win_trades"] + stats["loss_trades"]
            if closed > 0:
                stats["win_rate"] = round(stats["win_trades"] / closed * 100, 2)
            else:
                stats["win_rate"] = 0
        
        return list(symbol_stats.values())
    
    # ==================== 辅助方法 ====================
    
    def _trade_to_dict(self, trade) -> Dict:
        """Trade模型转字典"""
        return {
            "id": trade.id,
            "order_id": trade.order_id,
            "ticket": trade.ticket,
            "worker_id": trade.worker_id,
            "worker_name": trade.worker_name,
            "mt5_account": trade.mt5_account,
            "symbol": trade.symbol,
            "action": trade.action,
            "volume": float(trade.volume),
            "open_price": float(trade.open_price) if trade.open_price else None,
            "close_price": float(trade.close_price) if trade.close_price else None,
            "profit": float(trade.profit) if trade.profit else None,
            "status": trade.status,
            "strategy_id": trade.strategy_id,
            "strategy_name": trade.strategy_name,
            "created_at": trade.created_at.isoformat(),
            "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
            "closed_at": trade.closed_at.isoformat() if trade.closed_at else None
        }
```

---

## API接口

### REST API

```python
# src/services/execution/api/app.py

from fastapi import FastAPI, Query
from src.services.execution.trade_query_service import TradeQueryService

app = FastAPI()
query_service = TradeQueryService()

@app.get("/trades/positions")
def get_all_positions():
    """获取所有持仓（聚合所有Workers）"""
    return {
        "positions": query_service.get_all_positions()
    }

@app.get("/trades/positions/{ticket}")
def get_position_by_ticket(ticket: int):
    """根据票据号查询持仓"""
    position = query_service.get_position_by_ticket(ticket)
    if not position:
        return {"error": "Position not found"}
    return position

@app.get("/trades/positions/symbol/{symbol}")
def get_positions_by_symbol(symbol: str):
    """按品种查询持仓"""
    return {
        "symbol": symbol,
        "positions": query_service.get_positions_by_symbol(symbol)
    }

@app.get("/trades/positions/worker/{worker_id}")
def get_positions_by_worker(worker_id: str):
    """查询特定Worker的持仓"""
    return {
        "worker_id": worker_id,
        "positions": query_service.get_positions_by_worker(worker_id)
    }

@app.get("/trades/history")
def get_trade_history(
    symbol: Optional[str] = None,
    worker_id: Optional[str] = None,
    strategy_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=1000)
):
    """查询历史交易"""
    return {
        "trades": query_service.get_trade_history(
            symbol=symbol,
            worker_id=worker_id,
            strategy_id=strategy_id,
            status=status,
            limit=limit
        )
    }

@app.get("/trades/statistics/daily")
def get_daily_statistics():
    """今日统计"""
    return query_service.get_daily_statistics()

@app.get("/trades/statistics/workers")
def get_worker_statistics():
    """各Worker统计"""
    return {
        "workers": query_service.get_worker_statistics()
    }

@app.get("/trades/statistics/symbols")
def get_symbol_statistics(days: int = Query(30, le=365)):
    """各品种统计"""
    return {
        "symbols": query_service.get_symbol_statistics(days=days)
    }
```

---

## 使用示例

### 示例1: 查询所有持仓

```bash
curl http://localhost:8003/trades/positions

# 响应
{
  "positions": [
    {
      "worker_id": "real_worker_icm_1",
      "worker_name": "ICMarkets Real 1",
      "mt5_account": 8012345678,
      "ticket": 12345678,
      "symbol": "EURUSD",
      "type": "buy",
      "volume": 0.1,
      "price_open": 1.08456,
      "profit": 12.34
    },
    {
      "worker_id": "real_worker_pep_1",
      "worker_name": "Pepperstone Real 1",
      "mt5_account": 9012345678,
      "ticket": 87654321,
      "symbol": "GBPUSD",
      "type": "sell",
      "volume": 0.2,
      "price_open": 1.26543,
      "profit": -5.67
    }
  ]
}
```

### 示例2: 查询历史交易

```bash
curl "http://localhost:8003/trades/history?symbol=EURUSD&limit=10"

# 响应
{
  "trades": [
    {
      "order_id": 12345678,
      "worker_id": "real_worker_icm_1",
      "symbol": "EURUSD",
      "action": "buy",
      "volume": 0.1,
      "open_price": 1.08456,
      "close_price": 1.08556,
      "profit": 10.00,
      "status": "closed",
      "created_at": "2024-04-11T10:30:00",
      "closed_at": "2024-04-11T11:45:00"
    },
    ...
  ]
}
```

### 示例3: Worker统计

```bash
curl http://localhost:8003/trades/statistics/workers

# 响应
{
  "workers": [
    {
      "worker_id": "real_worker_icm_1",
      "worker_name": "ICMarkets Real 1",
      "mt5_account": 8012345678,
      "total_trades": 150,
      "closed_trades": 145,
      "total_profit": 1234.56,
      "open_positions": 5,
      "is_healthy": true
    },
    {
      "worker_id": "real_worker_pep_1",
      "worker_name": "Pepperstone Real 1",
      "mt5_account": 9012345678,
      "total_trades": 87,
      "closed_trades": 85,
      "total_profit": 543.21,
      "open_positions": 2,
      "is_healthy": true
    }
  ]
}
```

---

## Dashboard展示

### 实时持仓总览

```
┌─────────────────────────────────────────────────────┐
│ 实时持仓（所有Workers）                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Worker: ICMarkets Real 1                           │
│  ├─ EURUSD Buy 0.1手 → +$12.34                     │
│  └─ GBPUSD Buy 0.2手 → -$3.21                      │
│                                                     │
│  Worker: Pepperstone Real 1                         │
│  └─ USDJPY Sell 0.1手 → +$5.67                    │
│                                                     │
│  总计: 3个持仓, 盈亏: +$14.80                       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Workers状态

```
┌─────────────────────────────────────────────────────┐
│ Workers统计                                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ✓ ICMarkets Real 1      150笔  $1,234.56  5持仓   │
│  ✓ Pepperstone Real 1     87笔    $543.21  2持仓   │
│  ✓ Demo Worker 1          23笔     $89.12  0持仓   │
│  ✗ ICMarkets Real 2       未连接                    │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 总结

### ✅ 查询非常方便

1. **统一查询接口**
   - 一个API查询所有Workers持仓
   - 自动聚合分布式数据

2. **中心化存储**
   - 所有交易记录存数据库
   - 可按任意条件查询历史

3. **Worker追踪**
   - 每笔交易记录worker_id
   - 知道订单在哪个Worker上

4. **灵活过滤**
   ```python
   # 按品种
   query_service.get_positions_by_symbol("EURUSD")
   
   # 按Worker
   query_service.get_positions_by_worker("real_worker_1")
   
   # 按票据号（自动查找所有Workers）
   query_service.get_position_by_ticket(12345678)
   ```

**多Worker架构不影响查询便利性，反而提供了更灵活的过滤和统计！** ✅
