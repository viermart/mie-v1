"""
Real-Time Event Bus for MIE V1 Research Layer
Enables decoupled, async communication between components.

Components:
- Event: Base event structure
- EventSubscription: Topic-based subscriptions
- EventBus: Pub/sub broker
- EventLogger: Persistent event history
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading
from collections import defaultdict


class EventType(Enum):
    """Enumeration of event types."""
    # Market data events
    PRICE_UPDATE = "price_update"
    VOLUME_SPIKE = "volume_spike"
    VOLATILITY_CHANGE = "volatility_change"
    
    # Signal events
    SIGNAL_DETECTED = "signal_detected"
    SIGNAL_AGGREGATED = "signal_aggregated"
    
    # Hypothesis events
    HYPOTHESIS_GENERATED = "hypothesis_generated"
    HYPOTHESIS_VALIDATED = "hypothesis_validated"
    HYPOTHESIS_REJECTED = "hypothesis_rejected"
    HYPOTHESIS_STATUS_CHANGED = "hypothesis_status_changed"
    
    # Portfolio events
    PORTFOLIO_REBALANCE = "portfolio_rebalance"
    ALLOCATION_CHANGED = "allocation_changed"
    
    # Alert events
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_RESOLVED = "alert_resolved"
    
    # System events
    SYSTEM_HEALTHY = "system_healthy"
    SYSTEM_DEGRADED = "system_degraded"
    SYSTEM_CRITICAL = "system_critical"
    COMPONENT_ERROR = "component_error"
    
    # Learning events
    FEEDBACK_RECEIVED = "feedback_received"
    CONFIDENCE_ADJUSTED = "confidence_adjusted"
    BACKTEST_COMPLETE = "backtest_complete"


@dataclass
class Event:
    """Base event structure."""
    event_type: str
    timestamp: str
    source_component: str
    asset: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    priority: str = "normal"  # low, normal, high, critical

    def to_dict(self) -> Dict:
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "source_component": self.source_component,
            "asset": self.asset,
            "data": self.data or {},
            "correlation_id": self.correlation_id,
            "priority": self.priority
        }


class EventHandler:
    """Wrapper for event handler function."""

    def __init__(self, handler: Callable, event_types: List[str], 
                 component_name: str, async_exec: bool = False):
        self.handler = handler
        self.event_types = event_types
        self.component_name = component_name
        self.async_exec = async_exec
        self.execution_count = 0
        self.error_count = 0

    def can_handle(self, event_type: str) -> bool:
        """Check if handler is subscribed to this event type."""
        return event_type in self.event_types or "*" in self.event_types

    def execute(self, event: Event) -> bool:
        """Execute handler."""
        try:
            if self.async_exec:
                thread = threading.Thread(target=self.handler, args=(event,))
                thread.daemon = True
                thread.start()
            else:
                self.handler(event)
            
            self.execution_count += 1
            return True
        except Exception as e:
            self.error_count += 1
            print(f"❌ Event handler error ({self.component_name}): {e}")
            return False


class EventBus:
    """Pub/sub event broker with routing and filtering."""

    def __init__(self, logger=None):
        self.logger = logger
        self.handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self.event_history: List[Event] = []
        self.lock = threading.RLock()
        self.max_history = 1000

    def subscribe(self, event_types: List[str], handler: Callable,
                 component_name: str, async_exec: bool = False) -> EventHandler:
        """Subscribe handler to events."""
        with self.lock:
            event_handler = EventHandler(handler, event_types, component_name, async_exec)
            
            # Register for each event type
            for event_type in event_types:
                self.handlers[event_type].append(event_handler)

            return event_handler

    def subscribe_wildcard(self, handler: Callable, component_name: str,
                          async_exec: bool = False) -> EventHandler:
        """Subscribe to all events."""
        return self.subscribe(["*"], handler, component_name, async_exec)

    def unsubscribe(self, event_handler: EventHandler) -> None:
        """Remove subscription."""
        with self.lock:
            for handlers in self.handlers.values():
                if event_handler in handlers:
                    handlers.remove(event_handler)

    def publish(self, event: Event) -> int:
        """Publish event to all subscribers."""
        with self.lock:
            # Store in history
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)

            # Route to handlers
            handlers_executed = 0
            relevant_handlers = self.handlers.get(event.event_type, [])
            relevant_handlers.extend(self.handlers.get("*", []))

            for handler in relevant_handlers:
                if handler.execute(event):
                    handlers_executed += 1

            return handlers_executed

    def publish_async(self, event: Event) -> None:
        """Publish event asynchronously."""
        thread = threading.Thread(target=self.publish, args=(event,))
        thread.daemon = True
        thread.start()

    def get_event_history(self, event_type: Optional[str] = None,
                         asset: Optional[str] = None,
                         limit: Optional[int] = None) -> List[Event]:
        """Get event history with optional filtering."""
        with self.lock:
            filtered = self.event_history

            if event_type:
                filtered = [e for e in filtered if e.event_type == event_type]

            if asset:
                filtered = [e for e in filtered if e.asset == asset]

            if limit:
                filtered = filtered[-limit:]

            return filtered

    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        with self.lock:
            event_counts = {}
            handler_counts = {}

            for event_type in set(e.event_type for e in self.event_history):
                count = sum(1 for e in self.event_history if e.event_type == event_type)
                event_counts[event_type] = count

            for event_type, handlers in self.handlers.items():
                handler_counts[event_type] = len(handlers)

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "total_events_published": len(self.event_history),
                "event_types": event_counts,
                "subscriptions": handler_counts,
                "total_handlers": sum(
                    len(handlers) for handlers in self.handlers.values()
                )
            }


class EventLogger:
    """Persistent event logging."""

    def __init__(self, storage_dir: str = "data/events"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.session_events: List[Event] = []

    def log_event(self, event: Event) -> bool:
        """Log event to disk."""
        try:
            self.session_events.append(event)
            return True
        except Exception as e:
            print(f"❌ EventLogger.log_event error: {e}")
            return False

    def flush(self, session_id: str) -> bool:
        """Write all logged events to disk."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"events_{session_id}_{timestamp}.jsonl"
            filepath = self.storage_dir / filename

            with open(filepath, 'w') as f:
                for event in self.session_events:
                    f.write(json.dumps(event.to_dict()) + '\n')

            self.session_events = []
            return True
        except Exception as e:
            print(f"❌ EventLogger.flush error: {e}")
            return False

    def load_events(self, session_id: str, start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> List[Event]:
        """Load events from disk."""
        events = []

        for filepath in sorted(self.storage_dir.glob(f"events_{session_id}_*.jsonl")):
            try:
                with open(filepath, 'r') as f:
                    for line in f:
                        data = json.loads(line)
                        event = Event(
                            event_type=data["event_type"],
                            timestamp=data["timestamp"],
                            source_component=data["source_component"],
                            asset=data.get("asset"),
                            data=data.get("data", {}),
                            correlation_id=data.get("correlation_id"),
                            priority=data.get("priority", "normal")
                        )

                        # Optional filtering by date
                        if start_date and event.timestamp < start_date:
                            continue
                        if end_date and event.timestamp > end_date:
                            continue

                        events.append(event)
            except:
                continue

        return events


class EventBusManager:
    """Unified event system interface."""

    def __init__(self, session_id: str = "default", logger=None):
        self.session_id = session_id
        self.logger = logger
        self.bus = EventBus(logger=logger)
        self.event_logger = EventLogger()

    def create_event(self, event_type: str, source: str, asset: Optional[str] = None,
                    data: Optional[Dict] = None, priority: str = "normal",
                    correlation_id: Optional[str] = None) -> Event:
        """Create and publish event."""
        event = Event(
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            source_component=source,
            asset=asset,
            data=data,
            priority=priority,
            correlation_id=correlation_id
        )

        return event

    def publish(self, event: Event) -> int:
        """Publish event through bus and log."""
        self.event_logger.log_event(event)
        return self.bus.publish(event)

    def publish_async(self, event: Event) -> None:
        """Publish event async."""
        self.event_logger.log_event(event)
        self.bus.publish_async(event)

    def subscribe(self, event_types: List[str], handler: Callable,
                 component_name: str, async_exec: bool = False) -> EventHandler:
        """Subscribe to events."""
        return self.bus.subscribe(event_types, handler, component_name, async_exec)


    def subscribe_wildcard(self, handler: Callable, component_name: str,
                          async_exec: bool = False) -> EventHandler:
        """Subscribe to all events."""
        return self.bus.subscribe_wildcard(handler, component_name, async_exec)

    def get_bus_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return self.bus.get_statistics()

    def flush_logs(self) -> bool:
        """Persist event logs to disk."""
        return self.event_logger.flush(self.session_id)
