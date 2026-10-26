"""Data-product health scoring from SLO compliance + quality signals.

Each component scores 0..100; the total is a weighted blend, so a
product cannot hide a stale feed behind perfect completeness. Grades
give operators one glanceable word: healthy >= 80, degraded >= 50,
otherwise critical. Pure arithmetic — no thresholds hidden in code
that the SLO does not already declare.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import HealthSignal, SLO

WEIGHTS = {"freshness": 0.35, "completeness": 0.25, "availability": 0.25,
           "quality": 0.15}


@dataclass
class HealthScore:
    product_id: str
    score: float
    grade: str
    components: dict[str, float]
    slo_breaches: list[str]

    @staticmethod
    def grade_for(score: float) -> str:
        if score >= 80:
            return "healthy"
        if score >= 50:
            return "degraded"
        return "critical"


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_health(signal: HealthSignal, slo: SLO) -> HealthScore:
    # Freshness: full marks at or under the SLO, linear decay to 0 at 3x.
    if signal.newest_data_age_hours <= slo.freshness_hours:
        freshness = 100.0
    else:
        over = signal.newest_data_age_hours / slo.freshness_hours
        freshness = max(0.0, 100.0 * (1.0 - (over - 1.0) / 2.0))
    completeness = 100.0 * _clamp01(signal.completeness)
    availability = 100.0 * _clamp01(signal.availability)
    quality = 100.0 * _clamp01(signal.quality_score)
    components = {"freshness": round(freshness, 2), "completeness": round(completeness, 2),
                  "availability": round(availability, 2), "quality": round(quality, 2)}
    total = round(sum(components[k] * w for k, w in WEIGHTS.items()), 2)
    breaches: list[str] = []
    if signal.newest_data_age_hours > slo.freshness_hours:
        breaches.append(f"freshness: {signal.newest_data_age_hours}h > {slo.freshness_hours}h SLO")
    if signal.completeness < slo.completeness_min:
        breaches.append(f"completeness: {signal.completeness} < {slo.completeness_min} SLO")
    if signal.availability < slo.availability_min:
        breaches.append(f"availability: {signal.availability} < {slo.availability_min} SLO")
    return HealthScore(signal.product_id, total, HealthScore.grade_for(total),
                       components, breaches)
