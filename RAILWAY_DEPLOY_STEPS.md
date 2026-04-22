# Railway Deployment - Step by Step

## RAILWAY SETUP (1 minuto)

### 1. Create Project (if new)
- Go to https://railway.app
- Click "New Project"
- Choose "GitHub Repo"
- Select your MIE V1 repository
- Click "Deploy"

### 2. Configure Environment Variables

In Railway Dashboard → Your Project → Variables:

```
TELEGRAM_TOKEN=<your_bot_token>
TELEGRAM_CHAT_ID=<your_chat_id>
```

**How to get these:**
- **TELEGRAM_TOKEN**: Talk to @BotFather on Telegram, create new bot → Copy token
- **TELEGRAM_CHAT_ID**: Send message to your bot, then:
  ```
  curl https://api.telegram.org/bot<TOKEN>/getUpdates
  ```
  Look for `"chat":{"id":123456789}` → That's your CHAT_ID

### 3. Deploy
- Once variables are set, Railway auto-deploys
- Check "Deployments" tab to verify success
- Look for green checkmark

---

## VERIFY DEPLOYMENT (5 minutos)

### 1. Check Logs
```
Railway Dashboard → Logs

Expected output:
✅ MIE Scheduler started
✅ Loops: fast (5m), daily (08:00 UTC), weekly (Sun 17:00 UTC), monthly (1st 00:00 UTC)
✅ Fast loop executing...
```

### 2. Test Bot in Telegram
Send `/start` to your bot → Expect response within 5 seconds

### 3. Check Daily Report
- Wait until **08:00 UTC** next day
- Should receive automated report in Telegram

### 4. Check Research Logs
SSH into Railway container:
```
railway shell

ls -la research_logs/
  hypothesis_registry.json    ← Should exist
  experiment_log.jsonl        ← Should have entries
  observations.jsonl          ← Should have entries
  investigation_queue.json    ← Should exist

ls -la data/
  hypotheses/                 ← Directory created
  metrics/                    ← Directory created
  backtests/                  ← Directory created
  mie.db                      ← SQLite database
```

---

## TROUBLESHOOTING

### Bot Not Responding
1. Check Environment Variables are SET (not empty)
2. Verify TELEGRAM_TOKEN is correct
3. Check logs for errors:
   ```
   ERROR: Missing TELEGRAM_TOKEN
   ERROR: Missing TELEGRAM_CHAT_ID
   ```

### Scheduler Not Running
1. Check logs for startup errors
2. Verify Python version: `python --version` (should be 3.10+)
3. Look for: `MIE Scheduler started` in logs

### Memory Issues (OOM)
1. Check Railway resource allocation
2. If using free tier, upgrade to paid plan
3. Expected memory: 100-150 MB after 1 hour

---

## CONTINUOUS MONITORING

### Daily Checks
- [ ] Bot responds to messages
- [ ] Daily report arrives at 08:00 UTC
- [ ] No error messages in logs

### Weekly Checks
- [ ] Weekly report arrives (Sunday 17:00 UTC)
- [ ] Hypothesis generation working
- [ ] Research layer active

### Monthly Checks
- [ ] Monthly report arrives (1st @ 00:00 UTC)
- [ ] System health good
- [ ] No data corruption

---

## SCALE UP (if needed)

If experiencing OOM errors:

1. Railway Dashboard → Project → Settings
2. Upgrade to paid plan (minimum 512 MB)
3. Or use "Builder" plan with 1GB allocation

Current usage: ~100-150 MB (safe margin within 512 MB)

---

## EXPECTED MESSAGES

### At Deploy Time
```
Building Docker image...
Running: python -m mie.main scheduler
✅ MIE Scheduler started
✅ Loops registered: fast, daily, weekly, monthly
✅ Research layer initialized
```

### Every 5 Minutes (Fast Loop)
```
Fast loop executing...
Scanning market signals...
Generating observations...
[No message sent - internal processing only]
```

### At 08:00 UTC (Daily Loop)
```
Daily loop executing...
Deep analysis started...
Generating hypotheses...
[Telegram message sent with daily report]
```

### Every Sunday 17:00 UTC (Weekly Loop)
```
Weekly loop executing...
Meta-thinking started...
Portfolio review...
[Telegram message sent with weekly report]
```

### 1st @ 00:00 UTC (Monthly Loop)
```
Monthly loop executing...
System review started...
Quarterly analysis...
[Telegram message sent with monthly report]
```

---

## FINAL CHECKLIST

Before considering deployment successful:

- [ ] Railway shows "Build successful"
- [ ] Logs show "MIE Scheduler started"
- [ ] Bot responds to /start in Telegram
- [ ] Daily report received (next day @ 08:00 UTC)
- [ ] research_logs/ directory created with files
- [ ] data/mie.db exists and has size > 0
- [ ] No persistent errors in logs

---

## SUPPORT

If issues arise:
1. Check BRAIN_SPEC_VERIFICATION.md for architecture details
2. Check READY_FOR_DEPLOY.md for troubleshooting guide
3. Review logs in Railway Dashboard
4. Check GitHub commits for recent changes

---

**Status**: ✅ READY FOR DEPLOYMENT
**Last Updated**: 2026-04-22
**Verified By**: Claude
