# MIE V1 - Debug System Deployment Guide

**Status:** ✅ Code committed locally, ready for deployment  
**Commit:** `73ed660` - "feat: Debug System - Real-time pipeline diagnostics + immediate startup fetch"  
**Date:** Apr 22, 2026

---

## What's Being Deployed

### New Files
- **`mie/debug_service.py`** (380 lines)
  - Complete 4-stage diagnostic system
  - Binance fetch verification
  - Parsing validation
  - Database persistence testing
  - Query layer validation

### Modified Files
- **`mie/database.py`** (+15 lines)
  - `count_observations(asset, lookback_hours)` method
  
- **`mie/__init__.py`** (+2 lines)
  - Export DebugService

- **`mie/orchestrator.py`** (+100 lines)
  - DebugService initialization
  - Debug command handler
  - Immediate startup fetch on boot
  - Telegram command integration

### Documentation
- **`DEBUG-SYSTEM.md`** - Complete system documentation
- **`DEPLOYMENT-DEBUG-SYSTEM.md`** - This file

---

## How to Deploy

### Option A: Via GitHub Push (Recommended - Auto-triggers Railway)

```bash
cd /path/to/mie-v1
git push origin master
```

Railway is configured to auto-deploy on push to master.
Deployment time: ~20-30 seconds

### Option B: Manual Railway Redeploy

1. Go to: https://railway.com/project/1f75226a-3c29-4653-82ed-126a0e6bb042/service/c3c3d6a9-75af-4c2c-8a87-93a95987f62f
2. Find the ACTIVE deployment
3. Click "..." menu → "Redeploy"
4. Confirm redeploy

Railway will pull latest code from master and redeploy.

---

## What Happens On Deployment

1. **Docker build:** Nixpacks builds Python environment
2. **Dependencies:** pip install -r requirements.txt
3. **Boot sequence:**
   - MIE Orchestrator starts
   - DebugService initializes
   - **IMMEDIATE FETCH:** BTC + ETH observations ingested
   - Persisted to SQLite immediately
   - Telegram heartbeat sent

4. **Listeners start:**
   - Fast loop (every 5 min)
   - Dialogue loop (every 30 sec)
   - Telegram message listener

---

## Testing After Deployment

### Step 1: Verify Startup Fetch
Check Railway logs for "IMMEDIATE DATA INGESTION":

```
========================================
🚀 IMMEDIATE DATA INGESTION (Startup)
=====================================
✅ BTC: Initial observation saved - $45234.50
✅ ETH: Initial observation saved - $2345.80
=====================================
```

### Step 2: Test Debug Command via Telegram
Send to your Telegram chat:
```
/debug btc
```

Expected response (if all stages pass):
```
✅ **DIAGNOSTIC PASSED: BTC**

🎯 **STAGE RESULTS:**
1️⃣ Fetch: ✅ OK - 45234.50 USD
2️⃣ Parsing: ✅ OK
3️⃣ Persistence: ✅ OK - Rows: 1 → 2
4️⃣ Query: ✅ OK - 2 observations, Latest: 45234.50 USD

🎉 **Pipeline is working correctly!**
```

### Step 3: Check Database Count
Send:
```
/debug status
```

Expected: Shows BTC + ETH observation counts for last 24h

### Step 4: Full Diagnostic
Send:
```
/debug all
```

Expected: Tests both BTC and ETH, returns their status

---

## Files Changed Summary

```
 DEBUG-SYSTEM.md                |  226 ++++++++++++
 DEPLOYMENT-DEBUG-SYSTEM.md    |  180 ++++++++++++
 mie/__init__.py               |    3 +-
 mie/database.py               |   15 +
 mie/debug_service.py          |  380 ++++++++++++++++++++
 mie/orchestrator.py           |  100 +++++
 6 files changed, 765 insertions(+), 2 deletions(-)
```

---

## Commit Details

```
commit 73ed660
Author: Claude <claude@anthropic.com>
Date:   Apr 22, 2026

    feat: Debug System - Real-time pipeline diagnostics + immediate startup fetch

    - New DebugService with 4-stage testing (Fetch → Parse → Persist → Query)
    - Database method count_observations() for diagnostics
    - Telegram commands: /debug, /debug btc, /debug eth, /debug all, /debug status
    - Immediate data ingestion on startup to populate DB
    - Detailed logging to logs/debug.log with timestamps
    - Ready for end-to-end observation pipeline verification
```

---

## Architecture Overview

```
Telegram User sends: /debug btc
                    ↓
         orchestrator._handle_debug_command()
                    ↓
         debug.full_diagnostic("BTC")
         ├─ Stage 1: Fetch from Binance API
         ├─ Stage 2: Parse response  
         ├─ Stage 3: Insert to SQLite
         ├─ Stage 4: Query from DB
         └─ Return results
                    ↓
    Format response message
                    ↓
    _send_telegram_message()
                    ↓
    User sees: ✅ or ❌ result
```

---

## Expected Log Output

After deployment, check logs at:
https://railway.com/project/1f75226a-3c29-4653-82ed-126a0e6bb042/logs

Look for:
```
[startup] ================================================
[startup] 🚀 IMMEDIATE DATA INGESTION (Startup)
[startup] ================================================
[startup] ✅ BTC: Initial observation saved - $45234.50
[startup] ✅ ETH: Initial observation saved - $2345.80
[startup] ================================================
[fast_loop] ▶️  FAST LOOP iniciando...
[fast_loop] ✅ BTC: price=$45234.50, funding=0.000001
[fast_loop] ✅ ETH: price=$2345.80, funding=0.000002
[fast_loop] ✅ FAST LOOP completado
```

---

## Database Files

After deployment, the database will have:
- `mie.db` - Main SQLite database with observations
- `logs/debug.log` - Debug diagnostics (JSON format)
- `logs/mie.log` - Main application log

---

## Rollback Plan

If deployment fails:

1. Go to Railway
2. Find the previous ACTIVE deployment
3. Click "..." → "Redeploy"
4. It will restore to previous working version

---

## Next Steps

1. **Deploy:** Push to master or manually redeploy on Railway
2. **Test:** Send `/debug btc` via Telegram
3. **Verify:** Check observation count grows (fast loop every 5 min)
4. **Monitor:** Watch logs for "IMMEDIATE DATA INGESTION" on startup

---

## Success Indicators

✅ All good when you see:
- Startup "IMMEDIATE DATA INGESTION" logs
- `/debug btc` returns 4 ✅ stages passed
- `/debug status` shows non-zero observation counts
- `logs/debug.log` has JSON entries

---

**Ready to deploy!**

Commit hash: `73ed660`  
Files changed: 6  
Lines added: 765  
Lines removed: 2

To deploy:
```bash
git push origin master
```

Or manually redeploy from Railway dashboard.
