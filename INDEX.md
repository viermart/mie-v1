# MIE V1 - índice de documentación

## Primeros pasos

**Para empezar ahora**:
1. Lee: [README.md](README.md) (5 min)
2. Setup: `bash setup_local.sh`
3. Ejecuta: `python main.py`
4. Testing: [TESTING.md](TESTING.md)

## Documentación

| Archivo | Propósito | Lectores |
|---------|-----------|----------|
| [README.md](README.md) | Visión general, setup, scope V1 | Todos |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Diseño técnico, decisiones, flujos | Desarrolladores |
| [TESTING.md](TESTING.md) | Cómo probar MIE sin riesgo | Testers, Devs |
| [INDEX.md](INDEX.md) | Este archivo | Navegación |

## Estructura de código

```
mie-v1/
├── mie/
│   ├── __init__.py              # Package config
│   ├── database.py              # SQLite persistence
│   ├── binance_client.py        # Binance API integration
│   ├── research_layer.py        # Hypothesis generation + validation
│   ├── reporter.py              # Telegram reporting
│   └── orchestrator.py          # Loop coordinator
│
├── main.py                      # Entry point
├── test_database.py             # DB validation
├── setup_local.sh               # Automation
├── requirements.txt             # Dependencies
├── Procfile                     # Railway config
├── railway.json                 # Railway config
│
├── README.md                    # Guía principal
├── ARCHITECTURE.md              # Diseño técnico
├── TESTING.md                   # Testing guide
└── INDEX.md                     # Este archivo
```

## Flujo de ejecución

### Fast Loop (cada 5 min)
```
Binance API → ingest_observation() → observations (SQLite)
                                   ↓
                         check_hypothesis_triggers()
                                   ↓
                        mini-validate en histórico
                                   ↓
                        add_hypothesis() [si válido]
```

### Daily Loop (08:00 UTC)
```
observations (24h) → _reflect_on_observations()
                  ↓
         get_active_hypotheses()
                  ↓
          run_experiment() por c/u
                  ↓
        update_hypothesis() + results
                  ↓
        add_learning_log() + send_daily_report()
```

### Weekly Loop (domingo 08:00 UTC)
```
observations (7d) → _reflect_on_observations()
                 ↓
        hypothesis review + classification
                 ↓
        add_learning_log() + send_weekly_report()
```

## Quick reference

### Correr localmente
```bash
bash setup_local.sh
source venv/bin/activate
python main.py
```

### Ver logs en vivo
```bash
tail -f logs/mie.log
```

### Inspeccionar BD
```bash
sqlite3 mie.db
sqlite> SELECT * FROM observations LIMIT 5;
sqlite> SELECT * FROM hypotheses;
```

### Test manual (Python)
```python
from mie.orchestrator import MIEOrchestrator
orch = MIEOrchestrator()
orch.daily_loop()  # Ejecuta una vez
```

### Configurar Telegram (opcional)
Edita `.env`:
```
TELEGRAM_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=1234567890
```

### Deploy en Railway
```bash
railway login
railway init
railway variables add TELEGRAM_TOKEN=...
railway variables add TELEGRAM_CHAT_ID=...
railway up
```

## Decisiones de diseño clave

| Decisión | Razón | Tradeoff |
|----------|-------|----------|
| **SQLite** | Simplicidad en bootstrap | Escala limitada (V2 → PostgreSQL) |
| **3 loops** (no 5) | Minimize complexity | Menos reflexión (V1.1 + hourly) |
| **2+ observations trigger** | Evita ruido | Patrón debe repetirse |
| **7 día lookback** | Balance velocidad/evidencia | No detecta tendencias 30d |
| **No trades V1** | Bootstrap seguro | Reportes-only (V2 = alertas) |

## Roadmap

### V1.0 (ahora) ✅
- ✅ Observación: Binance BTC/ETH
- ✅ Hipótesis: Generación + mini-validation
- ✅ Research: Experimentos + clasificación
- ✅ Learning: Logs diarios/semanales
- ✅ Reporting: Telegram (opcional)

### V1.1 (próximo)
- [ ] Overfit detection: chi-squared test
- [ ] Diálogo: feedback del usuario
- [ ] Dashboard: web UI local
- [ ] Hourly loop: más reflexión

### V2 (post-bootstrap)
- [ ] Alertas reales basadas en hipótesis
- [ ] On-chain data
- [ ] ML classifier
- [ ] Multi-chain

## Contacto & debugging

**¿Preguntas?** Revisa [TESTING.md](TESTING.md) - "Preguntas frecuentes"

**¿Error de Binance API?** Logs en `mie.log` con detalles.

**¿Telegram no funciona?** Verifica `TELEGRAM_TOKEN` + `TELEGRAM_CHAT_ID` en `.env`.

---

**MIE V1 - Bootstrap Phase**
Observa. Reflexiona. Aprende. Sin trading. 🤖📊
