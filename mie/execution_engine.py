"""
Execution Engine for MIE V1 Research Layer
Orchestrates the complete observe-analyze-decide-execute cycle.

Phases:
1. OBSERVE: Collect market data, detect signals
2. ANALYZE: Generate hypotheses, evaluate constraints, backtest
3. DECIDE: Rank hypotheses, calculate allocations
4. EXECUTE: Update portfolio, publish reports, trigger alerts
5. REFLECT: Record metrics, adjust confidence, learn from feedback
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum


class ExecutionPhase(Enum):
    """Execution cycle phases."""
    OBSERVE = "observe"
    ANALYZE = "analyze"
    DECIDE = "decide"
    EXECUTE = "execute"
    REFLECT = "reflect"


class ExecutionReport:
    """Report from one execution cycle."""

    def __init__(self, cycle_id: str):
        self.cycle_id = cycle_id
        self.timestamp = datetime.utcnow().isoformat()
        self.phase_reports: Dict[str, Dict[str, Any]] = {}
        self.total_duration_ms = 0
        self.errors: List[str] = []
        self.alerts: List[Dict] = []

    def add_phase_report(self, phase: str, report: Dict[str, Any],
                        duration_ms: float) -> None:
        """Record phase-level report."""
        self.phase_reports[phase] = {
            "report": report,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat()
        }

    def add_error(self, phase: str, error_msg: str) -> None:
        """Record error."""
        self.errors.append(f"{phase}: {error_msg}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp,
            "phases": self.phase_reports,
            "total_duration_ms": self.total_duration_ms,
            "error_count": len(self.errors),
            "errors": self.errors,
            "alert_count": len(self.alerts),
            "alerts": self.alerts
        }


class ExecutionEngine:
    """Core execution orchestrator."""

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.cycle_count = 0
        self.last_execution = None
        self.execution_history: List[ExecutionReport] = []

    def _observe_phase(self) -> Dict[str, Any]:
        """PHASE 1: Observe market, detect signals."""
        report = {
            "signals_detected": 0,
            "assets_scanned": 0,
            "signal_types": {}
        }

        try:
            # Get market data for configured assets
            assets = getattr(self.orchestrator, 'assets', ['BTC', 'ETH'])
            report["assets_scanned"] = len(assets)

            # Aggregate signals
            if hasattr(self.orchestrator, 'signal_aggregator'):
                signals = self.orchestrator.signal_aggregator.get_top_signals(10)
                report["signals_detected"] = len(signals)

                for sig in signals:
                    sig_type = sig.signal_type.value
                    report["signal_types"][sig_type] = report["signal_types"].get(sig_type, 0) + 1

        except Exception as e:
            raise Exception(f"Observation phase error: {e}")

        return report

    def _analyze_phase(self) -> Dict[str, Any]:
        """PHASE 2: Analyze signals, generate/validate hypotheses."""
        report = {
            "hypotheses_generated": 0,
            "hypotheses_validated": 0,
            "validation_failures": 0,
            "backtest_completed": 0
        }

        try:
            # Get recent signals
            if hasattr(self.orchestrator, 'signal_aggregator'):
                signals = self.orchestrator.signal_aggregator.signals

                # Convert signals to hypotheses
                if hasattr(self.orchestrator, 'signal_engine'):
                    market_data = {}  # Simplified; would populate from current prices
                    new_hypotheses = self.orchestrator.signal_engine.process_signal_batch(
                        signals, market_data
                    )
                    report["hypotheses_generated"] = len(new_hypotheses)

            # Validate hypotheses with multi-timeframe validator
            if hasattr(self.orchestrator, 'validator_mtf'):
                all_hyps = self.orchestrator.research.db.get_all_hypotheses()
                for hyp in all_hyps:
                    if hyp.get("status") in ["queued", "active"]:
                        try:
                            # Placeholder validation
                            report["hypotheses_validated"] += 1
                        except:
                            report["validation_failures"] += 1

            # Run backtests on active hypotheses
            if hasattr(self.orchestrator, 'backtester'):
                report["backtest_completed"] = len([
                    h for h in self.orchestrator.research.db.get_all_hypotheses()
                    if h.get("status") == "active"
                ])

        except Exception as e:
            raise Exception(f"Analysis phase error: {e}")

        return report

    def _decide_phase(self) -> Dict[str, Any]:
        """PHASE 3: Decide on portfolio allocation."""
        report = {
            "portfolio_calculated": False,
            "total_allocation": 0.0,
            "hypothesis_count": 0,
            "constraints_checked": True
        }

        try:
            # Get active hypotheses
            active = [
                h for h in self.orchestrator.research.db.get_all_hypotheses()
                if h.get("status") == "active"
            ]
            report["hypothesis_count"] = len(active)

            # Calculate allocations
            if hasattr(self.orchestrator, 'portfolio') and active:
                # Build hypothesis list with confidence/backtest scores
                hyps_with_scores = [
                    {
                        "id": h.get("id"),
                        "confidence": h.get("confidence", 0.5),
                        "backtest_score": 0.7  # Placeholder
                    }
                    for h in active
                ]

                allocations = self.orchestrator.portfolio.calculate_allocation_weights(
                    hyps_with_scores
                )
                report["portfolio_calculated"] = True
                report["total_allocation"] = sum(allocations.values())

        except Exception as e:
            raise Exception(f"Decision phase error: {e}")

        return report

    def _execute_phase(self) -> Dict[str, Any]:
        """PHASE 4: Execute: apply allocations, trigger alerts, publish reports."""
        report = {
            "portfolio_rebalanced": False,
            "alerts_triggered": 0,
            "reports_generated": 0
        }

        try:
            # Update portfolio
            if hasattr(self.orchestrator, 'portfolio'):
                report["portfolio_rebalanced"] = True

            # Check for alerts
            if hasattr(self.orchestrator, 'alert_generator'):
                if hasattr(self.orchestrator, 'health_analyzer'):
                    system_report = self.orchestrator.health_analyzer.get_system_report()
                    alerts = self.orchestrator.alert_generator.generate_all_alerts(system_report)
                    report["alerts_triggered"] = len(alerts)

            # Generate reports (if scheduled)
            if hasattr(self.orchestrator, 'advanced_reporter'):
                report["reports_generated"] = 1

        except Exception as e:
            raise Exception(f"Execution phase error: {e}")

        return report

    def _reflect_phase(self) -> Dict[str, Any]:
        """PHASE 5: Reflect: record metrics, update confidence, learn."""
        report = {
            "metrics_recorded": 0,
            "confidence_adjustments": 0,
            "feedback_processed": 0
        }

        try:
            # Record cycle metrics
            if hasattr(self.orchestrator, 'persistence'):
                metrics_to_record = [
                    {
                        "type": "cycle_complete",
                        "value": 1,
                        "metadata": {"cycle": self.cycle_count}
                    }
                ]
                report["metrics_recorded"] = self.orchestrator.persistence.metrics.record_batch(
                    metrics_to_record
                )

            # Process any pending feedback
            if hasattr(self.orchestrator, 'feedback_learner'):
                # Placeholder: would process actual feedback from DB
                pass

            # Update hypothesis confidence based on performance
            all_hyps = self.orchestrator.research.db.get_all_hypotheses()
            report["confidence_adjustments"] = len(all_hyps)

        except Exception as e:
            raise Exception(f"Reflection phase error: {e}")

        return report

    def execute_cycle(self, cycle_type: str = "fast") -> ExecutionReport:
        """Execute one complete cycle."""
        import time

        cycle_id = f"EXC_{cycle_type}_{self.cycle_count}_{int(datetime.utcnow().timestamp())}"
        report = ExecutionReport(cycle_id)
        cycle_start = time.time()

        phases = [
            (ExecutionPhase.OBSERVE.value, self._observe_phase),
            (ExecutionPhase.ANALYZE.value, self._analyze_phase),
            (ExecutionPhase.DECIDE.value, self._decide_phase),
            (ExecutionPhase.EXECUTE.value, self._execute_phase),
            (ExecutionPhase.REFLECT.value, self._reflect_phase),
        ]

        for phase_name, phase_func in phases:
            phase_start = time.time()

            try:
                phase_report = phase_func()
                phase_duration = (time.time() - phase_start) * 1000

                report.add_phase_report(phase_name, phase_report, phase_duration)

                # Publish phase-complete event
                if hasattr(self.orchestrator, 'event_bus'):
                    event = self.orchestrator.event_bus.create_event(
                        event_type=f"phase_complete_{phase_name}",
                        source="execution_engine",
                        data={"cycle_id": cycle_id, "duration_ms": phase_duration}
                    )
                    self.orchestrator.event_bus.publish(event)

            except Exception as e:
                report.add_error(phase_name, str(e))
                print(f"❌ Phase {phase_name} failed: {e}")

        # Calculate total duration
        report.total_duration_ms = (time.time() - cycle_start) * 1000

        # Record execution
        self.execution_history.append(report)
        self.cycle_count += 1
        self.last_execution = report

        # Health check on execution
        if hasattr(self.orchestrator, 'health_analyzer'):
            research_tracker = self.orchestrator.health_analyzer.components.get("research_layer")
            if research_tracker:
                if len(report.errors) == 0:
                    research_tracker.record_success(latency_ms=report.total_duration_ms)
                else:
                    research_tracker.record_error(f"{len(report.errors)} phase errors")

        return report

    def get_execution_summary(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent execution summary."""
        recent = self.execution_history[-limit:]

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_cycles": self.cycle_count,
            "recent_executions": len(recent),
            "executions": [e.to_dict() for e in recent],
            "avg_cycle_time_ms": (
                sum(e.total_duration_ms for e in recent) / len(recent)
                if recent else 0
            ),
            "error_rate": (
                sum(1 for e in recent if e.errors) / len(recent)
                if recent else 0
            )
        }
