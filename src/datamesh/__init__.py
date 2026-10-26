"""data-mesh-platform: a federated data mesh platform.

Domains own data products; global policy packs + domain policies
govern them (global wins on conflict); consumers discover products,
request expiring access, and read health + lineage — and a version
publishes only if it passes its schema and SLO gate.
"""

from .platform import MeshPlatform

__all__ = ["MeshPlatform"]
__version__ = "1.0.0"
