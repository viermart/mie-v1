# MIE V1 - Market Intelligence Entity Research Layer

**Version:** 1.0.0  
**Status:** Production Ready  
**Last Updated:** 2026-04-22  
**Components:** 21 integrated systems

## Overview

MIE V1 is a sophisticated market intelligence research layer that autonomously discovers, validates, and manages investment hypotheses through a continuous observe-analyze-decide-execute-reflect cycle.

The system operates on three timescales:
- **Fast Loop (5 min):** Real-time signal detection
- **Daily Loop (08:00 UTC):** Deep analysis and hypothesis generation
- **Weekly Loop (Sunday 17:00 UTC):** Meta-thinking and portfolio review

## Architecture

### Core Research (11 components)
Research Layer, Hypothesis Analyzer, Feedback Learner, Multi-Timeframe Validator, Alert System, Backtester, Portfolio Manager, Advanced Reporter, Readiness Calculator, Hypothesis Predictor, Asset Correlation Analyzer

### System Infrastructure (10 components)
Data Persistence, Market Scanner, Signal-to-Hypothesis Engine, System Health Monitor, Event Bus, Configuration Manager, REST API, Execution Engine, Scheduler, Orchestrator

## Key Metrics

- Max active hypotheses: 5
- Max experiments/week: 2
- Observation threshold: 2
- Portfolio concentration: max 40%, min 10%
- Confidence range: 0.30-0.95
- Backtest Sharpe target: ≥1.0

## Quick Start

```bash
python -m mie.main status          # Check system status
python -m mie.main fast            # Run one fast cycle
python -m mie.main scheduler       # Start continuous execution
python -m mie.main api --port 8000 # Start REST API
```

## REST API

GET /api/status - System status
GET /api/health - Health report
GET /api/hypotheses - List hypotheses
GET /api/portfolio - Portfolio state
GET /api/metrics - System metrics
POST /api/feedback - Submit feedback

## Integration Tests

```bash
python3 -c "
from mie.orchestrator import MIEOrchestrator
from mie.integration_test import run_integration_tests

mie = MIEOrchestrator()
run_integration_tests(mie)
"
```

## Version 1.0.0 Features

- 21 integrated components
- Complete observe-analyze-decide-execute-reflect cycle
- REST API, CLI interface, scheduler
- Health monitoring and alerting
- Data persistence and cross-session recovery
- Dynamic configuration management
- Real-time event bus
- Integration test suite

---

**MIE V1 - Built with rigor. Validated continuously.**
