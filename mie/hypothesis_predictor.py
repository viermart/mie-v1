"""
Hypothesis Predictor
Predicts future confidence trends and readiness score progression
Uses historical patterns to forecast 7-30 day horizons
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

class HypothesisPredictor:
    """
    Predicts hypothesis confidence trajectories and system readiness
    Enables proactive system management during bootstrap phase
    """
    
    def __init__(self, db=None, logger=None):
        self.db = db
        self.logger = logger or logging.getLogger("MIE.HypothesisPredictor")
        self.registry_path = "research_logs/hypothesis_registry.json"
    
    def forecast_hypothesis_confidence(self, hypothesis: Dict, days: int = 7) -> List[Dict]:
        """
        Forecast confidence trajectory for a single hypothesis
        Returns daily predictions for next N days
        """
        forecasts = []
        
        current_conf = hypothesis.get("confidence", "repeated_observation")
        conf_levels = ["repeated_observation", "weakly_supported", "supported", "strongly_supported"]
        current_idx = conf_levels.index(current_conf) if current_conf in conf_levels else 0
        
        # Get historical trend (if available)
        feedback_quality = hypothesis.get("feedback_quality_avg", 0.5)
        tests_run = hypothesis.get("tests_run", 0)
        
        # Prediction formula:
        # High feedback + many tests = faster progression
        # Low feedback + few tests = slower progression
        progression_rate = (feedback_quality * 0.6 + min(tests_run / 10, 1.0) * 0.4) * 0.5
        
        for day in range(days):
            forecast_date = datetime.utcnow() + timedelta(days=day+1)
            
            # Simple linear progression model
            predicted_idx = min(len(conf_levels)-1, current_idx + (progression_rate * (day + 1)))
            predicted_conf = conf_levels[int(predicted_idx)]
            
            # Confidence interval (wider for further predictions)
            confidence_interval = 0.3 + (0.1 * day)  # Grows with horizon
            
            forecasts.append({
                "date": forecast_date.strftime("%Y-%m-%d"),
                "predicted_confidence": predicted_conf,
                "confidence_level_idx": predicted_idx,
                "probability": 1.0 - confidence_interval,
                "day_ahead": day + 1
            })
        
        return forecasts
    
    def forecast_readiness_progression(self, current_score: float, days: int = 30) -> Dict:
        """
        Forecast readiness score progression for next N days
        Assumes bootstrap phase dynamics
        """
        forecasts = {
            "current_score": current_score,
            "forecast_days": days,
            "predictions": [],
            "target_score": 75.0,
            "estimated_time_to_ready": None
        }
        
        # Bootstrap phase progression model
        # Assumes linear growth in early phase, slowing as it approaches 75
        growth_rate = 0.8  # Points per day
        deceleration = 0.98  # Growth slows as score increases
        
        current = current_score
        
        for day in range(1, days + 1):
            # Adjusted growth (slows as approaching 75)
            distance_to_target = 75.0 - current
            adjusted_growth = growth_rate * (distance_to_target / 75.0)
            
            current = min(75.0, current + adjusted_growth)
            
            forecasts["predictions"].append({
                "day": day,
                "date": (datetime.utcnow() + timedelta(days=day)).strftime("%Y-%m-%d"),
                "predicted_score": round(current, 1),
                "readiness_level": self._classify_level(current)
            })
            
            # Check if reached 75
            if current >= 74.5 and not forecasts["estimated_time_to_ready"]:
                forecasts["estimated_time_to_ready"] = day
        
        return forecasts
    
    def _classify_level(self, score: float) -> str:
        """Classify readiness level from score"""
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
    
    def predict_confidence_distribution(self, hypotheses: List[Dict]) -> Dict:
        """
        Predict distribution of confidence levels across all hypotheses
        7 and 30 day forecasts
        """
        predictions = {
            "current_distribution": self._get_current_distribution(hypotheses),
            "forecast_7_days": None,
            "forecast_30_days": None
        }
        
        # Count current distribution
        conf_map = {
            "repeated_observation": 0,
            "weakly_supported": 0,
            "supported": 0,
            "strongly_supported": 0
        }
        
        for hyp in hypotheses:
            conf = hyp.get("confidence", "repeated_observation")
            if conf in conf_map:
                conf_map[conf] += 1
        
        predictions["current_distribution"] = conf_map
        
        # Forecast 7 days
        forecast_7 = conf_map.copy()
        # Assume 30% of weakly_supported move to supported
        if forecast_7["weakly_supported"] > 0:
            movers = max(1, int(forecast_7["weakly_supported"] * 0.3))
            forecast_7["weakly_supported"] -= movers
            forecast_7["supported"] += movers
        
        predictions["forecast_7_days"] = forecast_7
        
        # Forecast 30 days (more aggressive)
        forecast_30 = conf_map.copy()
        # More movement expected
        if forecast_30["weakly_supported"] > 0:
            movers = max(1, int(forecast_30["weakly_supported"] * 0.6))
            forecast_30["weakly_supported"] -= movers
            forecast_30["supported"] += movers
        if forecast_30["supported"] > 0:
            movers = max(1, int(forecast_30["supported"] * 0.4))
            forecast_30["supported"] -= movers
            forecast_30["strongly_supported"] += movers
        
        predictions["forecast_30_days"] = forecast_30
        
        return predictions
    
    def _get_current_distribution(self, hypotheses: List[Dict]) -> Dict:
        """Get current confidence distribution"""
        dist = {
            "repeated_observation": 0,
            "weakly_supported": 0,
            "supported": 0,
            "strongly_supported": 0
        }
        
        for hyp in hypotheses:
            conf = hyp.get("confidence", "repeated_observation")
            if conf in dist:
                dist[conf] += 1
        
        return dist
    
    def get_prediction_report(self, hypotheses: List[Dict], current_readiness: float) -> Dict:
        """
        Generate comprehensive prediction report
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "readiness_forecast": self.forecast_readiness_progression(current_readiness, 30),
            "confidence_distribution_forecast": self.predict_confidence_distribution(hypotheses),
            "key_predictions": []
        }
        
        # Generate key predictions
        rf = report["readiness_forecast"]
        if rf["estimated_time_to_ready"]:
            report["key_predictions"].append(
                f"Estimated {rf['estimated_time_to_ready']} days until READY_FOR_ADVANCED status"
            )
        
        # Confidence trend prediction
        cdf = report["confidence_distribution_forecast"]
        if cdf["forecast_7_days"]:
            current_strong = cdf["current_distribution"].get("strongly_supported", 0)
            forecast_strong = cdf["forecast_7_days"].get("strongly_supported", 0)
            change = forecast_strong - current_strong
            if change != 0:
                direction = "increase" if change > 0 else "decrease"
                report["key_predictions"].append(
                    f"Expect {direction} in strongly_supported hypotheses (7-day: {change:+d})"
                )
        
        return report

