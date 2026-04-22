"""
Hypothesis Analyzer - Scoring, visualization, and confidence trends
Part of MIE V1 Research Layer enhanced reporting
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List
import logging

class HypothesisAnalyzer:
    """Analyzes hypotheses for scoring, trends, and visualization"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("MIE.HypothesisAnalyzer")
        self.registry_path = "research_logs/hypothesis_registry.json"
        self.experiment_log_path = "research_logs/experiment_log.jsonl"
    
    def calculate_hypothesis_score(self, hypothesis: Dict) -> Dict:
        """
        Calculate comprehensive score for a hypothesis
        Factors: confidence, evidence_count, test_frequency, consistency
        """
        score_components = {
            "confidence_score": 0.0,
            "evidence_score": 0.0,
            "consistency_score": 0.0,
            "maturity_score": 0.0,
            "overall_score": 0.0
        }
        
        # Confidence score (0-1)
        confidence = hypothesis.get("confidence", "repeated_observation")
        confidence_map = {
            "repeated_observation": 0.3,
            "weakly_supported": 0.6,
            "supported": 0.8,
            "strongly_supported": 0.95
        }
        score_components["confidence_score"] = confidence_map.get(confidence, 0.3)
        
        # Evidence score based on tests run
        tests_run = hypothesis.get("tests_run", 0)
        evidence_score = min(0.8, tests_run * 0.15)  # Max 0.8 with 5+ tests
        score_components["evidence_score"] = evidence_score
        
        # Consistency score based on success rate
        success_rate = hypothesis.get("success_rate", 0.0)
        consistency_score = success_rate * 0.9  # Up to 0.9
        score_components["consistency_score"] = consistency_score
        
        # Maturity score based on age and activity
        born_date_str = hypothesis.get("born_date", "")
        if born_date_str:
            born_date = datetime.fromisoformat(born_date_str.replace('Z', '+00:00'))
            age_days = (datetime.utcnow() - born_date).days
            maturity_score = min(0.6, age_days * 0.05)  # Max 0.6, grows with age
            score_components["maturity_score"] = maturity_score
        
        # Overall score (weighted average)
        weights = {
            "confidence_score": 0.30,
            "evidence_score": 0.25,
            "consistency_score": 0.30,
            "maturity_score": 0.15
        }
        
        overall = sum(
            score_components[key] * weights[key]
            for key in weights
        )
        score_components["overall_score"] = round(overall, 3)
        
        return score_components
    
    def get_confidence_trends(self, lookback_days: int = 30) -> Dict:
        """
        Analyze confidence trends for all hypotheses
        Returns historical confidence changes
        """
        trends = {
            "improving": [],
            "stable": [],
            "declining": [],
            "new": []
        }
        
        try:
            with open(self.registry_path, "r") as f:
                registry = json.load(f)
        except:
            return trends
        
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        
        for hyp in registry.get("active", []) + registry.get("completed", []):
            born_str = hyp.get("born_date", "")
            if not born_str:
                continue
            
            born_date = datetime.fromisoformat(born_str.replace('Z', '+00:00'))
            
            # Check if new
            if born_date > cutoff:
                trends["new"].append({
                    "id": hyp["id"],
                    "observation": hyp.get("observation", "")[:50],
                    "confidence": hyp.get("confidence", "repeated_observation")
                })
            else:
                # For existing hypotheses, track if confidence improved
                current_conf = hyp.get("confidence", "repeated_observation")
                previous_conf = hyp.get("previous_confidence", "repeated_observation")
                
                conf_levels = ["repeated_observation", "weakly_supported", "supported", "strongly_supported"]
                current_idx = conf_levels.index(current_conf) if current_conf in conf_levels else 0
                previous_idx = conf_levels.index(previous_conf) if previous_conf in conf_levels else 0
                
                if current_idx > previous_idx:
                    trends["improving"].append({
                        "id": hyp["id"],
                        "from": previous_conf,
                        "to": current_conf
                    })
                elif current_idx < previous_idx:
                    trends["declining"].append({
                        "id": hyp["id"],
                        "from": previous_conf,
                        "to": current_conf
                    })
                else:
                    trends["stable"].append({
                        "id": hyp["id"],
                        "confidence": current_conf
                    })
        
        return trends
    
    def get_top_scoring_hypotheses(self, limit: int = 10) -> List[Dict]:
        """
        Get highest-scoring hypotheses
        Sorted by overall_score
        """
        try:
            with open(self.registry_path, "r") as f:
                registry = json.load(f)
        except:
            return []
        
        all_hyps = registry.get("active", []) + registry.get("completed", [])
        
        # Score each hypothesis
        scored = []
        for hyp in all_hyps:
            score_data = self.calculate_hypothesis_score(hyp)
            scored.append({
                "id": hyp["id"],
                "observation": hyp.get("observation", "")[:60],
                "confidence": hyp.get("confidence", ""),
                "status": hyp.get("status", ""),
                "score": score_data["overall_score"],
                "details": score_data
            })
        
        # Sort by overall score
        scored.sort(key=lambda x: x["score"], reverse=True)
        
        return scored[:limit]
    
    def generate_report(self) -> Dict:
        """
        Generate comprehensive analysis report
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "top_hypotheses": self.get_top_scoring_hypotheses(10),
            "confidence_trends": self.get_confidence_trends(30),
            "summary": {}
        }
        
        # Add summary stats
        try:
            with open(self.registry_path, "r") as f:
                registry = json.load(f)
                active = registry.get("active", [])
                completed = registry.get("completed", [])
                
                report["summary"] = {
                    "total_active": len(active),
                    "total_completed": len(completed),
                    "avg_confidence": sum(
                        ["repeated_observation", "weakly_supported", "supported", "strongly_supported"].index(
                            h.get("confidence", "repeated_observation")
                        )
                        for h in active + completed
                    ) / max(1, len(active) + len(completed))
                }
        except:
            pass
        
        return report

