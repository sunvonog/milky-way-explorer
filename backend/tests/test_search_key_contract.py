import pytest

from app.core.names import search_key


@pytest.mark.parametrize(
    "a,b",
    [
        ("Rosaliadecastro", "Rosalíadecastro"),  # real exoplanet-host match
        ("ϵ Her", "ε Her"),  # lunate epsilon, NFKC-dependent
        ("Uñallamacha", "Unallamacha"),
        ("BATSŨ̀", "Batsu"),
    ],
)
def test_search_key_folds_equivalent_forms(a, b):
    assert search_key(a) == search_key(b)
