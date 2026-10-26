"""Access request workflow: request -> approve/deny, with an
append-only audit trail and expiring grants.

A grant is active only while unrevoked and before its expiry. Denied
requests never create grants; expired grants never become active
again. Every transition is appended to the audit log.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .errors import AccessDeniedError, NotFoundError
from .models import AccessRequest, AuditEntry, Grant, RequestStatus, utcnow


class AccessStore:
    def __init__(self) -> None:
        self.requests: dict[str, AccessRequest] = {}
        self.grants: dict[str, Grant] = {}
        self.audit: list[AuditEntry] = []
        self._seq = 0

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-{self._seq:04d}"

    def request_access(self, product_id: str, requester: str,
                       purpose: str) -> AccessRequest:
        req = AccessRequest(request_id=self._next_id("req"), product_id=product_id,
                            requester=requester, purpose=purpose)
        self.requests[req.request_id] = req
        self.audit.append(AuditEntry("access-requested",
                                     f"{req.request_id} {requester} -> {product_id}: {purpose}",
                                     requester))
        return req

    def decide(self, request_id: str, approver: str, approve: bool,
               reason: str = "", grant_days: int = 30) -> AccessRequest | Grant:
        try:
            req = self.requests[request_id]
        except KeyError:
            raise NotFoundError(f"request {request_id} not found") from None
        if req.status != RequestStatus.PENDING:
            raise ValueError(f"request {request_id} already decided: {req.status.value}")
        req.decided_by = approver
        req.decision_reason = reason
        req.decided_at = utcnow()
        if not approve:
            req.status = RequestStatus.DENIED
            self.audit.append(AuditEntry("access-denied",
                                         f"{request_id} denied by {approver}: {reason}", approver))
            return req
        req.status = RequestStatus.APPROVED
        grant = Grant(grant_id=self._next_id("grant"), request_id=request_id,
                      product_id=req.product_id, grantee=req.requester,
                      granted_by=approver,
                      expires_at=utcnow() + timedelta(days=grant_days))
        self.grants[grant.grant_id] = grant
        self.audit.append(AuditEntry("access-granted",
                                     f"{grant.grant_id} {req.requester} -> {req.product_id} "
                                     f"until {grant.expires_at.isoformat()}", approver))
        return grant

    def revoke(self, grant_id: str, actor: str) -> Grant:
        try:
            grant = self.grants[grant_id]
        except KeyError:
            raise NotFoundError(f"grant {grant_id} not found") from None
        grant.revoked = True
        self.audit.append(AuditEntry("access-revoked", grant_id, actor))
        return grant

    def check_access(self, product_id: str, user: str,
                     now: datetime | None = None) -> bool:
        now = now or utcnow()
        return any(g.product_id == product_id and g.grantee == user
                   and g.is_active(now) for g in self.grants.values())

    def require_access(self, product_id: str, user: str,
                       now: datetime | None = None) -> None:
        if not self.check_access(product_id, user, now):
            raise AccessDeniedError(f"{user} has no active grant for {product_id}")
