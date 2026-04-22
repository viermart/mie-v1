"""
REST API Layer for MIE V1 Research Layer
Exposes system capabilities via HTTP endpoints.

Endpoints:
- GET /api/hypotheses - List hypotheses
- GET /api/hypotheses/{id} - Get hypothesis details
- POST /api/hypotheses - Create hypothesis
- GET /api/portfolio - Get portfolio state
- GET /api/metrics - Get system metrics
- GET /api/health - Get system health
- POST /api/feedback - Submit feedback
- GET /api/config/constraints - Get constraints
- PUT /api/config/constraints/{name} - Update constraint
- GET /api/events - Get event history
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import asdict


class APIResponse:
    """Standard API response format."""

    def __init__(self, success: bool, data: Any = None, error: str = None,
                 timestamp: Optional[str] = None):
        self.success = success
        self.data = data
        self.error = error
        self.timestamp = timestamp or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp
        }


class HypothesesAPI:
    """Hypotheses management endpoints."""

    def __init__(self, research_layer, db):
        self.research = research_layer
        self.db = db

    def list_hypotheses(self, status: Optional[str] = None,
                       asset: Optional[str] = None,
                       limit: int = 50) -> APIResponse:
        """GET /api/hypotheses - List hypotheses."""
        try:
            hypotheses = self.research.db.get_all_hypotheses()

            if status:
                hypotheses = [h for h in hypotheses if h.get("status") == status]

            if asset:
                hypotheses = [h for h in hypotheses if h.get("asset") == asset]

            hypotheses = hypotheses[:limit]

            return APIResponse(
                success=True,
                data={
                    "count": len(hypotheses),
                    "hypotheses": hypotheses
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))

    def get_hypothesis(self, hypothesis_id: str) -> APIResponse:
        """GET /api/hypotheses/{id} - Get hypothesis."""
        try:
            hyp = self.research.db.get_hypothesis(hypothesis_id)

            if not hyp:
                return APIResponse(success=False, error="Hypothesis not found")

            return APIResponse(success=True, data=hyp)
        except Exception as e:
            return APIResponse(success=False, error=str(e))

    def create_hypothesis(self, hypothesis_data: Dict) -> APIResponse:
        """POST /api/hypotheses - Create hypothesis."""
        try:
            hyp_id = self.research.generate_hypothesis_from_signal(hypothesis_data)

            return APIResponse(
                success=True,
                data={"hypothesis_id": hyp_id}
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))


class PortfolioAPI:
    """Portfolio management endpoints."""

    def __init__(self, portfolio_manager):
        self.portfolio = portfolio_manager

    def get_portfolio_state(self) -> APIResponse:
        """GET /api/portfolio - Current portfolio state."""
        try:
            report = self.portfolio.get_portfolio_report()

            return APIResponse(
                success=True,
                data=report
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))

    def get_allocation_history(self, limit: int = 20) -> APIResponse:
        """GET /api/portfolio/history - Allocation history."""
        try:
            # Placeholder: would integrate with persistence layer
            timeline = []  # self.portfolio.persistence.get_allocation_timeline(limit)

            return APIResponse(
                success=True,
                data={"timeline": timeline}
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))


class MetricsAPI:
    """System metrics endpoints."""

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    def get_system_metrics(self) -> APIResponse:
        """GET /api/metrics - System-wide metrics."""
        try:
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "hypothesis_count": len(self.orchestrator.research.db.get_all_hypotheses()),
                "active_hypotheses": len([
                    h for h in self.orchestrator.research.db.get_all_hypotheses()
                    if h.get("status") in ["active", "queued"]
                ]),
                "portfolio": self.orchestrator.portfolio.get_portfolio_report() if hasattr(self.orchestrator, 'portfolio') else {},
                "health": self.orchestrator.health_analyzer.get_system_report() if hasattr(self.orchestrator, 'health_analyzer') else {}
            }

            return APIResponse(success=True, data=metrics)
        except Exception as e:
            return APIResponse(success=False, error=str(e))


class HealthAPI:
    """System health endpoints."""

    def __init__(self, health_analyzer):
        self.health = health_analyzer

    def get_system_health(self) -> APIResponse:
        """GET /api/health - System health status."""
        try:
            report = self.health.get_system_report()

            return APIResponse(
                success=True,
                data=report
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))

    def get_critical_issues(self) -> APIResponse:
        """GET /api/health/critical - Critical issues only."""
        try:
            critical = self.health.get_critical_components()

            return APIResponse(
                success=True,
                data={
                    "critical_count": len(critical),
                    "components": [c.to_dict() for c in critical]
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))


class FeedbackAPI:
    """Feedback submission endpoints."""

    def __init__(self, feedback_learner, research_layer):
        self.learner = feedback_learner
        self.research = research_layer

    def submit_feedback(self, hypothesis_id: str, rating: float,
                       comment: str = "") -> APIResponse:
        """POST /api/feedback - Submit hypothesis feedback."""
        try:
            if not (0.0 <= rating <= 1.0):
                return APIResponse(success=False, error="Rating must be 0.0-1.0")

            self.learner.process_feedback(
                hypothesis_id=hypothesis_id,
                user_rating=rating,
                comment=comment
            )

            return APIResponse(
                success=True,
                data={"feedback_id": hypothesis_id, "rating": rating}
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))


class ConfigurationAPI:
    """Configuration management endpoints."""

    def __init__(self, config_manager):
        self.config = config_manager

    def get_constraints(self) -> APIResponse:
        """GET /api/config/constraints - Get all constraints."""
        try:
            report = self.config.get_constraints_report()

            return APIResponse(success=True, data=report)
        except Exception as e:
            return APIResponse(success=False, error=str(e))

    def update_constraint(self, constraint_name: str, value: float,
                         reason: str = "") -> APIResponse:
        """PUT /api/config/constraints/{name} - Update constraint."""
        try:
            success = self.config.update_constraint(
                constraint_name,
                value,
                reason=reason
            )

            if not success:
                return APIResponse(
                    success=False,
                    error=f"Failed to update {constraint_name}"
                )

            return APIResponse(
                success=True,
                data={"constraint": constraint_name, "new_value": value}
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))


class EventsAPI:
    """Event history endpoints."""

    def __init__(self, event_bus):
        self.event_bus = event_bus

    def get_event_history(self, event_type: Optional[str] = None,
                         asset: Optional[str] = None,
                         limit: int = 100) -> APIResponse:
        """GET /api/events - Get event history."""
        try:
            history = self.event_bus.bus.get_event_history(
                event_type=event_type,
                asset=asset,
                limit=limit
            )

            return APIResponse(
                success=True,
                data={
                    "count": len(history),
                    "events": [e.to_dict() for e in history]
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))

    def get_event_stats(self) -> APIResponse:
        """GET /api/events/stats - Event bus statistics."""
        try:
            stats = self.event_bus.get_bus_stats()

            return APIResponse(success=True, data=stats)
        except Exception as e:
            return APIResponse(success=False, error=str(e))


class APIServer:
    """Unified API server interface."""

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

        # Initialize endpoint groups
        self.hypotheses = HypothesesAPI(
            orchestrator.research,
            orchestrator.db
        )
        self.portfolio = PortfolioAPI(orchestrator.portfolio)
        self.metrics = MetricsAPI(orchestrator)
        self.health = HealthAPI(orchestrator.health_analyzer)
        self.feedback = FeedbackAPI(
            orchestrator.feedback_learner,
            orchestrator.research
        )
        self.config = ConfigurationAPI(orchestrator.config)
        self.events = EventsAPI(orchestrator.event_bus)

    def get_api_status(self) -> APIResponse:
        """GET /api/status - API status."""
        try:
            return APIResponse(
                success=True,
                data={
                    "api_version": "1.0",
                    "mie_version": "1.0.0",
                    "endpoints": [
                        "GET /api/hypotheses",
                        "GET /api/hypotheses/{id}",
                        "POST /api/hypotheses",
                        "GET /api/portfolio",
                        "GET /api/portfolio/history",
                        "GET /api/metrics",
                        "GET /api/health",
                        "GET /api/health/critical",
                        "POST /api/feedback",
                        "GET /api/config/constraints",
                        "PUT /api/config/constraints/{name}",
                        "GET /api/events",
                        "GET /api/events/stats"
                    ]
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
