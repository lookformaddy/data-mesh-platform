"""MeshPlatform: the facade composing registry, governance, discovery,
access, health, lineage, and the publish gate.

Publish flow (the one flow that touches everything): the caller
supplies a version schema, sample records, and observed signals; the
gate must pass AND global governance must allow, or nothing ships and
published_version is untouched.
"""

from __future__ import annotations

from .access import AccessStore
from .discovery import SearchHit, search
from .governance import GovernanceEngine, PolicyDecision
from .health import HealthScore, score_health
from .lineage import LineageGraph
from .models import DataProduct, HealthSignal, VersionedSchema
from .publish import GateResult, evaluate_publish
from .registry import MeshRegistry


class MeshPlatform:
    def __init__(self) -> None:
        self.registry = MeshRegistry()
        self.governance = GovernanceEngine()
        self.access = AccessStore()
        self.lineage = LineageGraph()
        self.signals: dict[str, HealthSignal] = {}

    # -- discovery / health ------------------------------------------
    def search(self, query: str = "", owner: str | None = None,
               tag: str | None = None, limit: int = 20) -> list[SearchHit]:
        return search(self.registry.all_products(), query, owner, tag, limit)

    def record_signal(self, signal: HealthSignal) -> HealthSignal:
        self.registry.get_product(signal.product_id)
        self.signals[signal.product_id] = signal
        return signal

    def health(self, product_id: str) -> HealthScore:
        product = self.registry.get_product(product_id)
        signal = self.signals.get(product_id)
        if signal is None:
            raise ValueError(f"no health signal recorded for {product_id}")
        return score_health(signal, product.slo)

    def governance_decision(self, product_id: str) -> PolicyDecision:
        return self.governance.evaluate(self.registry.get_product(product_id))

    # -- publish ------------------------------------------------------
    def publish_version(self, product_id: str, schema: VersionedSchema,
                        records: list[dict], signal: HealthSignal) -> GateResult:
        product = self.registry.get_product(product_id)
        decision = self.governance.evaluate(product)
        result = evaluate_publish(schema, records, signal, product.slo)
        if not decision.allowed:
            result.violations.append(
                f"governance: denied by policy "
                f"{decision.winning_policy.policy_id if decision.winning_policy else '?'}")
            result.allowed = False
        if result.allowed:
            if schema.version not in product.schemas:
                product.add_schema(schema)
            product.published_version = schema.version
            self.signals[product_id] = signal
        return result

    def impact_report(self, product_id: str) -> dict:
        self.registry.get_product(product_id)
        impact = self.lineage.impact(product_id)
        return {"product_id": product_id, "upstream": impact["upstream"],
                "downstream": impact["downstream"],
                "has_cycle": self.lineage.has_cycle()}
