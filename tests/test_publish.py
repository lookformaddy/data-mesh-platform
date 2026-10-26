"""Publish gate: schema violations, SLO violations, blocked = no ship."""

from datamesh.models import HealthSignal


def _schema(mesh):
    return mesh.registry.get_product("orders.daily").schemas["1.0.0"]


def test_good_version_publishes(mesh, good_signal, good_records):
    result = mesh.publish_version("orders.daily", _schema(mesh), good_records, good_signal)
    assert result.allowed and result.violations == []
    assert mesh.registry.get_product("orders.daily").published_version == "1.0.0"


def test_missing_required_field_blocks(mesh, good_signal):
    result = mesh.publish_version("orders.daily", _schema(mesh),
                                  [{"order_id": "O-1"}], good_signal)
    assert not result.allowed
    assert any("customer_id" in v for v in result.violations)
    assert mesh.registry.get_product("orders.daily").published_version is None


def test_wrong_type_and_unknown_field_block(mesh, good_signal):
    result = mesh.publish_version("orders.daily", _schema(mesh),
                                  [{"order_id": "O-1", "order_date": "2026-10-25",
                                    "amount": "ten", "customer_id": "C-1",
                                    "surprise": 1}], good_signal)
    assert not result.allowed
    assert any("amount" in v for v in result.violations)
    assert any("surprise" in v for v in result.violations)


def test_bad_date_blocks(mesh, good_signal):
    result = mesh.publish_version("orders.daily", _schema(mesh),
                                  [{"order_id": "O-1", "order_date": "2026-02-30",
                                    "amount": 1.0, "customer_id": "C-1"}], good_signal)
    assert not result.allowed


def test_slo_breach_blocks_but_keeps_prior_version(mesh, good_signal, good_records):
    mesh.publish_version("orders.daily", _schema(mesh), good_records, good_signal)
    stale = HealthSignal("orders.daily", newest_data_age_hours=999,
                         completeness=0.99, availability=0.999)
    result = mesh.publish_version("orders.daily", _schema(mesh), good_records, stale)
    assert not result.allowed and any("freshness" in v for v in result.violations)
    assert mesh.registry.get_product("orders.daily").published_version == "1.0.0"
