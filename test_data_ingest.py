#!/usr/bin/env python3
"""
Test data ingestion - Run fast_loop manually to see if Binance API works
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mie.database import MIEDatabase
from mie.binance_client import BinanceClient
from mie.orchestrator import MIEOrchestrator
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("TestIngest")

# Create orchestrator
db = MIEDatabase("mie.db")
binance = BinanceClient(logger=logger)
orchestrator = MIEOrchestrator(
    db_path="mie.db",
    telegram_token="dummy",
    telegram_chat_id="dummy"
)

print("\n" + "="*60)
print("🧪 TEST DATA INGESTION")
print("="*60)

# Run fast_loop ONE TIME
print("\n▶️  Ejecutando fast_loop manualmente...")
try:
    orchestrator.fast_loop()
    print("✅ fast_loop completado")
except Exception as e:
    print(f"❌ Error en fast_loop: {e}")
    import traceback
    traceback.print_exc()

# Check what got saved
print("\n📊 VERIFICANDO DATOS GUARDADOS:")

for asset in ["BTC", "ETH"]:
    obs = db.get_observations(asset=asset, lookback_hours=24, observation_type="price")
    print(f"\n{asset}:")
    if obs:
        for o in obs[-3:]:  # Show last 3
            print(f"  - ${o['value']:,.2f} @ {o['timestamp']} (source: {o['source']})")
    else:
        print(f"  ❌ Sin observaciones")

print("\n" + "="*60)
