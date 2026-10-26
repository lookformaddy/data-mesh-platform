"""Shared fixtures: a small deterministic mesh used by every suite."""

import pytest

from datamesh.models import (DataProduct, Domain, HealthSignal, Port,
                            PortKind, SchemaField, Sensitivity, SLO,
                            VersionedSchema)
from datamesh.platform import MeshPlatform


def _product(pid, domain, name, tags, sensitivity=Sensitivity.INTERNAL,
             slo=None):
    return DataProduct(pid, domain, name, f"{name} (synthetic)",
                       owner=f"team-{domain}", tags=tags,
                       sensitivity=sensitivity, slo=slo or SLO())


@pytest.fixture
def mesh():
    m = MeshPlatform()
    m.registry.register_domain(Domain("orders", "Orders", "team-orders"))
    m.registry.register_domain(Domain("inventory", "Inventory", "team-inventory"))
    m.registry.register_product(_product("orders.daily", "orders", "Daily Orders",
                                          ["orders", "sales"]))
    m.registry.register_product(_product("inventory.stock", "inventory",
                                          "Stock Levels", ["inventory"]))
    m.registry.add_schema("orders.daily", VersionedSchema("1.0.0", [
        SchemaField("order_id", "string"), SchemaField("order_date", "date"),
        SchemaField("amount", "number"), SchemaField("customer_id", "string"),
    ]))
    m.registry.add_port("orders.daily", Port("orders-table", PortKind.OUTPUT, "table"))
    m.lineage.add_edge("inventory.stock", "orders.daily")
    return m


@pytest.fixture
def good_signal():
    return HealthSignal("orders.daily", newest_data_age_hours=6,
                        completeness=0.99, availability=0.999, quality_score=0.98)


@pytest.fixture
def good_records():
    return [{"order_id": "O-1", "order_date": "2026-10-25", "amount": 10.0,
             "customer_id": "C-1"}]
