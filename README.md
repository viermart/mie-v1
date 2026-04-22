# MIE V1 - Market Intelligence Entity

Una entidad que observa, reflexiona, investiga y aprende del mercado de criptomonedas.

## Arquitectura

```
MIE V1 - Bootstrap Phase
├─ Fast Loop (5 min): Observa Binance (BTC, ETH)
├─ Daily Loop (08:00 UTC): Reflexión + Research
├─ Weekly Loop (Domingo): Meta-thinking
└─ Memory: SQLite + JSON runtime

Data:
├─ Source: Binance API
├─ Assets: BTCUSDT, ETHUSDT
├─ Fields: price, funding, OI, volume, timestamp

Outputs:
├─ Daily Report (Telegram)
├─ Weekly Report (Telegram)
├─ Error/Heartbeat (Telegram)
└─ No alertas de oportunidades todavía
```

## Setup Local

```bash
# 1. Clone + setup
git clone https://github.com/viermart/mie-v1.git
cd mie-v1
bash setup_local.sh

# 2. Edit .env (Telegram token optional)
nano .env
# TELEGRAM_TOKEN=your_token_here (leave empty for logs-only)
# TELEGRAM_CHAT_ID=your_chat_id_here

# 3. Run
source venv/bin/activate
python main.py
```

### Alternativa manual (sin script):
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## V1 Scope

✅ Observación pura
✅ Memoria persistente (SQLite)
✅ Hipótesis generadas
✅ Mini-validaciones en histórico
✅ Diálogo aprendiente
✅ Reporting diario/semanal

❌ No alertas reales
❌ No on-chain data
❌ No feeds externos
❌ No dashboards
❌ No ML
❌ No auto-promoción

## Estructura de código

```
mie-v1/
├── mie/
│   ├── __init__.py
│   ├── database.py          # SQLite persistence layer
│   ├── binance_client.py    # Binance API integration
│   ├── research_layer.py    # Hypothesis generation + validation
│   ├── reporter.py          # Telegram reporting
│   └── orchestrator.py       # Loop coordinator (fast/daily/weekly)
├── main.py                   # Entry point
├── test_database.py          # Database validation script
├── setup_local.sh            # Local setup automation
├── requirements.txt          # Dependencies
├── Procfile                  # Heroku/Railway config
├── railway.json              # Railway deployment config
└── README.md                 # This file
```

## Ciclos de ejecución

### Fast Loop (cada 5 minutos)
- Ingesta de observaciones (precio, funding rate, OI)
- Detección de triggers para nuevas hipótesis
- Persistencia en SQLite

### Daily Loop (08:00 UTC)
- Reflexión sobre observaciones de 24h
- Ejecución de experimentos en testing
- Generación de learning logs
- Envío de daily report (Telegram + logs)

### Weekly Loop (domingo 08:00 UTC)
- Meta-reflexión sobre la semana
- Revisión de hipótesis completadas
- Generación de weekly learning log
- Envío de weekly report

## Flujo de hipótesis

```
1. TRIGGER
   └─ 2+ observaciones del mismo tipo → propone hipótesis

2. MINI-VALIDATION
   └─ Verifica patrón en histórico (7 días)
   └─ Si es válido → añade a BD con status "awaiting_validation"

3. EXPERIMENT
   └─ Daily loop elige hipótesis en "testing"
   └─ Ejecuta validación contra datos históricos

4. CLASSIFICATION
   └─ Resultado: falsified | weakly_supported | supported | strongly_supported
   └─ Actualiza hipótesis con decisión final
```

## Testing local sin Telegram

Si no configuraste TELEGRAM_TOKEN, MIE escribirá todo en logs:
```bash
tail -f logs/mie.log
```

Los reportes diarios/semanales aparecerán en la salida estándar.

## Deployment en Railway

```bash
# 1. Instala Railway CLI
npm install -g @railway/cli

# 2. Inicia sesión
railway login

# 3. Crea proyecto
railway init

# 4. Añade variables de entorno
railway variables add TELEGRAM_TOKEN=your_token
railway variables add TELEGRAM_CHAT_ID=your_chat_id

# 5. Deploy
railway up
```

Railway usará Procfile + railway.json para correr: `python main.py`

## Status

Bootstrap phase: MIE está aprendiendo sin tomar decisiones de trading.
