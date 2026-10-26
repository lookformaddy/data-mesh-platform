"""Core value objects for the data mesh platform.

Pure stdlib dataclasses. No employer data, no external identifiers:
every example domain below is generic (orders, inventory, marketing).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class PortKind(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass(frozen=True)
class Domain:
    """A business domain that owns data products (federated ownership)."""

    domain_id: str
    name: str
    owner: str  # team / owner id, e.g. "team-orders"
    description: str = ""
    contact: str = ""


@dataclass(frozen=True)
class SchemaField:
    name: str
    type: str  # "string" | "integer" | "number" | "boolean" | "date"
    required: bool = True
    description: str = ""


@dataclass
class VersionedSchema:
    version: str  # e.g. "1.0.0"
    fields: list[SchemaField] = field(default_factory=list)

    def field_names(self) -> set[str]:
        return {f.name for f in self.fields}

    def required_names(self) -> set[str]:
        return {f.name for f in self.fields if f.required}


@dataclass(frozen=True)
class SLO:
    """Service-level objectives a data product promises its consumers."""

    freshness_hours: float = 24.0  # max age of newest data
    completeness_min: float = 0.95  # min fraction of non-null required fields
    availability_min: float = 0.99  # min uptime fraction

    def __post_init__(self) -> None:
        if self.freshness_hours <= 0:
            raise ValueError("freshness_hours must be positive")
        for name, value in (("completeness_min", self.completeness_min),
                            ("availability_min", self.availability_min)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")


@dataclass(frozen=True)
class Port:
    """An input or output port of a data product."""

    port_id: str
    kind: PortKind
    format: str = "table"  # table | stream | api | file
    description: str = ""


@dataclass
class DataProduct:
    """A versioned, owned data product published by one domain."""

    product_id: str
    domain_id: str
    name: str
    description: str = ""
    owner: str = ""
    tags: list[str] = field(default_factory=list)
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    slo: SLO = field(default_factory=SLO)
    schemas: dict[str, VersionedSchema] = field(default_factory=dict)
    ports: list[Port] = field(default_factory=list)
    published_version: str | None = None
    created_at: datetime = field(default_factory=utcnow)

    def add_schema(self, schema: VersionedSchema) -> None:
        self.schemas[schema.version] = schema

    def latest_schema(self) -> VersionedSchema | None:
        if not self.schemas:
            return None
        return self.schemas[sorted(self.schemas)[-1]]


@dataclass(frozen=True)
class Policy:
    """A governance rule. Global policies apply mesh-wide; domain
    policies apply only inside one domain. On conflict, global wins."""

    policy_id: str
    name: str
    effect: PolicyEffect
    scope: str  # "global" or a domain_id
    applies_to_sensitivity: frozenset[Sensitivity] = frozenset()
    applies_to_tags: frozenset[str] = frozenset()
    description: str = ""

    @property
    def is_global(self) -> bool:
        return self.scope == "global"

    def matches(self, product: DataProduct) -> bool:
        if self.applies_to_sensitivity and product.sensitivity not in self.applies_to_sensitivity:
            return False
        if self.applies_to_tags and not (self.applies_to_tags & set(product.tags)):
            return False
        return True


@dataclass
class AccessRequest:
    request_id: str
    product_id: str
    requester: str
    purpose: str
    status: RequestStatus = RequestStatus.PENDING
    decided_by: str = ""
    decision_reason: str = ""
    created_at: datetime = field(default_factory=utcnow)
    decided_at: datetime | None = None


@dataclass
class Grant:
    grant_id: str
    request_id: str
    product_id: str
    grantee: str
    granted_by: str
    expires_at: datetime
    revoked: bool = False
    created_at: datetime = field(default_factory=utcnow)

    def is_active(self, now: datetime | None = None) -> bool:
        now = now or utcnow()
        return not self.revoked and now < self.expires_at


@dataclass(frozen=True)
class LineageEdge:
    upstream_product_id: str
    downstream_product_id: str
    description: str = ""


@dataclass
class HealthSignal:
    """Observed signals feeding a product's health score."""

    product_id: str
    newest_data_age_hours: float
    completeness: float  # 0..1
    availability: float  # 0..1
    quality_score: float = 1.0  # 0..1, from quality checks
    recorded_at: datetime = field(default_factory=utcnow)


@dataclass
class AuditEntry:
    kind: str
    detail: str
    actor: str = ""
    at: datetime = field(default_factory=utcnow)

    def __str__(self) -> str:
        return f"{self.at.isoformat()} [{self.kind}] {self.detail}"
