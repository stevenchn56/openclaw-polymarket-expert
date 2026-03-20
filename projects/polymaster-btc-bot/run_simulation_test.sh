#!/bin/bash
# MEV Protection Simulation Test Script

cd /Users/stevenwang/.openclaw/workspace/projects/polymaster-btc-bot

echo "========================================================================"
echo "🧪 MEV PROTECTION SIMULATION TEST"
echo "========================================================================"
echo ""
echo "Environment:"
echo "  - SIMULATION_MODE=true (No real trades)"
echo "  - ENABLE_MEV_PROTECTION=true"
echo "  - Trades limited: 3"
echo ""
echo "This will test:"
echo "  ✅ Defender initialization"
echo "  ✅ Background monitoring start"
echo "  ✅ Protected order submission wrapper"
echo "  ✅ Trading loop enhancement"
echo ""
echo "Expected output should show:"
echo "  🛡️ INITIALIZING ORDER ATTACK DEFENDER"
echo "  ✅ Defender initialized for..."
echo "  🚀 Order attack monitoring started"
echo ""

export SIMULATION_MODE=true
export ENABLE_MEV_PROTECTION=true
export TRADING_CAPITAL="5"

# Run with timeout to prevent hanging
timeout 60 python main.py --simulate-only --trades=3 2>&1 | tee /tmp/mev_sim_test.log

echo ""
echo "========================================================================"
echo "✅ Simulation test completed!"
echo "========================================================================"
echo ""
echo "Results saved to: /tmp/mev_sim_test.log"
echo ""
echo "Next steps:"
echo "  If OK → Review log, then deploy small live trades tomorrow"
echo "  If ERROR → Check /tmp/mev_sim_test.log and report error"
echo ""
