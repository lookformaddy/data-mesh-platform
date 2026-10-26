"""Domain registry: domains own data products; products carry
versioned schemas, SLOs, and ports. The single source of truth for
what exists in the mesh. No duplicates, no orphan products."""

from __future__ import annotations

from .errors import AlreadyExistsError, NotFoundError
from .models import DataProduct, Domain, Port, VersionedSchema


class MeshRegistry:
    def __init__(self) -> None:
        self.domains: dict[str, Domain] = {}
        self.products: dict[str, DataProduct] = {}

    # -- domains -----------------------------------------------------
    def register_domain(self, domain: Domain) -> Domain:
        if domain.domain_id in self.domains:
            raise AlreadyExistsError(f"domain {domain.domain_id} already exists")
        self.domains[domain.domain_id] = domain
        return domain

    def get_domain(self, domain_id: str) -> Domain:
        try:
            return self.domains[domain_id]
        except KeyError:
            raise NotFoundError(f"domain {domain_id} not found") from None

    # -- products ----------------------------------------------------
    def register_product(self, product: DataProduct) -> DataProduct:
        if product.product_id in self.products:
            raise AlreadyExistsError(f"product {product.product_id} already exists")
        self.get_domain(product.domain_id)  # orphan check
        self.products[product.product_id] = product
        return product

    def get_product(self, product_id: str) -> DataProduct:
        try:
            return self.products[product_id]
        except KeyError:
            raise NotFoundError(f"product {product_id} not found") from None

    def products_in_domain(self, domain_id: str) -> list[DataProduct]:
        self.get_domain(domain_id)
        return [p for p in self.products.values() if p.domain_id == domain_id]

    def add_schema(self, product_id: str, schema: VersionedSchema) -> VersionedSchema:
        product = self.get_product(product_id)
        if schema.version in product.schemas:
            raise AlreadyExistsError(
                f"schema {schema.version} already exists for {product_id}")
        product.add_schema(schema)
        return schema

    def add_port(self, product_id: str, port: Port) -> Port:
        product = self.get_product(product_id)
        if any(p.port_id == port.port_id for p in product.ports):
            raise AlreadyExistsError(f"port {port.port_id} already exists")
        product.ports.append(port)
        return port

    def all_products(self) -> list[DataProduct]:
        return sorted(self.products.values(), key=lambda p: p.product_id)
