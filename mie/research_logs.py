"""
MIE Research Logs Manager - Persistent audit trail for all research activities.

Manages:
- experiment_log.jsonl (append-only)
- daily_learning.jsonl (append-only)
- weekly_learning.jsonl (append-only)
- monthly_learning.jsonl (append-only)
- uncertainty_map.json
- error_log.json
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class ResearchLogManager:
    """Manage persistent logs for research activities with audit trail."""

    def __init__(self, base_dir: str = "research_logs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger("MIE.ResearchLogs")

        # Define paths
        self.experiment_log_path = self.base_dir / "experiment_log.jsonl"
        self.daily_learning_path = self.base_dir / "daily_learning.jsonl"
        self.weekly_learning_path = self.base_dir / "weekly_learning.jsonl"
        self.monthly_learning_path = self.base_dir / "monthly_learning.jsonl"
        self.invalid_experiments_path = self.base_dir / "invalid_experiments.jsonl"
        self.research_challenges_path = self.base_dir / "research_challenges.jsonl"
        self.uncertainty_map_path = self.base_dir / "uncertainty_map.json"
        self.error_log_path = self.base_dir / "error_log.json"

        # Initialize files if they don't exist
        self._init_files()

    def _init_files(self):
        """Initialize log files if they don't exist."""
        # Create append-only files
        for path in [
            self.experiment_log_path,
            self.daily_learning_path,
            self.weekly_learning_path,
            self.monthly_learning_path,
            self.invalid_experiments_path,
            self.research_challenges_path
        ]:
            if not path.exists():
                path.touch()
                self.logger.info(f"✅ Initialized {path.name}")

        # Create JSON files with initial structure
        if not self.uncertainty_map_path.exists():
            self._save_uncertainty_map({
                "initialized_at": datetime.utcnow().isoformat(),
                "confident_about": [],
                "needs_more_data": [],
                "blind_spots": []
            })

        if not self.error_log_path.exists():
            self._save_error_log({
                "initialized_at": datetime.utcnow().isoformat(),
                "errors": []
            })

    # ==================== EXPERIMENT LOG ====================

    def append_experiment(self, exp_data: Dict) -> bool:
        """
        Append experiment result to experiment_log.jsonl.

        Format:
        {
            "exp_id": str,
            "hypothesis_id": str,
            "created_date": ISO,
            "description": str,
            "test_design": dict,
            "results": dict,
            "classification": str,
            "overfit_risk": dict,
            "timestamp": ISO
        }
        """
        try:
            # Add timestamp if not present
            if "timestamp" not in exp_data:
                exp_data["timestamp"] = datetime.utcnow().isoformat()

            # Append to JSONL (one JSON per line)
            with open(self.experiment_log_path, "a") as f:
                f.write(json.dumps(exp_data) + "\n")

            self.logger.info(f"📝 Experiment logged: {exp_data.get('exp_id')}")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error appending experiment: {e}")
            return False

    def get_experiment_log(self, limit: Optional[int] = None) -> List[Dict]:
        """Read all experiments from experiment_log.jsonl."""
        try:
            experiments = []
            with open(self.experiment_log_path, "r") as f:
                for line in f:
                    if line.strip():
                        experiments.append(json.loads(line))

            if limit:
                experiments = experiments[-limit:]

            return experiments

        except Exception as e:
            self.logger.error(f"❌ Error reading experiment log: {e}")
            return []

    # ==================== LEARNING LOGS ====================

    def append_learning(self, log_type: str, content: Dict) -> bool:
        """
        Append learning reflection (daily/weekly/monthly).

        log_type: "daily" | "weekly" | "monthly"
        content: dict with learning content
        """
        try:
            if log_type == "daily":
                path = self.daily_learning_path
            elif log_type == "weekly":
                path = self.weekly_learning_path
            elif log_type == "monthly":
                path = self.monthly_learning_path
            else:
                self.logger.warning(f"Unknown log_type: {log_type}")
                return False

            # Add timestamp and type
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": log_type,
                "content": content
            }

            # Append to JSONL
            with open(path, "a") as f:
                f.write(json.dumps(entry) + "\n")

            self.logger.info(f"📝 {log_type.upper()} learning logged")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error appending {log_type} learning: {e}")
            return False

    def get_learning_log(self, log_type: str, limit: Optional[int] = None) -> List[Dict]:
        """Read learning logs by type."""
        try:
            if log_type == "daily":
                path = self.daily_learning_path
            elif log_type == "weekly":
                path = self.weekly_learning_path
            elif log_type == "monthly":
                path = self.monthly_learning_path
            else:
                return []

            entries = []
            with open(path, "r") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))

            if limit:
                entries = entries[-limit:]

            return entries

        except Exception as e:
            self.logger.error(f"❌ Error reading {log_type} learning: {e}")
            return []

    # ==================== UNCERTAINTY MAP ====================

    def _load_uncertainty_map(self) -> Dict:
        """Load uncertainty map."""
        try:
            with open(self.uncertainty_map_path, "r") as f:
                return json.load(f)
        except:
            return {
                "confident_about": [],
                "needs_more_data": [],
                "blind_spots": []
            }

    def _save_uncertainty_map(self, data: Dict) -> bool:
        """Save uncertainty map."""
        try:
            with open(self.uncertainty_map_path, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"❌ Error saving uncertainty map: {e}")
            return False

    def add_uncertainty(self, category: str, item: str) -> bool:
        """
        Add item to uncertainty map.

        category: "confident_about" | "needs_more_data" | "blind_spots"
        """
        try:
            uncertainty = self._load_uncertainty_map()

            if category not in uncertainty:
                uncertainty[category] = []

            if item not in uncertainty[category]:
                uncertainty[category].append(item)

            uncertainty["last_updated"] = datetime.utcnow().isoformat()
            return self._save_uncertainty_map(uncertainty)

        except Exception as e:
            self.logger.error(f"❌ Error adding uncertainty: {e}")
            return False

    # ==================== ERROR LOG ====================

    def _load_error_log(self) -> Dict:
        """Load error log."""
        try:
            with open(self.error_log_path, "r") as f:
                return json.load(f)
        except:
            return {"errors": []}

    def _save_error_log(self, data: Dict) -> bool:
        """Save error log."""
        try:
            with open(self.error_log_path, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"❌ Error saving error log: {e}")
            return False

    def log_error(self, error_type: str, description: str, context: Dict = None) -> bool:
        """Log an error for analysis."""
        try:
            error_log = self._load_error_log()

            error_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": error_type,
                "description": description,
                "context": context or {}
            }

            if "errors" not in error_log:
                error_log["errors"] = []

            error_log["errors"].append(error_entry)
            error_log["last_updated"] = datetime.utcnow().isoformat()

            return self._save_error_log(error_log)

        except Exception as e:
            self.logger.error(f"❌ Error logging error: {e}")
            return False

    # ==================== SUMMARY & STATS ====================

    def get_research_summary(self) -> Dict:
        """Generate summary of all research activities."""
        try:
            experiments = self.get_experiment_log()
            daily_logs = self.get_learning_log("daily")
            weekly_logs = self.get_learning_log("weekly")
            monthly_logs = self.get_learning_log("monthly")
            uncertainty = self._load_uncertainty_map()
            errors = self._load_error_log()

            # Count classifications
            classifications = {}
            for exp in experiments:
                c = exp.get("classification", "unknown")
                classifications[c] = classifications.get(c, 0) + 1

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "experiments": {
                    "total": len(experiments),
                    "classifications": classifications
                },
                "learning_logs": {
                    "daily": len(daily_logs),
                    "weekly": len(weekly_logs),
                    "monthly": len(monthly_logs)
                },
                "uncertainty": {
                    "confident_about": len(uncertainty.get("confident_about", [])),
                    "needs_more_data": len(uncertainty.get("needs_more_data", [])),
                    "blind_spots": len(uncertainty.get("blind_spots", []))
                },
                "errors": {
                    "total": len(errors.get("errors", []))
                }
            }

        except Exception as e:
            self.logger.error(f"❌ Error generating summary: {e}")
            return {}

    def print_summary(self):
        """Print research summary to logs."""
        summary = self.get_research_summary()

        self.logger.info("\n" + "="*70)
        self.logger.info("📊 RESEARCH LOG SUMMARY")
        self.logger.info("="*70)
        self.logger.info(f"Experiments: {summary.get('experiments', {}).get('total', 0)}")
        self.logger.info(f"  Classifications: {summary.get('experiments', {}).get('classifications', {})}")
        self.logger.info(f"Learning Logs: {summary.get('learning_logs', {})}")
        self.logger.info(f"Uncertainty: {summary.get('uncertainty', {})}")
        self.logger.info(f"Errors: {summary.get('errors', {}).get('total', 0)}")
        self.logger.info("="*70 + "\n")
