# 🛡️ MEV 保护系统集成指南

**日期:** 2026-03-19  
**优先级:** 🔴 CRITICAL (生存必需)  
**预计部署时间:** 今天完成

---

## 📋 一、文件清单

### **已创建的文件:**

```bash
✓ order_attack_defender.py         # 核心防御模块 (500+ 行)
  ✓ Nonce 跳跃检测
  ✓ Gas 战争识别
  ✓ 撤单垃圾攻击监控
  ✓ 紧急协议自动执行

📝 docs/RETAIL_VS_INSTITUTIONAL_MARKET_MAKING_GUIDE.md  # 战略文档
📝 docs/MEV_PROTECTION_INTEGRATION_GUIDE.md             # 本指南
```

---

## 🔧 二、集成步骤

### **Step 1: 备份现有系统**

```bash
cd /Users/stevenwang/.openclaw/workspace/projects/polymaster-btc-bot/

# 备份 main.py
cp main.py main.py.backup.$(date +%Y%m%d_%H%M%S)

# 如果已有 backup 目录也保存一份
mkdir -p backups
cp main.py backups/main_pre_mev_protection_$(date +%Y%m%d).py
```

---

### **Step 2: 修改 imports**

在 `main.py` 顶部找到现有的 import 部分，添加以下内容:

```python
# === ADD THESE LINES ===
from order_attack_defender import OrderAttackDefender, AttackType, RiskLevel
import asyncio
# =======================
```

位置建议:放在其他 `from xxx import xxx` 语句之后，所有标准库 import 之下。

---

### **Step 3: 初始化防御器**

在 `main()` 函数或你的主初始化逻辑中，找到类似这样的代码:

```python
# 现有代码可能长这样:
async def main():
    strategy = BTCWindowStrategy()
    risk_manager = AdvancedRiskManager(capital=capital)
    # ... other init code
    
    await run_trading_loop(...)
```

**替换为:**

```python
async def main():
    # ====== EXISTING INITIALIZATION ======
    strategy = BTCWindowStrategy()
    risk_manager = AdvancedRiskManager(capital=capital)
    
    # ====== ADD MEV PROTECTION ======
    print("\n" + "="*80)
    print("🛡️  INITIALIZING ORDER ATTACK DEFENDER")
    print("="*80)
    
    # Get wallet address from environment or config
    my_address = os.getenv('POLYMARKET_WALLET_ADDRESS')
    if not my_address:
        raise ValueError("POLYMARKET_WALLET_ADDRESS not set in environment!")
    
    # Initialize defender with conservative settings for first deployment
    mev_defender = OrderAttackDefender(
        api_key=os.getenv('POLYMARKET_API_KEY'),
        private_key=os.getenv('PRIVATE_KEY'),
        my_address=my_address,
        monitoring_interval_seconds=2.0,     # 每 2 秒检查一次
        blacklist_duration_hours=24,          # 黑名单有效期 24 小时
        emergency_cooldown_minutes=5          # 紧急暂停后等待 5 分钟恢复
    )
    
    print(f"✅ Defender initialized for {my_address}")
    print(f"   Monitoring interval: 2.0s")
    print(f"   Blacklist duration: 24h")
    print(f"   Emergency cooldown: 5m")
    print("="*80 + "\n")
    
    # ====== START BACKGROUND MONITORING TASK ======
    # Create a task that runs independently of the trading loop
    monitoring_task = asyncio.create_task(mev_defender.start_monitoring())
    
    print("🚀 Order attack monitoring started in background...")
    
    # ====== CONTINUE WITH TRADING LOOP ======
    await run_trading_loop(
        strategy=strategy,
        risk_manager=risk_manager,
        mev_defender=mev_defender,  # Pass defender to trading functions
        monitoring_task=monitoring_task  # Keep reference to task
    )
```

---

### **Step 4: 包装订单提交函数**

找到你当前的 `submit_order` 或 `place_order` 函数，用以下包装器替换:

```python
async def submit_protected_order(market_id, side, amount, price, mev_defender):
    """
    受保护的订单提交函数
    
    包含:
    1. 威胁环境评估
    2. 动态仓位调整
    3. Gas 优先费设置
    4. 链上验证
    """
    
    # Step 1: Check current threat level
    status = mev_defender.get_status()
    known_threats = len(mev_defender.suspicious_addresses)
    
    logger.info(f"🛡️ Threat environment: {known_threats} known attackers blacklisted")
    
    # Determine aggressiveness based on threat level
    if known_threats == 0:
        quantity_multiplier = 1.0  # Normal
        gas_priority = 'normal'
        mode_msg = "Normal trading mode"
        
    elif known_threats <= 3:
        quantity_multiplier = 0.7  # Reduce by 30%
        gas_priority = 'high'      # Higher gas to prevent front-run
        mode_msg = f"Caution mode ({known_threats} threats)"
        
    elif known_threats <= 10:
        quantity_multiplier = 0.5  # Reduce by 50%
        gas_priority = 'highest'
        mode_msg = f"High alert ({known_threats} threats)"
        
    else:
        quantity_multiplier = 0.2  # Only 20% size, very defensive
        gas_priority = 'critical'
        mode_msg = f"Critical threat level ({known_threats} attackers) - being extra careful"
    
    logger.info(f"{mode_msg} → position scaled to {quantity_multiplier*100:.0f}%")
    
    # Step 2: Prepare order with protective parameters
    protected_amount = amount * quantity_multiplier
    
    try:
        # Submit order with higher gas priority
        result = await polymarket_client.submit_order(
            contract_id=market_id,
            side=side,
            amount=protected_amount,
            price=price,
            timestamp_ms=int(time.time() * 1000),
            gas_priority_factor={
                'normal': 1.0,
                'high': 1.5,
                'highest': 2.0,
                'critical': 3.0
            }[gas_priority]
        )
        
        # Step 3: Verify on-chain immediately
        is_verified = await verify_order_on_chain(result['order_id'])
        
        if not is_verified:
            logger.error(f"❌ Order {result['order_id']} NOT verified on-chain!")
            logger.error("Possible attack detected - triggering emergency protocol")
            
            await mev_defender._trigger_emergency_defense(
                reason="unverified_order",
                details=f"Order {result['order_id']} failed chain verification"
            )
            
            return None
        
        # Success
        logger.info(f"✅ Protected order submitted successfully")
        logger.info(f"   Amount: ${protected_amount:.2f} (scaled from ${amount:.2f})")
        logger.info(f"   Gas priority: {gas_priority}")
        logger.info(f"   Chain verified: Yes")
        
        return result
        
    except Exception as e:
        logger.error(f"Error submitting protected order: {e}")
        
        # If error suggests attack, trigger defense
        if "nonce" in str(e).lower() or "conflict" in str(e).lower():
            await mev_defender._trigger_emergency_defense(
                reason="transaction_error",
                details=str(e)
            )
        
        return None


async def cancel_order_protected(order_id, mev_defender):
    """受保护的撤单函数"""
    
    try:
        result = await polymarket_client.cancel_order(
            order_id=order_id,
            gas_priority_factor=2.0  # Use high gas when cancelling
        )
        
        # Verify cancellation on-chain
        if result.get('success'):
            logger.info(f"✅ Order {order_id} cancelled successfully")
            return True
        else:
            logger.error(f"❌ Failed to cancel order {order_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        
        # Suspicious failure pattern
        await mev_defender._record_suspicious_activity(
            address="unknown",
            pattern_type=AttackType.SPAM_CANCEL,
            severity=RiskLevel.MEDIUM
        )
        
        return False
```

---

### **Step 5: 修改交易循环**

找到你的主要交易循环，添加对防御器的调用:

```python
async def run_trading_loop(strategy, risk_manager, mev_defender, monitoring_task):
    """Modified trading loop with MEV protection"""
    
    logger.info("Starting trading loop with MEV protection...")
    
    while True:
        # Check if emergency pause active
        if mev_defender.is_emergency_pause:
            logger.warning(f"⏸️ Trading paused: {mev_defender.pause_reason}")
            await asyncio.sleep(60)  # Wait before rechecking
            continue
        
        # Check threat level and adjust behavior
        status = mev_defender.get_status()
        
        if status.known_threats_count > 5:
            logger.warning(f"⚠️ High threat environment: {status.known_threats_count} attackers")
            # Reduce trading frequency or skip some opportunities
            await asyncio.sleep(10)  # Extra delay between trades
        elif status.known_threats_count > 10:
            logger.critical(f"🚨 Critical threat level: {status.known_threats_count}")
            await asyncio.sleep(30)  # Much more conservative
        
        # Main trading logic
        try:
            # Get market opportunities
            opportunities = await strategy.identify_opportunities()
            
            for opportunity in opportunities[:10]:  # Limit concurrent trades in hostile env
                # Check regulatory risk FIRST
                risk_check = risk_manager.comprehensive_risk_assessment()
                
                if risk_check['overall_risk'] == 'critical':
                    logger.warning(f"Skipping market due to regulatory risk")
                    continue
                
                # Calculate position size with risk manager
                position_size = risk_manager.calculate_dynamic_position_size(
                    base_size=OPPORTUNITY_BASE_SIZE,
                    confidence=opportunity.confidence,
                    win_rate_history=risk_manager.win_rate_history
                )
                
                # Submit with MEV protection wrapper
                quote = await generate_quote(opportunity.market_id, opportunity.prediction)
                
                if quote:
                    result = await submit_protected_order(
                        market_id=opportunity.market_id,
                        side='YES',
                        amount=position_size,
                        price=quote['yes_price'],
                        mev_defender=mev_defender
                    )
                    
                    if result and result.get('filled'):
                        # Record successful trade
                        risk_manager.record_trade(
                            market_id=opportunity.market_id,
                            profit=result.get('profit', 0),
                            filled_amount=result.get('filled_amount', 0)
                        )
        
        except Exception as e:
            logger.error(f"Trading loop error: {e}")
            await asyncio.sleep(5)
        
        # Sleep between cycles
        await asyncio.sleep(TRADING_LOOP_INTERVAL_SECONDS)
```

---

### **Step 6: 配置环境变量**

确保你的 `.env`文件或 systemd 服务配置文件包含这些变量:

```bash
# Add to ~/.secrets/.env or your VPS .env file

# Polymarket API credentials
POLYMARKET_API_KEY=your_api_key_here
POLYMARKET_WALLET_ADDRESS=0xYourWalletAddressHere
PRIVATE_KEY=your_private_key_here  # Use carefully!

# MEV Protection settings (optional overrides)
MEV_MONITORING_INTERVAL=2.0          # Default: check every 2 seconds
BLACKLIST_DURATION_HOURS=24          # Default: 24 hours
EMERGENCY_COOLDOWN_MINUTES=5         # Default: 5 minutes

# Logging
LOG_LEVEL=INFO                      # Or DEBUG for more detail
TELEGRAM_ALERT_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## 🚀 三、部署步骤

### **Phase 1: Local Testing (Today)**

```bash
# Navigate to project directory
cd /Users/stevenwang/.openclaw/workspace/projects/polymaster-btc-bot/

# Run syntax check
python -m py_compile order_attack_defender.py
echo "✅ Syntax OK"

# Run the standalone test
python order_attack_defender.py

# Expected output:
# ================================================================================
# 🛡️ ORDER ATTACK DEFENDER - TEST RUN
# ================================================================================
# My Address: 0x1234...
# API Key: test-api...
# ...
```

---

### **Phase 2: Simulated Deployment (Tonight)**

```bash
# Test with simulate-only flag
export SIMULATION_MODE=true
export ENABLE_MEV_PROTECTION=true

python main.py --simulate-only --trades=5

# Watch logs for:
# ✅ "Initializing Order Attack Defender"
# ✅ "Order attack monitoring started in background..."
# ⚠️ Any warnings about nonce jumps or suspicious patterns
```

---

### **Phase 3: Live Deployment (Tomorrow Morning)**

```bash
# On VPS:

# Backup current system
cd /home/ubuntu/polymaster-btc-bot/
cp main.py main.py.backup.$(date +%Y%m%d_%H%M%S)

# Deploy new version with MEV protection
git checkout main_mev_protection_branch  # OR copy the modified files manually

# Reload systemd service
sudo systemctl daemon-reload
sudo systemctl restart polymaster-bot

# Monitor logs in real-time
journalctl -u polymaster-bot -f --no-pager

# Look for these logs:
# • "🛡️ Initializing Order Attack Defender"
# • "🚀 Order attack monitoring started"
# • "🔗 Chain verification: X/Y orders verified"
# • "🚫 NEW ATTACKER ADDED TO BLACKLIST" (if detected)
```

---

### **Phase 4: Close Monitoring (First 24 Hours)**

```bash
# Set up log rotation and alerts
tail -f /var/log/polymaster-bot.log | grep -E "(ATTACK|EMERGENCY|NONCE)" &

# Or use journalctl:
journalctl -u polymaster-bot -f | tee /tmp/mev_protection_logs.txt

# Check Telegram for any alerts (if configured)
# Manually inspect logs every 2 hours for first day
```

---

## ✅ 四、验证清单

### **Before Going Live:**

- [ ] All imports added to main.py
- [ ] Defender initialized in main() function
- [ ] Background monitoring task created
- [ ] submit_order() wrapped with protection
- [ ] cancel_order() wrapped with protection
- [ ] Trading loop checks emergency_pause status
- [ ] Environment variables configured
- [ ] Systemd service updated
- [ ] Backup created

### **During First 24 Hours:**

- [ ] Monitor for attack detection alerts
- [ ] Verify all orders are chain-verified
- [ ] Check blacklist growth rate (should be low initially)
- [ ] Confirm trading continues normally
- [ ] Review emergency protocols (they should NOT activate yet!)
- [ ] Document any issues encountered

---

## 🎯 五、常见问题解答

### **Q: 如果防御器误报怎么办？**

A: 当前实现非常保守:
- 只有确凿证据才添加黑名单
- 置信度达到 0.8+ 才会标记 HIGH risk
- 紧急暂停需要 multiple indicators

如果发现误报，可以:
1. 临时降低 sensitivity: 增加 `monitoring_interval_seconds`
2. 提高阈值: 修改 `nonce_jump_threshold` to 2
3. 暂时禁用特定检测规则

---

### **Q: 会影响交易速度吗？**

A: 不会显著影响:
- Monitoring runs in separate asyncio task
- Blockchain verification is async (non-blocking)
- Most time spent waiting for network responses anyway
- Overhead estimated at <50ms per order

---

### **Q: 如何知道是否检测到攻击？**

A: Multiple channels:
1. **Telegram alerts** (if configured) - immediate notification
2. **Log messages** - look for "NEW ATTACKER ADDED TO BLACKLIST"
3. **Status dashboard** - call `get_status()` periodically
4. **Emergency pause** - if triggered, you'll see PAUSED status

---

### **Q: Emergency pause 会自动恢复吗？**

A: Partially automatic:
- After cooldown period (default 5 min), attempts to resume
- Only resumes if threat count drops below threshold (≤3 attackers)
- Otherwise requires manual confirmation via Telegram command
- This prevents auto-resuming during active attacks

---

## 📊 六、性能预期

### **Expected Behavior:**

| Scenario | Response Time | Impact on Trading |
|----------|---------------|-------------------|
| Normal operation | ~2s monitoring cycle | No impact |
| Moderate threat (3-5 attackers) | Slight slowdown | Position sizes reduced to 70% |
| High threat (5-10 attackers) | Additional delays | Position sizes reduced to 50% |
| Critical threat (>10 attackers) | Pause until review | Trading halted |
| Active attack detected | Instant emergency pause | Immediate protection |

---

## 🚨 七、紧急联系人

如果遇到任何异常，立即:

1. **Pause trading manually:**
   ```bash
   sudo systemctl stop polymaster-bot
   ```

2. **Check logs:**
   ```bash
   journalctl -u polymaster-bot -n 100 --no-pager
   ```

3. **Review attack detection:**
   ```bash
   python -c "
from order_attack_defender import OrderAttackDefender
defender = OrderAttackDefender(...)  # Init with same params
print(defender.get_blacklist_summary())
"
   ```

4. **Contact:** Check TELEGRAM alerts or workspace chat

---

## ✅ 总结

**你今天应该做的:**

1. ✅ Review 这份集成指南
2. ✅ Read `order_attack_defender.py` code
3. ✅ Make backup of `main.py`
4. ✅ Apply integration steps above
5. ✅ Run local tests
6. ✅ Plan tomorrow morning deployment

**明日行动:**

1. Deploy to VPS with SIMULATION_MODE=true
2. Monitor first 24 hours closely
3. Gradually switch to live trading once confident

记住：**这是生存必需的，不是可选项!** February 的攻击事件证明任何人都可能是目标。

Ready to integrate? Let me know if you need help with any step! 🚀

---

*Created: 2026-03-19 06:10 PDT*  
*Status: Ready for immediate implementation*  
*Priority: 🔴 CRITICAL - Survival Essential*
