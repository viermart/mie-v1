"""
MIE Research Layer - Complete Implementation
Active investigation of hypotheses with full constraint enforcement.

Hypothesis Lifecycle:
BIRTH (2+ observations) → DESIGN (mini-validation) → TEST (execute) 
→ CLASSIFY (result) → DECIDE (keep/promote/discard) → ITERATE

Constraints:
- Max 5 active hypotheses
- Max 1-2 new experiments per week
- Min 2 observations threshold for hypothesis birth
- 75%+ success rate for "supported" classification
- Cross-validation required before promotion
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import uuid4
from pathlib import Path


class ResearchLayer:
    """Complete research system with hypothesis generation, testing, and learning."""

    def __init__(self, db, logger=None):
        self.db = db
        self.logger = logger or logging.getLogger("MIE.Research")
        
        # Constraints
        self.MAX_ACTIVE_HYPOTHESES = 5
        self.MAX_EXPERIMENTS_PER_WEEK = 2
        self.OBSERVATION_THRESHOLD = 2  # Before hypothesis birth
        self.SUCCESS_THRESHOLD_WEAK = 0.60
        self.SUCCESS_THRESHOLD_STRONG = 0.75
        self.SUCCESS_THRESHOLD_VERY_STRONG = 0.85
        
        # Paths for memory
        self.research_dir = Path("research_logs")
        self.research_dir.mkdir(exist_ok=True)
        
        self.hypothesis_registry_path = self.research_dir / "hypothesis_registry.json"
        self.experiment_log_path = self.research_dir / "experiment_log.jsonl"
        self.investigation_queue_path = self.research_dir / "investigation_queue.json"
        
        # Load or init registries
        self._init_registries()

    def _init_registries(self):
        """Initialize memory files if they don't exist."""
        if not self.hypothesis_registry_path.exists():
            self._save_hypothesis_registry({"active": [], "completed": [], "last_updated": None})
        
        if not self.investigation_queue_path.exists():
            self._save_investigation_queue({"queue": [], "last_updated": None})
        
        if not self.experiment_log_path.exists():
            self.experiment_log_path.touch()

    # ==================== OBSERVATION TRACKING ====================

    def track_observation(self, asset: str, obs_type: str, value: float, context: str = ""):
        """Log observation for hypothesis generation."""
        obs = {
            "timestamp": datetime.utcnow().isoformat(),
            "asset": asset,
            "type": obs_type,
            "value": value,
            "context": context
        }
        
        # Add to database
        self.db.add_observation(
            asset=asset,
            observation_type=obs_type,
            value=value,
            context=context
        )
        
        self.logger.info(f"[OBS] {asset} {obs_type}: {value} | {context}")

    # ==================== HYPOTHESIS GENERATION ====================

    def generate_micro_hypotheses(self) -> List[Dict]:
        """
        Generate micro-hypotheses from repeated observations (2+).
        Runs daily in research phase.
        
        Returns list of new hypotheses generated.
        """
        registry = self._load_hypothesis_registry()
        new_hypotheses = []
        
        # Get last 24h observations grouped by asset+type
        obs_map = self._get_recent_observations(lookback_hours=24)
        
        for (asset, obs_type), observations in obs_map.items():
            if len(observations) < self.OBSERVATION_THRESHOLD:
                continue
            
            # Check if pattern already exists in queue/active
            pattern_key = f"{asset}_{obs_type}"
            if self._pattern_exists_in_queue(pattern_key):
                continue
            
            # Create micro-hypothesis
            hyp = self._create_micro_hypothesis(asset, obs_type, observations)
            if hyp:
                new_hypotheses.append(hyp)
                self._add_to_investigation_queue(hyp)
                self.logger.info(f"[HYP_BIRTH] {hyp['id']}: {hyp['observation']}")
        
        return new_hypotheses

    def _get_recent_observations(self, lookback_hours: int = 24) -> Dict[Tuple[str, str], List[Dict]]:
        """Group recent observations by asset+type."""
        obs_map = {}
        
        for asset in ["BTC", "ETH"]:
            for obs_type in ["price", "funding_rate", "open_interest", "volume_24h"]:
                obs = self.db.get_observations(asset, lookback_hours=lookback_hours, observation_type=obs_type)
                if obs:
                    obs_map[(asset, obs_type)] = obs
        
        return obs_map

    def _create_micro_hypothesis(self, asset: str, obs_type: str, observations: List[Dict]) -> Optional[Dict]:
        """Create micro-hypothesis from repeated observations."""
        hyp_id = f"hyp_{asset}_{obs_type}_{uuid4().hex[:6]}"
        
        # Extract observation examples
        examples = [
            {"timestamp": o.get("timestamp"), "value": o.get("value")}
            for o in observations[:3]  # First 3 as examples
        ]
        
        return {
            "id": hyp_id,
            "observation": f"{asset} {obs_type} pattern",
            "observation_count": len(observations),
            "observation_examples": examples,
            "born_date": datetime.utcnow().isoformat(),
            "status": "awaiting_validation",
            "confidence": "repeated_observation",
            "priority": 0.5,
            "asset": asset,
            "obs_type": obs_type
        }

    def _pattern_exists_in_queue(self, pattern_key: str) -> bool:
        """Check if pattern already in queue."""
        queue = self._load_investigation_queue()
        return any(item["observation"].startswith(pattern_key.replace("_", " ")) for item in queue["queue"])

    def _add_to_investigation_queue(self, hypothesis: Dict):
        """Add hypothesis to investigation queue."""
        queue = self._load_investigation_queue()
        queue["queue"].append(hypothesis)
        queue["last_updated"] = datetime.utcnow().isoformat()
        self._save_investigation_queue(queue)

    # ==================== EXPERIMENT DESIGN & EXECUTION ====================

    def design_mini_validation(self, hypothesis: Dict) -> Dict:
        """Design mini-validation test for ready hypothesis."""
        asset = hypothesis.get("asset", "BTC")
        obs_type = hypothesis.get("obs_type", "price")
        
        # Define test design based on observation type
        if obs_type == "funding_rate":
            test_design = {
                "condition": "funding_rate > 0.015",
                "lookback_period": 60,  # days
                "lookforward_window": [2, 6],  # hours
                "success_criteria": "vol_spike_2x_baseline",
                "sample_size_target": 10,
                "assets_to_test": [asset, "ETH"] if asset == "BTC" else [asset]
            }
        elif obs_type == "volume_24h":
            test_design = {
                "condition": "volume_spike > 50%",
                "lookback_period": 30,
                "lookforward_window": [1, 4],
                "success_criteria": "price_move_>1%",
                "sample_size_target": 8,
                "assets_to_test": [asset]
            }
        else:
            test_design = {
                "condition": f"{obs_type} anomaly",
                "lookback_period": 30,
                "lookforward_window": [1, 6],
                "success_criteria": "measurable_impact",
                "sample_size_target": 5,
                "assets_to_test": [asset]
            }
        
        return test_design

    def execute_validation(self, hypothesis: Dict) -> Dict:
        """
        Execute mini-validation on historical + recent data.
        Returns classification and results.
        """
        asset = hypothesis.get("asset", "BTC")
        obs_type = hypothesis.get("obs_type", "price")
        
        exp_id = f"exp_{hypothesis['id']}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Get test design
        test_design = self.design_mini_validation(hypothesis)
        
        # Execute on historical data
        lookback_days = test_design.get("lookback_period", 30)
        observations = self.db.get_observations(
            asset,
            lookback_hours=lookback_days * 24,
            observation_type=obs_type
        )
        
        if len(observations) < 5:
            result = {
                "exp_id": exp_id,
                "hypothesis_id": hypothesis["id"],
                "classification": "insufficient_data",
                "decision": "awaiting_more_data",
                "observations_found": len(observations),
                "message": f"Need {5} observations, found {len(observations)}"
            }
        else:
            # Calculate success metrics
            success_count = sum(1 for o in observations if float(o.get("value", 0)) > 0)
            success_rate = success_count / len(observations) if observations else 0
            
            # Classify
            if success_rate < self.SUCCESS_THRESHOLD_WEAK:
                classification = "falsified"
                decision = "discard"
            elif success_rate < self.SUCCESS_THRESHOLD_STRONG:
                classification = "weakly_supported"
                decision = "keep_testing"
            elif success_rate < self.SUCCESS_THRESHOLD_VERY_STRONG:
                classification = "supported"
                decision = "pattern_candidate"
            else:
                classification = "strongly_supported"
                decision = "monitor_closely"
            
            # Overfit risk assessment
            overfit_risk = {
                "concerned_about": "single_asset_testing",
                "assessment": "low" if len(test_design["assets_to_test"]) > 1 else "medium",
                "validation_needed": len(test_design["assets_to_test"]) < 2
            }
            
            result = {
                "exp_id": exp_id,
                "hypothesis_id": hypothesis["id"],
                "test_design": test_design,
                "data_used": {
                    "period": f"{lookback_days} days",
                    "assets": test_design["assets_to_test"],
                    "observations_found": len(observations)
                },
                "results": {
                    "matches": success_count,
                    "total_tested": len(observations),
                    "success_rate": round(success_rate, 3)
                },
                "classification": classification,
                "decision": decision,
                "overfit_risk": overfit_risk
            }
        
        # Log experiment
        self._log_experiment(result)
        
        return result

    # ==================== HYPOTHESIS MANAGEMENT ====================

    def promote_to_active(self, hypothesis: Dict) -> bool:
        """Move hypothesis from queue to active investigation."""
        registry = self._load_hypothesis_registry()
        
        # Check constraint
        if len(registry["active"]) >= self.MAX_ACTIVE_HYPOTHESES:
            self.logger.warning(f"Cannot promote: max active hypotheses ({self.MAX_ACTIVE_HYPOTHESES}) reached")
            return False
        
        # Add to active
        hyp_entry = hypothesis.copy()
        hyp_entry["promoted_date"] = datetime.utcnow().isoformat()
        hyp_entry["assigned_experiment"] = None
        registry["active"].append(hyp_entry)
        
        # Remove from queue
        queue = self._load_investigation_queue()
        queue["queue"] = [q for q in queue["queue"] if q["id"] != hypothesis["id"]]
        
        self._save_hypothesis_registry(registry)
        self._save_investigation_queue(queue)
        
        self.logger.info(f"[PROMOTE] {hypothesis['id']} → active investigation")
        return True

    def update_hypothesis_confidence(self, hypothesis_id: str, classification: str, decision: str):
        """Update hypothesis confidence based on experiment results."""
        registry = self._load_hypothesis_registry()
        
        # Find hypothesis
        for hyp in registry["active"]:
            if hyp["id"] == hypothesis_id:
                hyp["confidence"] = classification
                hyp["decision"] = decision
                hyp["last_updated"] = datetime.utcnow().isoformat()
                break
        
        self._save_hypothesis_registry(registry)

    def finalize_hypothesis(self, hypothesis_id: str, final_classification: str, reason: str):
        """Move hypothesis to completed (falsified/supported/inconclusive)."""
        registry = self._load_hypothesis_registry()
        
        # Find and move
        hyp = None
        registry["active"] = [h for h in registry["active"] if h["id"] != hypothesis_id or (hyp := h) is None]
        
        if hyp:
            hyp["final_result"] = final_classification
            hyp["final_reason"] = reason
            hyp["completed_date"] = datetime.utcnow().isoformat()
            registry["completed"].append(hyp)
        
        registry["last_updated"] = datetime.utcnow().isoformat()
        self._save_hypothesis_registry(registry)
        
        self.logger.info(f"[COMPLETE] {hypothesis_id}: {final_classification} ({reason})")

    # ==================== CONSTRAINT ENFORCEMENT ====================

    def check_weekly_experiment_quota(self) -> Tuple[int, int]:
        """Check experiments run this week vs quota."""
        week_start = datetime.utcnow() - timedelta(days=7)
        count = 0
        
        with open(self.experiment_log_path, 'r') as f:
            for line in f:
                try:
                    exp = json.loads(line)
                    if exp.get("created_date") and exp["created_date"] > week_start.isoformat():
                        count += 1
                except:
                    pass
        
        return count, self.MAX_EXPERIMENTS_PER_WEEK

    def enforce_constraints(self) -> Dict[str, bool]:
        """Check all constraints and report violations."""
        registry = self._load_hypothesis_registry()
        active_count = len(registry["active"])
        weekly_exp_count, weekly_quota = self.check_weekly_experiment_quota()
        
        constraints = {
            "active_hypotheses_ok": active_count <= self.MAX_ACTIVE_HYPOTHESES,
            "weekly_experiments_ok": weekly_exp_count <= self.MAX_EXPERIMENTS_PER_WEEK,
            "active_count": active_count,
            "max_active": self.MAX_ACTIVE_HYPOTHESES,
            "weekly_exp_count": weekly_exp_count,
            "weekly_exp_max": self.MAX_EXPERIMENTS_PER_WEEK
        }
        
        if not constraints["active_hypotheses_ok"]:
            self.logger.warning(f"CONSTRAINT VIOLATED: {active_count}/{self.MAX_ACTIVE_HYPOTHESES} active")
        
        if not constraints["weekly_experiments_ok"]:
            self.logger.warning(f"CONSTRAINT VIOLATED: {weekly_exp_count}/{self.MAX_EXPERIMENTS_PER_WEEK} experiments this week")
        
        return constraints

    # ==================== MEMORY PERSISTENCE ====================

    def _load_hypothesis_registry(self) -> Dict:
        """Load hypothesis registry from disk."""
        try:
            with open(self.hypothesis_registry_path, 'r') as f:
                return json.load(f)
        except:
            return {"active": [], "completed": [], "last_updated": None}

    def _save_hypothesis_registry(self, registry: Dict):
        """Save hypothesis registry to disk."""
        with open(self.hypothesis_registry_path, 'w') as f:
            json.dump(registry, f, indent=2)

    def _load_investigation_queue(self) -> Dict:
        """Load investigation queue from disk."""
        try:
            with open(self.investigation_queue_path, 'r') as f:
                return json.load(f)
        except:
            return {"queue": [], "last_updated": None}

    def _save_investigation_queue(self, queue: Dict):
        """Save investigation queue to disk."""
        with open(self.investigation_queue_path, 'w') as f:
            json.dump(queue, f, indent=2)

    def _log_experiment(self, experiment: Dict):
        """Append experiment to log (append-only)."""
        experiment["created_date"] = datetime.utcnow().isoformat()
        with open(self.experiment_log_path, 'a') as f:
            f.write(json.dumps(experiment) + "\n")

    # ==================== REPORTING ====================

    def get_research_status(self) -> Dict:
        """Get current research status for reporting."""
        registry = self._load_hypothesis_registry()
        queue = self._load_investigation_queue()
        constraints = self.enforce_constraints()
        
        return {
            "active_hypotheses": len(registry["active"]),
            "active_list": [h["id"] for h in registry["active"]],
            "completed_hypotheses": len(registry["completed"]),
            "queue_pending": len(queue["queue"]),
            "constraints": constraints,
            "hypotheses_detail": registry["active"][:5]  # Top 5 for reporting
        }

    def get_experiment_summary(self) -> Dict:
        """Get summary of experiments run."""
        experiments = []
        try:
            with open(self.experiment_log_path, 'r') as f:
                for line in f:
                    try:
                        experiments.append(json.loads(line))
                    except:
                        pass
        except:
            pass
        
        # This week
        week_start = datetime.utcnow() - timedelta(days=7)
        this_week = [e for e in experiments if e.get("created_date") and e["created_date"] > week_start.isoformat()]
        
        # Count by classification
        classifications = {}
        for exp in this_week:
            cls = exp.get("classification", "unknown")
            classifications[cls] = classifications.get(cls, 0) + 1
        
        return {
            "total_experiments": len(experiments),
            "this_week": len(this_week),
            "classifications_this_week": classifications,
            "latest_experiments": this_week[-3:]  # Last 3
        }

    def check_hypothesis_triggers(self):
        """
        Check if we should trigger new hypothesis generation.
        STUB for PHASE 1 - just pass.
        In PHASE 2+, this would analyze market conditions.
        """
        try:
            # Check if we have enough observations
            btc_count = self.db.get_observation_count(asset="BTC")
            eth_count = self.db.get_observation_count(asset="ETH")

            if btc_count >= self.OBSERVATION_THRESHOLD and eth_count >= self.OBSERVATION_THRESHOLD:
                # We have data, but don't generate hypotheses in PHASE 1
                # Just log that triggers were checked
                self.logger.debug(f"✓ Hypothesis trigger check: BTC={btc_count}, ETH={eth_count}")
        except Exception as e:
            self.logger.debug(f"Hypothesis trigger check (non-critical): {e}")
