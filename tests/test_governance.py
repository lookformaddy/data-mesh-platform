"""Federated governance: global-wins conflict resolution, logging."""

from datamesh.models import Policy, PolicyEffect, Sensitivity


def test_default_allow_with_no_policies(mesh):
    decision = mesh.governance_decision("orders.daily")
    assert decision.allowed and decision.winning_policy is None


def test_global_deny_overrides_domain_allow(mesh):
    product = mesh.registry.get_product("orders.daily")
    mesh.governance.add_policy(Policy("g-deny", "Global deny", PolicyEffect.DENY,
                                      "global"))
    mesh.governance.add_policy(Policy("d-allow", "Domain allow", PolicyEffect.ALLOW,
                                      "orders"))
    decision = mesh.governance_decision("orders.daily")
    assert not decision.allowed
    assert decision.winning_policy.policy_id == "g-deny"
    assert decision.conflicts, "conflict must be reported, not swallowed"
    assert any("global wins" in c for c in decision.conflicts)
    assert any(e.kind == "policy-conflict" for e in mesh.governance.audit)


def test_domain_deny_blocks_without_global(mesh):
    mesh.governance.add_policy(Policy("d-deny", "Domain deny", PolicyEffect.DENY,
                                      "orders"))
    assert not mesh.governance_decision("orders.daily").allowed


def test_sensitivity_scoped_policy_only_matches_its_class(mesh):
    from datamesh.models import DataProduct
    mesh.registry.register_product(DataProduct(
        "orders.secret", "orders", "Secret Orders", sensitivity=Sensitivity.RESTRICTED))
    mesh.governance.add_policy(Policy("g-restr", "Deny restricted", PolicyEffect.DENY,
                                      "global",
                                      applies_to_sensitivity=frozenset({Sensitivity.RESTRICTED})))
    assert not mesh.governance_decision("orders.secret").allowed
    assert mesh.governance_decision("orders.daily").allowed


def test_governance_deny_blocks_publish(mesh, good_signal, good_records):
    mesh.governance.add_policy(Policy("g-deny", "Deny", PolicyEffect.DENY, "global"))
    schema = mesh.registry.get_product("orders.daily").schemas["1.0.0"]
    result = mesh.publish_version("orders.daily", schema, good_records, good_signal)
    assert not result.allowed
    assert mesh.registry.get_product("orders.daily").published_version is None
