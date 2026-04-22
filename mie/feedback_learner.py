"""
Feedback Learner - Adaptive learning from user feedback
Improves hypothesis quality based on feedback signals
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List
import logging

class FeedbackLearner:
    """
    Learns from user feedback to improve hypothesis quality
    Tracks: useful/noise ratings, confidence adjustments, pattern recognition
    """
    
    def __init__(self, db=None, logger=None):
        self.db = db
        self.logger = logger or logging.getLogger("MIE.FeedbackLearner")
        self.registry_path = "research_logs/hypothesis_registry.json"
        self.feedback_weight = 0.15  # How much feedback influences confidence
    
    def process_feedback(self, hypothesis_id: str, feedback_type: str, quality_score: float) -> Dict:
        """
        Process user feedback and adjust hypothesis confidence
        feedback_type: "useful" (1.0) | "partial" (0.5) | "noise" (0.0)
        quality_score: 0.0 to 1.0
        """
        result = {
            "hypothesis_id": hypothesis_id,
            "feedback_processed": False,
            "confidence_adjustment": 0.0,
            "new_confidence": None
        }
        
        # Load registry
        try:
            with open(self.registry_path, "r") as f:
                registry = json.load(f)
        except:
            return result
        
        # Find hypothesis
        target_hyp = None
        for hyp in registry.get("active", []) + registry.get("completed", []):
            if hyp["id"] == hypothesis_id:
                target_hyp = hyp
                break
        
        if not target_hyp:
            self.logger.warning(f"Hypothesis {hypothesis_id} not found")
            return result
        
        # Calculate feedback-based adjustment
        # Positive feedback -> increase confidence
        # Negative feedback -> decrease confidence
        adjustment = quality_score * self.feedback_weight
        
        # Get current confidence level
        current_conf = target_hyp.get("confidence", "repeated_observation")
        conf_map = {
            "repeated_observation": 0.3,
            "weakly_supported": 0.6,
            "supported": 0.8,
            "strongly_supported": 0.95
        }
        
        current_score = conf_map.get(current_conf, 0.3)
        new_score = min(0.95, max(0.3, current_score + adjustment))
        
        # Map back to confidence level
        inv_map = {v: k for k, v in conf_map.items()}
        new_confidence = self._find_closest_confidence(new_score, conf_map)
        
        result["confidence_adjustment"] = adjustment
        result["new_confidence"] = new_confidence
        result["feedback_processed"] = True
        
        # Update hypothesis in registry
        target_hyp["previous_confidence"] = current_conf
        target_hyp["confidence"] = new_confidence
        target_hyp["feedback_count"] = target_hyp.get("feedback_count", 0) + 1
        target_hyp["last_feedback"] = datetime.utcnow().isoformat()
        target_hyp["feedback_quality_avg"] = self._calculate_avg_feedback(
            target_hyp.get("feedback_quality_avg", quality_score),
            target_hyp.get("feedback_count", 1),
            quality_score
        )
        
        # Save back
        with open(self.registry_path, "w") as f:
            json.dump(registry, f, indent=2)
        
        self.logger.info(f"Feedback processed for {hypothesis_id}: {current_conf} -> {new_confidence}")
        
        return result
    
    def _find_closest_confidence(self, score: float, conf_map: Dict) -> str:
        """Find closest confidence level to given score"""
        closest_key = "repeated_observation"
        closest_diff = abs(conf_map["repeated_observation"] - score)
        
        for key, value in conf_map.items():
            diff = abs(value - score)
            if diff < closest_diff:
                closest_diff = diff
                closest_key = key
        
        return closest_key
    
    def _calculate_avg_feedback(self, current_avg: float, count: int, new_score: float) -> float:
        """Calculate running average of feedback scores"""
        return ((current_avg * count) + new_score) / (count + 1)
    
    def get_feedback_impact_report(self) -> Dict:
        """
        Analyze how feedback has impacted hypothesis quality
        """
        try:
            with open(self.registry_path, "r") as f:
                registry = json.load(f)
        except:
            return {}
        
        report = {
            "total_hypotheses_with_feedback": 0,
            "avg_quality_from_feedback": 0.0,
            "confidence_improvements": 0,
            "confidence_regressions": 0,
            "high_quality_feedback": []
        }
        
        qualities = []
        for hyp in registry.get("active", []) + registry.get("completed", []):
            if hyp.get("feedback_count", 0) > 0:
                report["total_hypotheses_with_feedback"] += 1
                quality = hyp.get("feedback_quality_avg", 0.5)
                qualities.append(quality)
                
                # Track confidence changes
                if hyp.get("previous_confidence") and hyp.get("confidence"):
                    conf_levels = ["repeated_observation", "weakly_supported", "supported", "strongly_supported"]
                    prev_idx = conf_levels.index(hyp.get("previous_confidence", "repeated_observation"))
                    curr_idx = conf_levels.index(hyp.get("confidence", "repeated_observation"))
                    
                    if curr_idx > prev_idx:
                        report["confidence_improvements"] += 1
                    elif curr_idx < prev_idx:
                        report["confidence_regressions"] += 1
                
                # Track high-quality feedback
                if quality > 0.75:
                    report["high_quality_feedback"].append({
                        "id": hyp["id"],
                        "quality": quality,
                        "confidence": hyp.get("confidence")
                    })
        
        if qualities:
            report["avg_quality_from_feedback"] = sum(qualities) / len(qualities)
        
        return report
    
    def recommend_hypothesis_adjustment(self) -> List[Dict]:
        """
        Recommend which hypotheses should be adjusted based on feedback
        """
        try:
            with open(self.registry_path, "r") as f:
                registry = json.load(f)
        except:
            return []
        
        recommendations = []
        
        for hyp in registry.get("active", []):
            feedback_count = hyp.get("feedback_count", 0)
            feedback_quality = hyp.get("feedback_quality_avg", 0.5)
            
            # Low quality but has feedback -> consider retiring
            if feedback_count >= 3 and feedback_quality < 0.4:
                recommendations.append({
                    "action": "consider_retiring",
                    "hypothesis_id": hyp["id"],
                    "reason": f"Low feedback quality ({feedback_quality:.2f}) after {feedback_count} ratings",
                    "severity": "high"
                })
            
            # High quality but low confidence -> promote
            elif feedback_count >= 2 and feedback_quality > 0.75 and hyp.get("confidence") in ["repeated_observation", "weakly_supported"]:
                recommendations.append({
                    "action": "promote_confidence",
                    "hypothesis_id": hyp["id"],
                    "reason": f"High feedback quality ({feedback_quality:.2f}) supports confidence increase",
                    "severity": "medium"
                })
        
        return recommendations

