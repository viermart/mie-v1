"""
Multi-Timeframe Validator
Validates hypotheses across multiple timeframes (1h, 4h, 1d, 1w)
Prevents single-timeframe overfitting
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List
import logging

class MultiTimeframeValidator:
    """
    Validates hypotheses across multiple timeframes
    Ensures patterns hold consistently across different time scales
    """
    
    TIMEFRAMES = {
        "1h": timedelta(hours=1),
        "4h": timedelta(hours=4),
        "1d": timedelta(days=1),
        "1w": timedelta(weeks=1)
    }
    
    def __init__(self, db=None, logger=None):
        self.db = db
        self.logger = logger or logging.getLogger("MIE.MultiTimeframeValidator")
    
    def validate_across_timeframes(self, hypothesis: Dict) -> Dict:
        """
        Validate a hypothesis across all timeframes
        Returns validation results for each timeframe
        """
        results = {
            "hypothesis_id": hypothesis["id"],
            "overall_valid": False,
            "timeframes": {},
            "consistency_score": 0.0,
            "recommendation": None
        }
        
        # Get hypothesis observation window
        observation = hypothesis.get("observation", "")
        asset = hypothesis.get("asset", "BTC")
        
        # For each timeframe, validate
        valid_count = 0
        consistency_scores = []
        
        for tf_name, tf_duration in self.TIMEFRAMES.items():
            # Simulate validation on this timeframe
            # In production: fetch actual market data for this timeframe
            tf_result = self._validate_on_timeframe(hypothesis, tf_name, tf_duration)
            results["timeframes"][tf_name] = tf_result
            
            if tf_result["valid"]:
                valid_count += 1
            
            consistency_scores.append(tf_result["score"])
        
        # Overall valid if valid on at least 2 timeframes
        results["overall_valid"] = valid_count >= 2
        results["consistency_score"] = sum(consistency_scores) / len(consistency_scores)
        
        # Recommendation
        if results["overall_valid"]:
            if valid_count == 4:
                results["recommendation"] = "STRONG - Valid across all timeframes"
            elif valid_count == 3:
                results["recommendation"] = "GOOD - Valid on 3/4 timeframes"
            else:
                results["recommendation"] = "WEAK - Valid on only 2/4 timeframes"
        else:
            results["recommendation"] = "INVALID - Not consistent across timeframes"
        
        return results
    
    def _validate_on_timeframe(self, hypothesis: Dict, timeframe: str, duration: timedelta) -> Dict:
        """
        Validate hypothesis on a specific timeframe
        """
        # Simulate validation (in production: real market data)
        import random
        
        result = {
            "timeframe": timeframe,
            "valid": random.choice([True, True, True, False]),  # 75% pass rate
            "score": round(random.uniform(0.6, 0.95), 3),
            "sample_size": random.randint(20, 100),
            "observations": random.randint(5, 30)
        }
        
        return result
    
    def get_multiframe_report(self, hypotheses: List[Dict]) -> Dict:
        """
        Generate multi-timeframe validation report for multiple hypotheses
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_hypotheses": len(hypotheses),
            "multi_frame_valid": 0,
            "single_frame_only": 0,
            "invalid": 0,
            "avg_consistency": 0.0,
            "details": []
        }
        
        consistency_scores = []
        
        for hyp in hypotheses:
            validation = self.validate_across_timeframes(hyp)
            
            if validation["overall_valid"]:
                if len([tf for tf, result in validation["timeframes"].items() if result["valid"]]) == 4:
                    report["multi_frame_valid"] += 1
                else:
                    report["single_frame_only"] += 1
            else:
                report["invalid"] += 1
            
            consistency_scores.append(validation["consistency_score"])
            
            report["details"].append({
                "id": hyp["id"],
                "observation": hyp.get("observation", "")[:60],
                "overall_valid": validation["overall_valid"],
                "consistency": validation["consistency_score"],
                "recommendation": validation["recommendation"]
            })
        
        if consistency_scores:
            report["avg_consistency"] = sum(consistency_scores) / len(consistency_scores)
        
        return report
    
    def validate_for_promotion(self, hypothesis: Dict) -> bool:
        """
        Check if hypothesis passes multi-timeframe validation for promotion
        Requirement: Valid on at least 2 timeframes with >0.70 consistency
        """
        validation = self.validate_across_timeframes(hypothesis)
        
        required_timeframes = 2
        valid_count = len([tf for tf, result in validation["timeframes"].items() if result["valid"]])
        
        passes = (
            valid_count >= required_timeframes and
            validation["consistency_score"] >= 0.70
        )
        
        if not passes:
            reason = f"Valid on {valid_count}/{required_timeframes} timeframes, consistency {validation['consistency_score']:.2f}"
            self.logger.debug(f"Hypothesis {hypothesis['id']} failed multi-timeframe validation: {reason}")
        
        return passes

