"""
Status Dashboard - HTML file that shows MIE V1 validation metrics
Updates every 30 seconds with latest data from DB
Doesn't require Telegram - direct browser access
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List


class StatusDashboard:
    """Generates HTML dashboard with real-time MIE metrics"""

    def __init__(self, db, decision_registry=None, logger=None):
        self.db = db
        self.decision_registry = decision_registry
        self.logger = logger
        self.output_path = Path("mie_status.html")

    def get_observations_count(self) -> Dict[str, int]:
        """Count observations per asset"""
        btc_obs = self.db.get_observations(asset="BTC", lookback_hours=24)
        eth_obs = self.db.get_observations(asset="ETH", lookback_hours=24)

        return {
            "BTC": len(btc_obs) if btc_obs else 0,
            "ETH": len(eth_obs) if eth_obs else 0,
            "total": (len(btc_obs) if btc_obs else 0) + (len(eth_obs) if eth_obs else 0)
        }

    def get_latest_prices(self) -> Dict[str, float]:
        """Get latest prices from DB"""
        prices = {}

        for asset in ["BTC", "ETH"]:
            obs = self.db.get_observations(asset=asset, lookback_hours=24, observation_type="price")
            if obs and len(obs) > 0:
                prices[asset] = obs[-1]["value"]

        return prices

    def get_decision_metrics(self) -> Dict:
        """Get metrics from decision registry"""
        if not self.decision_registry:
            return {
                "total_decisions": 0,
                "active_decisions": 0,
                "completed_decisions": 0,
                "win_rate": 0.0,
            }

        active = len(self.decision_registry.active_decisions)
        completed = len(self.decision_registry.completed_decisions)

        wins = 0
        if completed > 0:
            wins = sum(1 for d in self.decision_registry.completed_decisions
                      if d.get("outcome_24h", {}).get("win", False))

        return {
            "total_decisions": active + completed,
            "active_decisions": active,
            "completed_decisions": completed,
            "win_rate": (wins / completed * 100) if completed > 0 else 0.0,
            "wins": wins,
        }

    def generate_html(self) -> str:
        """Generate HTML dashboard"""
        obs_count = self.get_observations_count()
        prices = self.get_latest_prices()
        decision_metrics = self.get_decision_metrics()

        timestamp = datetime.utcnow().isoformat()

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MIE V1 - Status Dashboard</title>
    <meta http-equiv="refresh" content="30">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #fff;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .card {{
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
        }}
        .card h2 {{
            font-size: 1.2em;
            margin-bottom: 15px;
            color: #4fb3d9;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .metric:last-child {{ border-bottom: none; }}
        .metric-label {{ color: #aaa; }}
        .metric-value {{ font-weight: bold; font-size: 1.1em; color: #4fb3d9; }}
        .status-good {{ color: #4caf50; }}
        .status-warning {{ color: #ff9800; }}
        .status-bad {{ color: #f44336; }}
        .timestamp {{
            text-align: center;
            margin-top: 30px;
            color: #999;
            font-size: 0.9em;
        }}
        .header-info {{
            text-align: center;
            margin-bottom: 20px;
            color: #aaa;
            font-size: 0.95em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 MIE V1 - Status Dashboard</h1>

        <div class="header-info">
            <p>Real-time validation metrics | Auto-refresh every 30 seconds</p>
            <p>Last update: {timestamp}</p>
        </div>

        <div class="grid">
            <!-- Observations -->
            <div class="card">
                <h2>📊 Market Data Ingestion</h2>
                <div class="metric">
                    <span class="metric-label">Total Observations</span>
                    <span class="metric-value">{obs_count['total']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">BTC Prices Captured</span>
                    <span class="metric-value">{obs_count['BTC']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">ETH Prices Captured</span>
                    <span class="metric-value">{obs_count['ETH']}</span>
                </div>
            </div>

            <!-- Latest Prices -->
            <div class="card">
                <h2>💹 Latest Prices</h2>
                <div class="metric">
                    <span class="metric-label">BTC</span>
                    <span class="metric-value">${prices.get('BTC', 0):.2f}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">ETH</span>
                    <span class="metric-value">${prices.get('ETH', 0):.2f}</span>
                </div>
            </div>

            <!-- Decisions -->
            <div class="card">
                <h2>💡 Decision Registry</h2>
                <div class="metric">
                    <span class="metric-label">Total Decisions</span>
                    <span class="metric-value">{decision_metrics['total_decisions']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Active (Pending)</span>
                    <span class="metric-value status-warning">{decision_metrics['active_decisions']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Completed</span>
                    <span class="metric-value status-good">{decision_metrics['completed_decisions']}</span>
                </div>
            </div>

            <!-- Performance -->
            <div class="card">
                <h2>🎯 Validation Metrics (72h)</h2>
                <div class="metric">
                    <span class="metric-label">Win Rate</span>
                    <span class="metric-value">{decision_metrics['win_rate']:.1f}%</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Wins</span>
                    <span class="metric-value">{decision_metrics['wins']}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Status</span>
                    <span class="metric-value status-good">✅ RUNNING</span>
                </div>
            </div>
        </div>

        <div class="timestamp">
            🔄 This page auto-refreshes every 30 seconds
            <br/>
            Last refresh: {timestamp}
        </div>
    </div>
</body>
</html>
"""
        return html

    def save(self):
        """Save dashboard to HTML file"""
        html = self.generate_html()
        self.output_path.write_text(html)

        if self.logger:
            self.logger.info(f"📊 Status dashboard saved to {self.output_path}")

        return self.output_path
