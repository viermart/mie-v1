"""
Data Persistence Layer for MIE V1 Research Layer
Enables hypothesis state tracking, historical metrics, and walk-forward validation checkpoints.

Components:
- HypothesisStore: JSON persistence for hypothesis lifecycle
- MetricsHistory: Time-series metric tracking
- BacktestCheckpoints: Walk-forward validation snapshots
- PortfolioHistory: Rebalance and allocation tracking
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import copy


class HypothesisStore:
    """Persist hypothesis state for cross-session evolution."""

    def __init__(self, storage_dir: str = "data/hypotheses"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_hypothesis(self, hypothesis_id: str, hypothesis_data: Dict[str, Any]) -> bool:
        """Save hypothesis state with timestamp."""
        try:
            data = {
                "id": hypothesis_id,
                "saved_at": datetime.utcnow().isoformat(),
                "data": hypothesis_data
            }

            filepath = self.storage_dir / f"{hypothesis_id}.json"
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            print(f"❌ HypothesisStore.save_hypothesis error: {e}")
            return False

    def load_hypothesis(self, hypothesis_id: str) -> Optional[Dict[str, Any]]:
        """Load hypothesis state."""
        try:
            filepath = self.storage_dir / f"{hypothesis_id}.json"
            if not filepath.exists():
                return None

            with open(filepath, 'r') as f:
                data = json.load(f)

            return data.get("data")
        except Exception as e:
            print(f"❌ HypothesisStore.load_hypothesis error: {e}")
            return None

    def save_batch(self, hypotheses: List[Dict[str, Any]]) -> int:
        """Batch save multiple hypotheses."""
        saved = 0
        for hyp in hypotheses:
            hyp_id = hyp.get("id")
            if hyp_id and self.save_hypothesis(hyp_id, hyp):
                saved += 1

        return saved

    def load_all(self) -> Dict[str, Dict[str, Any]]:
        """Load all persisted hypotheses."""
        result = {}
        for filepath in self.storage_dir.glob("*.json"):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    hyp_id = data.get("id")
                    if hyp_id:
                        result[hyp_id] = data.get("data", {})
            except:
                continue

        return result

    def delete_hypothesis(self, hypothesis_id: str) -> bool:
        """Delete persisted hypothesis."""
        try:
            filepath = self.storage_dir / f"{hypothesis_id}.json"
            if filepath.exists():
                filepath.unlink()
                return True
            return False
        except:
            return False


class MetricsHistory:
    """Time-series tracking of hypothesis and system metrics."""

    def __init__(self, storage_dir: str = "data/metrics"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.storage_dir / "metrics_history.json"
        self._load_or_init()

    def _load_or_init(self):
        """Load existing metrics or initialize empty."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    self.history = json.load(f)
            except:
                self.history = {"entries": []}
        else:
            self.history = {"entries": []}

    def record_metric(self, metric_type: str, value: float, metadata: Optional[Dict] = None) -> bool:
        """Record a single metric point."""
        try:
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": metric_type,
                "value": value,
                "metadata": metadata or {}
            }

            self.history["entries"].append(entry)
            self._persist()
            return True
        except Exception as e:
            print(f"❌ MetricsHistory.record_metric error: {e}")
            return False

    def record_batch(self, metrics: List[Dict[str, Any]]) -> int:
        """Record multiple metrics at once."""
        recorded = 0
        for metric in metrics:
            metric_type = metric.get("type")
            value = metric.get("value")
            metadata = metric.get("metadata")

            if metric_type is not None and value is not None:
                entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "type": metric_type,
                    "value": value,
                    "metadata": metadata or {}
                }
                self.history["entries"].append(entry)
                recorded += 1

        if recorded > 0:
            self._persist()

        return recorded

    def get_metrics_by_type(self, metric_type: str, limit: Optional[int] = None) -> List[Dict]:
        """Retrieve metrics by type."""
        filtered = [e for e in self.history["entries"] if e.get("type") == metric_type]

        if limit:
            filtered = filtered[-limit:]

        return filtered

    def get_latest(self, metric_type: str) -> Optional[Dict]:
        """Get latest value for a metric type."""
        filtered = [e for e in self.history["entries"] if e.get("type") == metric_type]
        return filtered[-1] if filtered else None

    def _persist(self):
        """Write metrics to disk."""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"❌ MetricsHistory._persist error: {e}")


class BacktestCheckpoints:
    """Store walk-forward validation snapshots for overfitting detection."""

    def __init__(self, storage_dir: str = "data/backtests"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, hypothesis_id: str, checkpoint_data: Dict[str, Any]) -> bool:
        """Save backtest checkpoint with timestamp."""
        try:
            checkpoint = {
                "hypothesis_id": hypothesis_id,
                "saved_at": datetime.utcnow().isoformat(),
                "data": checkpoint_data
            }

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{hypothesis_id}_{timestamp}.json"
            filepath = self.storage_dir / filename

            with open(filepath, 'w') as f:
                json.dump(checkpoint, f, indent=2)

            return True
        except Exception as e:
            print(f"❌ BacktestCheckpoints.save_checkpoint error: {e}")
            return False

    def load_checkpoints(self, hypothesis_id: str) -> List[Dict[str, Any]]:
        """Load all checkpoints for a hypothesis."""
        checkpoints = []
        pattern = f"{hypothesis_id}_*.json"

        for filepath in self.storage_dir.glob(pattern):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    checkpoints.append(data)
            except:
                continue

        # Sort by timestamp
        checkpoints.sort(key=lambda x: x.get("saved_at", ""))
        return checkpoints

    def get_latest_checkpoint(self, hypothesis_id: str) -> Optional[Dict[str, Any]]:
        """Get most recent checkpoint."""
        checkpoints = self.load_checkpoints(hypothesis_id)
        return checkpoints[-1] if checkpoints else None

    def calculate_overfitting_gap(self, hypothesis_id: str) -> Optional[float]:
        """Calculate in-sample vs out-sample performance gap."""
        checkpoints = self.load_checkpoints(hypothesis_id)

        if len(checkpoints) < 2:
            return None

        try:
            latest = checkpoints[-1].get("data", {})
            in_sample_sharpe = latest.get("in_sample_sharpe", 0)
            out_sample_sharpe = latest.get("out_sample_sharpe", 0)

            if in_sample_sharpe == 0:
                return None

            gap = abs(in_sample_sharpe - out_sample_sharpe) / abs(in_sample_sharpe)
            return gap
        except:
            return None


class PortfolioHistory:
    """Track portfolio allocation changes and rebalancing decisions."""

    def __init__(self, storage_dir: str = "data/portfolio"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.storage_dir / "allocation_history.json"
        self._load_or_init()

    def _load_or_init(self):
        """Load existing history or initialize."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
            except:
                self.history = {"allocations": []}
        else:
            self.history = {"allocations": []}

    def record_allocation(self, allocation: Dict[str, float], reason: str = "") -> bool:
        """Record portfolio allocation snapshot."""
        try:
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "allocation": allocation,
                "reason": reason
            }

            self.history["allocations"].append(entry)
            self._persist()
            return True
        except Exception as e:
            print(f"❌ PortfolioHistory.record_allocation error: {e}")
            return False

    def record_rebalance(self, before: Dict[str, float], after: Dict[str, float],
                        changes: Dict[str, float]) -> bool:
        """Record rebalancing action."""
        try:
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "rebalance",
                "before": before,
                "after": after,
                "changes": changes
            }

            self.history["allocations"].append(entry)
            self._persist()
            return True
        except Exception as e:
            print(f"❌ PortfolioHistory.record_rebalance error: {e}")
            return False

    def get_allocation_timeline(self, limit: Optional[int] = None) -> List[Dict]:
        """Get historical allocation changes."""
        timeline = self.history["allocations"]

        if limit:
            timeline = timeline[-limit:]

        return timeline

    def get_latest_allocation(self) -> Optional[Dict]:
        """Get most recent allocation."""
        if self.history["allocations"]:
            return self.history["allocations"][-1]
        return None

    def _persist(self):
        """Write history to disk."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"❌ PortfolioHistory._persist error: {e}")


class DataPersistenceManager:
    """Unified interface for all persistence components."""

    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.hypotheses = HypothesisStore(f"{base_dir}/hypotheses")
        self.metrics = MetricsHistory(f"{base_dir}/metrics")
        self.backtests = BacktestCheckpoints(f"{base_dir}/backtests")
        self.portfolio = PortfolioHistory(f"{base_dir}/portfolio")

    def snapshot_system_state(self, system_data: Dict[str, Any]) -> bool:
        """Persist complete system state for recovery."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            snapshot_file = self.base_dir / f"snapshot_{timestamp}.json"

            snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "system_data": system_data
            }

            with open(snapshot_file, 'w') as f:
                json.dump(snapshot, f, indent=2)

            return True
        except Exception as e:
            print(f"❌ DataPersistenceManager.snapshot_system_state error: {e}")
            return False

    def load_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        """Load most recent system snapshot."""
        snapshots = sorted(self.base_dir.glob("snapshot_*.json"))

        if not snapshots:
            return None

        try:
            with open(snapshots[-1], 'r') as f:
                return json.load(f)
        except:
            return None

    def get_system_summary(self) -> Dict[str, Any]:
        """Generate summary of all persisted data."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "hypotheses_count": len(self.hypotheses.load_all()),
            "metrics_entries": len(self.metrics.history["entries"]),
            "portfolio_events": len(self.portfolio.history["allocations"]),
            "latest_allocation": self.portfolio.get_latest_allocation(),
            "latest_metrics": {
                "confidence": self.metrics.get_latest("confidence_avg"),
                "readiness": self.metrics.get_latest("readiness_avg"),
                "sharpe": self.metrics.get_latest("portfolio_sharpe")
            }
        }
