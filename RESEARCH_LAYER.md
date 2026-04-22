# MIE V1 - Research Layer Documentation

## Overview

MIE V1 includes a complete active research system that investigates its own hypotheses through automated experimentation. The system is not predictive, not a trading bot, but an **active learner** that:

1. **Observes** market patterns (fast loop every 5 min)
2. **Generates hypotheses** from 2+ repeated observations (daily loop)
3. **Designs mini-validations** to test hypotheses on historical data
4. **Classifies results** and tracks confidence (falsified → weakly supported → strongly supported)
5. **Enforces constraints** to prevent runaway exploration
6. **Learns over time** with full audit trails

## Architecture

### Three Cognitive Rhythms

```
FAST LOOP (5 min)
├─ Ingest market data
├─ Detect anomalies
└─ Store observations

DAILY LOOP (08:00 UTC)
├─ Phase 1: Reflect on 24h observations
├─ Phase 2: RESEARCH - hypothesis generation & mini-validation
└─ Phase 3: Learning & decision

WEEKLY LOOP (Sunday 20:00 UTC)
├─ Review experiment results
├─ Update hypothesis confidence
├─ Plan next investigations

MONTHLY LOOP (1st, 18:00 UTC)
├─ Research health audit
├─ Readiness assessment for next phase
└─ Report full self-evaluation
```

### Research Layer - Key Components

**ResearchLayer** (`mie/research_layer.py`):
- Hypothesis generation from repeated observations
- Mini-validation design & execution
- Hypothesis registry management
- Experiment logging (append-only)
- Constraint enforcement (max 5 active, 1-2 exp/week)
- Investigation queue management

**Memory Structure** (`research_logs/`):
- `hypothesis_registry.json` - Active & completed hypotheses
- `investigation_queue.json` - Ideas waiting for investigation
- `experiment_log.jsonl` - All experiments (audit trail)

## Hypothesis Lifecycle

```
BIRTH
├─ Observation 1: Event X happens
├─ Observation 2: Event X happens again
└─ Micro-hypothesis generated: "Maybe X predicts Y?"

DESIGN
├─ Define test condition (e.g., "funding_rate > 0.015")
├─ Define lookback period (30-60 days)
└─ Define success criteria (e.g., "vol 2x baseline")

TEST
├─ Scan historical data for condition matches
├─ Check outcomes (did Y happen when X was met?)
└─ Calculate success rate & lag patterns

CLASSIFY
├─ <60%: "falsified" (discard)
├─ 60-75%: "weakly_supported" (continue testing)
├─ 75-85%: "supported" (pattern candidate)
└─ >85%: "strongly_supported" (monitor closely)

DECIDE
├─ Keep open (if enough evidence)
├─ Promote (if exceeds threshold + cross-validation)
├─ Demote (if evidence weak)
└─ Discard (if falsified)

ITERATE
└─ Next hypothesis or refine current
```

## Constraints (Safety)

1. **Max 5 active hypotheses** - prevents runaway exploration
2. **Max 1-2 new experiments/week** - controlled pace
3. **Min 2 observations for birth** - prevents guessing
4. **75%+ success rate for "supported"** - high bar
5. **Cross-validation required** - test on multiple assets
6. **Overfit detection** - catches cherry-picked data
7. **All changes documented** - full audit trail

## Example Flow

**Day 1-2**: Fast Loop detects funding rate spike → price move (2x)
- Observation 1: BTC funding 0.0145, vol +2% (2h later)
- Observation 2: BTC funding spike again, vol +1.8% (3h later)
- Micro-hypothesis BORN: "Funding spikes → vol increase?"

**Day 3**: Daily Loop (08:00 UTC)
- Research Phase: Design mini-validation
  - Test: funding_rate > 0.015 → vol spike 2-6h later?
  - Lookback: 60 days
  - Assets: BTC, ETH
- Execute on historical data
  - Found 14 funding spikes in 60 days
  - 10/14 followed by vol spike (71% success rate)
- Classify: "weakly_supported" (71% > 60%, < 75%)
- Decision: "Keep open, continue testing"

**Day 7**: Weekly Loop
- Review: Hypothesis still testing
- Plan: Run cross-validation on SOL + BNB next week
- Status: "Gaining support, needs validation"

## Integration Points

### Daily Loop Calls Research
```python
new_hyps = self.research.generate_micro_hypotheses()
registry = self.research._load_hypothesis_registry()
for hyp in active_ready[:1]:
    result = self.research.execute_validation(hyp)
    self.research.update_hypothesis_confidence(...)
```

### Constraint Enforcement
```python
constraints = self.research.enforce_constraints()
if not constraints["active_hypotheses_ok"]:
    logger.warning(f"Max active ({constraints['active_count']}/{constraints['max_active']}) reached")
```

### Dialogue Integration
- User can ask: "What are you investigating?"
  - System returns: current hypothesis registry + queue
- User can suggest: "Test whether X predicts Y"
  - System adds to queue (lower priority)
- User marks feedback: "This observation was useful"
  - System updates relevance filter

## Memory Files

### hypothesis_registry.json
```json
{
  "active": [
    {
      "id": "hyp_BTC_funding_precedes_vol",
      "observation": "BTC funding spikes precede vol increases",
      "observation_count": 3,
      "born_date": "2026-04-21T08:00:00",
      "status": "testing",
      "confidence": "repeated_observation",
      "priority": 0.7,
      "assigned_experiment": "exp_001"
    }
  ],
  "completed": [
    {
      "id": "hyp_X",
      "final_result": "falsified",
      "final_reason": "Success rate 33%"
    }
  ]
}
```

### experiment_log.jsonl
```
{exp_id, hypothesis_id, test_design, results, classification, decision}
{exp_id, hypothesis_id, ...}
...
```

(One experiment per line, append-only for audit trail)

### investigation_queue.json
```json
{
  "queue": [
    {
      "id": "hyp_macro_timing",
      "observation": "Macro events precede price moves",
      "observation_count": 2,
      "ready_to_test": false,
      "priority": 0.6
    }
  ]
}
```

## Readiness for Next Phase

Current phase is **Bootstrap** - hypothesis generation and evidence gathering.

Exit criteria for **Active Learning** phase:
- 3+ pattern candidates with 75%+ success rate
- <20% false positive rate in observations
- Dialogue feedback: 70%+ marked "useful"
- Evidence standards: convergence on patterns
- Estimated timeline: 8-12 weeks

## Usage

### Check Research Status
```python
status = orchestrator.research.get_research_status()
print(f"Active: {status['active_hypotheses']}")
print(f"Queue: {status['queue_pending']}")
```

### Get Experiment Summary
```python
summary = orchestrator.research.get_experiment_summary()
print(f"Experiments this week: {summary['this_week']}")
print(f"Classifications: {summary['classifications_this_week']}")
```

### Enforce Constraints
```python
constraints = orchestrator.research.enforce_constraints()
if constraints["active_hypotheses_ok"]:
    print("Constraint: Active hypotheses OK")
```

## Safety Guarantees

1. **Evidence-based only** - No guessing, 2+ observations minimum
2. **Constraint enforcement** - Automatic limits prevent runaway
3. **Overfit detection** - Cross-validation required
4. **Approval workflows** - Weekly/monthly review before promotion
5. **Full audit trail** - Every decision documented & reversible
6. **User control** - Dialogue feedback shapes direction
7. **No execution** - Never trades, never makes decisions autonomously

## Next Steps

1. Daily observations accumulate
2. Patterns detected and tested
3. Hypotheses converge or falsified
4. When ready (weeks 8-12): Transition to active monitoring
5. Eventually: Selective alerts on high-confidence patterns (not predictions)

---

**Current Status**: Bootstrap phase active  
**Last Updated**: 2026-04-22  
**MIE V1** - Market Intelligence Entity
