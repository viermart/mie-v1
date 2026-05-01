#!/usr/bin/env python3
"""
Run Quality Gate audit on all existing experiments.

This script:
1. Reads all experiments from experiment_log.jsonl
2. Validates each with ResearchQualityGate
3. Moves invalid ones to invalid_experiments.jsonl
4. Creates research challenges for failures
5. Generates audit report

Usage:
    python3 run_quality_gate.py
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from mie.research_quality_gate import ResearchQualityGate

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("QualityGateAudit")


def audit_experiments():
    """Audit all existing experiments in experiment_log.jsonl"""

    quality_gate = ResearchQualityGate(base_dir="research_logs")
    experiment_log_path = Path("research_logs/experiment_log.jsonl")

    if not experiment_log_path.exists():
        logger.error("❌ experiment_log.jsonl not found")
        return

    logger.info("="*70)
    logger.info("🔍 RESEARCH QUALITY GATE AUDIT")
    logger.info("="*70)

    # Read all experiments
    experiments = []
    with open(experiment_log_path, "r") as f:
        for line in f:
            if line.strip():
                try:
                    experiments.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"⚠️  Skipped malformed JSON line")

    logger.info(f"📊 Loaded {len(experiments)} experiments for validation\n")

    # Validate each experiment
    valid_count = 0
    invalid_count = 0
    failures_by_type = {}

    for i, exp in enumerate(experiments, 1):
        exp_id = exp.get("exp_id", "unknown")
        hyp_id = exp.get("hypothesis_id", "unknown")

        is_valid, failure_reasons = quality_gate.validate(exp)

        if is_valid:
            valid_count += 1
            logger.info(f"[{i:3d}] ✅ PASS: {exp_id}")
        else:
            invalid_count += 1
            logger.warning(f"[{i:3d}] ❌ FAIL: {exp_id}")

            # Count failure types
            for reason in failure_reasons:
                reason_type = reason.split(":")[0]
                failures_by_type[reason_type] = failures_by_type.get(reason_type, 0) + 1

            # Log details
            for reason in failure_reasons:
                logger.warning(f"        → {reason}")

            # Archive the invalid experiment
            quality_gate.archive_invalid_experiment(exp, failure_reasons)
            logger.info(f"        📋 Archived as invalid, created research challenge")

    # Print summary
    logger.info("\n" + "="*70)
    logger.info("📊 AUDIT SUMMARY")
    logger.info("="*70)
    logger.info(f"Total experiments audited:  {len(experiments)}")
    logger.info(f"  ✅ Valid:                 {valid_count}")
    logger.info(f"  ❌ Invalid:               {invalid_count}")

    if failures_by_type:
        logger.info(f"\n❌ Failure breakdown:")
        for failure_type, count in sorted(failures_by_type.items(), key=lambda x: -x[1]):
            logger.info(f"  • {failure_type}: {count}")

    # Get quality metrics
    metrics = quality_gate.get_quality_metrics()
    logger.info(f"\n📈 Quality Metrics:")
    logger.info(f"  Invalid experiments archived: {metrics.get('invalid_experiments', 0)}")
    logger.info(f"  Research challenges created: {metrics.get('open_research_challenges', 0)}")

    logger.info("\n" + "="*70)
    logger.info("✅ Quality gate audit complete")
    logger.info("="*70)


if __name__ == "__main__":
    audit_experiments()
