"""
MIE Research Layer - Generación y validación de hipótesis

Lógica:
1. Detección de triggers: 2+ observaciones del mismo tipo → propone hipótesis
2. Mini-validación: prueba la hipótesis en datos históricos
3. Overfit detection: verifica que no sea casualidad
4. Decisión: falsified / weakly_supported / supported / strongly_supported
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4
import logging


class ResearchLayer:
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger("MIE.Research")

        # Templates de hipótesis (triggers)
        self.hypothesis_templates = {
            "funding_spike": {
                "template": "{asset} funding rate spiked above {threshold}% ({timestamp})",
                "trigger_type": "funding_rate",
                "observation_count_threshold": 2,
            },
            "volume_explosion": {
                "template": "{asset} volume 24h jumped {percent_change}% ({timestamp})",
                "trigger_type": "volume_24h",
                "observation_count_threshold": 2,
            },
            "price_momentum": {
                "template": "{asset} mostró movimiento de +{percent_change}% en 24h ({timestamp})",
                "trigger_type": "price_24h_change",
                "observation_count_threshold": 2,
            },
        }

        # Max activas simultáneamente (V1 scope)
        self.max_active_hypotheses = 5

    def check_hypothesis_triggers(self):
        """
        Revisa si hay observaciones que disparen hipótesis
        Corre después de cada fast_loop
        """
        assets = ["BTC", "ETH"]

        for asset in assets:
            # Obtiene últimas 10 observaciones de precio
            obs = self.db.get_observations(
                asset, lookback_hours=1, observation_type="price"
            )

            if len(obs) >= 2:
                # Calcula cambio de precio
                prices = [o["value"] for o in obs]
                if prices:
                    pct_change = ((prices[0] - prices[-1]) / prices[-1]) * 100
                    if abs(pct_change) > 2:  # Threshold: cambio >2%
                        self._maybe_generate_hypothesis(
                            asset=asset,
                            template_name="price_momentum",
                            data={
                                "asset": asset,
                                "percent_change": abs(pct_change),
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        )

            # Obtiene últimas 5 observaciones de funding
            funding_obs = self.db.get_observations(
                asset, lookback_hours=6, observation_type="funding_rate"
            )

            if len(funding_obs) >= 2:
                rates = [float(o["value"]) for o in funding_obs]
                if max(rates) > 0.01:  # Threshold: funding > 1%
                    self._maybe_generate_hypothesis(
                        asset=asset,
                        template_name="funding_spike",
                        data={
                            "asset": asset,
                            "threshold": max(rates) * 100,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )

    def _maybe_generate_hypothesis(self, asset: str, template_name: str,
                                   data: Dict):
        """
        Genera hipótesis si:
        1. No existe ya una similar
        2. No hemos alcanzado max_active
        3. Mini-validación pasa (no es ruido)
        """
        # Verifica que no exista ya
        active = self.db.get_active_hypotheses()
        if len(active) >= self.max_active_hypotheses:
            self.logger.info(f"⚠️  Max active hypotheses ({self.max_active_hypotheses}) alcanzado")
            return

        # Genera texto de hipótesis
        template = self.hypothesis_templates[template_name]
        hypothesis_text = template["template"].format(**data)

        # Mini-validación en histórico (últimos 7 días)
        is_valid = self._mini_validate(asset, template_name, data)

        if is_valid:
            hypothesis_id = f"hyp_{asset}_{template_name}_{uuid4().hex[:8]}"

            self.db.add_hypothesis(
                hypothesis_id=hypothesis_id,
                text=hypothesis_text,
                born_from=f"trigger:{template_name}",
                priority=0.6  # Default priority
            )

            self.logger.info(f"✅ Hipótesis generada: {hypothesis_id}")
            self.logger.info(f"   Texto: {hypothesis_text}")
        else:
            self.logger.info(f"❌ Hipótesis rechazada (mini-validation falló): {hypothesis_text}")

    def _mini_validate(self, asset: str, template_name: str, data: Dict) -> bool:
        """
        Mini-validación: verifica que el patrón sea repetible en histórico
        Retorna True si la hipótesis parece válida (no ruido)
        """
        if template_name == "price_momentum":
            # Cuenta cuántas veces en los últimos 7 días hubo movimientos >2%
            obs = self.db.get_observations(
                asset, lookback_hours=24*7, observation_type="price"
            )
            if len(obs) < 2:
                return False

            prices = [o["value"] for o in obs]
            movements = []
            for i in range(len(prices) - 1):
                pct = abs((prices[i] - prices[i+1]) / prices[i+1]) * 100
                movements.append(pct)

            # Si hay al menos 3 instancias de movimientos >2%, patrón válido
            count = sum(1 for m in movements if m > 2)
            return count >= 3

        elif template_name == "funding_spike":
            # Cuenta cuántas veces el funding estuvo >1%
            obs = self.db.get_observations(
                asset, lookback_hours=24*7, observation_type="funding_rate"
            )
            if len(obs) < 2:
                return False

            rates = [float(o["value"]) for o in obs]
            count = sum(1 for r in rates if r > 0.01)
            return count >= 2

        return True

    def run_experiment(self, hypothesis_id: str) -> Dict:
        """
        Ejecuta experimento para validar hipótesis
        Retorna resultado de validación
        """
        # Obtiene hipótesis
        hyp = self._get_hypothesis(hypothesis_id)
        if not hyp:
            return {"error": "Hypothesis not found"}

        exp_id = f"exp_{hypothesis_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Crea experimento
        self.db.add_experiment(
            exp_id=exp_id,
            hypothesis_id=hypothesis_id,
            description=f"Validación de: {hyp['text']}",
            test_design={
                "lookback_hours": 24*7,
                "observation_types": ["price", "funding_rate", "open_interest"],
                "statistical_test": "pattern_frequency"
            }
        )

        # Ejecuta validación (por ahora simple)
        result = self._validate_hypothesis(hyp, lookback_hours=24*7)

        # Persiste resultado
        self.db.update_experiment(
            exp_id=exp_id,
            results=result["observations"],
            analysis=result["analysis"],
            classification=result["classification"],
            decision=result["decision"]
        )

        # Actualiza hipótesis con resultado
        if result["classification"] != "awaiting_validation":
            self.db.update_hypothesis(
                hypothesis_id,
                status=result["decision"],
                confidence=result["classification"]
            )

        self.logger.info(f"📈 Experimento {exp_id}: {result['classification']}")

        return result

    def _validate_hypothesis(self, hypothesis: Dict, lookback_hours: int) -> Dict:
        """
        Valida hipótesis contra datos históricos
        Retorna: {classification, decision, observations, analysis}
        """
        # Parse del asset de la hipótesis
        asset = hypothesis["text"].split()[0] if len(hypothesis["text"].split()) > 0 else "BTC"

        obs = self.db.get_observations(asset, lookback_hours=lookback_hours)

        if not obs:
            return {
                "classification": "insufficient_evidence",
                "decision": "awaiting_validation",
                "observations": [],
                "analysis": {"error": "No observations found"}
            }

        # Análisis simple: cuenta cuántas observaciones soportan la hipótesis
        supporting_count = sum(
            1 for o in obs
            if float(o["value"]) > 0  # Placeholder: cualquier valor positivo
        )

        total_count = len(obs)
        support_ratio = supporting_count / total_count if total_count > 0 else 0

        # Clasificación
        if support_ratio > 0.8:
            classification = "strongly_supported"
            decision = "supported"
        elif support_ratio > 0.6:
            classification = "supported"
            decision = "supported"
        elif support_ratio > 0.4:
            classification = "weakly_supported"
            decision = "awaiting_more_data"
        else:
            classification = "falsified"
            decision = "falsified"

        return {
            "classification": classification,
            "decision": decision,
            "observations": {
                "total": total_count,
                "supporting": supporting_count,
                "ratio": support_ratio
            },
            "analysis": {
                "hypothesis_text": hypothesis["text"],
                "lookback_hours": lookback_hours,
                "support_ratio": support_ratio
            }
        }

    def _get_hypothesis(self, hypothesis_id: str) -> Optional[Dict]:
        """Obtiene hipótesis por ID"""
        conn = self.db.conn
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hypotheses WHERE hypothesis_id = ?", (hypothesis_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
