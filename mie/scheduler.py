"""
Scheduler & Automation for MIE V1 Research Layer
Manages periodic execution cycles at multiple frequencies.

Loops:
- Fast Loop (5 min): Observe market, detect signals
- Daily Loop (8h UTC): Deep analysis, hypothesis generation
- Weekly Loop (Sun 17h UTC): Meta-thinking, portfolio review
"""

import schedule
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Any, Optional
from enum import Enum


class LoopType(Enum):
    """Loop execution frequencies."""
    FAST = "fast"  # Every 5 minutes
    DAILY = "daily"  # Every 24h at 08:00 UTC
    WEEKLY = "weekly"  # Every Sunday at 17:00 UTC
    MONTHLY = "monthly"  # Every 1st at 00:00 UTC


class ScheduledTask:
    """Represents a scheduled task."""

    def __init__(self, task_id: str, task_func: Callable, loop_type: LoopType,
                 description: str = ""):
        self.task_id = task_id
        self.task_func = task_func
        self.loop_type = loop_type
        self.description = description
        self.execution_count = 0
        self.last_execution = None
        self.last_error = None
        self.total_duration_ms = 0.0

    def execute(self) -> bool:
        """Execute the task."""
        import time
        start = time.time()

        try:
            self.task_func()
            self.execution_count += 1
            self.last_execution = datetime.utcnow().isoformat()
            self.last_error = None
            self.total_duration_ms = (time.time() - start) * 1000
            return True
        except Exception as e:
            self.last_error = str(e)
            self.total_duration_ms = (time.time() - start) * 1000
            print(f"❌ Task {self.task_id} failed: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "loop_type": self.loop_type.value,
            "description": self.description,
            "execution_count": self.execution_count,
            "last_execution": self.last_execution,
            "last_error": self.last_error,
            "total_duration_ms": self.total_duration_ms
        }


class LoopScheduler:
    """Manages execution loops at different frequencies."""

    def __init__(self, orchestrator, logger=None):
        self.orchestrator = orchestrator
        self.logger = logger
        self.scheduler = schedule.Scheduler()
        self.tasks: Dict[str, ScheduledTask] = {}
        self.loop_history: List[Dict[str, Any]] = []
        self.running = False

    def register_fast_loop(self, task_id: str, task_func: Callable,
                          description: str = "", interval_minutes: int = 5) -> ScheduledTask:
        """Register task for fast loop (default 5 min)."""
        task = ScheduledTask(task_id, task_func, LoopType.FAST, description)
        self.tasks[task_id] = task

        # Schedule with scheduler
        self.scheduler.every(interval_minutes).minutes.do(task.execute)

        return task

    def register_daily_loop(self, task_id: str, task_func: Callable,
                           description: str = "", hour: int = 8) -> ScheduledTask:
        """Register task for daily loop (default 08:00 UTC)."""
        task = ScheduledTask(task_id, task_func, LoopType.DAILY, description)
        self.tasks[task_id] = task

        # Schedule with scheduler
        self.scheduler.every().day.at(f"{hour:02d}:00").do(task.execute)

        return task

    def register_weekly_loop(self, task_id: str, task_func: Callable,
                            description: str = "", day: str = "sunday",
                            hour: int = 17) -> ScheduledTask:
        """Register task for weekly loop (default Sunday 17:00 UTC)."""
        task = ScheduledTask(task_id, task_func, LoopType.WEEKLY, description)
        self.tasks[task_id] = task

        # Schedule with scheduler
        day_map = {
            "monday": "monday", "tuesday": "tuesday", "wednesday": "wednesday",
            "thursday": "thursday", "friday": "friday", "saturday": "saturday",
            "sunday": "sunday"
        }

        self.scheduler.every().weeks().tag(day).at(f"{hour:02d}:00").do(task.execute)

        return task

    def register_monthly_loop(self, task_id: str, task_func: Callable,
                             description: str = "", day: int = 1,
                             hour: int = 0) -> ScheduledTask:
        """Register task for monthly loop (default 1st at 00:00 UTC)."""
        task = ScheduledTask(task_id, task_func, LoopType.MONTHLY, description)
        self.tasks[task_id] = task

        # Note: schedule library doesn't have built-in monthly scheduling
        # Using workaround: check daily at specified hour, execute only on 1st
        def monthly_wrapper():
            from datetime import datetime
            if datetime.utcnow().day == day and datetime.utcnow().hour == hour:
                return task.execute()
            return False

        self.scheduler.every().day.at(f"{hour:02d}:00").do(monthly_wrapper)

        return task

    def run_once(self, loop_type: LoopType) -> Dict[str, Any]:
        """Run one iteration of the execution loop."""
        loop_start = datetime.utcnow().isoformat()

        # Select tasks for this loop type
        tasks_to_run = [
            task for task in self.tasks.values()
            if task.loop_type == loop_type
        ]

        results = []
        for task in tasks_to_run:
            success = task.execute()
            results.append({
                "task_id": task.task_id,
                "success": success,
                "duration_ms": task.total_duration_ms,
                "error": task.last_error
            })

        loop_report = {
            "loop_type": loop_type.value,
            "timestamp": loop_start,
            "tasks_executed": len(tasks_to_run),
            "tasks_succeeded": sum(1 for r in results if r["success"]),
            "tasks_failed": sum(1 for r in results if not r["success"]),
            "results": results
        }

        self.loop_history.append(loop_report)
        return loop_report

    def get_task_status(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of scheduled tasks."""
        if task_id:
            task = self.tasks.get(task_id)
            return task.to_dict() if task else None

        return {
            task_id: task.to_dict()
            for task_id, task in self.tasks.items()
        }

    def get_loop_history(self, loop_type: Optional[str] = None,
                        limit: int = 20) -> List[Dict[str, Any]]:
        """Get loop execution history."""
        history = self.loop_history

        if loop_type:
            history = [h for h in history if h["loop_type"] == loop_type]

        return history[-limit:]

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "running": self.running,
            "total_tasks": len(self.tasks),
            "tasks": self.get_task_status(),
            "scheduled_jobs": len(self.scheduler.jobs),
            "recent_loops": self.get_loop_history(limit=5)
        }


class MIEScheduler:
    """High-level MIE scheduler configuration."""

    def __init__(self, orchestrator, logger=None):
        self.orchestrator = orchestrator
        self.logger = logger
        self.scheduler = LoopScheduler(orchestrator, logger)
        self._setup_tasks()

    def _setup_tasks(self):
        """Setup default MIE tasks."""

        # Fast loop: Market scanning and signal detection
        def fast_loop():
            """Fast loop: Scan market, detect signals (5 min)."""
            if hasattr(self.orchestrator, 'execution'):
                report = self.orchestrator.execution.execute_cycle(cycle_type="fast")
                return report

        # Daily loop: Deep analysis and hypothesis generation
        def daily_loop():
            """Daily loop: Deep analysis (08:00 UTC)."""
            if hasattr(self.orchestrator, 'execution'):
                report = self.orchestrator.execution.execute_cycle(cycle_type="daily")

                # Generate daily report
                if hasattr(self.orchestrator, 'enhanced_reporter'):
                    self.orchestrator.enhanced_reporter.send_daily_report()

                return report

        # Weekly loop: Meta-thinking and portfolio review
        def weekly_loop():
            """Weekly loop: Meta-thinking (Sunday 17:00 UTC)."""
            if hasattr(self.orchestrator, 'execution'):
                report = self.orchestrator.execution.execute_cycle(cycle_type="weekly")

                # Generate weekly report
                if hasattr(self.orchestrator, 'enhanced_reporter'):
                    self.orchestrator.enhanced_reporter.send_weekly_report()

                return report

        # Monthly loop: Quarterly review and system optimization
        def monthly_loop():
            """Monthly loop: System review and optimization (1st at 00:00 UTC)."""
            if hasattr(self.orchestrator, 'execution'):
                report = self.orchestrator.execution.execute_cycle(cycle_type="monthly")

                # Generate monthly report
                if hasattr(self.orchestrator, 'enhanced_reporter'):
                    # Send monthly summary (reuse weekly report or create new)
                    self.orchestrator.enhanced_reporter.send_weekly_report()

                return report

        # Register tasks
        self.scheduler.register_fast_loop(
            "fast_market_scan",
            fast_loop,
            description="Fast market scanning and signal detection",
            interval_minutes=5
        )

        self.scheduler.register_daily_loop(
            "daily_analysis",
            daily_loop,
            description="Daily deep analysis and hypothesis generation",
            hour=8
        )

        self.scheduler.register_weekly_loop(
            "weekly_review",
            weekly_loop,
            description="Weekly meta-thinking and portfolio review",
            day="sunday",
            hour=17
        )

        self.scheduler.register_monthly_loop(
            "monthly_review",
            monthly_loop,
            description="Monthly system review and optimization",
            day=1,
            hour=0
        )

    def start(self):
        """Start the scheduler."""
        self.scheduler.running = True
        print("✅ MIE Scheduler started")

        # Counter para chequear mensajes cada N iteraciones (evita spam)
        telegram_check_counter = 0
        telegram_check_interval = 10  # Chequea cada 10 segundos

        while self.scheduler.running:
            try:
                self.scheduler.scheduler.run_pending()

                # Chequea mensajes de Telegram cada N iteraciones
                telegram_check_counter += 1
                if telegram_check_counter >= telegram_check_interval:
                    try:
                        self.orchestrator._check_telegram_messages()
                    except Exception as e:
                        self.orchestrator.logger.error(f"Error checking Telegram: {e}")
                    telegram_check_counter = 0

                time.sleep(1)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Scheduler error: {e}")
                time.sleep(5)

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.running = False
        print("✅ MIE Scheduler stopped")

    def run_fast_cycle_now(self) -> Dict[str, Any]:
        """Manually trigger fast cycle."""
        return self.scheduler.run_once(LoopType.FAST)

    def run_daily_cycle_now(self) -> Dict[str, Any]:
        """Manually trigger daily cycle."""
        return self.scheduler.run_once(LoopType.DAILY)

    def run_weekly_cycle_now(self) -> Dict[str, Any]:
        """Manually trigger weekly cycle."""
        return self.scheduler.run_once(LoopType.WEEKLY)

    def run_monthly_cycle_now(self) -> Dict[str, Any]:
        """Manually trigger monthly cycle."""
        return self.scheduler.run_once(LoopType.MONTHLY)

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return self.scheduler.get_scheduler_status()

    def get_next_execution(self) -> Dict[str, str]:
        """Get next scheduled execution times."""
        next_runs = {}

        for job in self.scheduler.scheduler.jobs:
            job_id = str(job)
            next_time = job.next_run

            if next_time:
                next_runs[job_id] = next_time.isoformat()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "next_executions": next_runs
        }
