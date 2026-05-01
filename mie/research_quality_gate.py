"""
Research Quality Gate V1 - Automatic validation of experiment designs and results.

Prevents invalid experiments from contaminating the research system by:
- Detecting tautologies (circular logic)
- Enforcing minimum sample sizes
- Validating temporal separation (lookforward window)
- Ensuring specific, testable conditions
- Preventing success criteria that match conditions

Invalid experiments are archived as "invalid_quality_gate" and converted into
research challenges to drive improvements in hypothesis testing.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path


class ResearchQualityGate:
    """Automatic validation of research experiments."""

    # Configuration constants
    MIN_SAMPLE_SIZE = 10  # Require at least 10 observations for statistical significance
    MAX_SUCCESS_RATE_FOR_OBVIOUS = 0.95  # Pattern >95% success likely too simple
    TAUTOLOGY_KEYWORDS = {
        "price": ["anomaly", "change", "move", "impact", "fluctuation"],
        "volume": ["surge", "spike", "volume", "activity"],
        "funding": ["extreme", "abnormal", "high"]
    }

    # Semantic equivalence patterns (condition -> invalid success criteria)
    INVALID_COMBINATIONS = {
        "price anomaly": ["measurable_impact", "price_change", "price_move", "price_movement"],
        "volume spike": ["volume_increase", "volume_change", "trading_activity"],
    }

    def __init__(self, base_dir: str = "research_logs"):
        self.base_dir = Path(base_dir)
        self.logger = logging.getLogger("MIE.QualityGate")
        self.invalid_experiments_path = self.base_dir / "invalid_experiments.jsonl"
        self.research_challenges_path = self.base_dir / "research_challenges.jsonl"

    def validate(self, result: Dict, hypothesis: Dict = None) -> Tuple[bool, List[str]]:
        """
        Validate experiment result. Returns (is_valid, reasons_if_invalid).

        Args:
            result: Experiment result from execute_validation()
            hypothesis: Original hypothesis (optional, for context)

        Returns:
            (is_valid: bool, failure_reasons: List[str])
            - If valid: (True, [])
            - If invalid: (False, ["reason1", "reason2"])
        """
        failures = []

        # Extract data
        test_design = result.get("test_design", {})
        data_used = result.get("data_used", {})
        results = result.get("results", {})
        classification = result.get("classification", "unknown")

        # Skip validation for non-testable classifications
        if classification in ["insufficient_data", "error"]:
            return True, []  # These aren't invalid, just incomplete

        # ========== QUALITY GATE 1: Sample Size ==========
        total_tested = results.get("total_tested", 0)
        if total_tested < self.MIN_SAMPLE_SIZE:
            failures.append(
                f"insufficient_sample_size: tested {total_tested} observations, "
                f"need at least {self.MIN_SAMPLE_SIZE} for statistical significance"
            )

        # ========== QUALITY GATE 2: Obvious/Tautological Logic ==========
        # Detect when success rate is suspiciously high (>95%) with small sample
        success_rate = results.get("success_rate", 0)
        if total_tested < 20 and success_rate >= self.MAX_SUCCESS_RATE_FOR_OBVIOUS:
            failures.append(
                f"tautology_risk: {success_rate*100:.1f}% success rate on {total_tested} "
                f"observations - likely circular logic or self-evident condition"
            )

        # ========== QUALITY GATE 3: Condition-Success Criteria Equivalence ==========
        condition = test_design.get("condition", "").lower()
        success_criteria = test_design.get("success_criteria", "").lower()

        # Direct semantic equivalence check
        for invalid_cond, invalid_success_list in self.INVALID_COMBINATIONS.items():
            if invalid_cond in condition:
                for invalid_success in invalid_success_list:
                    if invalid_success in success_criteria:
                        failures.append(
                            f"tautology: condition '{condition}' and success_criteria "
                            f"'{success_criteria}' are semantically equivalent - "
                            f"measuring the same thing twice"
                        )
                        break

        # ========== QUALITY GATE 4: Lookforward Window Validation ==========
        # Ensure temporal separation between condition and outcome
        lookforward_window = test_design.get("lookforward_window", [0, 0])
        if isinstance(lookforward_window, list) and len(lookforward_window) >= 2:
            min_hours = lookforward_window[0]
            if min_hours <= 0:
                failures.append(
                    f"no_temporal_separation: lookforward_window starts at {min_hours}h - "
                    f"condition and outcome must be separated in time (use [2,6] minimum)"
                )

        # ========== QUALITY GATE 5: Condition Specificity ==========
        # Flag vague, non-testable conditions
        vague_indicators = ["anomaly", "unusual", "change", "maybe", "could"]
        if any(vague in condition for vague in vague_indicators):
            # Allow if success criteria is very specific
            if not self._is_specific_success_criteria(success_criteria):
                failures.append(
                    f"non_specific_condition: '{condition}' is too vague - "
                    f"must be measurable and objective (e.g. 'funding_rate > 0.015')"
                )

        # ========== QUALITY GATE 6: Success Criteria Specificity ==========
        if "impact" in success_criteria or "change" in success_criteria:
            if not self._is_specific_success_criteria(success_criteria):
                failures.append(
                    f"non_specific_success_criteria: '{success_criteria}' is too vague - "
                    f"must define measurable threshold (e.g. 'vol_spike_2x_baseline')"
                )

        # Return validation result
        is_valid = len(failures) == 0
        return is_valid, failures

    def _is_specific_success_criteria(self, criteria: str) -> bool:
        """Check if success criteria is specific and measurable."""
        specific_patterns = [
            "2x", "3x", "greater_than", "less_than", ">", "<", "threshold",
            "baseline", "spike", "drop", "percent", "%", "basis_point", "bp"
        ]
        return any(pattern in criteria.lower() for pattern in specific_patterns)

    def archive_invalid_experiment(self, result: Dict, failure_reasons: List[str]) -> bool:
        """
        Archive experiment as invalid and create research challenge.

        Returns True if successful.
        """
        try:
            # Mark as invalid in result
            result_marked = result.copy()
            result_marked["classification"] = "invalid_quality_gate"
            result_marked["quality_gate_failures"] = failure_reasons
            result_marked["archived_at"] = datetime.utcnow().isoformat()

            # Append to invalid_experiments.jsonl
            with open(self.invalid_experiments_path, "a") as f:
                f.write(json.dumps(result_marked) + "\n")

            self.logger.info(
                f"📋 Archived invalid experiment {result.get('exp_id')} - "
                f"Reasons: {'; '.join(failure_reasons[:2])}"
            )

            # Create research challenge
            challenge = self._create_research_challenge(result, failure_reasons)
            self.append_research_challenge(challenge)

            return True

        except Exception as e:
            self.logger.error(f"❌ Error archiving invalid experiment: {e}")
            return False

    def _create_research_challenge(self, result: Dict, failure_reasons: List[str]) -> Dict:
        """Create a research challenge from a failed experiment."""
        exp_id = result.get("exp_id", "unknown")
        hyp_id = result.get("hypothesis_id", "unknown")
        test_design = result.get("test_design", {})

        # Determine what needs fixing based on failure type
        primary_failure = failure_reasons[0] if failure_reasons else "unknown"

        if "tautology" in primary_failure:
            what_needs_fixing = (
                "Redesign test to use future outcome, not circular logic. "
                "Condition must be observable BEFORE outcome measurement."
            )
            suggested_next = (
                "Define: specific condition at time T, specific measurable outcome at T+X. "
                "Use lookforward_window with X > 1 hour."
            )

        elif "insufficient_sample" in primary_failure:
            lookback = test_design.get('lookback_period', 30)
            what_needs_fixing = (
                f"Increase lookback_period to get {self.MIN_SAMPLE_SIZE}+ observations. "
                f"Current lookback: {lookback} days"
            )
            suggested_next = (
                f"Extend lookback_period to {lookback * 2} days "
                f"or find more frequent observation type."
            )

        elif "non_specific" in primary_failure:
            what_needs_fixing = (
                "Replace vague terms (anomaly, change, unusual) with specific, "
                "measurable thresholds."
            )
            suggested_next = (
                "Example: Replace 'price anomaly' with "
                "'price_pct_change > 2%' or 'funding_rate > 0.015'"
            )

        elif "temporal_separation" in primary_failure:
            what_needs_fixing = (
                "Add lookforward window with time gap between condition and outcome. "
                f"Current: {test_design.get('lookforward_window', [0, 0])}"
            )
            suggested_next = (
                "Set lookforward_window: [2, 6] to measure outcome 2-6 hours after "
                "condition is observed."
            )

        else:
            what_needs_fixing = "Review all quality gate failures and redesign test."
            suggested_next = "Analyze failure reasons and propose specific improvements."

        challenge_id = f"challenge_{hyp_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        return {
            "challenge_id": challenge_id,
            "hypothesis_id": hyp_id,
            "failed_experiment_id": exp_id,
            "created_at": datetime.utcnow().isoformat(),
            "failure_reasons": failure_reasons,
            "what_needs_fixing": what_needs_fixing,
            "suggested_next_test": suggested_next,
            "priority": "high" if "tautology" in primary_failure else "medium",
            "status": "open"
        }

    def append_research_challenge(self, challenge: Dict) -> bool:
        """Append challenge to research_challenges.jsonl."""
        try:
            with open(self.research_challenges_path, "a") as f:
                f.write(json.dumps(challenge) + "\n")

            self.logger.info(
                f"🔍 Created research challenge {challenge.get('challenge_id')} - "
                f"Priority: {challenge.get('priority')}"
            )
            return True

        except Exception as e:
            self.logger.error(f"❌ Error appending research challenge: {e}")
            return False

    def get_quality_metrics(self) -> Dict:
        """Get summary of quality gate enforcement."""
        try:
            invalid_count = 0
            invalid_reasons = {}

            if self.invalid_experiments_path.exists():
                with open(self.invalid_experiments_path, "r") as f:
                    for line in f:
                        if line.strip():
                            invalid_count += 1
                            data = json.loads(line)
                            for reason in data.get("quality_gate_failures", []):
                                reason_type = reason.split(":")[0]
                                invalid_reasons[reason_type] = invalid_reasons.get(reason_type, 0) + 1

            challenge_count = 0
            if self.research_challenges_path.exists():
                with open(self.research_challenges_path, "r") as f:
                    for line in f:
                        if line.strip():
                            challenge_count += 1

            return {
                "invalid_experiments": invalid_count,
                "invalid_reasons": invalid_reasons,
                "open_research_challenges": challenge_count,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.logger.error(f"❌ Error calculating quality metrics: {e}")
            return {}
