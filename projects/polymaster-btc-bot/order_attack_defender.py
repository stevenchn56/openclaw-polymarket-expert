#!/usr/bin/env python3
"""
🛡️ Order Attack Prevention System (订单攻击防御系统)
Monitors for suspicious cancel patterns and auto-defends against MEV attacks.

Protects against:
1. Nonce-based front-running attacks (2 月攻击事件主要手法)
2. Gas wars (攻击者出更高 Gas 费抢跑)
3. Spam cancellation (大量撤单清除挂单)

Created: 2026-03-19
Priority: 🔴 CRITICAL - Survival Essential
"""

import asyncio
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set, Any
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class AttackType(Enum):
    """攻击类型枚举"""
    NONCE_FRONTRUN = "nonce_front_run"          # Nonce 跳跃抢跑
    GAS_WAR = "gas_war"                          # Gas 战争
    SPAM_CANCEL = "spam_cancel"                  # 撒单清除
    SUSPICIOUS_PATTERN = "suspicious_pattern"    # 可疑模式
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SuspiciousPattern:
    """检测到的可疑攻击模式"""
    attacker_address: str
    pattern_type: AttackType
    first_seen: datetime
    last_seen: datetime
    total_attacks: int
    estimated_damage_usd: float
    confidence_score: float  # 0.0-1.0
    blacklisted_until: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            'attacker_address': self.attacker_address,
            'pattern_type': self.pattern_type.value,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'total_attacks': self.total_attacks,
            'estimated_damage_usd': self.estimated_damage_usd,
            'confidence_score': self.confidence_score,
            'blacklisted_until': self.blacklisted_until.isoformat() if self.blacklisted_until else None
        }


@dataclass  
class DefenseStatus:
    """防御状态报告"""
    active: bool
    current_mode: str
    known_threats_count: int
    last_attack_detected: Optional[datetime]
    emergency_active: bool
    paused_reason: Optional[str]
    
    def to_dict(self) -> dict:
        return asdict(self)


class OrderAttackDefender:
    """
    三层 MEV 攻击防御系统
    
    防御层 1: Nonce 跳跃监控
    - 检测非连续的 nonce 变化
    - 识别可能的抢跑攻击
    
    防御层 2: 撤单垃圾攻击识别
    - 追踪高频撤单模式
    - 识别 gas 战争
    
    防御层 3: 链上交易验证
    - 不信任 API 返回的成交信号
    - 直接查询区块链确认
    """
    
    def __init__(self,
                 api_key: str,
                 private_key: str,
                 my_address: str,
                 monitoring_interval_seconds: float = 2.0,
                 blacklist_duration_hours: int = 24,
                 emergency_cooldown_minutes: int = 5):
        
        self.api_key = api_key
        self.private_key = private_key
        self.my_address = my_address.lower()
        self.monitoring_interval = monitoring_interval_seconds
        self.blacklist_duration_hours = blacklist_duration_hours
        self.emergency_cooldown_minutes = emergency_cooldown_minutes
        
        # 状态追踪
        self.last_known_nonce = 0
        self.cancel_history: List[dict] = []
        self.suspicious_addresses: Dict[str, SuspiciousPattern] = {}
        
        # 防御措施
        self.active_defenses: Set[str] = set()
        self.blacklist_expiry: Dict[str, datetime] = {}
        
        # 当前运行状态
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.is_emergency_pause = False
        self.pause_reason: Optional[str] = None
        
        # 配置
        self.gas_price_threshold_multiplier = 1.2  # Gas 价格上涨 20% 触发警报
        self.nonce_jump_threshold = 1              # 任何跳跃都触发
        self.cancel_frequency_threshold = 10       # 10 秒内多次撤单算异常
        
        logger.info(f"🛡️ OrderAttackDefender initialized for {self.my_address}")
        logger.info(f"   Monitoring interval: {monitoring_interval_seconds}s")
        logger.info(f"   Blacklist duration: {blacklist_duration_hours}h")
        logger.info(f"   Emergency cooldown: {emergency_cooldown_minutes}m")
    
    async def start_monitoring(self):
        """启动实时攻击检测"""
        if self.is_monitoring:
            logger.warning("Monitoring already active")
            return
        
        self.is_monitoring = True
        logger.info("🚀 Starting order attack monitoring...")
        
        try:
            while self.is_monitoring:
                try:
                    await self.check_for_attacks()
                    await asyncio.sleep(self.monitoring_interval)
                except Exception as e:
                    logger.error(f"Monitor cycle error: {e}")
                    await asyncio.sleep(5)  # 失败时退避
        finally:
            self.is_monitoring = False
            logger.info("⏹️ Order attack monitoring stopped")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            self.monitor_task = None
    
    async def check_for_attacks(self):
        """检查近期交易中的可疑模式"""
        
        if self.is_emergency_pause:
            # 紧急模式下跳过检测，减少负担
            return
        
        try:
            # 第 1 步：检查 Nonce 跳跃
            await self._check_nonce_jumps()
            
            # 第 2 步：分析撤单模式
            await self._analyze_cancellation_patterns()
            
            # 第 3 步：检查 Gas 战争迹象
            await self._check_gas_wars()
            
            # 第 4 步：验证挂单实际执行
            await self._verify_pending_orders_on_chain()
            
        except Exception as e:
            logger.error(f"Attack check failed: {e}")
    
    async def _check_nonce_jumps(self):
        """检测 Nonce 跳跃攻击"""
        try:
            current_nonce = await self._get_current_nonce()
            
            if current_nonce > self.last_known_nonce + self.nonce_jump_threshold:
                nonce_jump = current_nonce - self.last_known_nonce
                
                logger.warning(f"🚨 NONCE JUMP DETECTED: +{nonce_jump}")
                logger.warning(f"   Last nonce: {self.last_known_nonce}")
                logger.warning(f"   Current nonce: {current_nonce}")
                logger.warning("   Possible front-running attempt!")
                
                # 触发防御协议
                await self._trigger_emergency_defense(
                    reason="nonce_jump",
                    details=f"Nonce jump of {nonce_jump}"
                )
            
            # 更新已知 nonce (允许+1 的正常递增)
            if current_nonce == self.last_known_nonce + 1:
                self.last_known_nonce = current_nonce
            
        except Exception as e:
            logger.error(f"Failed to check nonce jumps: {e}")
    
    async def _analyze_cancellation_patterns(self):
        """分析撤单模式以识别垃圾攻击"""
        try:
            recent_cancels = await self._get_recent_cancellations(limit=50)
            
            now = datetime.utcnow()
            
            # 分组统计每个地址的撤单频率
            cancel_frequencies: Dict[str, List[datetime]] = {}
            
            for cancel_tx in recent_cancels:
                if cancel_tx['from'] == self.my_address:
                    continue  # 跳过自己的撤单
                
                from_addr = cancel_tx['from'].lower()
                
                if from_addr not in cancel_frequencies:
                    cancel_frequencies[from_addr] = []
                
                cancel_frequencies[from_addr].append(cancel_tx['timestamp'])
            
            # 检测高频撤单地址
            for addr, timestamps in cancel_frequencies.items():
                # 过滤掉超过 1 分钟的旧数据
                recent_timestamps = [ts for ts in timestamps 
                                   if now - ts < timedelta(minutes=1)]
                
                if len(recent_timestamps) >= self.cancel_frequency_threshold:
                    logger.warning(f"🔄 HIGH FREQUENCY CANCEL DETECTED: {addr}")
                    logger.warning(f"   Cancel count in 1min: {len(recent_timestamps)}")
                    
                    await self._record_suspicious_activity(
                        address=addr,
                        pattern_type=AttackType.SPAM_CANCEL,
                        severity=RiskLevel.MEDIUM
                    )
            
        except Exception as e:
            logger.error(f"Failed to analyze cancellation patterns: {e}")
    
    async def _check_gas_wars(self):
        """检测 Gas 战争攻击"""
        try:
            current_gas_price = await self._get_current_gas_price()
            
            # 获取最近交易的 Gas 价格分布
            recent_txs = await self._get_recent_transactions(limit=20)
            
            high_gas_txs = [tx for tx in recent_txs 
                           if tx.get('gas_price', 0) > current_gas_price * self.gas_price_threshold_multiplier]
            
            if len(high_gas_txs) > 3:  # 多笔高 Gas 交易
                logger.warning(f"⚡ POTENTIAL GAS WAR: {len(high_gas_txs)} high-gas transactions")
                
                # 记录可疑活动
                for tx in high_gas_txs[:5]:  # 只看前 5 个
                    await self._record_suspicious_activity(
                        address=tx['from'],
                        pattern_type=AttackType.GAS_WAR,
                        severity=RiskLevel.HIGH
                    )
            
        except Exception as e:
            logger.error(f"Failed to check gas wars: {e}")
    
    async def _verify_pending_orders_on_chain(self):
        """验证挂单是否在链上实际执行"""
        try:
            pending_orders = await self._get_pending_orders()
            
            verified_count = 0
            failed_count = 0
            
            for order in pending_orders:
                is_verified = await self._verify_order_on_chain(order['order_id'])
                
                if is_verified:
                    verified_count += 1
                else:
                    failed_count += 1
                    logger.error(f"❌ Order {order['order_id']} NOT verified on-chain!")
                    logger.error(f"   API reported: {order['api_status']}")
                    logger.error(f"   Chain shows: PENDING")
                    
                    # 如果连续失败增多，可能是攻击迹象
                    if failed_count >= 3:
                        await self._trigger_emergency_defense(
                            reason="verification_failure",
                            details=f"{failed_count} orders failed chain verification"
                        )
            
            if pending_orders:
                logger.info(f"🔗 Chain verification: {verified_count}/{len(pending_orders)} orders verified")
            
        except Exception as e:
            logger.error(f"Failed to verify orders on-chain: {e}")
    
    async def _record_suspicious_activity(self, 
                                         address: str,
                                         pattern_type: AttackType,
                                         severity: RiskLevel):
        """记录可疑活动到黑名单"""
        
        address_lower = address.lower()
        now = datetime.utcnow()
        
        if address_lower not in self.suspicious_addresses:
            # 新威胁
            self.suspicious_addresses[address_lower] = SuspiciousPattern(
                attacker_address=address_lower,
                pattern_type=pattern_type,
                first_seen=now,
                last_seen=now,
                total_attacks=1,
                estimated_damage_usd=0.0,
                confidence_score=0.5,
                blacklisted_until=now + timedelta(hours=self.blacklist_duration_hours)
            )
            
            logger.warning(f"🚫 NEW ATTACKER ADDED TO BLACKLIST: {address}")
            logger.warning(f"   Type: {pattern_type.value}")
            logger.warning(f"   Severity: {severity.value}")
            logger.warning(f"   Expires: {self.suspicious_addresses[address_lower].blacklisted_until}")
            
        else:
            # 更新现有威胁
            pattern = self.suspicious_addresses[address_lower]
            pattern.total_attacks += 1
            pattern.last_seen = now
            
            # 根据 severity 升级模式类型
            if severity == RiskLevel.HIGH or severity == RiskLevel.CRITICAL:
                pattern.pattern_type = max(pattern.pattern_type, AttackType.GAS_WAR, key=lambda x: x.value)
                pattern.confidence_score = min(1.0, pattern.confidence_score + 0.2)
            
            # 延长过期时间
            pattern.blacklisted_until = now + timedelta(hours=self.blacklist_duration_hours)
        
        # 发送到 Telegram 告警 (如果有)
        await self._send_telegram_alert(address, pattern_type, severity)
    
    async def _send_telegram_alert(self, address: str, pattern_type: AttackType, severity: RiskLevel):
        """发送 Telegram 告警"""
        
        alert_message = f"""
🛡️ ORDER ATTACK ALERT

Time: {datetime.utcnow().isoformat()}
Threat Address: {address}
Attack Type: {pattern_type.value}
Severity: {severity.value.upper()}
Total Attacks: {self.suspicious_addresses[address.lower()].total_attacks if address.lower() in self.suspicious_addresses else "?"}

Status: ADDRESS BLACKLISTED until {datetime.utcnow().replace(hour=datetime.utcnow().hour+self.blacklist_duration_hours).isoformat() if address.lower() in self.suspicious_addresses and self.suspicious_addresses[address.lower()].blacklisted_until else '?'}
"""
        
        # TODO: Implement actual Telegram integration
        # await telegram_sender.send_alert(alert_message)
        logger.warning(alert_message)
    
    async def _trigger_emergency_defense(self, reason: str, details: str):
        """触发紧急防御协议"""
        
        if self.is_emergency_pause:
            logger.info(f"Emergency mode already active: {self.pause_reason}")
            return
        
        logger.critical("🚨 EMERGENCY DEFENSE ACTIVATED! 🚨")
        logger.critical(f"Reason: {reason}")
        logger.critical(f"Details: {details}")
        
        # 标记紧急状态
        self.is_emergency_pause = True
        self.pause_reason = f"{reason}: {details}"
        
        # Action 1: 暂停所有交易
        await self._pause_all_trading(reason=reason)
        
        # Action 2: 取消所有挂单
        await self._cancel_all_positions()
        
        # Action 3: 通知管理员
        await self._notify_admin_emergency()
        
        # Action 4: 等待冷却期后谨慎恢复
        logger.info(f"Waiting {self.emergency_cooldown_minutes} minutes before resume...")
        
        # 在后台任务中等待并尝试恢复
        asyncio.create_task(self._wait_and_resume())
    
    async def _wait_and_resume(self):
        """等待冷却期后尝试恢复"""
        try:
            await asyncio.sleep(self.emergency_cooldown_minutes * 60)
            
            logger.info("🔄 Attempting to resume trading after emergency...")
            
            # 检查威胁环境是否缓解
            threat_level = len(self.suspicious_addresses)
            
            if threat_level <= 3:  # 威胁减少到安全水平
                await self._resume_trading(mode="conservative")
                logger.info("✅ Trading resumed with conservative settings")
            else:
                logger.warning(f"⚠️ Threat level still high ({threat_level} attackers)")
                logger.warning("Manual intervention required before resuming")
                # 保持暂停直到人工确认
                
        except Exception as e:
            logger.error(f"Error during resume: {e}")
    
    async def _pause_all_trading(self, reason: str):
        """暂停所有交易"""
        try:
            # Signal to main trading loop
            pause_signal = {
                'action': 'PAUSE_TRADING',
                'reason': reason,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # TODO: Send to main trading controller
            # await self.trading_controller.receive_control_signal(pause_signal)
            
            logger.warning(f"Trading PAUSED: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to pause trading: {e}")
    
    async def _cancel_all_positions(self):
        """取消所有挂单"""
        try:
            active_orders = await self._get_all_open_orders()
            
            cancelled_count = 0
            
            for order in active_orders:
                success = await self._safe_cancel_order(order['order_id'])
                if success:
                    cancelled_count += 1
            
            logger.info(f"✅ Cancelled {cancelled_count}/{len(active_orders)} positions during emergency")
            
        except Exception as e:
            logger.error(f"Failed to cancel positions: {e}")
    
    async def _safe_cancel_order(self, order_id: str) -> bool:
        """安全地取消单个订单"""
        try:
            # 使用较高的 Gas priority 确保快速包含
            result = await self._execute_cancel_order(
                order_id=order_id,
                gas_priority='high'
            )
            
            return result.get('success', False)
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def _notify_admin_emergency(self):
        """通知管理员紧急情况"""
        
        alert_message = f"""
🚨 URGENT: EMERGENCY DEFENSE PROTOCOL ACTIVE

System Time: {datetime.utcnow().isoformat()}
Trigger Reason: {self.pause_reason}

Actions Taken:
✓ All trading paused
✓ Positions being cancelled
✓ Known attackers blacklisted

Current Threat Status:
• Active threats: {len(self.suspicious_addresses)}
• Emergency cooldown: {self.emergency_cooldown_minutes} minutes

Next Steps:
• System will auto-resume in {self.emergency_cooldown_minutes} mins if threat level decreases
• Otherwise, manual confirmation required via Telegram command
• Check full incident log: /workspace/projects/polymaster-btc-bot/emergency_logs/

DO NOT IGNORE THIS ALERT unless you've manually verified safety.
"""
        
        # TODO: Implement Telegram admin notification
        logger.critical(alert_message)
    
    async def _resume_trading(self, mode: str = "conservative"):
        """谨慎恢复交易"""
        
        self.is_emergency_pause = False
        self.pause_reason = None
        
        status_msg = f"Trading resumed in {mode} mode"
        logger.info(f"✅ {status_msg}")
        
        # Signal to main trading loop
        resume_signal = {
            'action': 'RESUME_TRADING',
            'mode': mode,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # TODO: Send to main trading controller
        # await self.trading_controller.receive_control_signal(resume_signal)
    
    # ===== 辅助函数 (需要与你的 API 集成) =====
    
    async def _get_current_nonce(self) -> int:
        """获取当前账户 nonce"""
        # TODO: Replace with actual API call
        # example: result = await polymarket_api.get_nonce(self.my_address)
        # return result['nonce']
        
        logger.debug("Getting current nonce (mock)...")
        return self.last_known_nonce + 1
    
    async def _get_recent_cancellations(self, limit: int = 50) -> List[dict]:
        """获取最近的撤单交易"""
        # TODO: Replace with actual blockchain query
        # Use Polygon RPC to query recent transactions involving your address
        
        # Mock implementation for testing
        return []
    
    async def _get_current_gas_price(self) -> float:
        """获取当前 Gas 价格 (Gwei)"""
        # TODO: Replace with actual API call
        # example: result = await polygon_rpc.get_gas_price()
        # return result['standard']
        
        logger.debug("Getting current gas price (mock)...")
        return 30.0  # 30 Gwei typical
    
    async def _get_recent_transactions(self, limit: int = 20) -> List[dict]:
        """获取最近的交易"""
        # TODO: Query blockchain for recent transactions
        return []
    
    async def _get_pending_orders(self) -> List[dict]:
        """获取待处理的挂单"""
        # TODO: Query open orders from exchange
        return []
    
    async def _verify_order_on_chain(self, order_id: str) -> bool:
        """验证订单是否在链上实际执行"""
        # TODO: Query blockchain contract state
        # Example: state = await polygon_rpc.query_contract('getOrderState', [order_id])
        # return state['status'] == 'FILLED'
        
        logger.debug(f"Verifying order {order_id} on-chain (mock)...")
        return True  # Mock success
    
    async def _get_all_open_orders(self) -> List[dict]:
        """获取所有未完成的订单"""
        # TODO: Query open orders
        return []
    
    async def _execute_cancel_order(self, order_id: str, gas_priority: str = 'normal') -> dict:
        """执行订单取消"""
        # TODO: Submit cancel transaction with appropriate gas priority
        return {'success': True}
    
    def get_status(self) -> DefenseStatus:
        """获取当前防御状态"""
        return DefenseStatus(
            active=self.is_monitoring,
            current_mode="EMERGENCY" if self.is_emergency_pause else "ACTIVE",
            known_threats_count=len(self.suspicious_addresses),
            last_attack_detected=max(
                [p.last_seen for p in self.suspicious_addresses.values()],
                default=None
            ),
            emergency_active=self.is_emergency_pause,
            paused_reason=self.pause_reason
        )
    
    def should_block_address(self, address: str) -> bool:
        """检查地址是否在黑名单中"""
        address_lower = address.lower()
        
        if address_lower not in self.suspicious_addresses:
            return False
        
        pattern = self.suspicious_addresses[address_lower]
        
        if datetime.utcnow() > pattern.blacklisted_until:
            # 过期移除
            del self.suspicious_addresses[address_lower]
            return False
        
        return True
    
    def get_blacklist_summary(self) -> dict:
        """获取黑名单摘要"""
        return {
            'total_threats': len(self.suspicious_addresses),
            'threat_types': {
                pt.value: sum(1 for p in self.suspicious_addresses.values() if p.pattern_type == pt)
                for pt in AttackType
            },
            'high_confidence_threats': sum(
                1 for p in self.suspicious_addresses.values() 
                if p.confidence_score >= 0.8
            ),
            'threats_by_severity': self._categorize_by_severity()
        }
    
    def _categorize_by_severity(self) -> Dict[str, int]:
        """按严重性分类威胁"""
        severity_counts = {'HIGH': 0, 'CRITICAL': 0, 'MEDIUM': 0, 'LOW': 0}
        
        for pattern in self.suspicious_addresses.values():
            if pattern.confidence_score >= 0.9:
                severity_counts['CRITICAL'] += 1
            elif pattern.confidence_score >= 0.8:
                severity_counts['HIGH'] += 1
            elif pattern.confidence_score >= 0.6:
                severity_counts['MEDIUM'] += 1
            else:
                severity_counts['LOW'] += 1
        
        return severity_counts


# ===== 测试入口点 =====
if __name__ == "__main__":
    # 简单的测试运行
    import os
    
    # 从环境变量或默认值获取配置
    MY_ADDRESS = os.getenv('POLYMARKET_WALLET_ADDRESS', '0x1234567890abcdef1234567890abcdef12345678')
    API_KEY = os.getenv('POLYMARKET_API_KEY', 'test-api-key')
    PRIVATE_KEY = os.getenv('PRIVATE_KEY', 'test-private-key')
    
    print("=" * 80)
    print("🛡️ ORDER ATTACK DEFENDER - TEST RUN")
    print("=" * 80)
    print(f"My Address: {MY_ADDRESS}")
    print(f"API Key: {API_KEY[:10]}...")
    print("=" * 80)
    
    # 初始化防御器
    defender = OrderAttackDefender(
        api_key=API_KEY,
        private_key=PRIVATE_KEY,
        my_address=MY_ADDRESS,
        monitoring_interval_seconds=2.0,
        blacklist_duration_hours=24,
        emergency_cooldown_minutes=5
    )
    
    print("\n📊 Initial Status:")
    status = defender.get_status()
    print(json.dumps(status.to_dict(), indent=2))
    
    print("\n💡 Next steps:")
    print("1. Review code and integrate with your trading loop")
    print("2. Add real API calls for _get_XXX functions")
    print("3. Deploy with --simulate-only flag first")
    print("4. Monitor Telegram alerts for attack detection")
    
    print("\n" + "=" * 80)
