#!/usr/bin/env python3
"""
Test Binance API response format
"""

import requests
import json

url = "https://api.binance.com/api/v3/ticker/24hr"
params = {"symbol": "BTCUSDT"}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

print("🔍 Fetching Binance ticker for BTCUSDT...")
response = requests.get(url, params=params, headers=headers, timeout=10)
response.raise_for_status()

data = response.json()

print("\n📊 BINANCE API RESPONSE FIELDS:")
for key in sorted(data.keys()):
    value = data[key]
    if isinstance(value, (int, float)):
        print(f"  {key}: {value}")
    else:
        print(f"  {key}: {str(value)[:50]}...")

print("\n🔍 Looking for volume fields:")
volume_fields = [k for k in data.keys() if 'volume' in k.lower() or 'vol' in k.lower()]
for field in volume_fields:
    print(f"  {field}: {data[field]}")

print("\n✅ Full response:")
print(json.dumps(data, indent=2)[:1000])
