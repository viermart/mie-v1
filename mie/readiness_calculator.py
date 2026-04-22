"""
Readiness Score Calculator
Calculates system readiness for advancement from bootstrap phase
Based on: observation quality, hypothesis maturity, confidence growth
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List
import logging

class ReadinessCalculator:
    """
    Calculates readiness score for advancement from bootstrap phase
    Combines multiple factors into single readiness metric (0-100)
    """
    
    def __init__(self, db=None, logger=None):
        self.db = db
        self.logger = logger or logging.getLogger("MIE.ReadinessCalculator")
        self.registry_path = "research_logs/hypothesis_registry.json"
        self.experiment_log_path = "research_logs/experiment_log.jsonl"
    
    def calculate_observation_quality_score(self, lookback_days: int = 7) -> float:
        """
        Score observation quality based on:
        - Consistency (obs per day)
        - Diversity (different asset types)
        - Signal-to-noise ratio
        
        Returns: 0-1 score
        """
        if not self.db:
            return 0.5
        
        # Get observation count from last N days
        obs_count = self.db.count_observations_since(days=lookback_days) if hasattr(self.db, 'count_observations_since') else 50
        
        # Target: 40+ observations per week = ~5-6 per day
        expected_per_day = 5
        expected_total = expected_per_day * lookback_days
        
        obs_score = min(1.0, obs_count / expected_total)
        
        return round(obs_score, 3)
    
    def calculate_hypothesis_maturity_score(self) -> float:
        """
        Score hypothesis maturity based on:
        - Age (older = more mature)
        - Tests run (more tests = more mature)
        - Status distribution
        
        Returns: 0-1 score
        """
        try:
            with open(self.registry_path, "r") as f:
                registry = json.load(f)
        except:
            return 0.3
        
        active = registry.get("active", [])
        completed = registry.get("completed", [])
        all_hyps = active + completed
        
        if not all_hyps:
            return 0.2
        
        # Calculate average age
        now = datetime.utcnow()
        ages = []
        
        for hyp in all_hyps:
            born_str = hyp.get("born_date", "")
            if born_str:
                try:
                    born = datetime.fromisoformat(born_str.replace('Z', '+00:00'))
                    age_days = (now - born).days
                    ages.append(age_days)
                except:
                    pass
        
        avg_age = sum(ages) / len(ages) if ages else 0
        age_score = min(1.0, avg_age / 30)  # Max at 30 days
        
        # Calculate test depth
        avg_tests = sum(h.get("tests_run", 0) for h in all_hyps) / len(all_hyps) if all_hyps else 0
        test_score = min(1.0, avg_tests / 5)  # Max at 5 tests average
        
        # Weighted combination
        maturity = (age_score * 0.6 + test_score * 0.4)
        
        return round(maturity, 3)
    
    def calculate_confidence_growth_score(self, lookback_days: int = 7) -> float:
        """
        Score confidence growth based on:
        - Number of hypotheses improved
        - Average confidence level increases
        - Promotion rate (queue to active)
        
        Returns: 0-1 score
        """
        try:
            with open(self.registry_path, "r") as f:
                registry = json.load(f)
        except:
            return 0.3
        
        all_hyps = registry.get("active", []) + registry.get("completed", [])
        
        if not all_hyps:
            return 0.2
        
        # Count hypotheses with improved confidence
        improved_count = 0
        for hyp in all_hyps:
            if hyp.get("previous_confidence") and hyp.get("confidence"):
                conf_levels = ["repeated_observation", "weakly_supported", "supported", "strongly_supported"]
                prev_idx = conf_levels.index(hyp.get("previous_confidence", "repeated_observation"))
                curr_idx = conf_levels.index(hyp.get("confidence", "repeated_observation"))
                if curr_idx > prev_idx:
                    improved_count += 1
        
        improvement_rate = improved_count / len(all_hyps) if all_hyps else 0
        
        # Calculate average confidence level
        conf_map = {
            "repeated_observation": 0.25,
            "weakly_supported": 0.50,
            "supported": 0.75,
            "strongly_supported": 0.95
        }
        
        avg_conf = sum(
            conf_map.get(h.get("confidence", "repeated_observation"), 0.25)
            for h in all_hyps
        ) / len(all_hyps)
        
        # Weighted combination
        growth = (improvement_rate * 0.6 + avg_conf * 0.4)
        
        return round(growth, 3)
    
    def calculate_overall_readiness_score(self) -> Dict:
        """
        Calculate complete readiness score (0-100)
        Combines all factors
        """
        obs_score = self.calculate_observation_quality_score(7)
        maturity_score = self.calculate_hypothesis_maturity_score()
        growth_score = self.calculate_confidence_growth_score(7)
        
        # Weighted combination
        # Equal weight for all three factors
        overall = (
            obs_score * 0.33 +
            maturity_score * 0.33 +
            growth_score * 0.34
        ) * 100
        
        return {
            "overall_score": round(overall, 1),
            "observation_quality": round(obs_score * 100, 1),
            "hypothesis_maturity": round(maturity_score * 100, 1),
            "confidence_growth": round(growth_score * 100, 1),
            "timestamp": datetime.utcnow().isoformat(),
            "readiness_level": self._classify_readiness(overall)
        }
    
    def _classify_readiness(self, score: float) -> str:
        """
        Classify readiness level based on score
        """
        if score < 20:
            return "BOOTSTRAP_EARLY"
        elif score < 40:
            return "BOOTSTRAP_MID"
        elif score < 60:
            return "BOOTSTRAP_LATE"
        elif score < 75:
            return "PRE_ADVANCED"
        else:
            return "READY_FOR_ADVANCED"
    
    def get_readiness_report(self) -> Dict:
        """
        Generate comprehensive readiness report
        """
        scores = self.calculate_overall_readiness_score()
        
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "scores": scores,
            "recommendations": self._generate_recommendations(scores)
        }
        
        return report
    
    def _generate_recommendations(self, scores: Dict) -> List[str]:
        """
        Generate recommendations based on readiness scores
        """
        recommendations = []
        
        if scores["observation_quality"] < 50:
            recommendations.append("Increase observation collection frequency")
        
        if scores["hypothesis_maturity"] < 40:
            recommendations.append("Continue testing hypotheses - need more age/depth")
        
        if scores["confidence_growth"] < 50:
            recommendations.append("Focus on hypothesis improvement - confidence not growing")
        
        overall = scores["overall_score"]
        if overall > 75:
            recommendations.append("✅ System ready for advanced features")
        elif overall > 60:
            recommendations.append("2-3 weeks until advanced features ready")
        elif overall > 40:
            recommendations.append("4-6 weeks estimated to readiness")
        else:
            recommendations.append("Continue bootstrap phase - significant growth needed")
        
        return recommendations

