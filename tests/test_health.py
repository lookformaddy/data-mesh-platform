"""SLO health scoring: grades, component weights, breach reporting."""

from datamesh.models import HealthSignal


def test_healthy_product_scores_high(mesh, good_signal):
    mesh.record_signal(good_signal)
    score = mesh.health("orders.daily")
    assert score.grade == "healthy" and score.score >= 90
    assert score.slo_breaches == []


def test_stale_product_is_degraded_or_critical(mesh):
    mesh.record_signal(HealthSignal("orders.daily", newest_data_age_hours=72,
                                    completeness=0.99, availability=0.999))
    score = mesh.health("orders.daily")
    assert score.grade in ("degraded", "critical")
    assert any("freshness" in b for b in score.slo_breaches)


def test_low_completeness_breaches_slo(mesh):
    mesh.record_signal(HealthSignal("orders.daily", newest_data_age_hours=1,
                                    completeness=0.50, availability=0.999))
    score = mesh.health("orders.daily")
    assert any("completeness" in b for b in score.slo_breaches)
    assert score.components["completeness"] == 50.0


def test_no_signal_is_an_error(mesh):
    import pytest
    with pytest.raises(ValueError):
        mesh.health("orders.daily")


def test_grade_boundaries():
    from datamesh.health import HealthScore
    assert HealthScore.grade_for(80) == "healthy"
    assert HealthScore.grade_for(50) == "degraded"
    assert HealthScore.grade_for(49.9) == "critical"
