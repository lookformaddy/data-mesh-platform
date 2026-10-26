"""Optional FastAPI service. Importing this module requires FastAPI;
callers that lack it should not import it (tests auto-skip instead).
Pure read/decision surface over a MeshPlatform instance.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .platform import MeshPlatform


def create_app(platform: MeshPlatform | None = None) -> FastAPI:
    platform = platform or MeshPlatform()
    app = FastAPI(title="data-mesh-platform")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/products")
    def list_products(query: str = "", tag: str | None = None):
        hits = platform.search(query=query, tag=tag)
        return [{"product_id": h.product.product_id, "name": h.product.name,
                 "domain_id": h.product.domain_id, "score": h.score,
                 "reasons": h.reasons} for h in hits]

    @app.get("/products/{product_id}")
    def get_product(product_id: str):
        try:
            p = platform.registry.get_product(product_id)
        except Exception as exc:
            raise HTTPException(404, str(exc)) from exc
        return {"product_id": p.product_id, "domain_id": p.domain_id,
                "name": p.name, "owner": p.owner, "tags": p.tags,
                "sensitivity": p.sensitivity.value,
                "published_version": p.published_version,
                "ports": [{"port_id": x.port_id, "kind": x.kind.value,
                           "format": x.format} for x in p.ports]}

    @app.get("/products/{product_id}/health")
    def product_health(product_id: str):
        try:
            score = platform.health(product_id)
        except Exception as exc:
            raise HTTPException(404, str(exc)) from exc
        return {"product_id": score.product_id, "score": score.score,
                "grade": score.grade, "components": score.components,
                "slo_breaches": score.slo_breaches}

    @app.get("/products/{product_id}/impact")
    def product_impact(product_id: str):
        try:
            return platform.impact_report(product_id)
        except Exception as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.get("/products/{product_id}/governance")
    def product_governance(product_id: str):
        try:
            d = platform.governance_decision(product_id)
        except Exception as exc:
            raise HTTPException(404, str(exc)) from exc
        return {"allowed": d.allowed,
                "winning_policy": d.winning_policy.policy_id if d.winning_policy else None,
                "conflicts": d.conflicts}

    return app
