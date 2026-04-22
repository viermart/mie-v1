"""
System Health Monitor for MIE V1 Research Layer
Tracks component health, data quality, and system state.

Components:
- ComponentHealthTracker: Monitor each component's status
- DataQualityMonitor: Track data freshness and completeness
- SystemStateAnalyzer: Aggregate health into system-wide status
- HealthAlertGenerator: Trigger alerts on degradation
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class HealthStatus(Enum):
    """Component health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"


@dataclass
class ComponentHealth:
    """Health state of a single component."""
    name: str
    status: str
    last_update: str
    error_count: int
    success_count: int
    uptime_percent: float
    last_error: Optional[str] = None
    latency_ms: float = 0.0
    custom_metrics: Dict[str, float] = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "status": self.status,
            "last_update": self.last_update,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "uptime_percent": self.uptime_percent,
            "last_error": self.last_error,
            "latency_ms": self.latency_ms,
            "custom_metrics": self.custom_metrics or {}
        }


@dataclass
class HealthAlert:
    """Alert triggered by health monitoring."""
    timestamp: str
    severity: str
    component: str
    message: str
    value: float
    threshold: float
    recommendation: str

    def to_dict(self) -> Dict:
        return asdict(self)


class ComponentHealthTracker:
    """Track individual component health."""

    def __init__(self, component_name: str):
        self.name = component_name
        self.error_count = 0
        self.success_count = 0
        self.last_update = datetime.utcnow().isoformat()
        self.last_error = None
        self.latency_ms = 0.0
        self.custom_metrics: Dict[str, float] = {}

    def record_success(self, latency_ms: float = 0) -> None:
        """Record successful operation."""
        self.success_count += 1
        self.last_update = datetime.utcnow().isoformat()
        self.latency_ms = latency_ms

    def record_error(self, error_msg: str) -> None:
        """Record failed operation."""
        self.error_count += 1
        self.last_update = datetime.utcnow().isoformat()
        self.last_error = error_msg

    def record_metric(self, metric_name: str, value: float) -> None:
        """Record custom metric."""
        self.custom_metrics[metric_name] = value

    def get_uptime_percent(self) -> float:
        """Calculate uptime percentage."""
        total = self.success_count + self.error_count
        if total == 0:
            return 100.0

        return (self.success_count / total) * 100

    def get_status(self) -> str:
        """Determine health status."""
        uptime = self.get_uptime_percent()

        if uptime >= 95:
            return HealthStatus.HEALTHY.value
        elif uptime >= 80:
            return HealthStatus.DEGRADED.value
        elif uptime >= 50:
            return HealthStatus.CRITICAL.value
        else:
            return HealthStatus.OFFLINE.value

    def get_health(self) -> ComponentHealth:
        """Get component health snapshot."""
        return ComponentHealth(
            name=self.name,
            status=self.get_status(),
            last_update=self.last_update,
            error_count=self.error_count,
            success_count=self.success_count,
            uptime_percent=self.get_uptime_percent(),
            last_error=self.last_error,
            latency_ms=self.latency_ms,
            custom_metrics=self.custom_metrics.copy()
        )


class DataQualityMonitor:
    """Monitor data freshness and completeness."""

    def __init__(self):
        self.last_price_update: Dict[str, str] = {}
        self.last_volume_update: Dict[str, str] = {}
        self.price_data_count: Dict[str, int] = {}
        self.volume_data_count: Dict[str, int] = {}
        self.missing_candles: Dict[str, int] = {}

    def record_price_update(self, asset: str) -> None:
        """Record price data arrival."""
        self.last_price_update[asset] = datetime.utcnow().isoformat()

    def record_volume_update(self, asset: str) -> None:
        """Record volume data arrival."""
        self.last_volume_update[asset] = datetime.utcnow().isoformat()

    def add_price_data(self, asset: str, count: int) -> None:
        """Record received price candles."""
        self.price_data_count[asset] = self.price_data_count.get(asset, 0) + count

    def add_volume_data(self, asset: str, count: int) -> None:
        """Record received volume candles."""
        self.volume_data_count[asset] = self.volume_data_count.get(asset, 0) + count

    def record_missing_candles(self, asset: str, count: int) -> None:
        """Record missing candles in data."""
        self.missing_candles[asset] = self.missing_candles.get(asset, 0) + count

    def get_data_freshness(self, asset: str, max_age_hours: int = 1) -> Dict[str, Any]:
        """Check how fresh data is."""
        now = datetime.utcnow()

        price_update = self.last_price_update.get(asset)
        volume_update = self.last_volume_update.get(asset)

        price_fresh = True
        volume_fresh = True
        price_age_hours = float('inf')
        volume_age_hours = float('inf')

        if price_update:
            price_dt = datetime.fromisoformat(price_update)
            price_age_hours = (now - price_dt).total_seconds() / 3600
            price_fresh = price_age_hours <= max_age_hours

        if volume_update:
            volume_dt = datetime.fromisoformat(volume_update)
            volume_age_hours = (now - volume_dt).total_seconds() / 3600
            volume_fresh = volume_age_hours <= max_age_hours

        return {
            "asset": asset,
            "price_fresh": price_fresh,
            "price_age_hours": price_age_hours,
            "volume_fresh": volume_fresh,
            "volume_age_hours": volume_age_hours,
            "all_fresh": price_fresh and volume_fresh
        }

    def get_data_completeness(self, asset: str) -> float:
        """Estimate data completeness (0-1)."""
        total_candles = self.price_data_count.get(asset, 0)
        missing = self.missing_candles.get(asset, 0)

        if total_candles == 0:
            return 0.0

        return (total_candles - missing) / total_candles


class SystemStateAnalyzer:
    """Aggregate component health into system state."""

    def __init__(self):
        self.components: Dict[str, ComponentHealthTracker] = {}
        self.data_quality = DataQualityMonitor()

    def register_component(self, name: str) -> ComponentHealthTracker:
        """Register component for tracking."""
        tracker = ComponentHealthTracker(name)
        self.components[name] = tracker
        return tracker

    def get_system_status(self) -> str:
        """Overall system health status."""
        if not self.components:
            return HealthStatus.OFFLINE.value

        statuses = [comp.get_status() for comp in self.components.values()]

        # System is as healthy as its worst component
        if HealthStatus.OFFLINE.value in statuses:
            return HealthStatus.OFFLINE.value
        elif HealthStatus.CRITICAL.value in statuses:
            return HealthStatus.CRITICAL.value
        elif HealthStatus.DEGRADED.value in statuses:
            return HealthStatus.DEGRADED.value
        else:
            return HealthStatus.HEALTHY.value

    def get_system_health_score(self) -> float:
        """Numeric health score (0-100)."""
        if not self.components:
            return 0.0

        total_uptime = sum(comp.get_uptime_percent() for comp in self.components.values())
        avg_uptime = total_uptime / len(self.components)

        return avg_uptime

    def get_critical_components(self) -> List[ComponentHealth]:
        """Get all unhealthy components."""
        return [
            comp.get_health()
            for comp in self.components.values()
            if comp.get_status() in [HealthStatus.DEGRADED.value, HealthStatus.CRITICAL.value]
        ]

    def get_system_report(self) -> Dict[str, Any]:
        """Comprehensive system health report."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system_status": self.get_system_status(),
            "health_score": self.get_system_health_score(),
            "total_components": len(self.components),
            "components": {
                name: comp.get_health().to_dict()
                for name, comp in self.components.items()
            },
            "critical_components": [
                h.to_dict() for h in self.get_critical_components()
            ]
        }


class HealthAlertGenerator:
    """Generate alerts based on health degradation."""

    def __init__(self):
        self.alerts: List[HealthAlert] = []
        self.thresholds = {
            "uptime_critical": 50.0,
            "uptime_degraded": 80.0,
            "latency_warning_ms": 1000,
            "data_freshness_hours": 2,
            "data_completeness": 0.9
        }

    def check_component_health(self, health: ComponentHealth) -> List[HealthAlert]:
        """Check component and generate alerts."""
        alerts = []

        # Check uptime
        if health.uptime_percent < self.thresholds["uptime_critical"]:
            alerts.append(HealthAlert(
                timestamp=datetime.utcnow().isoformat(),
                severity=AlertSeverity.CRITICAL.value,
                component=health.name,
                message=f"{health.name} uptime critical: {health.uptime_percent:.1f}%",
                value=health.uptime_percent,
                threshold=self.thresholds["uptime_critical"],
                recommendation=f"Investigate {health.name} failures. Last error: {health.last_error}"
            ))
        elif health.uptime_percent < self.thresholds["uptime_degraded"]:
            alerts.append(HealthAlert(
                timestamp=datetime.utcnow().isoformat(),
                severity=AlertSeverity.WARNING.value,
                component=health.name,
                message=f"{health.name} uptime degraded: {health.uptime_percent:.1f}%",
                value=health.uptime_percent,
                threshold=self.thresholds["uptime_degraded"],
                recommendation=f"Monitor {health.name} for issues"
            ))

        # Check latency
        if health.latency_ms > self.thresholds["latency_warning_ms"]:
            alerts.append(HealthAlert(
                timestamp=datetime.utcnow().isoformat(),
                severity=AlertSeverity.WARNING.value,
                component=health.name,
                message=f"{health.name} latency high: {health.latency_ms:.0f}ms",
                value=health.latency_ms,
                threshold=self.thresholds["latency_warning_ms"],
                recommendation=f"Check {health.name} performance and dependencies"
            ))

        return alerts

    def check_data_quality(self, asset: str, freshness: Dict, 
                          completeness: float) -> List[HealthAlert]:
        """Check data quality and generate alerts."""
        alerts = []

        # Check freshness
        if not freshness["price_fresh"]:
            alerts.append(HealthAlert(
                timestamp=datetime.utcnow().isoformat(),
                severity=AlertSeverity.WARNING.value,
                component=f"data_quality_{asset}",
                message=f"{asset} price data stale: {freshness['price_age_hours']:.1f}h old",
                value=freshness['price_age_hours'],
                threshold=self.thresholds["data_freshness_hours"],
                recommendation=f"Check {asset} data source connection"
            ))

        # Check completeness
        if completeness < self.thresholds["data_completeness"]:
            alerts.append(HealthAlert(
                timestamp=datetime.utcnow().isoformat(),
                severity=AlertSeverity.WARNING.value,
                component=f"data_quality_{asset}",
                message=f"{asset} data incomplete: {completeness*100:.1f}%",
                value=completeness,
                threshold=self.thresholds["data_completeness"],
                recommendation=f"Investigate missing candles for {asset}"
            ))

        return alerts

    def generate_all_alerts(self, system_report: Dict) -> List[HealthAlert]:
        """Generate all applicable alerts."""
        all_alerts = []

        # Check components
        for comp_data in system_report["components"].values():
            comp_health = ComponentHealth(**comp_data)
            all_alerts.extend(self.check_component_health(comp_health))

        return all_alerts
