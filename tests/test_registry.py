"""Domain/product registration, schemas, ports, and error paths."""

import pytest

from datamesh.errors import AlreadyExistsError, NotFoundError
from datamesh.models import DataProduct, Domain, SchemaField, VersionedSchema


def test_register_domain_and_product(mesh):
    assert mesh.registry.get_domain("orders").name == "Orders"
    assert mesh.registry.get_product("orders.daily").owner == "team-orders"
    assert [p.product_id for p in mesh.registry.products_in_domain("orders")] == ["orders.daily"]


def test_duplicate_domain_and_product_rejected(mesh):
    with pytest.raises(AlreadyExistsError):
        mesh.registry.register_domain(Domain("orders", "Orders", "team-orders"))
    with pytest.raises(AlreadyExistsError):
        mesh.registry.register_product(DataProduct("orders.daily", "orders", "X"))


def test_orphan_product_rejected(mesh):
    with pytest.raises(NotFoundError):
        mesh.registry.register_product(DataProduct("ghost.x", "no-such-domain", "X"))


def test_unknown_product_lookup(mesh):
    with pytest.raises(NotFoundError):
        mesh.registry.get_product("nope")


def test_duplicate_schema_and_port_rejected(mesh):
    with pytest.raises(AlreadyExistsError):
        mesh.registry.add_schema("orders.daily", VersionedSchema("1.0.0", []))
    from datamesh.models import Port, PortKind
    with pytest.raises(AlreadyExistsError):
        mesh.registry.add_port("orders.daily", Port("orders-table", PortKind.OUTPUT))


def test_schema_helpers():
    schema = VersionedSchema("2.0.0", [SchemaField("a", "string"),
                                       SchemaField("b", "integer", required=False)])
    assert schema.required_names() == {"a"}
    assert schema.field_names() == {"a", "b"}
