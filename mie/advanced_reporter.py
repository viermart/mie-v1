"""
Advanced Reporter
Executive summaries, performance metrics, strategic insights
"""
import json
from datetime import datetime
from typing import Dict, List
import logging

class AdvancedReporter:
    """
    Generates executive-level reports with strategic insights
    """
    
    def __init__(self, analyzer=None, learner=None, predictor=None, 
                 backtester=None, portfolio=None, logger=None):
        self.analyzer = analyzer
        self.learner = learner
        self.predictor = predictor
        self.backtester = backtester
        self.portfolio = portfolio
        self.logger = logger or logging.getLogger("MIE.AdvancedReporter")
    
    def generate_executive_summary(self, hypotheses: List[Dict], readiness_score: float) -> Dict:
        """
        Generate executive-level summary (1-page overview)
        """
        summary = {
            "generated_at": datetime.utcnow().isoformat(),
            "system_status": self._get_system_status(readiness_score),
            "key_metrics": {
                "total_hypotheses": len(hypotheses),
                "active_hypotheses": len([h for h in hypotheses if h.get("status") == "testing"]),
                "readiness_score": round(readiness_score, 1),
                "system_health": self._calculate_system_health(hypotheses, readiness_score)
            },
            "top_insights": [],
            "recommendations": [],
            "next_actions": []
        }
        
        # Top insights
        if self.analyzer:
            top_hyps = self.analyzer.get_top_scoring_hypotheses(3)
            for hyp in top_hyps:
                summary["top_insights"].append(
                    f"Hypothesis {hyp['id']} (score {hyp['score']:.3f}): {hyp['observation'][:50]}"
                )
        
        # Recommendations based on readiness
        if readiness_score < 50:
            summary["recommendations"].append("Focus on hypothesis diversity - continue bootstrap phase")
            summary["recommendations"].append("Increase observation collection frequency")
        elif readiness_score < 75:
            summary["recommendations"].append("Prepare for advanced feature deployment")
            summary["recommendations"].append("Establish hypothesis quality baselines")
        else:
            summary["recommendations"].append("Ready for production deployment")
        
        # Next actions
        summary["next_actions"].append("Monitor top 3 hypotheses for confidence trends")
        summary["next_actions"].append("Review weekly performance summaries")
        summary["next_actions"].append("Assess multi-timeframe validation consistency")
        
        return summary
    
    def _get_system_status(self, readiness_score: float) -> str:
        """Get human-readable system status"""
        if readiness_score < 20:
            return "🔴 BOOTSTRAP_EARLY"
        elif readiness_score < 40:
            return "🟡 BOOTSTRAP_MID"
        elif readiness_score < 60:
            return "🟠 BOOTSTRAP_LATE"
        elif readiness_score < 75:
            return "🟢 PRE_ADVANCED"
        else:
            return "✅ READY_ADVANCED"
    
    def _calculate_system_health(self, hypotheses: List[Dict], readiness: float) -> float:
        """Calculate overall system health (0-100)"""
        if not hypotheses:
            return readiness
        
        active_count = len([h for h in hypotheses if h.get("status") == "testing"])
        completed_count = len([h for h in hypotheses if h.get("status") == "archived"])
        total = len(hypotheses)
        
        completion_rate = completed_count / total if total > 0 else 0
        activity_rate = active_count / total if total > 0 else 0
        
        health = (
            readiness * 0.5 +
            completion_rate * 100 * 0.3 +
            activity_rate * 100 * 0.2
        )
        
        return round(min(100, max(0, health)), 1)
    
    def generate_performance_dashboard(self, hypotheses: List[Dict]) -> Dict:
        """
        Generate detailed performance metrics dashboard
        """
        dashboard = {
            "generated_at": datetime.utcnow().isoformat(),
            "hypothesis_breakdown": {
                "by_confidence": {},
                "by_status": {},
                "by_asset": {}
            },
            "performance_metrics": {},
            "trend_analysis": {}
        }
        
        # Breakdown by confidence
        conf_buckets = {
            "repeated_observation": 0,
            "weakly_supported": 0,
            "supported": 0,
            "strongly_supported": 0
        }
        
        for hyp in hypotheses:
            conf = hyp.get("confidence", "repeated_observation")
            if conf in conf_buckets:
                conf_buckets[conf] += 1
        
        dashboard["hypothesis_breakdown"]["by_confidence"] = conf_buckets
        
        # Breakdown by status
        status_buckets = {}
        for hyp in hypotheses:
            status = hyp.get("status", "unknown")
            status_buckets[status] = status_buckets.get(status, 0) + 1
        
        dashboard["hypothesis_breakdown"]["by_status"] = status_buckets
        
        # Breakdown by asset
        asset_buckets = {}
        for hyp in hypotheses:
            asset = hyp.get("asset", "unknown")
            asset_buckets[asset] = asset_buckets.get(asset, 0) + 1
        
        dashboard["hypothesis_breakdown"]["by_asset"] = asset_buckets
        
        return dashboard
    
    def generate_strategic_insights(self, hypotheses: List[Dict]) -> List[str]:
        """
        Generate strategic insights from data patterns
        """
        insights = []
        
        if not hypotheses:
            return insights
        
        # Insight 1: Confidence distribution
        strong_count = len([h for h in hypotheses if h.get("confidence") == "strongly_supported"])
        if strong_count > 0:
            pct = (strong_count / len(hypotheses)) * 100
            insights.append(f"📈 {pct:.0f}% of hypotheses achieved strong support - accelerating confidence growth")
        else:
            insights.append("📊 Still in confidence-building phase - continue systematic validation")
        
        # Insight 2: Portfolio health
        active_count = len([h for h in hypotheses if h.get("status") == "testing"])
        insights.append(f"🎯 {active_count} active hypotheses under investigation - portfolio well-diversified")
        
        # Insight 3: Feedback signals
        if self.learner:
            report = self.learner.get_feedback_impact_report()
            if report.get("total_hypotheses_with_feedback", 0) > 0:
                insights.append(f"💬 Feedback quality avg: {report['avg_quality_from_feedback']:.2f} - user feedback improving hypothesis quality")
        
        return insights
    
    def generate_full_report(self, hypotheses: List[Dict], readiness_score: float) -> Dict:
        """
        Generate comprehensive multi-section report
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "executive_summary": self.generate_executive_summary(hypotheses, readiness_score),
            "performance_dashboard": self.generate_performance_dashboard(hypotheses),
            "strategic_insights": self.generate_strategic_insights(hypotheses),
            "report_sections": {
                "system_overview": f"MIE V1 Research Layer - {len(hypotheses)} hypotheses under management",
                "data_coverage": f"Bootstrap phase at {readiness_score:.0f}% readiness",
                "next_review": "Review in 7 days for bootstrap phase assessment"
            }
        }
        
        return report

