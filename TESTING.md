# Testing MIE V1

## Safety first: MIE V1 NO EJECUTA TRADES

MIE V1 **observa**, **reflexiona** e **investiga** sin ejecutar nada en el mercado real. Es 100% seguro para testing.

## Configuración local (recomendado para bootstrap)

### 1. Setup sin Telegram

```bash
bash setup_local.sh
```

Deja `.env` vacío o sin `TELEGRAM_TOKEN`. Todos los reportes irán a logs:

```bash
tail -f logs/mie.log
```

### 2. Correr localmente

```bash
source venv/bin/activate
python main.py
```

Verás salida como:
```
2026-04-21 10:15:23 - MIE - INFO - 🚀 MIE V1 iniciando...
2026-04-21 10:15:23 - MIE - INFO -    Assets: ['BTC', 'ETH']
2026-04-21 10:15:23 - MIE - INFO -    DB: mie.db
2026-04-21 10:15:25 - MIE - INFO - ✅ Loops programados:
2026-04-21 10:15:25 - MIE - INFO -   - Fast: cada 5 minutos
2026-04-21 10:15:25 - MIE - INFO -   - Daily: 08:00 UTC
2026-04-21 10:15:25 - MIE - INFO -   - Weekly: domingo 08:00 UTC
```

### 3. Observar en vivo

MIE correrá silenciosamente. Cada 5 minutos ejecuta `fast_loop`:

```
2026-04-21 10:20:15 - MIE - INFO - ▶️  FAST LOOP iniciando...
2026-04-21 10:20:17 - MIE - INFO - ✅ BTC: price=$45234.50, funding=0.000123
2026-04-21 10:20:18 - MIE - INFO - ✅ ETH: price=$2345.30, funding=0.000089
2026-04-21 10:20:18 - MIE - INFO - ✅ FAST LOOP completado
```

### 4. Detener

```bash
Ctrl+C
```

## Inspeccionar base de datos

Mientras MIE corre (o después), inspecciona mie.db:

```bash
sqlite3 mie.db

sqlite> SELECT COUNT(*) FROM observations;
45

sqlite> SELECT * FROM hypotheses LIMIT 1;
hyp_BTC_price_spike_001|BTC mostró movimiento de +2.5%...|awaiting_validation

sqlite> SELECT * FROM learning_logs ORDER BY timestamp DESC LIMIT 1;
daily|2026-04-21T08:00:00...|{"observation_count": 45, ...}

sqlite> .quit
```

## Simular daily loop manualmente

Si quieres ver el daily loop SIN esperar a las 08:00 UTC:

```python
# En Python REPL
import sys
sys.path.insert(0, '/path/to/mie-v1')

from mie.orchestrator import MIEOrchestrator

orch = MIEOrchestrator()
orch.daily_loop()  # Ejecuta una vez
```

Verás:
```
🔄 DAILY LOOP iniciando...
📊 Resumen 24h: {'BTC': {'obs_count': 45, 'current_price': 45234.50, ...}}
🔬 Hipótesis activas: 2
📈 Experimento para hyp_BTC_price_spike_001: {'classification': 'supported', ...}
✅ DAILY LOOP completado
```

## Testing con Telegram (opcional)

Si querés reportes en Telegram:

### 1. Crea un bot en BotFather

En Telegram, busca `@BotFather`:
```
/start
/newbot
Nombre: "MIE Test"
Username: "mie_test_bot_XXXXXX"
```

BotFather te dará un token: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`

### 2. Obtén tu CHAT_ID

Envía cualquier mensaje al bot desde tu cuenta Telegram.

Luego:
```bash
curl https://api.telegram.org/bot<TOKEN>/getUpdates | grep chat_id
```

Encontrarás algo como `"chat_id": 1234567890`

### 3. Configura .env

```bash
cp .env.example .env
nano .env
```

```
TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=1234567890
```

### 4. Correr con Telegram

```bash
python main.py
```

Cada daily/weekly loop enviará mensajes a tu Telegram.

## Escenarios de test

### Escenario 1: Observar patrón de precio

**Tiempo real**: 5-10 minutos de ejecución

```bash
# Terminal 1: Correr MIE
python main.py

# Terminal 2: Inspeccionar logs en vivo
tail -f logs/mie.log | grep "price"
```

Esperarás ver:
```
✅ BTC: price=$45234.50, funding=0.000123
✅ ETH: price=$2345.30, funding=0.000089
```

### Escenario 2: Disparar hipótesis

**Cómo**: MIE dispara hipótesis cuando detecta 2+ observaciones del mismo tipo con patrón.

Ejemplo: Si BTC sube >2% en dos snapshots de 5 min:
```
TRIGGER: price_momentum
├─ Observación 1: $45000
├─ Observación 2: $45900 (+2%)
└─ GENERATE: "BTC mostró movimiento de +2.0%"
```

**Verás en logs**:
```
✅ Hipótesis generada: hyp_BTC_price_momentum_abc123
   Texto: BTC mostró movimiento de +2.0%
```

### Escenario 3: Ver experimento ejecutarse

**Timing**: Espera hasta las 08:00 UTC (o llama `daily_loop()` manualmente).

MIE ejecutará validación:
```
🔄 DAILY LOOP iniciando...
🔬 Hipótesis activas: 1
📈 Experimento para hyp_BTC_price_momentum_abc123:
   Classification: weakly_supported
   Support ratio: 0.65
```

## Datos de prueba: histórico real

MIE obtiene datos REALES de Binance API. No hay mock data.

```python
# binance_client.py
self.base_url = "https://api.binance.com/api/v3"  # REAL

# Cada call a ingest_observation() hace HTTP request
ticker = requests.get(...).json()  # REAL precio BTC/ETH ahora
```

**Esto significa**:
- ✅ Datos actualizados cada 5 min
- ✅ Hipótesis generadas de patrones reales
- ✅ Testing es sobre la realidad del mercado (no simulación)

## Debugging

### Si MIE no genera hipótesis

Posibles razones:
1. **No hay 2+ observaciones del mismo tipo** → espera 10 minutos
2. **Patrón no es repetible en histórico** → mini-validation rechaza
3. **Ya alcanzó max_active_hypotheses (5)** → completa algunos tests primero

Ver logs:
```bash
grep "Hipótesis" logs/mie.log
grep "mini-validation falló" logs/mie.log
```

### Si Telegram no funciona

```bash
# Test direct request
curl -X POST https://api.telegram.org/bot<TOKEN>/sendMessage \
  -d "chat_id=<CHAT_ID>&text=Test"
```

Si falla: verifica TELEGRAM_TOKEN y CHAT_ID en `.env`.

MIE continúa funcionando incluso sin Telegram (solo logs).

### Si Binance API da timeout

MIE maneja esto:
```python
except requests.RequestException as e:
    self.logger.error(f"Error ingesting {asset}: {e}")
    # Sigue al siguiente asset, no crashea
```

Ver en logs:
```bash
grep "Error ingesting" logs/mie.log
```

## Pasos recomendados para tu primer test

### 1. Setup (2 min)
```bash
bash setup_local.sh
cp .env.example .env
# Dejar .env sin Telegram por ahora
```

### 2. Ejecutar (5-10 min)
```bash
python main.py
```

Observa logs. Verás `FAST LOOP` cada 5 minutos.

### 3. Generar hipótesis (10-30 min)
Espera a que se detecte un patrón (ej. BTC sube >2%).

Verás en logs:
```
✅ Hipótesis generada: hyp_BTC_price_momentum_xxx
```

### 4. Ver experimento (espera a 08:00 UTC o 24h)
Corre `daily_loop()` manualmente si no puedes esperar:

```python
# En otra terminal
python -c "
import sys; sys.path.insert(0, '.')
from mie.orchestrator import MIEOrchestrator
MIEOrchestrator().daily_loop()
"
```

### 5. Inspeccionar BD
```bash
sqlite3 mie.db "SELECT * FROM hypotheses;"
```

## Cleanup

Para limpiar entre tests:

```bash
# Elimina BD + logs
rm mie.db logs/*.log

# Correr de nuevo (crea BD nueva)
python main.py
```

## Preguntas frecuentes

**¿Puede MIE perder dinero?**
No. V1 no ejecuta trades. Solo observa y aprende.

**¿Qué pasa si Binance API falla?**
MIE logea el error y continúa en el siguiente ciclo. No crashea.

**¿Por qué tan lento (5 min por ciclo)?**
Para observar patrones reales. Más rápido = más ruido = falsas hipótesis.

**¿Puedo cambiar los assets?**
Sí. Modifica `orchestrator.py`:
```python
self.assets = ["BTC", "ETH", "SOL"]  # Añade más
```

**¿Cuándo pasamos a V2?**
Cuando hipótesis tengan >80% confidence en 50+ tests.

---

**Happy testing! 🧪**
