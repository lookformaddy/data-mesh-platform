"""Discovery ranking: name > tag > description, owner boost, filters."""

from datamesh.discovery import search


def test_name_match_ranks_first(mesh):
    hits = mesh.search("orders")
    assert hits[0].product.product_id == "orders.daily"
    assert "name match" in hits[0].reasons


def test_tag_filter_and_search(mesh):
    assert [h.product.product_id for h in mesh.search(tag="inventory")] == ["inventory.stock"]
    assert mesh.search("nonexistent-term") == []


def test_owner_boost_beats_plain_description_match(mesh):
    hits = mesh.search("synthetic", owner="team-orders")
    assert hits[0].product.product_id == "orders.daily"
    assert "owner match" in hits[0].reasons


def test_empty_query_lists_catalog_sorted(mesh):
    ids = [h.product.product_id for h in mesh.search("")]
    assert ids == sorted(ids) and len(ids) == 2


def test_deterministic_tie_break(mesh):
    first = [h.product.product_id for h in mesh.search("synthetic")]
    second = [h.product.product_id for h in mesh.search("synthetic")]
    assert first == second
