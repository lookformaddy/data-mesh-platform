"""Access workflow: approve/deny, expiry, revocation, audit."""

from datetime import timedelta

import pytest

from datamesh.errors import AccessDeniedError
from datamesh.models import utcnow


def test_approve_creates_active_grant(mesh):
    req = mesh.access.request_access("orders.daily", "analyst-1", "report")
    grant = mesh.access.decide(req.request_id, "team-orders", True, "ok")
    assert mesh.access.check_access("orders.daily", "analyst-1")
    assert grant.is_active()
    assert any(e.kind == "access-granted" for e in mesh.access.audit)


def test_deny_creates_no_grant(mesh):
    req = mesh.access.request_access("orders.daily", "analyst-1", "report")
    result = mesh.access.decide(req.request_id, "team-orders", False, "no need")
    assert result.status.value == "denied"
    assert not mesh.access.check_access("orders.daily", "analyst-1")


def test_expired_grant_is_inactive(mesh):
    req = mesh.access.request_access("orders.daily", "analyst-1", "report")
    grant = mesh.access.decide(req.request_id, "team-orders", True, grant_days=0)
    # A 0-day grant expires immediately; a future check is inactive too.
    assert not mesh.access.check_access("orders.daily", "analyst-1",
                                        now=utcnow() + timedelta(days=1))


def test_revoke_kills_grant(mesh):
    req = mesh.access.request_access("orders.daily", "analyst-1", "report")
    grant = mesh.access.decide(req.request_id, "team-orders", True)
    mesh.access.revoke(grant.grant_id, "team-orders")
    assert not mesh.access.check_access("orders.daily", "analyst-1")
    with pytest.raises(AccessDeniedError):
        mesh.access.require_access("orders.daily", "analyst-1")


def test_double_decision_rejected(mesh):
    req = mesh.access.request_access("orders.daily", "analyst-1", "report")
    mesh.access.decide(req.request_id, "team-orders", True)
    with pytest.raises(ValueError):
        mesh.access.decide(req.request_id, "team-orders", True)
