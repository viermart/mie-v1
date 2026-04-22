"""
MIE V1 Research Layer - Main Entry Point
Deployment wrapper, CLI interface, and bootstrap.

Usage:
    python -m mie.main --mode fast         # Run fast loop once
    python -m mie.main --mode daily        # Run daily cycle once
    python -m mie.main --mode scheduler    # Start continuous scheduler
    python -m mie.main --api --port 8000   # Start API server
    python -m mie.main --status            # Check system status
"""

import sys
import os
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Import core components
from mie.orchestrator import MIEOrchestrator
from mie.scheduler import LoopType


class MIEMain:
    """Main entry point for MIE V1."""

    def __init__(self, db_path: str = "mie.db", telegram_token: Optional[str] = None,
                 telegram_chat_id: Optional[str] = None):
        """Initialize MIE orchestrator."""
        self.orchestrator = MIEOrchestrator(
            db_path=db_path,
            telegram_token=telegram_token,
            telegram_chat_id=telegram_chat_id
        )
        self.logger = self.orchestrator.logger

    def run_fast_cycle(self) -> int:
        """Execute one fast cycle."""
        self.logger.info("=" * 60)
        self.logger.info("CICLO RÁPIDO - Fast Cycle")
        self.logger.info(f"Start: {datetime.utcnow().isoformat()}")
        self.logger.info("=" * 60)

        try:
            report = self.orchestrator.scheduler.run_fast_cycle_now()
            self.logger.info(f"Fast cycle completed: {len(report.get('results', []))} tasks")
            return 0
        except Exception as e:
            self.logger.error(f"Fast cycle failed: {e}")
            return 1

    def run_daily_cycle(self) -> int:
        """Execute one daily cycle."""
        self.logger.info("=" * 60)
        self.logger.info("CICLO DIARIO - Daily Cycle")
        self.logger.info(f"Start: {datetime.utcnow().isoformat()}")
        self.logger.info("=" * 60)

        try:
            report = self.orchestrator.scheduler.run_daily_cycle_now()
            self.logger.info(f"Daily cycle completed")
            return 0
        except Exception as e:
            self.logger.error(f"Daily cycle failed: {e}")
            return 1

    def run_weekly_cycle(self) -> int:
        """Execute one weekly cycle."""
        self.logger.info("=" * 60)
        self.logger.info("CICLO SEMANAL - Weekly Cycle")
        self.logger.info(f"Start: {datetime.utcnow().isoformat()}")
        self.logger.info("=" * 60)

        try:
            report = self.orchestrator.scheduler.run_weekly_cycle_now()
            self.logger.info(f"Weekly cycle completed")
            return 0
        except Exception as e:
            self.logger.error(f"Weekly cycle failed: {e}")
            return 1

    def run_scheduler(self) -> int:
        """Start continuous scheduler."""
        self.logger.info("=" * 60)
        self.logger.info("MIE V1 SCHEDULER - Continuous Execution")
        self.logger.info(f"Start: {datetime.utcnow().isoformat()}")
        self.logger.info("Loops: fast (5m), daily (08:00 UTC), weekly (Sun 17:00 UTC)")
        self.logger.info("=" * 60)

        try:
            self.orchestrator.scheduler.start()
            return 0
        except KeyboardInterrupt:
            self.logger.info("Scheduler stopped by user")
            self.orchestrator.scheduler.stop()
            return 0
        except Exception as e:
            self.logger.error(f"Scheduler error: {e}")
            return 1

    def start_api_server(self, host: str = "0.0.0.0", port: int = 8000) -> int:
        """Start REST API server."""
        self.logger.info("=" * 60)
        self.logger.info(f"MIE V1 API SERVER - {host}:{port}")
        self.logger.info(f"Start: {datetime.utcnow().isoformat()}")
        self.logger.info("=" * 60)

        try:
            # Check if Flask is available
            try:
                from flask import Flask, jsonify
            except ImportError:
                self.logger.warning("Flask not installed. Install with: pip install flask")
                return 1

            app = Flask("MIE-V1-API")

            # Register API endpoints
            @app.route("/api/status", methods=["GET"])
            def api_status():
                return jsonify(self.orchestrator.api.get_api_status().to_dict())

            @app.route("/api/hypotheses", methods=["GET"])
            def list_hypotheses():
                return jsonify(
                    self.orchestrator.api.hypotheses.list_hypotheses().to_dict()
                )

            @app.route("/api/health", methods=["GET"])
            def health_status():
                return jsonify(self.orchestrator.api.health.get_system_health().to_dict())

            @app.route("/api/metrics", methods=["GET"])
            def metrics():
                return jsonify(self.orchestrator.api.metrics.get_system_metrics().to_dict())

            @app.route("/api/config/constraints", methods=["GET"])
            def get_constraints():
                return jsonify(self.orchestrator.api.config.get_constraints().to_dict())

            @app.route("/api/scheduler/status", methods=["GET"])
            def scheduler_status():
                status = self.orchestrator.scheduler.get_status()
                return jsonify({"success": True, "data": status})

            self.logger.info(f"API listening on {host}:{port}")
            app.run(host=host, port=port, debug=False)

            return 0
        except Exception as e:
            self.logger.error(f"API server error: {e}")
            return 1

    def check_status(self) -> int:
        """Check system status."""
        print("\n" + "=" * 60)
        print("MIE V1 - SYSTEM STATUS")
        print("=" * 60)

        try:
            health = self.orchestrator.health_analyzer.get_system_report()
            print(f"\nHealth Status: {health['system_status'].upper()}")
            print(f"Health Score: {health['health_score']:.1f}/100")

            print(f"\nComponents ({health['total_components']}):")
            for comp_name, comp_health in health["components"].items():
                status = comp_health["status"].upper()
                uptime = comp_health["uptime_percent"]
                print(f"  - {comp_name:30s} {status:12s} {uptime:.1f}%")

            if health["critical_components"]:
                print(f"\n⚠️ CRITICAL COMPONENTS ({len(health['critical_components'])}):")
                for comp in health["critical_components"]:
                    print(f"  - {comp['name']}: {comp['status']}")

            scheduler_status = self.orchestrator.scheduler.get_status()
            print(f"\nScheduler: {'RUNNING' if scheduler_status['running'] else 'STOPPED'}")
            print(f"Scheduled Tasks: {scheduler_status['total_tasks']}")

            print("\n" + "=" * 60 + "\n")
            return 0
        except Exception as e:
            print(f"❌ Status check failed: {e}\n")
            return 1

    def show_help(self):
        """Show help message."""
        help_text = """
MIE V1 Research Layer - Market Intelligence Entity
Version 1.0.0

USAGE:
    python -m mie.main [COMMAND] [OPTIONS]

COMMANDS:
    fast            Run one fast cycle (observe → analyze → decide → execute)
    daily           Run one daily cycle with deep analysis
    weekly          Run one weekly cycle with meta-thinking
    scheduler       Start continuous scheduler (fast + daily + weekly loops)
    api             Start REST API server (default port 8000)
    status          Check system status and health
    help            Show this help message

OPTIONS:
    --db PATH       Database path (default: mie.db)
    --telegram-token TOKEN    Telegram bot token
    --telegram-chat-id ID     Telegram chat ID
    --host HOST     API server host (default: 0.0.0.0)
    --port PORT     API server port (default: 8000)
    --config PATH   Config directory (default: config)

EXAMPLES:
    # Run one fast cycle
    python -m mie.main fast

    # Run continuous scheduler
    python -m mie.main scheduler

    # Start API server on port 8000
    python -m mie.main api --port 8000

    # Check system status
    python -m mie.main status

ENDPOINTS (when API is running):
    GET    /api/status                    System status
    GET    /api/hypotheses                List hypotheses
    GET    /api/hypotheses/{id}           Get hypothesis details
    GET    /api/portfolio                 Portfolio state
    GET    /api/metrics                   System metrics
    GET    /api/health                    Health status
    GET    /api/config/constraints        Get constraints
    GET    /api/events                    Event history
    GET    /api/scheduler/status          Scheduler status

CONFIGURATION:
    Edit config/mie_config.yaml to adjust:
    - Constraints (max_active_hypotheses, etc.)
    - Thresholds (volatility, volume, correlation)
    - Backtesting parameters
    - Reporting schedules

LOGS:
    View logs in: logs/mie.log

VERSION: 1.0.0
LAST UPDATED: 2026-04-22
        """
        print(help_text)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="mie",
        description="MIE V1 Research Layer - Market Intelligence Entity",
        add_help=False
    )

    parser.add_argument("command", nargs="?", default="help",
                       choices=["fast", "daily", "weekly", "scheduler", "api", "status", "help"])
    parser.add_argument("--db", default="mie.db", help="Database path")
    parser.add_argument("--telegram-token", help="Telegram bot token")
    parser.add_argument("--telegram-chat-id", help="Telegram chat ID")
    parser.add_argument("--host", default="0.0.0.0", help="API server host")
    parser.add_argument("--port", type=int, default=8000, help="API server port")
    parser.add_argument("--config", default="config", help="Config directory")

    args = parser.parse_args()

    # Read Telegram credentials from environment if not provided via CLI
    telegram_token = args.telegram_token or os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = args.telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")

    mie = MIEMain(
        db_path=args.db,
        telegram_token=telegram_token,
        telegram_chat_id=telegram_chat_id
    )

    if args.command == "fast":
        return mie.run_fast_cycle()
    elif args.command == "daily":
        return mie.run_daily_cycle()
    elif args.command == "weekly":
        return mie.run_weekly_cycle()
    elif args.command == "scheduler":
        return mie.run_scheduler()
    elif args.command == "api":
        return mie.start_api_server(host=args.host, port=args.port)
    elif args.command == "status":
        return mie.check_status()
    else:
        mie.show_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
