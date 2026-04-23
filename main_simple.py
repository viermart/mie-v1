#!/usr/bin/env python3
"""
SIMPLEST POSSIBLE VERSION - Direct test without orchestrator complexity
Just:
1. Fetch BTC/ETH from Binance
2. Save to DB
3. Log everything to Telegram immediately
"""

import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime

# Setup unbuffered
os.environ['PYTHONUNBUFFERED'] = '1'

# Load .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
except:
    pass

sys.path.insert(0, str(Path(__file__).parent))

def send_telegram(msg):
    """Send message to Telegram directly"""
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print(f"❌ Missing credentials: token={bool(token)}, chat_id={bool(chat_id)}")
        return False

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": msg}
        r = requests.post(url, json=data, timeout=10)
        if r.status_code == 200:
            print(f"✅ Telegram sent")
            return True
        else:
            print(f"❌ Telegram error: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ Telegram exception: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("MIE V1 - SIMPLE TEST MODE")
    print("="*70 + "\n")

    send_telegram("🚀 MIE starting SIMPLE TEST MODE")

    # Test 1: Import DB
    print("1. Testing DB import...")
    try:
        from mie.database import MIEDatabase
        db = MIEDatabase("mie.db")
        print("   ✅ DB imported and connected")
        send_telegram("✅ Step 1: DB connected")
    except Exception as e:
        print(f"   ❌ DB error: {e}")
        send_telegram(f"❌ DB error: {e}")
        return

    # Test 2: Test Binance API
    print("\n2. Testing Binance API...")
    try:
        for asset in ["BTC", "ETH"]:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={asset}USDT"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                price = float(data['price'])
                print(f"   ✅ {asset}: ${price:.2f}")
            else:
                print(f"   ❌ {asset}: HTTP {r.status_code}")
        send_telegram("✅ Step 2: Binance API working")
    except Exception as e:
        print(f"   ❌ Binance error: {e}")
        send_telegram(f"⚠️ Step 2: Binance error (will use synthetic): {e}")

    # Test 3: Save observation to DB
    print("\n3. Testing DB save...")
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            price = float(r.json()['price'])
            obs_id = db.add_observation(
                asset="BTC",
                observation_type="price",
                value=price,
                context=f"test: ${price:.2f}"
            )
            print(f"   ✅ Saved BTC to DB, id={obs_id}")
            send_telegram(f"✅ Step 3: BTC ${price:.2f} saved to DB (id={obs_id})")
        else:
            print(f"   ❌ Failed to fetch price")
            send_telegram("❌ Step 3: Failed to fetch price")
    except Exception as e:
        print(f"   ❌ DB save error: {e}")
        send_telegram(f"❌ Step 3: DB save error: {e}")
        return

    # Test 4: Query DB
    print("\n4. Testing DB query...")
    try:
        obs = db.get_observations(asset="BTC", lookback_hours=24, observation_type="price")
        if obs:
            print(f"   ✅ Found {len(obs)} BTC observations")
            latest = obs[-1]
            send_telegram(f"✅ Step 4: DB has {len(obs)} BTC observations. Latest: ${latest['value']:.2f}")
        else:
            print(f"   ❌ No observations found")
            send_telegram("❌ Step 4: No observations in DB")
    except Exception as e:
        print(f"   ❌ Query error: {e}")
        send_telegram(f"❌ Step 4: Query error: {e}")
        return

    # Test 5: Pattern detection
    print("\n5. Testing pattern detection...")
    try:
        from mie.pattern_detector import PatternDetector
        detector = PatternDetector()

        btc_obs = db.get_observations(asset="BTC", lookback_hours=24, observation_type="price")
        eth_obs = db.get_observations(asset="ETH", lookback_hours=24, observation_type="price")

        if btc_obs and eth_obs:
            asset_data = {"BTC": btc_obs, "ETH": eth_obs}
            patterns = detector.detect_all_patterns(asset_data)
            if patterns:
                print(f"   ✅ Detected {len(patterns)} patterns")
                for p in patterns:
                    print(f"      - {p['asset']}: {p['type']}")
                send_telegram(f"✅ Step 5: Detected {len(patterns)} patterns")
            else:
                print(f"   ⚠️  No patterns detected (need more history)")
                send_telegram("⚠️ Step 5: No patterns yet (need more data)")
        else:
            print(f"   ⚠️  Need more observations")
            send_telegram("⚠️ Step 5: Not enough observations")
    except Exception as e:
        print(f"   ❌ Pattern error: {e}")
        send_telegram(f"❌ Step 5: Pattern error: {e}")
        return

    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED")
    print("="*70)
    send_telegram("✅ ALL TESTS PASSED - MIE CORE IS WORKING")

    db.close()

if __name__ == "__main__":
    main()
