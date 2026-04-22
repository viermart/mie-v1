"""
Advanced Alert System
Detects critical hypothesis transitions and triggers timely notifications
Monitors readiness progression and confidence shifts
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List
import logging

class AlertSystem:
    """
    Multi-level alert system for hypothesis monitoring
    Alerts on: confidence jumps, readiness milestones, correlation shifts
    """
    
    # Alert severity levels
    SEVERITY_INFO = "INFO"
    SEVERITY_WARN = "WARN"
    SEVERITY_CRITICAL = "CRITICAL"
    
    def __init__(self, db=None, logger=None):
        self.db = db
        self.logger = logger or logging.getLogger("MIE.AlertSystem")
        self.registry_path = "research_logs/hypothesis_registry.json"
        self.alert_history = []
    
    def check_confidence_jumps(self, hypotheses: List[Dict]) -> List[Dict]:
        """
        Detect sudden confidence level increases
        Alert if hypothesis jumps 2+ levels in single validation
        """
        alerts = []
        
        for hyp in hypotheses:
            if hyp.get("previous_confidence") and hyp.get("confidence"):
                conf_levels = ["repeated_observation", "weakly_supported", "supported", "strongly_supported"]
                
                prev_idx = conf_levels.index(hyp.get("previous_confidence", "repeated_observation"))
                curr_idx = conf_levels.index(hyp.get("confidence", "repeated_observation"))
                
                jump = curr_idx - prev_idx
                
                if jump >= 2:
                    alerts.append({
                        "type": "confidence_jump",
                        "severity": self.SEVERITY_WARN,
                        "hypothesis_id": hyp["id"],
                        "from": hyp.get("previous_confidence"),
                        "to": hyp.get("confidence"),
                        "jump_magnitude": jump,
                        "message": f"⚠️ {hyp['id']}: Confidence jumped {jump} levels ({hyp.get('previous_confidence')} → {hyp.get('confidence')})",
                        "timestamp": datetime.utcnow().isoformat()
                    })
        
        return alerts
    
    def check_readiness_milestones(self, current_score: float, previous_score: float = None) -> List[Dict]:
        """
        Alert on readiness score milestones (25, 50, 75, 100)
        """
        alerts = []
        milestones = [25, 50, 75, 100]
        
        if previous_score is None:
            previous_score = current_score - 1
        
        for milestone in milestones:
            if previous_score < milestone <= current_score:
                severity = self.SEVERITY_CRITICAL if milestone >= 75 else self.SEVERITY_WARN
                alerts.append({
                    "type": "readiness_milestone",
                    "severity": severity,
                    "milestone": milestone,
                    "current_score": current_score,
                    "message": f"🎯 READINESS MILESTONE {milestone}/100 REACHED",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return alerts
    
    def check_hypothesis_status_changes(self, hypotheses: List[Dict]) -> List[Dict]:
        """
        Alert on hypothesis status changes (queued → active → completed)
        """
        alerts = []
        
        status_progression = ["queued", "awaiting_validation", "testing", "archived"]
        
        for hyp in hypotheses:
            current_status = hyp.get("status", "queued")
            previous_status = hyp.get("previous_status", "queued")
            
            if current_status != previous_status:
                alerts.append({
                    "type": "status_change",
                    "severity": self.SEVERITY_INFO,
                    "hypothesis_id": hyp["id"],
                    "from_status": previous_status,
                    "to_status": current_status,
                    "message": f"📊 {hyp['id']}: Status {previous_status} → {current_status}",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return alerts
    
    def check_correlation_shifts(self, current_correlations: Dict, previous_correlations: Dict = None) -> List[Dict]:
        """
        Alert on significant correlation shifts between assets
        """
        alerts = []
        
        if not previous_correlations:
            return alerts
        
        shift_threshold = 0.20  # 20% change triggers alert
        
        for asset_pair, current_corr in current_correlations.items():
            previous_corr = previous_correlations.get(asset_pair, current_corr)
            shift = abs(current_corr - previous_corr)
            
            if shift >= shift_threshold:
                direction = "↑" if current_corr > previous_corr else "↓"
                alerts.append({
                    "type": "correlation_shift",
                    "severity": self.SEVERITY_WARN,
                    "asset_pair": asset_pair,
                    "previous": round(previous_corr, 3),
                    "current": round(current_corr, 3),
                    "shift": round(shift, 3),
                    "message": f"📈 {asset_pair} correlation {direction} ({previous_corr:.3f} → {current_corr:.3f})",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return alerts
    
    def check_feedback_quality_alerts(self, hypotheses: List[Dict]) -> List[Dict]:
        """
        Alert on poor feedback quality (suggest hypothesis retirement)
        """
        alerts = []
        
        for hyp in hypotheses:
            feedback_count = hyp.get("feedback_count", 0)
            feedback_quality = hyp.get("feedback_quality_avg", 0.5)
            
            # Alert if poor feedback despite multiple ratings
            if feedback_count >= 3 and feedback_quality < 0.4:
                alerts.append({
                    "type": "poor_feedback_quality",
                    "severity": self.SEVERITY_WARN,
                    "hypothesis_id": hyp["id"],
                    "feedback_quality": round(feedback_quality, 2),
                    "feedback_count": feedback_count,
                    "message": f"⚠️ {hyp['id']}: Poor feedback quality ({feedback_quality:.2f}) after {feedback_count} ratings - consider retiring",
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        return alerts
    
    def generate_alert_digest(self, all_alerts: List[Dict]) -> Dict:
        """
        Generate summary of all alerts with categorization
        """
        digest = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_alerts": len(all_alerts),
            "by_severity": {
                self.SEVERITY_CRITICAL: [],
                self.SEVERITY_WARN: [],
                self.SEVERITY_INFO: []
            },
            "by_type": {}
        }
        
        for alert in all_alerts:
            severity = alert.get("severity", self.SEVERITY_INFO)
            alert_type = alert.get("type", "unknown")
            
            digest["by_severity"][severity].append(alert)
            
            if alert_type not in digest["by_type"]:
                digest["by_type"][alert_type] = []
            digest["by_type"][alert_type].append(alert)
        
        return digest
    
    def should_notify_user(self, alert: Dict) -> bool:
        """
        Determine if alert warrants user notification
        """
        # Always notify on critical
        if alert.get("severity") == self.SEVERITY_CRITICAL:
            return True
        
        # Notify on confidence jumps
        if alert.get("type") == "confidence_jump":
            return True
        
        # Notify on readiness milestones
        if alert.get("type") == "readiness_milestone":
            return True
        
        return False

