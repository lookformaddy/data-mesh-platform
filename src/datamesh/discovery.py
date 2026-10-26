"""Discovery across the mesh catalog.

Deterministic ranking, no ML: exact name match > tag match > keyword
in description > owner match. Ties break by product_id so results are
stable across runs. Empty query returns everything, sorted by id.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import DataProduct


@dataclass
class SearchHit:
    product: DataProduct
    score: float
    reasons: list[str]


def _tokens(text: str) -> set[str]:
    return {t for t in text.lower().replace("_", " ").replace("-", " ").split() if t}


def score_product(product: DataProduct, query: str,
                  owner: str | None = None) -> SearchHit:
    reasons: list[str] = []
    score = 0.0
    qtokens = _tokens(query)
    if not qtokens:
        return SearchHit(product, 0.0, ["catalog listing"])
    name_tokens = _tokens(product.name)
    desc_tokens = _tokens(product.description)
    tags = {t.lower() for t in product.tags}
    if qtokens & name_tokens:
        score += 10.0 * len(qtokens & name_tokens)
        reasons.append("name match")
    if qtokens & tags:
        score += 6.0 * len(qtokens & tags)
        reasons.append("tag match")
    if qtokens & desc_tokens:
        score += 2.0 * len(qtokens & desc_tokens)
        reasons.append("description match")
    if owner and product.owner == owner:
        score += 5.0
        reasons.append("owner match")
    return SearchHit(product, score, reasons)


def search(products: list[DataProduct], query: str = "",
           owner: str | None = None, tag: str | None = None,
           limit: int = 20) -> list[SearchHit]:
    pool = products
    if tag:
        pool = [p for p in pool if tag.lower() in {t.lower() for t in p.tags}]
    if owner and not query:
        pool = [p for p in pool if p.owner == owner]
    hits = [score_product(p, query, owner) for p in pool]
    if query.strip():
        hits = [h for h in hits if h.score > 0]
    hits.sort(key=lambda h: (-h.score, h.product.product_id))
    return hits[:limit]
