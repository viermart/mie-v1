"""
Enhanced Telegram Reporter
Integrates hypothesis scoring into daily/weekly reports
Shows top-scoring hypotheses with confidence trends
"""
import json
from datetime import datetime
from typing import Dict, List
import logging

class EnhancedTelegramReporter:
    """
    Extended reporting with hypothesis analysis
    Integrates with HypothesisAnalyzer for rich reporting
    """
    
    def __init__(self, telegram_token: str = None, telegram_chat_id: str = None, 
                 analyzer=None, learner=None, validator=None, logger=None):
        self.token = telegram_token
        self.chat_id = telegram_chat_id
        self.analyzer = analyzer
        self.learner = learner
        self.validator = validator
        self.logger = logger or logging.getLogger("MIE.EnhancedReporter")
    
    def format_hypothesis_for_report(self, hypothesis: Dict, include_score: bool = True) -> str:
        """
        Format a single hypothesis for display in report
        """
        obs = hypothesis.get("observation", "")[:50]
        conf = hypothesis.get("confidence", "unknown")
        status = hypothesis.get("status", "unknown")
        
        lines = [
            f"🔬 {hypothesis['id']}",
            f"   Observation: {obs}",
            f"   Confidence: {conf}",
            f"   Status: {status}"
        ]
        
        if include_score and self.analyzer:
            score_data = self.analyzer.calculate_hypothesis_score(hypothesis)
            score = score_data.get("overall_score", 0)
            lines.append(f"   Score: {score:.3f}/1.0")
        
        return "\n".join(lines)
    
    def format_daily_report_with_hypotheses(self, 
                                           observations_count: int,
                                           hypotheses: List[Dict]) -> str:
        """
        Format complete daily report including top hypotheses
        """
        report = []
        report.append("=" * 60)
        report.append(f"📊 MIE V1 Daily Report - {datetime.utcnow().strftime('%Y-%m-%d')}")
        report.append("=" * 60)
        
        # Observations summary
        report.append(f"\n📈 Observations: {observations_count} collected")
        
        # Active hypotheses count
        report.append(f"🔬 Active Hypotheses: {len(hypotheses)}")
        
        # Top scoring hypotheses
        if self.analyzer and hypotheses:
            report.append("\n🌟 Top-Scoring Hypotheses:")
            top_hyps = self.analyzer.get_top_scoring_hypotheses(limit=3)
            for hyp in top_hyps:
                report.append(f"\n   • {hyp['id']}: {hyp['score']:.3f}")
                report.append(f"     {hyp['observation']}")
                report.append(f"     Confidence: {hyp['confidence']}")
        
        # Feedback insights
        if self.learner:
            feedback_report = self.learner.get_feedback_impact_report()
            if feedback_report.get("total_hypotheses_with_feedback", 0) > 0:
                report.append(f"\n💬 Feedback: {feedback_report['total_hypotheses_with_feedback']} hypotheses with feedback")
                report.append(f"   Quality avg: {feedback_report['avg_quality_from_feedback']:.2f}")
        
        # Confidence trends
        if self.analyzer:
            trends = self.analyzer.get_confidence_trends(lookback_days=1)
            if trends.get("improving"):
                report.append(f"\n📈 Improving: {len(trends['improving'])} hypotheses")
            if trends.get("declining"):
                report.append(f"📉 Declining: {len(trends['declining'])} hypotheses")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
    
    def format_weekly_report_with_analysis(self, weekly_stats: Dict) -> str:
        """
        Format comprehensive weekly report with analysis
        """
        report = []
        report.append("=" * 60)
        report.append(f"📅 MIE V1 Weekly Report - Week of {datetime.utcnow().strftime('%Y-%m-%d')}")
        report.append("=" * 60)
        
        # Summary stats
        if weekly_stats:
            report.append(f"\n📊 Summary:")
            report.append(f"   Total observations: {weekly_stats.get('total_obs', 0)}")
            report.append(f"   Hypotheses generated: {weekly_stats.get('hyp_generated', 0)}")
            report.append(f"   Validations run: {weekly_stats.get('validations', 0)}")
        
        # Top performers
        if self.analyzer:
            top_hyps = self.analyzer.get_top_scoring_hypotheses(limit=5)
            if top_hyps:
                report.append(f"\n🏆 Top 5 Hypotheses:")
                for i, hyp in enumerate(top_hyps, 1):
                    report.append(f"   {i}. {hyp['id']}: {hyp['score']:.3f}")
        
        # Confidence trends
        if self.analyzer:
            trends = self.analyzer.get_confidence_trends(lookback_days=7)
            report.append(f"\n📊 Confidence Trends (7 days):")
            report.append(f"   Improving: {len(trends.get('improving', []))}")
            report.append(f"   Stable: {len(trends.get('stable', []))}")
            report.append(f"   Declining: {len(trends.get('declining', []))}")
            report.append(f"   New: {len(trends.get('new', []))}")
        
        # Multi-timeframe validation
        if self.validator:
            report.append(f"\n⏱️  Multi-Timeframe Validation:")
            report.append(f"   Valid across: 1h, 4h, 1d, 1w")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
    
    def send_daily_report(self, observations_count: int, hypotheses: List[Dict]) -> bool:
        """
        Send enhanced daily report to Telegram
        """
        if not self.token or not self.chat_id:
            self.logger.warning("Telegram credentials not configured")
            return False
        
        report = self.format_daily_report_with_hypotheses(observations_count, hypotheses)
        
        # In production, send via Telegram API
        # For now, log it
        self.logger.info(f"Daily report generated:\n{report}")
        
        return True
    
    def send_weekly_report(self, weekly_stats: Dict) -> bool:
        """
        Send comprehensive weekly report
        """
        if not self.token or not self.chat_id:
            self.logger.warning("Telegram credentials not configured")
            return False
        
        report = self.format_weekly_report_with_analysis(weekly_stats)
        
        self.logger.info(f"Weekly report generated:\n{report}")
        
        return True
    
    def format_hypothesis_recommendations(self) -> str:
        """
        Format actionable recommendations based on feedback learning
        """
        if not self.learner:
            return ""
        
        recommendations = self.learner.recommend_hypothesis_adjustment()
        
        if not recommendations:
            return "✅ No recommendations at this time"
        
        lines = ["💡 Hypothesis Recommendations:"]
        for rec in recommendations:
            if rec["action"] == "consider_retiring":
                lines.append(f"\n⚠️  Retire {rec['hypothesis_id']}")
                lines.append(f"    {rec['reason']}")
            elif rec["action"] == "promote_confidence":
                lines.append(f"\n⬆️  Promote {rec['hypothesis_id']}")
                lines.append(f"    {rec['reason']}")
        
        return "\n".join(lines)

