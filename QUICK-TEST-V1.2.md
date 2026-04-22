# MIE V1.2 - Quick Test Guide 🧪

## Deploy (2 min)

```bash
cd mie-v1

# Option 1: Automatic
bash deploy-v1.2.sh

# Option 2: Manual
git add .
git commit -m "feat: MIE V1.2 - Dialogue"
git push
railway deploy
```

## Test Queries (Envía al bot por Telegram)

### Information Queries

```
1. "como ves el mercado"
   → 📊 Price, range, 24h change

2. "que observas"
   → 👀 Count by type & asset

3. "que aprendiste"
   → 📚 Learning logs

4. "hipotesis activas"
   → 🔬 Active hypotheses with status

5. "status"
   → ✅ Health check

6. "btc" o "eth"
   → 📈 Asset-specific stats
```

### Feedback Queries

```
7. "esto fue util"
   → ✅ Positive feedback saved

8. "esto fue ruido"
   → 📝 Negative feedback saved

9. "enfocate mas en btc"
   → 🎯 Focus priority changed

10. "menos intradia"
    → ⏱️ Timeframe preference saved
```

### Unknown

```
11. "hola" / "que tal" / "random text"
    → ❓ Shows help with examples
```

---

## Verify Response (< 30 seconds)

✅ MIE should respond via Telegram within **30 seconds** of your message

**If no response:**

```bash
# Check logs
tail -f logs/mie.log

# Look for:
grep "💬" logs/mie.log  # Message received
grep "✅ Respuesta" logs/mie.log  # Response sent
grep "ERROR" logs/mie.log  # Any errors
```

---

## Local Test (without Railway)

```bash
source venv/bin/activate
python main.py

# In another terminal:
tail -f logs/mie.log | grep "💬\|✅"
```

**Direct test:**

```python
from mie.dialogue import DialogueHandler, QueryType
from mie.database import MIEDatabase
import logging

db = MIEDatabase()
logger = logging.getLogger("test")
dialogue = DialogueHandler(db, logger)

# Test market overview
response = dialogue.handle_message("como ves el mercado", "test_user")
print(response)  # Should show 📊 or "Sin observaciones"

# Test feedback
response = dialogue.handle_message("esto fue util", "test_user")
print(response)  # Should show ✅
```

---

## Expected Responses

| Query | Expected Contains |
|-------|------------------|
| Market overview | `📊` or `Sin observaciones` |
| What watching | `👀` and `Total de observaciones` |
| What learned | `📚` and `DAILY\|WEEKLY` |
| Active hyp | `🔬` and `hypothesis_id` |
| Status | `✅` and `Assets monitorizados` |
| Asset query | `📈` and `USDT` |
| Positive FB | `✅` and `Feedback positivo` |
| Negative FB | `📝` and `Feedback negativo` |
| Focus FB | `🎯` and asset name |
| Timeframe FB | `⏱️` and `Preferencia` |
| Unknown | `❓` and list of examples |

---

## Troubleshooting

### No response from MIE

1. **Check deployment status**
   ```bash
   railway status
   ```

2. **Check service is running**
   ```bash
   railway logs
   ```
   Should see: `🚀 MIE V1 iniciando...`

3. **Verify Telegram credentials**
   ```bash
   railway variables list
   ```
   Should have:
   - `TELEGRAM_TOKEN=...`
   - `TELEGRAM_CHAT_ID=...`

4. **Check if messages are arriving**
   ```bash
   railway logs | grep "💬"
   ```

### Responses are empty

- DB might be empty (need 5+ minutes for observations)
- Try: `"status"` → should work even with no observations

### Classify error

- Add pattern to `mie/dialogue.py` `query_patterns` dict
- Or rephrase question to match existing patterns

---

## Files Changed for V1.2

```
NEW:
  ✅ mie/dialogue.py (350 lines)
  ✅ DIALOGUE-V1.2.md
  ✅ deploy-v1.2.sh
  ✅ MIE-V1.2-SUMMARY.md
  ✅ QUICK-TEST-V1.2.md (this)

MODIFIED:
  ✅ mie/orchestrator.py (+150 lines)
  ✅ mie/__init__.py (+1 line)
```

---

## Next Steps After Testing

✅ All working?
→ Congratulations! V1.2 is live

🔧 Minor issues?
→ Create task for fixes in V1.3

🚀 Ready for V1.3?
→ Plan feedback learning & memory context

---

**Ready? Send "como ves el mercado" to your bot now! 🚀**
