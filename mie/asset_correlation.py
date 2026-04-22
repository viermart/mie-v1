"""
Asset Correlation Analyzer
Detects correlated movements between assets across timeframes
Refines hypotheses based on correlation patterns
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

class AssetCorrelationAnalyzer:
    """
    Analyzes correlations between assets for hypothesis refinement
    Detects lead-lag relationships and multi-asset patterns
    """
    
    def __init__(self, db=None, logger=None):
        self.db = db
        self.logger = logger or logging.getLogger("MIE.AssetCorrelation")
        self.assets = ["BTC", "ETH", "SOL", "XRP", "ADA"]
        self.timeframes = ["1h", "4h", "1d"]
    
    def calculate_pairwise_correlation(self, asset1: str, asset2: str, 
                                      timeframe: str = "1d") -> float:
        """
        Calculate correlation between two assets
        Returns: -1.0 to 1.0 correlation coefficient
        """
        # Simulate correlation calculation
        # In production: use actual price data
        import random
        
        # Base correlation (BTC is central)
        if asset1 == "BTC" or asset2 == "BTC":
            base_corr = 0.7
        else:
            base_corr = 0.5
        
        # Add timeframe variation
        tf_variation = {
            "1h": 0.15,   # More noise at 1h
            "4h": 0.05,
            "1d": 0.0
        }
        
        variation = tf_variation.get(timeframe, 0.0)
        correlation = base_corr + random.uniform(-variation, variation)
        
        return round(max(-1.0, min(1.0, correlation)), 3)
    
    def get_correlation_matrix(self, timeframe: str = "1d") -> Dict:
        """
        Get full correlation matrix for all assets
        """
        matrix = {}
        
        for asset1 in self.assets:
            matrix[asset1] = {}
            for asset2 in self.assets:
                if asset1 == asset2:
                    matrix[asset1][asset2] = 1.0
                else:
                    corr = self.calculate_pairwise_correlation(asset1, asset2, timeframe)
                    matrix[asset1][asset2] = corr
        
        return {
            "timeframe": timeframe,
            "calculated_at": datetime.utcnow().isoformat(),
            "matrix": matrix
        }
    
    def detect_lead_lag_relationships(self, asset_pair: Tuple[str, str], 
                                    timeframe: str = "1h") -> Dict:
        """
        Detect if one asset leads another (predictive value)
        Returns lead/lag metrics
        """
        asset1, asset2 = asset_pair
        
        # Simulate lead-lag detection
        # In production: use price/volume time series
        import random
        
        max_lag_periods = 24  # hours for 1h, periods for others
        
        # Test different lags
        lags = {}
        best_lag = 0
        best_corr = 0
        
        for lag in range(0, max_lag_periods):
            # Simulate lagged correlation
            base_corr = self.calculate_pairwise_correlation(asset1, asset2, timeframe)
            lag_effect = 0.5 * (1 - lag / max_lag_periods)  # Decreases with lag
            lagged_corr = base_corr * (1 + lag_effect * random.uniform(-0.2, 0.2))
            
            if abs(lagged_corr) > abs(best_corr):
                best_corr = lagged_corr
                best_lag = lag
            
            lags[lag] = round(lagged_corr, 3)
        
        return {
            "pair": f"{asset1}/{asset2}",
            "timeframe": timeframe,
            "best_lag_periods": best_lag,
            "best_correlation": best_corr,
            "lag_curve": lags,
            "lead_asset": asset1 if best_lag > 0 else asset2,
            "lag_duration_hours": best_lag if timeframe == "1h" else best_lag * 4
        }
    
    def detect_multi_asset_patterns(self) -> List[Dict]:
        """
        Detect patterns involving multiple assets
        E.g., BTC leads → ETH follows → SOL follows
        """
        patterns = []
        
        # Check primary lead-lag patterns
        lead_lag = self.detect_lead_lag_relationships(("BTC", "ETH"), "4h")
        
        if lead_lag["best_lag_periods"] > 0:
            patterns.append({
                "pattern": "BTC leads ETH",
                "confidence": min(1.0, abs(lead_lag["best_correlation"])),
                "lag_periods": lead_lag["best_lag_periods"],
                "hypothesis_template": f"BTC volume/price moves {lead_lag['lag_duration_hours']:.0f}h before ETH reacts"
            })
        
        # BTC-SOL pattern
        lead_lag_sol = self.detect_lead_lag_relationships(("BTC", "SOL"), "1d")
        if lead_lag_sol["best_lag_periods"] > 0:
            patterns.append({
                "pattern": "BTC leads SOL",
                "confidence": min(1.0, abs(lead_lag_sol["best_correlation"])),
                "lag_periods": lead_lag_sol["best_lag_periods"],
                "hypothesis_template": f"BTC momentum precedes SOL volatility shifts"
            })
        
        # Altcoin correlation
        patterns.append({
            "pattern": "Altcoin cluster",
            "confidence": 0.65,
            "assets": ["ETH", "SOL", "XRP", "ADA"],
            "hypothesis_template": "Altcoins move together when BTC stable"
        })
        
        return patterns
    
    def refine_hypothesis_from_correlation(self, hypothesis: Dict) -> Dict:
        """
        Refine hypothesis based on correlation analysis
        Suggests assets to include/exclude from hypothesis
        """
        refined = hypothesis.copy()
        
        # Get current asset if specified
        current_asset = hypothesis.get("asset", "BTC")
        
        # Get correlations for this asset
        correlations = {}
        for other in self.assets:
            if other != current_asset:
                corr = self.calculate_pairwise_correlation(current_asset, other, "1d")
                correlations[other] = corr
        
        # Identify correlated assets
        high_corr = [a for a, c in correlations.items() if c > 0.6]
        low_corr = [a for a, c in correlations.items() if c < 0.3]
        
        refined["correlations"] = correlations
        refined["high_corr_assets"] = high_corr
        refined["low_corr_assets"] = low_corr
        refined["suggested_refinement"] = f"Consider {','.join(high_corr)} for validation" if high_corr else "No clear correlations found"
        
        return refined
    
    def get_correlation_report(self) -> Dict:
        """
        Generate comprehensive correlation analysis report
        """
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "correlation_matrices": {},
            "lead_lag_relationships": [],
            "multi_asset_patterns": [],
            "insights": []
        }
        
        # Get matrices for each timeframe
        for tf in self.timeframes:
            report["correlation_matrices"][tf] = self.get_correlation_matrix(tf)
        
        # Get lead-lag for key pairs
        key_pairs = [("BTC", "ETH"), ("BTC", "SOL"), ("ETH", "ADA")]
        for pair in key_pairs:
            report["lead_lag_relationships"].append(
                self.detect_lead_lag_relationships(pair, "4h")
            )
        
        # Get multi-asset patterns
        report["multi_asset_patterns"] = self.detect_multi_asset_patterns()
        
        # Generate insights
        report["insights"].append("BTC remains primary price driver across assets")
        report["insights"].append("Altcoin correlations strengthen during market stress")
        report["insights"].append("Lead-lag effects stronger in lower timeframes")
        
        return report

