"""
Portfolio Manager
Manages hypothesis portfolio with diversification and risk controls
Allocates resources across active hypotheses
"""
import json
from datetime import datetime
from typing import Dict, List
import logging

class PortfolioManager:
    """
    Manages multi-hypothesis portfolio
    Diversification, allocation, rebalancing
    """
    
    def __init__(self, db=None, logger=None):
        self.db = db
        self.logger = logger or logging.getLogger("MIE.PortfolioManager")
        self.registry_path = "research_logs/hypothesis_registry.json"
        self.max_allocation_single = 0.40  # Max 40% to single hypothesis
        self.min_allocation = 0.10  # Min 10% per hypothesis
    
    def calculate_allocation_weights(self, hypotheses: List[Dict]) -> Dict:
        """
        Calculate optimal allocation weights based on:
        - Confidence level
        - Backtest score
        - Correlation with existing
        """
        allocations = {}
        
        if not hypotheses:
            return allocations
        
        # Score each hypothesis
        scores = {}
        for hyp in hypotheses:
            confidence = hyp.get("confidence", "repeated_observation")
            conf_map = {
                "repeated_observation": 0.25,
                "weakly_supported": 0.50,
                "supported": 0.75,
                "strongly_supported": 0.95
            }
            
            conf_score = conf_map.get(confidence, 0.25)
            backtest_score = hyp.get("backtest_score", 0.5)
            
            # Combined score
            combined = (conf_score * 0.6 + backtest_score * 0.4)
            scores[hyp["id"]] = combined
        
        # Normalize to weights
        total_score = sum(scores.values())
        
        for hyp_id, score in scores.items():
            weight = score / total_score if total_score > 0 else 1.0 / len(hypotheses)
            
            # Apply constraints
            weight = min(self.max_allocation_single, weight)
            weight = max(self.min_allocation, weight)
            
            allocations[hyp_id] = round(weight, 3)
        
        # Normalize to sum to 1.0
        total = sum(allocations.values())
        if total > 0:
            allocations = {k: round(v / total, 3) for k, v in allocations.items()}
        
        return allocations
    
    def calculate_portfolio_metrics(self, hypotheses: List[Dict]) -> Dict:
        """
        Calculate portfolio-level metrics
        """
        metrics = {
            "total_hypotheses": len(hypotheses),
            "avg_confidence": 0.0,
            "portfolio_sharpe": 0.0,
            "diversification_score": 0.0,
            "concentration": 0.0
        }
        
        if not hypotheses:
            return metrics
        
        # Average confidence
        conf_levels = ["repeated_observation", "weakly_supported", "supported", "strongly_supported"]
        conf_map = {
            "repeated_observation": 0.25,
            "weakly_supported": 0.50,
            "supported": 0.75,
            "strongly_supported": 0.95
        }
        
        confidences = [conf_map.get(h.get("confidence", "repeated_observation"), 0.25) for h in hypotheses]
        metrics["avg_confidence"] = round(sum(confidences) / len(confidences), 3) if confidences else 0
        
        # Diversification (number of different assets/patterns)
        assets = set()
        patterns = set()
        for hyp in hypotheses:
            assets.add(hyp.get("asset", "unknown"))
            obs = hyp.get("observation", "")
            pattern_type = obs.split()[0] if obs else "unknown"
            patterns.add(pattern_type)
        
        diversification = (len(assets) + len(patterns)) / (2 * len(hypotheses)) if hypotheses else 0
        metrics["diversification_score"] = round(min(1.0, diversification), 3)
        
        # Concentration (Herfindahl index)
        allocations = self.calculate_allocation_weights(hypotheses)
        concentration = sum(w ** 2 for w in allocations.values()) if allocations else 0
        metrics["concentration"] = round(concentration, 3)
        
        return metrics
    
    def rebalance_portfolio(self, hypotheses: List[Dict]) -> Dict:
        """
        Rebalance portfolio based on performance
        """
        allocations = self.calculate_allocation_weights(hypotheses)
        
        rebalance = {
            "timestamp": datetime.utcnow().isoformat(),
            "allocations": allocations,
            "actions": [],
            "metrics": self.calculate_portfolio_metrics(hypotheses)
        }
        
        for hyp_id, allocation in allocations.items():
            # Find hypothesis
            hyp = next((h for h in hypotheses if h["id"] == hyp_id), None)
            if not hyp:
                continue
            
            current_allocation = hyp.get("allocation", 0)
            allocation_change = allocation - current_allocation
            
            if allocation_change > 0.05:
                rebalance["actions"].append({
                    "hypothesis_id": hyp_id,
                    "action": "increase",
                    "from": round(current_allocation, 3),
                    "to": allocation,
                    "change": round(allocation_change, 3)
                })
            elif allocation_change < -0.05:
                rebalance["actions"].append({
                    "hypothesis_id": hyp_id,
                    "action": "decrease",
                    "from": round(current_allocation, 3),
                    "to": allocation,
                    "change": round(allocation_change, 3)
                })
        
        return rebalance
    
    def get_portfolio_report(self, hypotheses: List[Dict]) -> Dict:
        """
        Generate comprehensive portfolio report
        """
        allocations = self.calculate_allocation_weights(hypotheses)
        
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "allocations": allocations,
            "metrics": self.calculate_portfolio_metrics(hypotheses),
            "rebalance_plan": self.rebalance_portfolio(hypotheses),
            "top_contributors": [],
            "risk_assessment": {}
        }
        
        # Top contributors
        sorted_alloc = sorted(allocations.items(), key=lambda x: x[1], reverse=True)
        for hyp_id, alloc in sorted_alloc[:3]:
            hyp = next((h for h in hypotheses if h["id"] == hyp_id), None)
            if hyp:
                report["top_contributors"].append({
                    "hypothesis_id": hyp_id,
                    "allocation": alloc,
                    "confidence": hyp.get("confidence", "unknown")
                })
        
        # Risk assessment
        metrics = report["metrics"]
        risk_score = 1.0 - metrics["avg_confidence"]
        concentration_risk = metrics["concentration"]
        diversification_benefit = metrics["diversification_score"]
        
        report["risk_assessment"] = {
            "confidence_risk": round(risk_score, 3),
            "concentration_risk": round(concentration_risk, 3),
            "diversification_benefit": round(diversification_benefit, 3),
            "overall_risk": round((risk_score * 0.4 + concentration_risk * 0.6), 3)
        }
        
        return report

