"""Domain errors for the data mesh platform.

All errors are plain ValueError/LookupError subclasses so callers can
handle them without importing a framework. Fail-closed: anything the
platform cannot resolve is an error, never a silent default.
"""


class MeshError(Exception):
    """Base class for all data-mesh errors."""


class AlreadyExistsError(MeshError):
    """A domain, product, version, or policy with this key already exists."""


class NotFoundError(MeshError):
    """A referenced domain, product, version, or request does not exist."""


class ValidationError(MeshError):
    """A schema, SLO, or publish-gate check failed (details in the message)."""


class PolicyConflictError(MeshError):
    """Raised only when a caller asks for strict conflict rejection."""


class AccessDeniedError(MeshError):
    """An access decision was deny, or no active grant covers the request."""
