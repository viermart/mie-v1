# MIE V1.2 - Dialogue System

## Fase 1.2: MIE ahora es dialogable vía Telegram

MIE V1.2 agrega capacidad de diálogo bidireccional. Ahora puedes hacer preguntas y dar feedback directamente vía Telegram, y MIE responde con contexto del mercado actual.

---

## Qué es nuevo en V1.2

### QueryType enum (11 tipos de interacción)

```python
MARKET_OVERVIEW       # "como ves el mercado hoy"
WHAT_WATCHING        # "que estas mirando"
WHAT_LEARNED         # "que aprendiste"
ACTIVE_HYPOTHESES    # "hipotesis activas"
STATUS               # "status", "como vas"
ASSET_QUERY          # "btc", "eth", específicos
FEEDBACK_POSITIVE    # "esto fue util", "bien"
FEEDBACK_NEGATIVE    # "esto fue ruido", "mal"
FEEDBACK_FOCUS       # "enfocate mas en btc"
FEEDBACK_TIMEFRAME   # "menos intradia"
UNKNOWN              # No clasificado
```

### DialogueHandler class (mie/dialogue.py)

- **classify_query(message)** → Identifica qué pregunta es
- **generate_response(query_type)** → Responde basado en DB actual
- **handle_feedback(feedback_type)** → Procesa feedback + lo guarda
- **handle_message(message, user_id)** → Orquestador completo
- Pattern matching con regex para cada tipo

### Integración en Orchestrator

- **_check_telegram_messages()** → Polling cada 30 segundos
- **_send_telegram_message(text)** → Respuesta automática
- **dialogue_loop()** → Loop dedicado para mensajes
- Agregado a schedule junto con Fast/Daily/Weekly

---

## Arquitectura de respuestas

### 1. Market Overview

**Trigger**: "como ves el mercado", "que tal el mercado", "overview"

```
_market_overview()
├─ get_observations(lookback_hours=24)
├─ Agrupa por asset
├─ Calcula: precio actual, rango, cambio %
└─ Retorna: 📊 Overview con stats
```

Ejemplo de respuesta:
```
📊 **Overview del mercado (últimas 24h):**

**BTCUSDT**
  Precio actual: $45,234.50
  Rango: $44,100.00 - $46,500.00
  Cambio 24h: +2.35%
  Observaciones: 45

**ETHUSDT**
  Precio actual: $2,345.80
  Rango: $2,200.00 - $2,400.00
  Cambio 24h: +1.20%
  Observaciones: 45
```

### 2. What Watching

**Trigger**: "que estas mirando", "que observas", "monitoring"

```
_what_watching()
├─ get_observations(lookback_hours=24)
├─ Cuenta por tipo (price, funding_rate, OI)
├─ Cuenta por asset (BTC, ETH)
└─ Retorna: 👀 Breakdown de observaciones
```

Ejemplo:
```
👀 **Estoy observando (últimas 24h):**

**Total de observaciones**: 135

**Por tipo:**
  • price: 45
  • funding_rate: 45
  • open_interest: 45

**Por asset:**
  • BTC: 45
  • ETH: 45
```

### 3. What Learned

**Trigger**: "que aprendiste", "insights", "conclusiones"

```
_what_learned()
├─ get_learning_logs(limit=5)
├─ Parsea JSON content
├─ Extrae summary de cada log
└─ Retorna: 📚 Aprendizajes registrados
```

Ejemplo:
```
📚 **Aprendizajes registrados:**

**DAILY** (2026-04-22T08:00:00)
  BTC mostró movimiento de +2.35% en 24h
  ETH funding rate promedio: 0.0001

**DAILY** (2026-04-21T08:00:00)
  5 hipótesis activas en testing
  Observaciones soportan patrón de momentum
```

### 4. Active Hypotheses

**Trigger**: "hipotesis activas", "que hipotesis", "que estoy testando"

```
_active_hypotheses()
├─ get_active_hypotheses()
├─ Por cada hipótesis: ID, text, status, confidence, obs_count
└─ Retorna: 🔬 Listado con detalles
```

Ejemplo:
```
🔬 **Hipótesis activas:**

**hyp_BTC_price_momentum_001**
  Texto: BTC mostró movimiento de +2.0%
  Status: testing
  Confianza: insufficient_evidence
  Observaciones: 12

**hyp_ETH_funding_spike_001**
  Texto: ETH funding rate elevado > 0.0001
  Status: awaiting_validation
  Confianza: insufficient_evidence
  Observaciones: 8
```

### 5. Status

**Trigger**: "status", "como vas", "funciono"

```
_status()
├─ Cuenta observaciones (24h)
├─ Cuenta hipótesis activas
├─ Obtiene últimos learning logs
└─ Retorna: ✅ Summary de salud
```

Ejemplo:
```
✅ **MIE V1 Status:**

  • Observaciones (24h): 135
  • Hipótesis activas: 2
  • Learning logs: 5
  • Assets monitorizados: BTC, ETH
  • Loops: Fast (5min), Daily (08:00 UTC), Weekly (Dom)
```

### 6. Asset Query

**Trigger**: "btc", "eth", "como ves btc", "status eth"

```
_asset_query(asset)
├─ get_observations(asset=BTC|ETH, lookback_hours=24, type=price)
├─ Calcula: min, max, avg, % change
├─ Busca hipótesis activas sobre ese asset
└─ Retorna: 📈 Stats + hipótesis relacionadas
```

Ejemplo:
```
📈 **BTCUSDT - Últimas 24h:**

  Precio actual: $45,234.50
  Promedio: $45,100.25
  Rango: $44,100.00 - $46,500.00
  Cambio: +2.35%
  Observaciones: 45

  **Hipótesis activas:**
    • hyp_BTC_price_momentum_001: BTC mostró movimiento de +2.0%
```

---

## Feedback Processing

### Positive Feedback

**Trigger**: "esto fue util", "bien", "exacto"

```python
handle_feedback(FEEDBACK_POSITIVE, message, user_id)
├─ db.add_user_feedback({type: "positive", ...})
├─ Log: Feedback registrado
└─ Respuesta: "✅ Feedback positivo registrado. Continuaré así."
```

**Efecto futuro (V1.3+)**: Aumenta weight de patrones similares

### Negative Feedback

**Trigger**: "esto fue ruido", "mal", "equivocado"

```python
handle_feedback(FEEDBACK_NEGATIVE, message, user_id)
├─ db.add_user_feedback({type: "negative", ...})
├─ Log: Feedback negativo
└─ Respuesta: "📝 Feedback negativo registrado. Revisaré mis criterios."
```

**Efecto futuro**: Reduce weight de patrones problemáticos

### Focus Feedback

**Trigger**: "enfocate mas en btc", "menos eth", "prioriza btc"

```python
handle_feedback(FEEDBACK_FOCUS, message, user_id)
├─ Extract asset: BTC|ETH
├─ db.add_user_feedback({type: "focus", asset: "BTC", ...})
└─ Respuesta: "🎯 Aumentando prioridad en BTC. Lo haré."
```

**Efecto futuro**: Aumenta frecuencia de observaciones para ese asset

### Timeframe Feedback

**Trigger**: "menos intradia", "mas diario", "enfocate en weekly"

```python
handle_feedback(FEEDBACK_TIMEFRAME, message, user_id)
├─ db.add_user_feedback({type: "timeframe", preference: "daily", ...})
└─ Respuesta: "⏱️ Preferencia de timeframe registrada."
```

**Efecto futuro**: Ajusta triggers de hipótesis por timeframe

---

## Flujo completo: Cómo funciona

### 1. Usuario envía mensaje por Telegram

```
Usuario: "como ves el mercado"
```

### 2. MIE detecta el mensaje (dialogue_loop cada 30 seg)

```python
_check_telegram_messages()
├─ GET /getUpdates con offset=last_message_id
├─ Recibe: {update_id: 123, message: {text: "como ves el mercado", ...}}
├─ Llama: dialogue.handle_message("como ves el mercado", user_id)
└─ Obtiene respuesta
```

### 3. DialogueHandler clasifica y responde

```python
classify_query("como ves el mercado")
├─ Busca en query_patterns[MARKET_OVERVIEW]
├─ Match: r"como ves el mercado"
├─ Retorna: (QueryType.MARKET_OVERVIEW, None)

generate_response(MARKET_OVERVIEW)
├─ Llama: _market_overview()
├─ DB query: get_observations(asset=None, lookback_hours=24)
├─ Procesa: calcula stats por asset
└─ Retorna: String con 📊 formato
```

### 4. Respuesta se envía a Telegram

```python
_send_telegram_message(response)
├─ POST /sendMessage
├─ chat_id=1234567890
├─ text="📊 **Overview del mercado...**"
├─ parse_mode="Markdown"
└─ Usuario recibe: respuesta formateada
```

### 5. Diálogo se guarda en BD

```
db.add_dialogue(user_id, "como ves el mercado", response)
└─ dialogue_memory table: id | user_id | timestamp | user_message | response
```

---

## Testing V1.2

### Opción A: Local + Telegram real

```bash
# 1. Setup si no lo hiciste
bash setup_local.sh

# 2. Asegúrate que .env tiene Telegram:
cat .env
# TELEGRAM_TOKEN=123456:ABC-DEF...
# TELEGRAM_CHAT_ID=1234567890

# 3. Corre MIE V1.2
source venv/bin/activate
python main.py

# 4. En otra terminal, observa logs:
tail -f logs/mie.log | grep "💬"

# 5. Envía mensajes por Telegram al bot
# Usuario: "como ves el mercado"
# MIE responde: "📊 **Overview del mercado...**"
```

### Opción B: Local sin Telegram (modo prueba)

```bash
# Edita .env:
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=

# Corre MIE:
python main.py

# Logs mostrarán intención pero sin respuesta Telegram:
# "Telegram no configurado, mensaje no enviado"
```

### Opción C: Probar DialogueHandler directo

```python
# Python REPL
from mie.dialogue import DialogueHandler
from mie.database import MIEDatabase
import logging

db = MIEDatabase()
logger = logging.getLogger("test")
dialogue = DialogueHandler(db, logger)

# Test clasificación
query_type, param = dialogue.classify_query("como ves el mercado")
print(query_type)  # QueryType.MARKET_OVERVIEW

# Test respuesta
response = dialogue.handle_message("como ves el mercado", user_id="123")
print(response)  # 📊 **Overview del mercado...**
```

---

## Mensajes de ejemplo para probar

### Queries que deberían funcionar

```
"como ves el mercado hoy"
→ MARKET_OVERVIEW

"que estoy mirando"
→ WHAT_WATCHING

"que aprendiste"
→ WHAT_LEARNED

"hipotesis activas"
→ ACTIVE_HYPOTHESES

"status"
→ STATUS

"btc"
"eth"
"como ves btc"
→ ASSET_QUERY

"esto fue util"
→ FEEDBACK_POSITIVE

"esto fue ruido"
→ FEEDBACK_NEGATIVE

"enfocate mas en btc"
"menos eth"
→ FEEDBACK_FOCUS

"menos intradia"
"mas diario"
→ FEEDBACK_TIMEFRAME

"hola che"
→ UNKNOWN (muestra ayuda)
```

---

## Integración con loops

### Fast Loop (cada 5 min)

```python
def fast_loop(self):
    # 1. Chequea Telegram
    self._check_telegram_messages()
    
    # 2. Ingesta observaciones
    # 3. Detecta triggers
    # 4. Genera hipótesis
```

### Dialogue Loop (cada 30 seg)

Ejecutado por schedule:
```python
schedule.every(30).seconds.do(self.dialogue_loop)
```

Permite respuesta rápida a mensajes sin esperar 5 minutos.

### Daily Loop (08:00 UTC)

Sin cambios. Sigue reflejando + experimentando.

---

## Próximos pasos (V1.3+)

- [ ] **Memoria contextual**: Recordar preguntas previas, mantener conversación
- [ ] **Feedback learning**: Usar feedback positivo/negativo para ajustar triggers
- [ ] **Dynamic timeframes**: Cambiar lookback según preferencia del usuario
- [ ] **Asset priorities**: Aumentar frecuencia de observaciones para assets priorizados
- [ ] **Inline commands**: `/status`, `/btc`, `/hypotheses` como comandos Telegram
- [ ] **Notifications**: Alertar cuando hipótesis cambien de status
- [ ] **Backtest en feedback**: Si usuario dice "esto fue ruido", ejecutar backtest del patrón

---

## Debugging

### Si MIE no responde a mensajes

1. **Verifica que están llegando** (en logs):
   ```bash
   grep "💬" logs/mie.log
   ```
   Si no hay nada → Telegram no está enviando mensajes

2. **Chequea credentials**:
   ```bash
   echo $TELEGRAM_TOKEN
   echo $TELEGRAM_CHAT_ID
   ```

3. **Test manual de Telegram**:
   ```bash
   curl https://api.telegram.org/bot${TELEGRAM_TOKEN}/getMe
   ```
   Debería retornar info del bot

4. **Revisa si el bot recibe mensajes**:
   ```bash
   curl "https://api.telegram.org/bot${TELEGRAM_TOKEN}/getUpdates"
   ```
   Debería mostrar tus mensajes recientes

### Si la respuesta no es útil

- Revisa que DB tiene observaciones:
  ```bash
  sqlite3 mie.db "SELECT COUNT(*) FROM observations;"
  ```

- Si está vacío, fast_loop aún no ha ingestado datos. Espera 5 minutos.

### Si un patrón no se clasifica

- La query puede no matchear ningún pattern regex
- Prueba añadiendo el patrón a `dialogue.py`
- O entra a UNKNOWN y recibe ayuda

---

## Estructura de tablas (nuevas en V1.2)

### dialogue_memory

```sql
id INTEGER PRIMARY KEY
user_id TEXT
timestamp TEXT (ISO UTC)
user_message TEXT
response TEXT
```

Guarda cada interacción para histórico.

### user_feedback

```sql
id INTEGER PRIMARY KEY
user_id TEXT
feedback_type TEXT (positive|negative|focus|timeframe)
message TEXT
timestamp TEXT (ISO UTC)
```

Guarda feedback para aprendizaje futuro.

---

## Status

✅ **V1.2 implementado y listo para deploy**

- [x] QueryType enum con 11 tipos
- [x] DialogueHandler con clasificación regex
- [x] Métodos de respuesta (_market_overview, etc)
- [x] Feedback processing
- [x] Integración en Orchestrator
- [x] Telegram polling cada 30 seg
- [x] Persistencia de diálogo en BD

**Próxima acción:**
```bash
# Push a Railway
git add .
git commit -m "feat: MIE V1.2 - Dialogue system"
git push

# O redeploy en Railway:
railway deploy
```

---

**MIE V1.2 - ¡Ya puedes hablar con MIE! 🗣️**
