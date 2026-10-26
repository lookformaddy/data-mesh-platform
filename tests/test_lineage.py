"""Lineage: upstream/downstream BFS with hops, cycles, impact report."""

import pytest

from datamesh.errors import AlreadyExistsError


def test_downstream_and_upstream_with_hops(mesh):
    mesh.lineage.add_edge("orders.daily", "marketing.campaigns")
    assert mesh.lineage.downstream("inventory.stock") == {
        "orders.daily": 1, "marketing.campaigns": 2}
    assert mesh.lineage.upstream("marketing.campaigns") == {
        "orders.daily": 1, "inventory.stock": 2}


def test_self_edge_and_duplicate_rejected(mesh):
    with pytest.raises(ValueError):
        mesh.lineage.add_edge("orders.daily", "orders.daily")
    with pytest.raises(AlreadyExistsError):
        mesh.lineage.add_edge("inventory.stock", "orders.daily")


def test_cycle_detection(mesh):
    assert not mesh.lineage.has_cycle()
    mesh.lineage.add_edge("orders.daily", "inventory.stock")
    assert mesh.lineage.has_cycle()


def test_impact_report(mesh):
    report = mesh.impact_report("inventory.stock")
    assert report["downstream"] == {"orders.daily": 1}
    assert report["upstream"] == {}
    assert report["has_cycle"] is False
