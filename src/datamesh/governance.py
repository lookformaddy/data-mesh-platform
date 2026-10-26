"""Federated governance: global policy packs + domain-local policies.

Conflict rule (documented, deterministic, logged): when a global and a
domain policy both match a product and disagree, the global policy
wins. A domain policy can only narrow, never widen, a global deny.
Evaluation returns the winning effect plus every conflict observed,
so governance decisions are auditable, not just enforced.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .errors import AlreadyExistsError
from .models import AuditEntry, DataProduct, Policy, PolicyEffect


@dataclass
class PolicyDecision:
    effect: PolicyEffect
    winning_policy: Policy | None
    conflicts: list[str] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return self.effect == PolicyEffect.ALLOW


class GovernanceEngine:
    def __init__(self) -> None:
        self.policies: dict[str, Policy] = {}
        self.audit: list[AuditEntry] = []

    def add_policy(self, policy: Policy) -> Policy:
        if policy.policy_id in self.policies:
            raise AlreadyExistsError(f"policy {policy.policy_id} already exists")
        self.policies[policy.policy_id] = policy
        self.audit.append(AuditEntry("policy-added",
                                     f"{policy.policy_id} scope={policy.scope} "
                                     f"effect={policy.effect.value}", "governance"))
        return policy

    def applicable(self, product: DataProduct) -> list[Policy]:
        out = []
        for policy in self.policies.values():
            if policy.is_global or policy.scope == product.domain_id:
                if policy.matches(product):
                    out.append(policy)
        return out

    def evaluate(self, product: DataProduct) -> PolicyDecision:
        """Default-allow when nothing matches; global deny beats all;
        otherwise any deny beats allow; conflicts are logged."""
        matching = self.applicable(product)
        global_pols = [p for p in matching if p.is_global]
        domain_pols = [p for p in matching if not p.is_global]
        conflicts: list[str] = []
        global_deny = next((p for p in global_pols if p.effect == PolicyEffect.DENY), None)
        domain_allow = next((p for p in domain_pols if p.effect == PolicyEffect.ALLOW), None)
        if global_deny is not None and domain_allow is not None:
            msg = (f"conflict on {product.product_id}: global deny "
                   f"{global_deny.policy_id} overrides domain allow "
                   f"{domain_allow.policy_id}; global wins")
            conflicts.append(msg)
            self.audit.append(AuditEntry("policy-conflict", msg, "governance"))
            return PolicyDecision(PolicyEffect.DENY, global_deny, conflicts)
        if global_deny is not None:
            return PolicyDecision(PolicyEffect.DENY, global_deny, conflicts)
        domain_deny = next((p for p in domain_pols if p.effect == PolicyEffect.DENY), None)
        if domain_deny is not None:
            return PolicyDecision(PolicyEffect.DENY, domain_deny, conflicts)
        winner = global_pols[0] if global_pols else (domain_pols[0] if domain_pols else None)
        effect = winner.effect if winner else PolicyEffect.ALLOW
        return PolicyDecision(effect, winner, conflicts)
