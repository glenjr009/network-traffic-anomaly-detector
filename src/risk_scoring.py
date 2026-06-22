"""
Risk Scoring Engine
Calculates security and risk indices based on classified threat states and confidence intervals.
"""

from typing import Dict, Any

class RiskScoringEngine:
    """Computes categorical security scores and determines final operational operational risk tiers."""
    def __init__(self) -> None:
        # Base security scores assigned to each category (100 = perfectly safe, 0 = entirely compromised)
        self._base_scores: Dict[str, int] = {
            "normal traffic": 100,
            "port scan": 78,
            "brute force": 55,
            "data exfiltration": 32,
            "botnet activity": 20,
            "ddos": 15
        }

    def compute_risk(self, threat_name: str, model_confidence: float = 1.0) -> Dict[str, Any]:
        """
        Calculates detailed security scores and assigns a severity band.
        Accepts model confidence to fine-tune the resulting metrics.
        """
        normalized_name = threat_name.lower().strip()
        base_score = self._base_scores.get(normalized_name, 50) # Default score if unrecognized

        # Adjust score slightly based on ML confidence metrics
        if normalized_name != "normal traffic":
            # Higher confidence in an attack lowers the final security score
            adjusted_score = int(base_score * (1.0 - (model_confidence * 0.15)))
        else:
            # Lower confidence in normal traffic shifts it slightly down from 100
            adjusted_score = int(base_score * (0.9 + (model_confidence * 0.1)))

        # Ensure values stay bound between strict operational boundaries
        final_score = max(0, min(100, adjusted_score))
        risk_level = self._determine_tier(final_score)

        return {
            "security_score": final_score,
            "risk_level": risk_level
        }

    def _determine_tier(self, score: int) -> str:
        """Maps an inverted numeric security index to specific operational risk levels."""
        if 95 <= score <= 100:
            return "LOW"
        elif 70 <= score <= 94:
            return "MEDIUM"
        elif 40 <= score <= 69:
            return "HIGH"
        else:
            return "CRITICAL"