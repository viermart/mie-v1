"""
Configuration & Parameter Manager for MIE V1 Research Layer
Dynamic tuning of system constraints and thresholds.

Components:
- ConfigStore: YAML/JSON config persistence
- ConstraintManager: Runtime constraint tuning
- ParameterValidator: Validate parameter changes
- ConfigHistory: Track configuration changes
"""

import json
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Constraint:
    """System constraint definition."""
    name: str
    current_value: float
    min_value: float
    max_value: float
    description: str
    last_modified: str
    modified_by: str = "system"


@dataclass
class ConstraintChange:
    """Record of constraint modification."""
    constraint_name: str
    old_value: float
    new_value: float
    timestamp: str
    changed_by: str
    reason: str


class ConfigStore:
    """Persist configuration to disk."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "mie_config.yaml"

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from disk."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return yaml.safe_load(f) or {}
            except:
                return self._default_config()
        return self._default_config()

    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to disk."""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            return True
        except Exception as e:
            print(f"❌ ConfigStore.save_config error: {e}")
            return False

    def _default_config(self) -> Dict[str, Any]:
        """Default MIE V1 configuration."""
        return {
            "system": {
                "name": "MIE V1",
                "version": "1.0.0",
                "environment": "production",
                "logging_level": "INFO"
            },
            "constraints": {
                "max_active_hypotheses": 5,
                "max_experiments_per_week": 2,
                "observation_threshold": 2,
                "max_portfolio_concentration": 0.4,
                "min_hypothesis_allocation": 0.1,
                "max_confidence_threshold": 0.95,
                "min_confidence_threshold": 0.3
            },
            "thresholds": {
                "volatility_expansion_multiplier": 1.5,
                "volume_spike_multiplier": 1.5,
                "correlation_strength": 0.7,
                "data_freshness_hours": 2,
                "data_completeness_target": 0.9
            },
            "backtesting": {
                "lookback_periods": [90, 180, 365],
                "walk_forward_window_days": 30,
                "min_backtest_samples": 50,
                "max_drawdown_acceptable": 0.25,
                "min_sharpe_acceptable": 1.0
            },
            "reporting": {
                "daily_report_hour": 8,
                "weekly_report_day": "sunday",
                "weekly_report_hour": 17,
                "telegram_enabled": True,
                "email_enabled": False
            },
            "research": {
                "confidence_decay_days": 7,
                "feedback_confidence_delta": 0.15,
                "hypothesis_timeout_days": 30,
                "max_hypothesis_age_days": 90
            }
        }


class ConstraintManager:
    """Runtime constraint management."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.constraints: Dict[str, Constraint] = {}
        self.constraint_history: List[ConstraintChange] = []
        self._initialize_constraints(config or {})

    def _initialize_constraints(self, config: Dict[str, Any]) -> None:
        """Initialize constraints from config."""
        constraints_config = config.get("constraints", {})
        thresholds_config = config.get("thresholds", {})

        # Create constraint definitions
        constraint_defs = {
            "max_active_hypotheses": (5, 1, 100, "Maximum simultaneously active hypotheses"),
            "max_experiments_per_week": (2, 1, 10, "Max new hypothesis experiments per week"),
            "observation_threshold": (2, 1, 10, "Observations required to support hypothesis"),
            "max_portfolio_concentration": (0.4, 0.1, 1.0, "Max allocation to single hypothesis"),
            "min_hypothesis_allocation": (0.1, 0.01, 0.5, "Minimum allocation per hypothesis"),
            "volatility_expansion_multiplier": (1.5, 1.0, 3.0, "Volatility spike detection threshold"),
            "volume_spike_multiplier": (1.5, 1.0, 3.0, "Volume spike detection threshold"),
            "correlation_strength": (0.7, 0.3, 1.0, "Minimum correlation for detection"),
        }

        for name, (default, min_val, max_val, desc) in constraint_defs.items():
            value = constraints_config.get(name) or thresholds_config.get(name) or default
            self.constraints[name] = Constraint(
                name=name,
                current_value=value,
                min_value=min_val,
                max_value=max_val,
                description=desc,
                last_modified=datetime.utcnow().isoformat()
            )

    def get_constraint(self, name: str) -> Optional[Constraint]:
        """Get constraint by name."""
        return self.constraints.get(name)

    def get_value(self, name: str) -> Optional[float]:
        """Get constraint value."""
        constraint = self.constraints.get(name)
        return constraint.current_value if constraint else None

    def set_constraint(self, name: str, value: float, reason: str = "",
                      changed_by: str = "system") -> bool:
        """Update constraint value."""
        constraint = self.constraints.get(name)

        if not constraint:
            return False

        if value < constraint.min_value or value > constraint.max_value:
            print(f"❌ Constraint {name} out of bounds: {value} "
                  f"(min: {constraint.min_value}, max: {constraint.max_value})")
            return False

        old_value = constraint.current_value

        # Record change
        change = ConstraintChange(
            constraint_name=name,
            old_value=old_value,
            new_value=value,
            timestamp=datetime.utcnow().isoformat(),
            changed_by=changed_by,
            reason=reason
        )
        self.constraint_history.append(change)

        # Update constraint
        constraint.current_value = value
        constraint.last_modified = datetime.utcnow().isoformat()
        constraint.modified_by = changed_by

        print(f"✅ Constraint {name}: {old_value} → {value}")
        return True

    def get_all_constraints(self) -> Dict[str, Constraint]:
        """Get all constraints."""
        return self.constraints.copy()

    def get_history(self, constraint_name: Optional[str] = None,
                   limit: Optional[int] = None) -> List[ConstraintChange]:
        """Get constraint change history."""
        history = self.constraint_history

        if constraint_name:
            history = [c for c in history if c.constraint_name == constraint_name]

        if limit:
            history = history[-limit:]

        return history


class ParameterValidator:
    """Validate parameter changes."""

    def __init__(self):
        self.validation_rules = {
            "max_active_hypotheses": [
                ("greater_than_zero", lambda x: x > 0),
                ("less_than_100", lambda x: x <= 100)
            ],
            "max_experiments_per_week": [
                ("greater_than_zero", lambda x: x > 0),
                ("less_than_10", lambda x: x <= 10)
            ],
            "max_portfolio_concentration": [
                ("between_0_and_1", lambda x: 0 < x <= 1.0),
                ("reasonable_limit", lambda x: x <= 0.5)
            ]
        }

    def validate(self, parameter_name: str, value: float) -> tuple[bool, str]:
        """Validate parameter value."""
        rules = self.validation_rules.get(parameter_name, [])

        for rule_name, rule_func in rules:
            try:
                if not rule_func(value):
                    return False, f"Failed validation: {rule_name}"
            except Exception as e:
                return False, f"Validation error: {e}"

        return True, "Valid"

    def validate_batch(self, parameters: Dict[str, float]) -> Dict[str, tuple[bool, str]]:
        """Validate multiple parameters."""
        results = {}
        for name, value in parameters.items():
            results[name] = self.validate(name, value)
        return results


class ConfigManager:
    """Unified configuration interface."""

    def __init__(self, config_dir: str = "config"):
        self.store = ConfigStore(config_dir)
        self.config = self.store.load_config()
        self.constraints = ConstraintManager(self.config)
        self.validator = ParameterValidator()

    def load_config(self) -> Dict[str, Any]:
        """Load or reload configuration."""
        self.config = self.store.load_config()
        self.constraints = ConstraintManager(self.config)
        return self.config

    def save_config(self) -> bool:
        """Persist current configuration."""
        return self.store.save_config(self.config)

    def get_setting(self, section: str, key: str) -> Any:
        """Get a configuration setting."""
        try:
            return self.config[section][key]
        except KeyError:
            return None

    def set_setting(self, section: str, key: str, value: Any) -> bool:
        """Set a configuration setting."""
        if section not in self.config:
            self.config[section] = {}

        self.config[section][key] = value
        return self.save_config()

    def update_constraint(self, name: str, value: float, reason: str = "") -> bool:
        """Update constraint and persist."""
        success = self.constraints.set_constraint(name, value, reason)

        if success:
            # Update config file
            if "constraints" not in self.config:
                self.config["constraints"] = {}
            self.config["constraints"][name] = value
            self.save_config()

        return success

    def get_constraints_report(self) -> Dict[str, Any]:
        """Get comprehensive constraint report."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "constraints": {
                name: {
                    "value": c.current_value,
                    "min": c.min_value,
                    "max": c.max_value,
                    "description": c.description,
                    "last_modified": c.last_modified,
                    "modified_by": c.modified_by
                }
                for name, c in self.constraints.get_all_constraints().items()
            },
            "recent_changes": [
                {
                    "constraint": c.constraint_name,
                    "old_value": c.old_value,
                    "new_value": c.new_value,
                    "timestamp": c.timestamp,
                    "reason": c.reason
                }
                for c in self.constraints.get_history(limit=10)
            ]
        }
