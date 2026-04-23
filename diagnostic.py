#!/usr/bin/env python3
"""
Diagnostic script to verify Railway deployment state.
Run this to check:
1. Code version (marker)
2. fast_loop execution
3. Binance fetch status
4. DB persistence status
"""

import sys
import os
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from mie.database import MIEDatabase
from mie.binance_client import BinanceClient
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

print("\n" + "="*70)
print("🔍 MIE V1 RAILWAY DIAGNOSTIC")
print("="*70)

# 1. CHECK CODE VERSION
print("\n1️⃣  CODE VERSION CHECK")
print("-" * 70)
try:
    with open('mie/main.py', 'r') as f:
        content = f.read()
        if 'VERSION:20260422-BINANCE-FIX' in content:
            print("✅ VERSION MARKER FOUND: VERSION:20260422-BINANCE-FIX")
            print("   → Code contains new Binance fix")
        else:
            print("❌ VERSION MARKER NOT FOUND")
            print("   → Railway is running OLD code (before bf392f6)")
except Exception as e:
    print(f"❌ Error reading main.py: {e}")

# 2. CHECK BINANCE FETCH
print("\n2️⃣  BINANCE API FETCH TEST")
print("-" * 70)
try:
    binance = BinanceClient(logger=logger)

    for symbol in ["BTCUSDT", "ETHUSDT"]:
        print(f"\n  Testing {symbol}:")
        try:
            ticker = binance.get_ticker(symbol)
            if ticker:
                price = ticker.get("price", 0)
                print(f"    ✅ Fetched: ${price:.2f}")
                if price == 0:
                    print(f"    ⚠️  WARNING: Price is $0 - indicates fallback provider or parse error")
            else:
                print(f"    ❌ Returned None")
        except Exception as e:
            print(f"    ❌ Error: {str(e)[:80]}")

except Exception as e:
    print(f"❌ BinanceClient init error: {e}")

# 3. CHECK DATABASE STATE
print("\n3️⃣  DATABASE STATE CHECK")
print("-" * 70)
try:
    db = MIEDatabase("mie.db")

    for asset in ["BTC", "ETH"]:
        obs_recent = db.get_observations(asset=asset, lookback_hours=1, observation_type="price")
        obs_all = db.get_observation_count(asset=asset)

        print(f"\n  {asset}:")
        print(f"    Total observations: {obs_all}")
        print(f"    Recent (< 1 hour): {len(obs_recent) if obs_recent else 0}")

        if obs_all == 0:
            print(f"    ❌ No observations at all - fast_loop never ran OR persistance failed")
        elif obs_recent and len(obs_recent) > 0:
            latest = obs_recent[-1]
            price = latest.get('value', 0)
            timestamp = latest.get('timestamp', 'unknown')
            print(f"    ✅ Latest: ${price:.2f} @ {timestamp}")
            if price == 0:
                print(f"    ⚠️  Price is $0 - Binance fetch failed, used fallback")
        else:
            print(f"    ⚠️  Data exists ({obs_all} total) but ALL older than 1h")
            print(f"       → fast_loop is NOT running regularly")

    db.close()

except Exception as e:
    print(f"❌ Database error: {e}")

# 4. DIAGNOSIS
print("\n4️⃣  DIAGNOSIS")
print("-" * 70)

try:
    db = MIEDatabase("mie.db")
    btc_recent = db.get_observations(asset="BTC", lookback_hours=1, observation_type="price")
    btc_all = db.get_observation_count(asset="BTC")

    with open('mie/main.py', 'r') as f:
        has_marker = 'VERSION:20260422-BINANCE-FIX' in f.read()

    if not has_marker:
        print("\n⚠️  DIAGNOSIS: OPTION A")
        print("    Railway is running OLD code (before bf392f6)")
        print("    ACTION: Force Railway redeploy")
    elif btc_all == 0:
        print("\n⚠️  DIAGNOSIS: OPTION B")
        print("    fast_loop is NOT running at all")
        print("    ACTION: Check Railway scheduler / cron config")
    elif not btc_recent:
        print("\n⚠️  DIAGNOSIS: OPTION B (variant)")
        print("    fast_loop ran in past but hasn't run in last hour")
        print("    ACTION: Check if fast_loop is scheduled correctly")
    else:
        print("\n⚠️  DIAGNOSIS: CHECK PRICES")
        if btc_recent and btc_recent[-1].get('value', 0) == 0:
            print("    OPTION C: Binance fetch fails, fallback to $0")
        else:
            print("    ✅ Everything looks OK - check Telegram token for duplicate issue")

    db.close()

except Exception as e:
    print(f"❌ Diagnosis error: {e}")

print("\n" + "="*70)
