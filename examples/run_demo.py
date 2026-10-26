"""End-to-end demo: build a small mesh (orders + inventory + marketing
domains, all synthetic), publish products through the gate, wire
lineage, run governance, discovery, access, and health — and print it.

Run:  python examples/run_demo.py        (from the repo root)
   or: python -m datamesh demo
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datamesh.governance import PolicyDecision  # noqa: E402
from datamesh.models import (DataProduct, Domain, HealthSignal, Policy,  # noqa: E402
                             PolicyEffect, Port, PortKind, SchemaField,
                             Sensitivity, SLO, VersionedSchema)
from datamesh.platform import MeshPlatform  # noqa: E402


def build_mesh() -> MeshPlatform:
    mesh = MeshPlatform()
    mesh.registry.register_domain(Domain("orders", "Orders", "team-orders",
                                         "Order and fulfilment data"))
    mesh.registry.register_domain(Domain("inventory", "Inventory", "team-inventory",
                                         "Stock and warehouse data"))
    mesh.registry.register_domain(Domain("marketing", "Marketing", "team-marketing",
                                         "Campaign and channel data"))

    orders = DataProduct("orders.daily", "orders", "Daily Orders",
                         "One row per order, refreshed nightly",
                         owner="team-orders", tags=["orders", "sales"],
                         sensitivity=Sensitivity.INTERNAL,
                         slo=SLO(freshness_hours=24, completeness_min=0.95,
                                 availability_min=0.99))
    orders.add_schema(VersionedSchema("1.0.0", [
        SchemaField("order_id", "string"), SchemaField("order_date", "date"),
        SchemaField("amount", "number"), SchemaField("customer_id", "string"),
    ]))
    orders.ports.append(Port("orders-table", PortKind.OUTPUT, "table"))
    mesh.registry.register_product(orders)

    stock = DataProduct("inventory.stock", "inventory", "Stock Levels",
                        "Current stock per warehouse and SKU",
                        owner="team-inventory", tags=["inventory", "stock"],
                        sensitivity=Sensitivity.INTERNAL)
    stock.add_schema(VersionedSchema("1.0.0", [
        SchemaField("sku", "string"), SchemaField("warehouse", "string"),
        SchemaField("quantity", "integer"),
    ]))
    mesh.registry.register_product(stock)

    # Cross-domain lineage: stock levels feed the daily orders product.
    mesh.lineage.add_edge("inventory.stock", "orders.daily",
                          "stock snapshot joined to orders")
    # Global policy pack: restricted data is never auto-approved.
    mesh.governance.add_policy(Policy("global-restricted-deny", "Deny restricted",
                                      PolicyEffect.DENY, "global",
                                      applies_to_sensitivity=frozenset(
                                          {Sensitivity.RESTRICTED})))
    return mesh


def main() -> None:
    mesh = build_mesh()
    schema = mesh.registry.get_product("orders.daily").schemas["1.0.0"]
    records = [{"order_id": "O-1", "order_date": "2026-10-25", "amount": 49.99,
                "customer_id": "C-1"}]
    signal = HealthSignal("orders.daily", newest_data_age_hours=6,
                          completeness=0.99, availability=0.999, quality_score=0.98)
    result = mesh.publish_version("orders.daily", schema, records, signal)
    print(f"publish orders.daily v1.0.0: allowed={result.allowed} "
          f"violations={result.violations}")

    bad = mesh.publish_version("orders.daily", schema,
                               [{"order_id": "O-2", "amount": "not-a-number"}],
                               signal)
    print(f"publish with bad record: allowed={bad.allowed} violations={bad.violations}")

    for hit in mesh.search("orders"):
        print(f"discovery: {hit.product.product_id} score={hit.score} {hit.reasons}")
    req = mesh.access.request_access("orders.daily", "analyst-1", "weekly sales report")
    grant = mesh.access.decide(req.request_id, "team-orders", True, "approved")
    print(f"access: request {req.request_id} -> grant {grant.grant_id} "
          f"active={grant.is_active()}")
    print(f"health: {mesh.health('orders.daily')}")
    print(f"impact of inventory.stock: {mesh.impact_report('inventory.stock')}")


if __name__ == "__main__":
    main()
