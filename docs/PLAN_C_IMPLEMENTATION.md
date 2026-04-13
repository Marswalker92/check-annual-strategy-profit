# 方案 C 实现说明

## 问题背景
floatingPnL 只包含当前活跃仓位的未实现盈亏，**忽略了已结算/平仓市场的损失**。
- 场景：某市场结算亏了100块 → 仓位从API中消失 → 历史数据无法追踪这个-100

## 方案 C：本地快照对比追踪

### 核心原理
1. **每天保存活跃仓位快照**：记录当天从API拿到的所有仓位（market_id, initialValue, currentValue)
2. **对比昨天快照**：发现今天消失的仓位 = 今天结算的仓位
3. **计算结算盈亏**：对消失的仓位，用其最后的(currentValue - initialValue)作为realized PnL
4. **累计到历史**：把今天的结算盈亏加到总的cumulative realized_pnl中
5. **总浮动盈亏 = 未实现 + 已结算**

### 数据文件

#### 📄 polymarket_positions_snapshot.json
```json
{
  "2026-04-13": {
    "Poly:0xWalletAddress": [
      {
        "market_id": "0x123...",
        "initial_value": 100.5,
        "current_value": 95.2,
        "position": 10
      }
    ]
  },
  "2026-04-14": {
    "Poly:0xWalletAddress": [
      // ... 注意：前面的那个市场消失了，说明已结算
    ]
  }
}
```

#### 📋 polymarket_realized_pnl.json
```json
{
  "Poly:0xWalletAddress": {
    "total_realized_pnl": -50.5,           // 累计已结算盈亏
    "settled_positions_count": 3,          // 总共结算过3个仓位  
    "last_updated": "2026-04-13"
  }
}
```

#### 📊 portfolio 历史记录中的新字段
```json
{
  "2026-04-13": {
    "Poly:0xWalletAddress": {
      "unrealized_pnl": 47.8,          // 活跃仓位的未实现盈亏
      "realized_pnl": -5.0,            // 已结算累计盈亏
      "floating_pnl": 42.8,            // = unrealized + realized
      ...
    }
  }
}
```

### 代码改动

#### 新文件：`src/poly_realized_pnl.py`
- `update_realized_pnl_for_wallet(wallet_key, orders)` - 对比快照，更新已结算PnL
- `get_wallet_realized_pnl(wallet_key)` - 获取累计已结算PnL
- `calculate_settled_pnl(current, previous)` - 智能检测消失的仓位

#### 改动：`src/platforms/polymarket.py`
```python
def summarize_wallet(wallet_entry):
    # 获取活跃仓位
    rows = fetch_positions(user)
    
    # 计算未实现PnL（活跃仓位）
    unrealized_pnl = sum(current - initial for each position)
    
    # 👇 新增：追踪已结算仓位
    wallet_key = f"Poly:{user}"
    update_realized_pnl_for_wallet(wallet_key, rows)
    realized_pnl = get_wallet_realized_pnl(wallet_key)
    
    # 总浮动盈亏 = 未实现 + 已结算  
    floating_pnl = unrealized_pnl + realized_pnl
    
    return {
        "unrealized_pnl": unrealized_pnl,    # 新增
        "realized_pnl": realized_pnl,        # 新增  
        "floating_pnl": floating_pnl,        # 现在包含已结算
        ...
    }
```

### 日变化计算的改进

原理不变：`daily_change = today_floating_pnl - yesterday_floating_pnl`

但现在包含了已结算部分：
- 如果今天有市场结算亏了10块
- realized_pnl 会从0变成-10
- floating_pnl 会相应下降10块
- 日报告会显示这个-10的下跌 ✓

### 优势总结

| 问题 | 原方案（cashPnl） | 新方案（方案C） | 
|-----|-----------------|---------------|
| 已结算损失是否被追踪 | ✗ 消失不见 | ✓ 永久记录 |
| 何时计算已结算PnL | API不提供 | 本地对比 |
| API依赖性 | 高（需要新端点） | 低（仅用现有数据） |
| 历史数据准确度 | 差（无法回溯） | 好（从今天开始准确） |
| 实现复杂度 | 简单 | 中等 |

### 使用示例

```
Day 1 (2026-04-13)：
  - 活跃仓位1：[market A, market B]
  - unrealized_pnl: +50
  - realized_pnl: 0 (首次运行)
  - floating_pnl: +50

Day 2 (2026-04-14)：
  - 活跃仓位2：[market C] (market A, B 消失 = 结算了)
  - 检测到 market A 和 B 结算了
  - 计算它们最后的 PnL：A 亏-20，B 亏-15 → 总-35
  - unrealized_pnl: +20
  - realized_pnl: 0 (昨天) + (-35) (今天结算) = -35
  - floating_pnl: +20 + (-35) = -15 ✓ (正确反映了总损失)
  - daily_change = -15 - 50 = -65 (又亏了35，加上活跃仓位变化的30)
```

### 后续优化方向

1. **回填历史数据**：如果有过去的快照记录，可以重新计算之前的realized_pnL
2. **结算事件日志**：记录每个结算仓位的详细信息（结算时间、市场、结算价格）
3. **区分类型**：区分不同类型的结算（正常结算 vs 强制平仓 vs 订单取消)
4. **对账验证**：与Polymarket官方数据对比验证计算的准确性

## 完成标志

✅ 新增 `poly_realized_pnl.py` 模块  
✅ 修改 `polymarket.py` 集成已结算追踪  
✅ 创建两个新JSON追踪文件  
✅ 返回 unrealized_pnl 和 realized_pnl 字段  
✅ floating_pnl 现在 = unrealized + realized  
✅ 单元测试通过（测试数据正确生成）
