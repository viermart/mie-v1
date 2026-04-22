# MIE V1 Architecture

## Visión general

MIE V1 es una entidad de mercado que **observa**, **reflexiona**, **investiga** y **aprende** sin ejecutar transacciones. Está diseñada para bootstrap: acumular evidencia, generar hipótesis y validarlas antes de la fase V2 (alertas + decisiones).

## Decisiones de diseño

### 1. SQLite + contexto en memoria

**Por qué**: Simplicidad. El bootstrap no requiere escala distribuida. Los datos se persisten en SQLite (durabilidad) + JSON runtime (velocidad en lectura).

**Trade-off**: SQLite en producción Railway es viable para observaciones de 2 assets. Si escala a 50 assets, migramos a PostgreSQL.

### 2. Tres loops, no cinco

**V1 scope**:
- ✅ Fast (5 min): Ingesta pura
- ✅ Daily (08:00 UTC): Reflexión + research
- ✅ Weekly: Meta-thinking
- ❌ Hourly: Pospuesto a V2
- ❌ Monthly: Pospuesto a V2

**Por qué**: Minimizar complejidad operacional. Tres loops son suficientes para bootstrap.

### 3. Triggers basados en repetición (2+ observaciones)

**Regla**: No generamos hipótesis de eventos únicos.

```
Evento único: 1 spike de funding → ignorar
Patrón: 2+ spikes en 7 días → hipótesis
```

**Beneficio**: Reducimos ruido. Solo investigamos patrones repetibles.

### 4. Mini-validación antes de persistencia

**Flujo**:
```
Trigger detectado → Mini-validate en histórico
  └─ Si válido (patrón > 2 instancias en 7d) → Persistimos hipótesis
  └─ Si inválido → Ignoramos (no ruido en BD)
```

**Por qué**: Mantienen la BD limpia. No almacenamos hipótesis de ruido.

### 5. Overfit detection (roadmap V1.1)

Hoy: Contamos frecuencia del patrón en 7 días.
V1.1: Añadimos test de significancia estadística (chi-squared, etc.).

## Tablas y flujos

### observations (append-only)

```sql
CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,          -- UTC ISO format
    source TEXT,             -- 'binance'
    asset TEXT,              -- 'BTC', 'ETH'
    observation_type TEXT,   -- 'price', 'funding_rate', 'open_interest'
    value REAL,              -- valor numérico
    context TEXT,            -- metadatos (e.g., "24h_change: +2.3%")
    flags TEXT,              -- deprecated, para futura expansión
    created_at TEXT          -- timestamp de inserción
)
```

**Inserción**: Fast loop → `add_observation()`
**Lectura**: Research layer → `get_observations(asset, lookback_hours, type)`

### hypotheses (mutable state)

```sql
CREATE TABLE hypotheses (
    id INTEGER PRIMARY KEY,
    hypothesis_id TEXT UNIQUE,     -- 'hyp_BTC_price_spike_001'
    text TEXT,                     -- descripción natural
    born_date TEXT,                -- cuándo fue generada
    born_from TEXT,                -- 'trigger:price_momentum'
    status TEXT,                   -- 'awaiting_validation', 'testing', 'supported', 'falsified'
    confidence TEXT,               -- 'insufficient_evidence', 'weakly_supported', 'supported', 'strongly_supported'
    priority REAL,                 -- 0.0 a 1.0 (default 0.5)
    decision TEXT,                 -- resultado final: 'supported', 'falsified', 'awaiting_more_data'
    observation_count INTEGER,     -- cuántas observaciones la soportan
    notes TEXT,                    -- anotaciones del investigador
    created_at TEXT,
    updated_at TEXT
)
```

**Lifecycle**:
1. Birth: `born_date`, `status='awaiting_validation'`, `confidence='insufficient_evidence'`
2. Testing: `status='testing'` (cuando daily loop ejecuta experimento)
3. Classification: `confidence` ← resultado del experimento
4. Decision: `status='supported'|'falsified'|'awaiting_more_data'`

### experiments (append-only log)

```sql
CREATE TABLE experiments (
    id INTEGER PRIMARY KEY,
    exp_id TEXT UNIQUE,         -- 'exp_hyp_001_20260421_083000'
    hypothesis_id TEXT,         -- foreign key a hypotheses
    created_date TEXT,          -- cuándo se ejecutó
    description TEXT,           -- descripción del test
    test_design TEXT,           -- JSON: lookback_hours, statistical_test, etc.
    results TEXT,               -- JSON: {supporting, total, ratio}
    analysis TEXT,              -- JSON: análisis detallado
    classification TEXT,        -- 'falsified', 'weakly_supported', 'supported', 'strongly_supported'
    overfit_risk TEXT,          -- 'low', 'medium', 'high' (V1.1)
    decision TEXT,              -- resultado: 'supported', 'falsified'
    created_at TEXT
)
```

**Inserción**: Daily loop → `add_experiment()` y luego `update_experiment()` con resultados

### learning_logs

```sql
CREATE TABLE learning_logs (
    id INTEGER PRIMARY KEY,
    log_type TEXT,         -- 'daily', 'weekly'
    timestamp TEXT,        -- cuándo se registró
    content TEXT,          -- JSON: resumen + observaciones + estado
    created_at TEXT
)
```

Guarda reflexiones periódicas para post-mortem y análisis de aprendizaje.

## Módulos principales

### 1. database.py - MIEDatabase

Wrapper de SQLite3 con métodos para:
- `add_observation()` - ingesta
- `get_observations()` - lectura con time window
- `add_hypothesis()` - crear hipótesis
- `update_hypothesis()` - cambiar estado
- `get_active_hypotheses()` - hipótesis en investigación
- `add_experiment()` - registrar test
- `update_experiment()` - persistir resultados
- `add_learning_log()` - reflexión periódica

**Principio**: Todas las operaciones son atómicas. Commit después de cada inserción.

### 2. binance_client.py - BinanceClient

Integración con Binance API v3 (spot) y v1 (futures).

```python
BinanceClient.ingest_observation(asset)
# → obtiene ticker + funding + OI
# → retorna dict crudo para persistencia

BinanceClient.parse_observation(raw)
# → extrae campos atomizados (price, volume, funding_rate, OI)
# → retorna dict con tipos correctos
```

**Errores manejados**: RequestException → log + skip observación (no crash del loop)

### 3. research_layer.py - ResearchLayer

Coordinador de hipótesis: generación, validación, clasificación.

**Métodos principales**:
- `check_hypothesis_triggers()` - corre después de cada fast_loop
  - Busca patrones en observaciones recientes
  - Llama a `_maybe_generate_hypothesis()`
  
- `_mini_validate()` - valida que el patrón sea repetible en 7 días
  - Si pasa → `db.add_hypothesis()` con `status='awaiting_validation'`
  - Si falla → ignorar (evita ruido)

- `run_experiment()` - valida hipótesis contra histórico
  - Corre en daily loop para hipótesis en `status='testing'`
  - Retorna `{classification, decision, observations, analysis}`

**Overfit detection**: Hoy cuenta frecuencia. V1.1 → chi-squared test.

### 4. reporter.py - Reporter

Comunica estado a Telegram (opcional) y logs.

**Tres tipos de mensajes**:
1. `send_heartbeat()` - "MIE está vivo"
2. `send_daily_report()` - resumen 24h + estado de hipótesis
3. `send_weekly_report()` - análisis semanal

Si `TELEGRAM_TOKEN` está vacío, solo escribe en logs.

### 5. orchestrator.py - MIEOrchestrator

Orquestador principal. Coordina los tres loops.

```python
orchestrator = MIEOrchestrator(db_path, telegram_token, chat_id)
orchestrator.schedule_loops()  # configura schedule
orchestrator.run()             # loop infinito
```

**Loops**:
- `fast_loop()` - cada 5 min
  - Ingesta de observaciones
  - `check_hypothesis_triggers()`
  
- `daily_loop()` - 08:00 UTC
  - `_reflect_on_observations()` - resumen 24h
  - Ejecuta experimentos
  - `add_learning_log()`
  - Envía daily report
  
- `weekly_loop()` - domingo 08:00 UTC
  - Reflexión 7 días
  - Revisión de hipótesis
  - Learning log semanal
  - Weekly report

## Flujo de datos completo

```
1. FAST LOOP (5 min)
   ├─ binance_client.ingest_observation("BTC")
   ├─ Binance API → {ticker, funding, OI}
   ├─ parse_observation() → valores atomizados
   ├─ db.add_observation() × 3 (price, funding, OI)
   ├─ research.check_hypothesis_triggers()
   │  ├─ Detecta patrón: funding rate > 1% × 2 veces en 6h
   │  ├─ _mini_validate() → ¿existe patrón en 7 días?
   │  └─ Si sí: db.add_hypothesis() con status='awaiting_validation'
   └─ reporter.send_heartbeat() [opcional]

2. DAILY LOOP (08:00 UTC)
   ├─ _reflect_on_observations(lookback_hours=24)
   │  └─ Calcula: current_price, min, max, avg, obs_count
   ├─ Obtiene hypotheses con status='testing'
   ├─ Para cada hipótesis:
   │  ├─ research.run_experiment(hyp_id)
   │  ├─ _validate_hypothesis() → análisis en histórico
   │  ├─ db.update_experiment() con resultados
   │  ├─ db.update_hypothesis() con confidence + decision
   │  └─ Resultado: "ONGUSDT funding patrón: SUPPORTED (0.85 ratio)"
   ├─ db.add_learning_log(log_type='daily', content=JSON)
   └─ reporter.send_daily_report()

3. WEEKLY LOOP (domingo 08:00 UTC)
   ├─ _reflect_on_observations(lookback_hours=24*7)
   ├─ get_active_hypotheses() → estado general
   ├─ db.add_learning_log(log_type='weekly')
   └─ reporter.send_weekly_report()
```

## Control de calidad

### Append-only tables
- `observations` - nunca se modifica. Útil para auditoría + backtest.
- `experiments` - nunca se modifica. Log inmutable de cada test.
- `learning_logs` - nunca se modifica. Histórico de reflexión.

### Mutable state (con cuidado)
- `hypotheses` - solo cambia status/confidence (no text ni born_date).
  - Válido: marcar como "falsified" después del test
  - Inválido: reescribir la hipótesis

### Transacciones
Todas las operaciones usan `conn.commit()` después de INSERT/UPDATE. No hay rollback en V1 (todo es best-effort).

## Error handling

### Network errors (Binance API)
```python
try:
    ingest_observation()
except RequestException:
    logger.error(f"Error: {e}")
    reporter.send_error()
    # Sigue al siguiente asset, no crashea el loop
```

### Database errors
```python
try:
    db.add_observation()
except sqlite3.Error:
    logger.error()
    reporter.send_error()
    # Sigue ejecutando
```

### Telegram errors
Si falla envío a Telegram, log pero no afecta MIE.

## Extensibilidad

### Para añadir un nuevo observation_type
1. Modifica `binance_client.ingest_observation()` para obtenerlo
2. Modifica `binance_client.parse_observation()` para parsearlo
3. Modifica `fast_loop()` para `db.add_observation()` con nuevo type
4. Modifica `research_layer.check_hypothesis_triggers()` para detectar patrones

### Para añadir un nuevo hypothesis template
1. Modifica `research_layer.hypothesis_templates` dict
2. Implementa la lógica de trigger en `check_hypothesis_triggers()`
3. Implementa mini-validación en `_mini_validate()`

### Para cambiar frecuencias de loops
Modifica `orchestrator.schedule_loops()`:
```python
# Cambiar fast loop a 10 min
schedule.every(10).minutes.do(self.fast_loop)

# Cambiar daily a 18:00 UTC
schedule.every().day.at("18:00").do(self.daily_loop)
```

## Roadmap V1.1 (sin V1 release)

- [ ] Overfit detection: chi-squared test
- [ ] Diálogo: capturar feedback del usuario → ajustar prioridades
- [ ] Dashboard local: web UI para ver estado en tiempo real
- [ ] Histórico: analysis_lag para detectar si el patrón cambió desde el test

## Roadmap V2 (post-bootstrap)

- [ ] Alertas reales basadas en hipótesis soportadas
- [ ] On-chain data (OpenSea, blockchain)
- [ ] ML classifier para confidence (no solo frecuencia)
- [ ] Exportación de datos: CSV con histórico de hipótesis
- [ ] Multi-chain: no solo Binance spot

---

**Última actualización**: 2026-04-21
**Autor**: Javi
**Status**: V1 - Bootstrap Phase
