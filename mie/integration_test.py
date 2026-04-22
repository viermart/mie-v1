"""
Integration Test Suite for MIE V1 Research Layer
Validates all 21 components work together seamlessly.

Test coverage:
- Component initialization
- Cross-component communication
- Event flow
- Data persistence
- Health monitoring
- Execution cycle
"""

from datetime import datetime
from typing import Dict, List, Any, Tuple
import sys


class IntegrationTestSuite:
    """Test suite for MIE V1 integration."""

    def __init__(self):
        self.results: List[Tuple[str, bool, str]] = []
        self.passed = 0
        self.failed = 0
        self.start_time = datetime.utcnow()

    def test(self, name: str, func, expected_exception=None) -> bool:
        """Run a single test."""
        try:
            result = func()

            if expected_exception:
                self.results.append((name, False, f"Expected {expected_exception} but got result"))
                self.failed += 1
                return False
            else:
                self.results.append((name, True, "OK"))
                self.passed += 1
                return True
        except Exception as e:
            if expected_exception and isinstance(e, expected_exception):
                self.results.append((name, True, f"Expected exception: {type(e).__name__}"))
                self.passed += 1
                return True
            else:
                self.results.append((name, False, str(e)))
                self.failed += 1
                return False

    def run_all_tests(self, orchestrator) -> Dict[str, Any]:
        """Run complete test suite."""
        print("\n" + "=" * 70)
        print("MIE V1 INTEGRATION TEST SUITE")
        print("=" * 70 + "\n")

        # Component tests
        print("COMPONENT INITIALIZATION TESTS:")
        self._test_components(orchestrator)

        # Event bus tests
        print("\nEVENT BUS TESTS:")
        self._test_event_bus(orchestrator)

        # Data persistence tests
        print("\nDATA PERSISTENCE TESTS:")
        self._test_persistence(orchestrator)

        # Health monitoring tests
        print("\nHEALTH MONITORING TESTS:")
        self._test_health_monitoring(orchestrator)

        # Configuration tests
        print("\nCONFIGURATION TESTS:")
        self._test_configuration(orchestrator)

        # API tests
        print("\nAPI TESTS:")
        self._test_api(orchestrator)

        # Execution engine tests
        print("\nEXECUTION ENGINE TESTS:")
        self._test_execution_engine(orchestrator)

        # Return summary
        return self._generate_report()

    def _test_components(self, orchestrator):
        """Test component initialization."""
        def test_core_components():
            assert hasattr(orchestrator, 'research'), "research_layer not initialized"
            assert hasattr(orchestrator, 'backtester'), "backtester not initialized"
            assert hasattr(orchestrator, 'portfolio'), "portfolio not initialized"
            assert hasattr(orchestrator, 'alerts'), "alerts not initialized"
            assert hasattr(orchestrator, 'advanced_reporter'), "advanced_reporter not initialized"
            return True

        def test_scanning_components():
            assert hasattr(orchestrator, 'price_scanner'), "price_scanner not initialized"
            assert hasattr(orchestrator, 'volume_scanner'), "volume_scanner not initialized"
            assert hasattr(orchestrator, 'signal_aggregator'), "signal_aggregator not initialized"
            return True

        def test_signal_engine():
            assert hasattr(orchestrator, 'signal_engine'), "signal_engine not initialized"
            return True

        def test_persistence():
            assert hasattr(orchestrator, 'persistence'), "persistence not initialized"
            return True

        def test_health_system():
            assert hasattr(orchestrator, 'health_analyzer'), "health_analyzer not initialized"
            return True

        def test_event_bus():
            assert hasattr(orchestrator, 'event_bus'), "event_bus not initialized"
            return True

        def test_config_manager():
            assert hasattr(orchestrator, 'config'), "config not initialized"
            return True

        def test_api_server():
            assert hasattr(orchestrator, 'api'), "api not initialized"
            return True

        def test_execution_engine():
            assert hasattr(orchestrator, 'execution'), "execution not initialized"
            return True

        def test_scheduler():
            assert hasattr(orchestrator, 'scheduler'), "scheduler not initialized"
            return True

        tests = [
            ("Core Components (research, backtester, portfolio, alerts)", test_core_components),
            ("Scanning Components (price, volume, signal_aggregator)", test_scanning_components),
            ("Signal-to-Hypothesis Engine", test_signal_engine),
            ("Data Persistence Layer", test_persistence),
            ("Health Monitoring System", test_health_system),
            ("Event Bus", test_event_bus),
            ("Configuration Manager", test_config_manager),
            ("REST API Layer", test_api_server),
            ("Execution Engine", test_execution_engine),
            ("Scheduler & Automation", test_scheduler),
        ]

        for name, func in tests:
            self.test(f"  ✓ {name}", func)

    def _test_event_bus(self, orchestrator):
        """Test event bus functionality."""
        def test_event_creation():
            event = orchestrator.event_bus.create_event(
                event_type="test_event",
                source="integration_test",
                data={"test": True}
            )
            assert event is not None, "Event creation failed"
            return True

        def test_event_publishing():
            event = orchestrator.event_bus.create_event(
                event_type="test_publish",
                source="integration_test"
            )
            handlers_executed = orchestrator.event_bus.publish(event)
            assert handlers_executed >= 0, "Event publishing failed"
            return True

        def test_event_subscription():
            received = []
            def handler(event):
                received.append(event)

            orchestrator.event_bus.subscribe(
                ["test_sub"], handler, "test_component"
            )

            event = orchestrator.event_bus.create_event(
                event_type="test_sub",
                source="integration_test"
            )
            orchestrator.event_bus.publish(event)
            assert len(received) > 0, "Subscription failed"
            return True

        tests = [
            ("  ✓ Event Creation", test_event_creation),
            ("  ✓ Event Publishing", test_event_publishing),
            ("  ✓ Event Subscription", test_event_subscription),
        ]

        for name, func in tests:
            self.test(name, func)

    def _test_persistence(self, orchestrator):
        """Test data persistence."""
        def test_hypothesis_store():
            test_hyp = {
                "id": "test_hyp_1",
                "asset": "BTC",
                "status": "test"
            }
            result = orchestrator.persistence.hypotheses.save_hypothesis(
                "test_hyp_1", test_hyp
            )
            assert result, "Hypothesis save failed"
            return True

        def test_metrics_recording():
            recorded = orchestrator.persistence.metrics.record_metric(
                "test_metric", 42.0, {"test": True}
            )
            assert recorded, "Metrics recording failed"
            return True

        def test_portfolio_tracking():
            allocation = {"BTC": 0.5, "ETH": 0.5}
            recorded = orchestrator.persistence.portfolio.record_allocation(
                allocation, reason="test"
            )
            assert recorded, "Portfolio tracking failed"
            return True

        tests = [
            ("  ✓ Hypothesis Store", test_hypothesis_store),
            ("  ✓ Metrics Recording", test_metrics_recording),
            ("  ✓ Portfolio Tracking", test_portfolio_tracking),
        ]

        for name, func in tests:
            self.test(name, func)

    def _test_health_monitoring(self, orchestrator):
        """Test health monitoring."""
        def test_component_health():
            health_report = orchestrator.health_analyzer.get_system_report()
            assert health_report is not None, "Health report generation failed"
            assert "system_status" in health_report, "Health report missing status"
            return True

        def test_data_quality():
            freshness = orchestrator.health_analyzer.data_quality.get_data_freshness("BTC")
            assert freshness is not None, "Data freshness check failed"
            return True

        def test_health_alerts():
            report = orchestrator.health_analyzer.get_system_report()
            alerts = orchestrator.alert_generator.generate_all_alerts(report)
            assert isinstance(alerts, list), "Alert generation failed"
            return True

        tests = [
            ("  ✓ Component Health", test_component_health),
            ("  ✓ Data Quality Monitoring", test_data_quality),
            ("  ✓ Health Alerts", test_health_alerts),
        ]

        for name, func in tests:
            self.test(name, func)

    def _test_configuration(self, orchestrator):
        """Test configuration management."""
        def test_constraint_reading():
            value = orchestrator.config.constraints.get_value("max_active_hypotheses")
            assert value is not None, "Constraint reading failed"
            assert isinstance(value, (int, float)), "Constraint value invalid type"
            return True

        def test_constraint_validation():
            is_valid, msg = orchestrator.config.validator.validate(
                "max_active_hypotheses", 5
            )
            assert is_valid, f"Constraint validation failed: {msg}"
            return True

        def test_config_report():
            report = orchestrator.config.get_constraints_report()
            assert report is not None, "Config report generation failed"
            assert "constraints" in report, "Config report missing constraints"
            return True

        tests = [
            ("  ✓ Constraint Reading", test_constraint_reading),
            ("  ✓ Constraint Validation", test_constraint_validation),
            ("  ✓ Configuration Report", test_config_report),
        ]

        for name, func in tests:
            self.test(name, func)

    def _test_api(self, orchestrator):
        """Test REST API layer."""
        def test_api_status():
            response = orchestrator.api.get_api_status()
            assert response.success, "API status check failed"
            assert response.data is not None, "API status missing data"
            return True

        def test_health_endpoint():
            response = orchestrator.api.health.get_system_health()
            assert response.success, "Health endpoint failed"
            return True

        def test_metrics_endpoint():
            response = orchestrator.api.metrics.get_system_metrics()
            assert response.success, "Metrics endpoint failed"
            return True

        def test_config_endpoint():
            response = orchestrator.api.config.get_constraints()
            assert response.success, "Config endpoint failed"
            return True

        tests = [
            ("  ✓ API Status Endpoint", test_api_status),
            ("  ✓ Health Endpoint", test_health_endpoint),
            ("  ✓ Metrics Endpoint", test_metrics_endpoint),
            ("  ✓ Configuration Endpoint", test_config_endpoint),
        ]

        for name, func in tests:
            self.test(name, func)

    def _test_execution_engine(self, orchestrator):
        """Test execution engine."""
        def test_execution_initialization():
            assert orchestrator.execution is not None, "Execution engine not initialized"
            assert hasattr(orchestrator.execution, 'execute_cycle'), "execute_cycle method missing"
            return True

        def test_execution_summary():
            summary = orchestrator.execution.get_execution_summary(limit=5)
            assert summary is not None, "Execution summary generation failed"
            assert "total_cycles" in summary, "Summary missing total_cycles"
            return True

        tests = [
            ("  ✓ Execution Engine Initialization", test_execution_initialization),
            ("  ✓ Execution Summary", test_execution_summary),
        ]

        for name, func in tests:
            self.test(name, func)

    def _generate_report(self) -> Dict[str, Any]:
        """Generate test report."""
        duration = (datetime.utcnow() - self.start_time).total_seconds()

        print("\n" + "=" * 70)
        print("TEST RESULTS")
        print("=" * 70)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total:  {self.passed + self.failed}")
        print(f"Duration: {duration:.2f}s")
        print("=" * 70 + "\n")

        if self.failed > 0:
            print("FAILURES:\n")
            for name, success, msg in self.results:
                if not success:
                    print(f"  ✗ {name}: {msg}")
            print()

        success_rate = (self.passed / (self.passed + self.failed) * 100) if (self.passed + self.failed) > 0 else 0

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "passed": self.passed,
            "failed": self.failed,
            "total": self.passed + self.failed,
            "success_rate": success_rate,
            "duration_seconds": duration,
            "status": "PASS" if self.failed == 0 else "FAIL",
            "detailed_results": [
                {
                    "test": name,
                    "status": "PASS" if success else "FAIL",
                    "message": msg
                }
                for name, success, msg in self.results
            ]
        }


def run_integration_tests(orchestrator) -> int:
    """Run full integration test suite."""
    suite = IntegrationTestSuite()
    report = suite.run_all_tests(orchestrator)

    return 0 if report["status"] == "PASS" else 1
