import pytest

from app.data.paths import BuildNotPublishedError
from app.services.search import search


def test_search_raises_when_unpublished(tmp_path):
    with pytest.raises(BuildNotPublishedError):
        search(tmp_path / "processed", "Sirius")


def test_search_exact_match(search_dataset):
    hits = search(search_dataset, "Sirius")
    assert len(hits) == 1
    hit = hits[0]
    assert hit.star_id == "iau:sirius"
    assert hit.display_name == "Sirius"
    assert hit.matched_alias == "Sirius"
    assert hit.catalogue == "IAU"
    assert hit.is_exact is True
    assert hit.ra_deg == 101.287
    assert hit.dec_deg == -16.716


def test_search_prefix_ranking(search_dataset):
    hits = search(search_dataset, "Sir")
    assert [h.star_id for h in hits] == ["iau:sirius", "iau:sirona"]
    assert all(h.is_exact is False for h in hits)


def test_search_empty_key_returns_empty(search_dataset):
    assert search(search_dataset, "!!!") == []
